"""Deterministic recovery tests for the real serial reader, parser, and consumer."""

import struct
import sys
import types
import unittest
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from coinft_demo import DemoSource, RelativeProjector, SATURATION


def wire(value, count=1):
    body = b"\x00\x00" + struct.pack("<12H", *([value] * 12))
    return body * count + b"\x00\x00"


@dataclass
class Read:
    delay: float
    data: object
    stop: bool = False


class Clock:
    def __init__(self):
        self.now = 100.0
        self.monotonic_calls = 0
        self.cancel_monotonic_index = None
        self.cancel = None

    def advance(self, seconds):
        self.now += seconds

    def monotonic(self):
        self.monotonic_calls += 1
        if self.cancel_monotonic_index == self.monotonic_calls:
            self.cancel()
        return self.now

    def wall(self):
        return 1_800_000_000.0 + self.now


class FakeEvent:
    def __init__(self, clock, cancel_waits=(), cancel_wait_index=None, wait_actions=()):
        self.clock = clock
        self.cancel_waits = list(cancel_waits)
        self.cancel_wait_index = cancel_wait_index
        self.wait_actions = list(wait_actions)
        self.waits = []
        self.set_value = False

    def is_set(self):
        return self.set_value

    def set(self):
        self.set_value = True

    def wait(self, timeout=None):
        self.waits.append((self.clock.now, timeout))
        self.clock.advance(timeout or 0)
        if self.wait_actions and abs(timeout - self.wait_actions[0][0]) < 1e-9:
            _, action = self.wait_actions.pop(0)
            action()
        if self.cancel_waits and abs(timeout - self.cancel_waits[0]) < 1e-9:
            self.cancel_waits.pop(0)
            self.set()
        if self.cancel_wait_index == len(self.waits):
            self.set()
        return self.is_set()


class SerialHarness:
    def __init__(self, source, sessions, *, cancel_waits=(), cancel_wait_index=None,
                 cancel_monotonic_index=None, wait_actions=(), max_reads=1000):
        self.source = source
        self.clock = Clock()
        self.event = FakeEvent(self.clock, cancel_waits, cancel_wait_index, wait_actions)
        self.clock.cancel_monotonic_index = cancel_monotonic_index
        self.clock.cancel = self.event.set
        self.source.stop_event = self.event
        self.sessions = iter(sessions)
        self.max_reads = max_reads
        self.read_count = 0
        self.opens = []
        self.commands = []
        self.resets = []
        self.closes = []
        self.read_snapshots = []

        harness = self

        class FakeSerial:
            def __init__(self, port, baud, timeout):
                if port != "TEST_ONLY" or baud != 115200 or timeout != 0.1:
                    raise AssertionError((port, baud, timeout))
                self.session = next(harness.sessions)
                harness.opens.append((harness.clock.now, port))
                if isinstance(self.session, Exception):
                    raise self.session
                self.reads = iter(self.session.get("reads", ()))
                self.write_failures = list(self.session.get("write_failures", ()))
                self.closed = False

            def write(self, command):
                harness.commands.append((harness.clock.now, command, id(self)))
                if self.write_failures and command == self.write_failures[0][0]:
                    _, error = self.write_failures.pop(0)
                    raise error

            def reset_input_buffer(self):
                harness.resets.append((harness.clock.now, id(self)))

            def read(self, size):
                if size != 4096:
                    raise AssertionError(size)
                harness.read_count += 1
                harness.read_snapshots.append(harness.source.snapshot())
                if harness.read_count > harness.max_reads:
                    harness.event.set()
                    raise AssertionError("serial recovery loop exceeded bounded reads")
                try:
                    item = next(self.reads)
                except StopIteration:
                    harness.event.set()
                    return b""
                harness.clock.advance(item.delay)
                if item.stop:
                    harness.event.set()
                if isinstance(item.data, Exception):
                    raise item.data
                return item.data

            def close(self):
                self.closed = True
                harness.closes.append((harness.clock.now, id(self)))

            def __enter__(self):
                return self

            def __exit__(self, *args):
                self.close()
                return False

        self.serial_module = types.SimpleNamespace(Serial=FakeSerial, SerialException=OSError)

    def run(self):
        with patch.dict(sys.modules, serial=self.serial_module), \
                patch("coinft_demo.time.monotonic", side_effect=self.clock.monotonic), \
                patch("coinft_demo.time.time", side_effect=self.clock.wall), \
                patch("coinft_demo.time.sleep", side_effect=self.clock.advance):
            self.source._run_serial()
        return self.source.snapshot()

    def command_bytes(self):
        return [command for _, command, _ in self.commands]


class SerialRecoveryTests(unittest.TestCase):
    def source(self):
        return DemoSource(port="TEST_ONLY")

    def live_source(self, baseline=1000):
        source = self.source()
        matrix = [[0.0] * 6 for _ in range(24)]
        matrix[0][0] = 1.0
        source.projector = RelativeProjector(matrix)
        source.projector.baseline = [float(baseline)] * 12
        source.tare_requested = False
        source.state.update(status="live", raw=[baseline] * 12)
        return source

    def test_silence_boundary_reopens_only_at_two_seconds_and_same_port(self):
        source = self.live_source()
        harness = SerialHarness(source, [
            {"reads": [Read(1.999, b""), Read(0.001, b"")]},
            {"reads": [Read(0, wire(1010), stop=True)]},
        ])
        state = harness.run()

        self.assertEqual([port for _, port in harness.opens], ["TEST_ONLY", "TEST_ONLY"])
        first_start = next(at for at, command, _ in harness.commands if command == b"s")
        self.assertGreaterEqual(harness.opens[1][0] - first_start, 2.0)
        self.assertEqual(state["recovery"]["attempts"], 1)
        self.assertEqual(state["recovery"]["successes"], 1)
        self.assertEqual(harness.command_bytes(), [b"i", b"s", b"i", b"s", b"i"])
        self.assertEqual(len(harness.resets), 2)
        self.assertTrue(all(command in (b"i", b"s") for command in harness.command_bytes()))

    def test_progressing_valid_invalid_saturated_and_garbage_streams_do_not_reopen(self):
        for chunks in (
                [wire(1000), wire(1000), wire(1000)],
                [wire(1200, 300), wire(1200, 300), wire(1200, 300)],
                [wire(SATURATION), wire(SATURATION), wire(SATURATION)],
                [wire(65535), wire(65535), wire(65535)],
                [b"garbage" * 20, b"garbage" * 20, b"garbage" * 20]):
            with self.subTest(first=chunks[0][:8]):
                source = self.live_source()
                reads = [Read(1.0, chunk, stop=index == 2)
                         for index, chunk in enumerate(chunks)]
                harness = SerialHarness(source, [{"reads": reads}])
                state = harness.run()
                self.assertEqual(len(harness.opens), 1)
                self.assertEqual(state["recovery"]["attempts"], 0)
                self.assertEqual(harness.command_bytes(), [b"i", b"s", b"i"])

    def test_failed_automatic_opens_are_visible_and_spaced_five_seconds(self):
        source = self.live_source()
        harness = SerialHarness(source, [
            {"reads": [Read(2.0, b"")]},
            OSError("busy one"),
            OSError("busy two"),
            {"reads": [Read(0, wire(1001), stop=True)]},
        ])
        state = harness.run()
        automatic_starts = [opened for opened, _ in harness.opens[1:]]
        self.assertEqual(state["recovery"]["attempts"], 3)
        self.assertEqual(state["recovery"]["successes"], 1)
        self.assertGreaterEqual(automatic_starts[1] - automatic_starts[0], 5.0)
        self.assertGreaterEqual(automatic_starts[2] - automatic_starts[1], 5.0)
        self.assertIn("busy two", state["recovery"]["last_fault"]["reason"])

    def test_repeated_silent_attempts_are_spaced_five_seconds(self):
        source = self.live_source()
        harness = SerialHarness(source, [
            {"reads": [Read(2.0, b"")]},
            {"reads": [Read(2.0, b"")]},
            {"reads": [Read(0, wire(1001), stop=True)]},
        ])
        state = harness.run()
        automatic_starts = [opened for opened, _ in harness.opens[1:]]
        self.assertGreaterEqual(automatic_starts[1] - automatic_starts[0], 5.0)
        self.assertEqual(state["recovery"]["attempts"], 2)
        self.assertEqual(state["recovery"]["successes"], 1)

    def test_read_error_preserves_pending_fault_diagnostics_before_reopen_clear(self):
        source = self.live_source()
        partial = wire(1000)[:10]
        harness = SerialHarness(source, [
            {"reads": [Read(0.1, partial), Read(0.1, OSError("read lost"))]},
            {"reads": [Read(0, b"", stop=True)]},
        ])
        state = harness.run()
        fault = state["recovery"]["last_fault"]
        self.assertIn("read lost", fault["reason"])
        self.assertEqual(fault["diagnostics"]["parser_pending_bytes"], 10)
        self.assertEqual(fault["diagnostics"]["serial_reads"], 1)
        self.assertEqual(state["diagnostics"]["parser_pending_bytes"], 0)
        self.assertEqual(state["diagnostics"]["serial_reads"], 2)
        self.assertEqual(state["frames"], fault["frames"])

    def test_silence_fault_freezes_pending_discard_and_resync_before_clear(self):
        source = self.live_source()
        harness = SerialHarness(source, [
            {"reads": [Read(0.1, b"x" * 30), Read(2.0, b"")]},
            {"reads": [Read(0, wire(1000), stop=True)]},
        ])
        state = harness.run()
        fault_diagnostics = state["recovery"]["last_fault"]["diagnostics"]
        self.assertEqual(fault_diagnostics["parser_pending_bytes"], 1)
        self.assertEqual(fault_diagnostics["parser_discarded_bytes"], 29)
        self.assertEqual(state["diagnostics"]["parser_pending_bytes"], 2)
        self.assertEqual(state["diagnostics"]["parser_discarded_bytes"], 29)
        self.assertEqual(source.parser.resyncs, 29)
        self.assertEqual(state["resyncs"], 29)

    def test_stop_during_startup_and_cooldown_prevents_later_start_or_open(self):
        startup_source = self.live_source()
        startup = SerialHarness(startup_source, [{"reads": []}], cancel_waits=(0.2,))
        startup.run()
        self.assertEqual(startup.command_bytes(), [b"i", b"i"])
        self.assertEqual(len(startup.closes), 1)
        self.assertEqual(len(startup.resets), 0)

        automatic_startup_source = self.live_source()
        automatic_startup = SerialHarness(automatic_startup_source, [
            {"reads": [Read(0, OSError("lost"))]},
            {"reads": []},
        ], cancel_wait_index=2)
        automatic_state = automatic_startup.run()
        self.assertEqual(len(automatic_startup.opens), 2)
        self.assertEqual(automatic_startup.command_bytes(), [b"i", b"s", b"i", b"i"])
        self.assertEqual(len(automatic_startup.resets), 1)
        self.assertEqual(automatic_state["recovery"]["attempts"], 1)

        cooldown_source = self.live_source()
        cooldown = SerialHarness(cooldown_source, [
            OSError("initial open failed"),
            OSError("automatic open failed"),
        ], cancel_waits=(5.0,))
        state = cooldown.run()
        self.assertEqual(len(cooldown.opens), 2)
        self.assertEqual(state["recovery"]["attempts"], 1)

    def test_stop_at_automatic_open_boundary_counts_only_an_attempted_open(self):
        source = self.live_source()
        harness = SerialHarness(source, [
            OSError("initial open failed"),
            OSError("automatic open failed"),
        ], cancel_monotonic_index=1)

        state = harness.run()
        automatic_opens = len(harness.opens) - 1

        self.assertTrue(harness.event.is_set())
        self.assertEqual(state["recovery"]["attempts"], automatic_opens)
        self.assertEqual(automatic_opens, 1)

    def test_manual_tare_requested_during_cooldown_survives_reopen(self):
        source = self.live_source(900)
        harness = SerialHarness(source, [
            {"reads": [Read(0, OSError("lost"))]},
            OSError("busy"),
            {"reads": [Read(0.1, wire(1000, 400), stop=True)]},
        ], wait_actions=[(5.0, source.request_tare)])
        state = harness.run()
        self.assertFalse(source.tare_requested)
        self.assertEqual(source.projector.baseline, [1000.0] * 12)
        self.assertEqual(state["recovery"]["successes"], 1)

    def test_recovery_preserves_baseline_frames_counters_and_held_load(self):
        source = self.live_source(1000)
        source._consume((1005,) * 12)
        baseline = list(source.projector.baseline)
        before = source.snapshot()
        harness = SerialHarness(source, [
            {"reads": [Read(2.0, b"")]},
            {"reads": [Read(0.1, wire(1100, 30), stop=True)]},
        ])
        state = harness.run()
        self.assertEqual(source.projector.baseline, baseline)
        self.assertFalse(source.tare_requested)
        self.assertGreater(state["frames"], before["frames"])
        self.assertGreater(state["diagnostics"]["parsed_frames"], 0)
        self.assertEqual(state["channels"], [100.0] * 12)
        self.assertNotEqual(state["axes"][0], 0.0)
        self.assertGreater(state["diagnostics"]["last_byte_at"], 0)
        self.assertGreater(state["diagnostics"]["last_parsed_frame_at"], 0)

    def test_initial_tare_acquisition_continues_across_reconnect(self):
        source = self.source()
        harness = SerialHarness(source, [
            {"reads": [Read(0.1, wire(1000, 200)), Read(0.1, OSError("split"))]},
            {"reads": [Read(0.1, wire(1000, 100)), Read(0.1, OSError("split again"))]},
            {"reads": [Read(0.1, wire(1000, 100), stop=True)]},
        ])
        state = harness.run()
        self.assertTrue(all(snapshot["recovery"]["successes"] == 0
                            for snapshot in harness.read_snapshots))
        self.assertFalse(source.tare_requested)
        self.assertEqual(source.projector.baseline, [1000.0] * 12)
        self.assertEqual(state["frames"], 400)
        self.assertEqual(state["recovery"]["successes"], 1)
        self.assertEqual(state["status"], "live")

    def test_start_write_error_is_visible_and_retried(self):
        source = self.live_source()
        harness = SerialHarness(source, [
            {"reads": [], "write_failures": [(b"s", OSError("start write failed"))]},
            {"reads": [Read(0, wire(1000), stop=True)]},
        ])
        state = harness.run()
        self.assertEqual(state["recovery"]["attempts"], 1)
        self.assertEqual(state["recovery"]["successes"], 1)
        self.assertIn("start write failed", state["recovery"]["last_fault"]["reason"])

    def test_manual_tare_continues_across_reconnect_and_success_waits_for_live(self):
        source = self.live_source(900)
        source.request_tare()
        harness = SerialHarness(source, [
            {"reads": [Read(0.1, wire(1000, 399)), Read(0.1, OSError("split"))]},
            {"reads": [Read(0.1, wire(1000), stop=True)]},
        ])
        state = harness.run()
        self.assertFalse(source.tare_requested)
        self.assertEqual(source.projector.baseline, [1000.0] * 12)
        self.assertEqual(state["recovery"]["successes"], 1)
        self.assertEqual(state["status"], "live")

    def test_invalid_recovered_data_is_not_success_and_snapshot_is_isolated(self):
        source = self.live_source()
        harness = SerialHarness(source, [
            {"reads": [Read(2.0, b"")]},
            {"reads": [Read(0.1, wire(65535)), Read(0.1, OSError("still bad"))]},
            {"reads": [Read(0.1, wire(1000), stop=True)]},
        ])
        state = harness.run()
        self.assertEqual(state["recovery"]["attempts"], 2)
        self.assertEqual(state["recovery"]["successes"], 1)
        first = source.snapshot()
        first["recovery"]["attempts"] = 99
        first["recovery"]["last_fault"]["diagnostics"]["serial_reads"] = 99
        second = source.snapshot()
        self.assertEqual(second["recovery"]["attempts"], 2)
        self.assertNotEqual(second["recovery"]["last_fault"]["diagnostics"]["serial_reads"], 99)


if __name__ == "__main__":
    unittest.main()
