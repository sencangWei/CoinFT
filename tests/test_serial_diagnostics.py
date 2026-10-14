"""Exercise serial diagnostics through the real parser and consumer, without hardware."""

import struct
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from coinft_demo import DemoSource


ZEROS = dict(serial_reads=0, serial_bytes=0, parsed_frames=0, last_byte_at=0,
             last_parsed_frame_at=0, parser_pending_bytes=0, parser_discarded_bytes=0)


def frame(value):
    return b"\x00\x00" + struct.pack("<12H", *([value] * 12))


class SerialDiagnosticsTests(unittest.TestCase):
    def run_sessions(self, sessions):
        source = DemoSource(port="TEST_ONLY")
        snapshots, openings, commands = [], [], []
        clock = [100.0]
        remaining = iter(sessions)

        class FakeSerial:
            def __init__(self, port, baud, timeout):
                self.chunks = iter(next(remaining))
                self.commands = []
                commands.append(self.commands)

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def write(self, command):
                self.commands.append(command)
                if command == b"i" and len(self.commands) == 1:
                    openings.append(source.snapshot())

            def reset_input_buffer(self):
                pass

            def close(self):
                pass

            def read(self, size):
                snapshots.append(source.snapshot())
                item = next(self.chunks)
                if isinstance(item, Exception):
                    raise item
                clock[0] += 1
                chunk, final = item
                if final:
                    source.stop_event.set()
                return chunk

        fake_module = types.SimpleNamespace(Serial=FakeSerial, SerialException=OSError)
        with patch.dict(sys.modules, serial=fake_module), \
                patch("coinft_demo.time.sleep"), \
                patch("coinft_demo.time.monotonic", return_value=1.0), \
                patch("coinft_demo.time.time", side_effect=lambda: clock[0]) as wall_time, \
                patch.object(source.stop_event, "wait", return_value=False):
            source._run_serial()
        snapshots.append(source.snapshot())
        return source, snapshots, openings, commands, wall_time.call_count

    def diagnostics(self, snapshot):
        self.assertIn("diagnostics", snapshot)
        return snapshot["diagnostics"]

    def test_initial_values_and_snapshot_isolation(self):
        source = DemoSource(port="TEST_ONLY")
        first, second = source.snapshot(), source.snapshot()
        self.assertEqual(self.diagnostics(first), ZEROS)
        first["diagnostics"]["serial_reads"] = 99
        self.assertEqual(self.diagnostics(second), ZEROS)
        self.assertEqual(self.diagnostics(source.snapshot()), ZEROS)

    def test_empty_and_garbage_reads_count_bytes_and_discard_without_frames(self):
        _, states, _, commands, calls = self.run_sessions([
            [(b"", False), (b"x" * 30, False), (b"", True)]])
        self.assertEqual(self.diagnostics(states[1]), dict(ZEROS, serial_reads=1))
        expected = dict(ZEROS, serial_reads=2, serial_bytes=30, last_byte_at=102,
                        parser_pending_bytes=1, parser_discarded_bytes=29)
        self.assertEqual(self.diagnostics(states[2]), expected)
        self.assertEqual(self.diagnostics(states[3]), dict(expected, serial_reads=3))
        self.assertEqual(states[3]["frames"], 0)
        self.assertEqual(states[3]["resyncs"], 0)
        self.assertEqual(commands, [[b"i", b"s", b"i"]])
        self.assertEqual(calls, 3)

    def test_split_frame_waits_for_following_header_and_processes_last_read(self):
        wire = frame(1000)
        source, states, _, commands, calls = self.run_sessions([
            [(wire[:10], False), (wire[10:], False), (b"\x00\x00", True)]])
        for index, pending in ((1, 10), (2, 26)):
            diag = self.diagnostics(states[index])
            self.assertEqual(diag["parser_pending_bytes"], pending)
            self.assertEqual(diag["parsed_frames"], 0)
        self.assertEqual(self.diagnostics(states[-1]), dict(
            ZEROS, serial_reads=3, serial_bytes=28, parsed_frames=1,
            last_byte_at=103, last_parsed_frame_at=103, parser_pending_bytes=2))
        self.assertEqual(states[-1]["raw"], [1000] * 12)
        self.assertEqual(states[-1]["updated_at"], 103)
        self.assertEqual(len(source.tare_frames), 1)
        self.assertEqual(commands, [[b"i", b"s", b"i"]])
        self.assertEqual(calls, 4)  # Three reads and the unchanged valid-frame consumer.

    def test_rejected_parsed_frame_advances_diagnostics_but_not_valid_update(self):
        _, states, _, _, calls = self.run_sessions([
            [(frame(1000) + b"\x00\x00", False),
             (frame(65535)[2:] + b"\x00\x00", True)]])
        before, after = states[1], states[2]
        self.assertEqual(self.diagnostics(after)["parsed_frames"], 2)
        self.assertEqual(after["diagnostics"]["last_parsed_frame_at"], 102)
        self.assertEqual(after["frames"], 2)
        self.assertEqual(after["invalid_frames"], 1)
        self.assertEqual(after["updated_at"], before["updated_at"])
        self.assertEqual(after["raw"], before["raw"])
        self.assertEqual(calls, 3)

    def test_reopen_preserves_totals_and_times_and_resets_pending(self):
        _, states, openings, commands, calls = self.run_sessions([
            [(b"x" * 30, False), (frame(1000) + b"\x00\x00", False),
             OSError("test disconnect")],
            [(b"", False), (b"y" * 30, True)]])
        before = self.diagnostics(states[2])
        reopened = self.diagnostics(openings[1])
        self.assertEqual(reopened, dict(before, parser_pending_bytes=0))
        self.assertEqual(self.diagnostics(states[4]), dict(reopened, serial_reads=3))
        final = self.diagnostics(states[-1])
        self.assertEqual(final, dict(reopened, serial_reads=4, serial_bytes=88,
                                    last_byte_at=104, parser_pending_bytes=1,
                                    parser_discarded_bytes=59))
        self.assertEqual(before["last_parsed_frame_at"], 102)
        self.assertEqual(commands, [[b"i", b"s"], [b"i", b"s", b"i"]])
        self.assertEqual(calls, 6)  # Includes the frozen host fault timestamp.


if __name__ == "__main__":
    unittest.main()
