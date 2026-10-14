"""Meaningful checks for the browser demo's wire protocol and six-axis projection."""

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from coinft_demo import DemoSource, FrameParser, RelativeProjector


class FrameParserTests(unittest.TestCase):
    def test_accepts_split_frames_and_skips_misaligned_bytes(self):
        import struct

        first = tuple(range(1, 13))
        second = tuple(range(101, 113))
        wire = b"\x7f\x41" + b"\x00\x00" + struct.pack("<12H", *first)
        wire += b"\x00\x00" + struct.pack("<12H", *second) + b"\x00\x00"
        parser = FrameParser()
        seen = []
        for chunk in (wire[:5], wire[5:19], wire[19:41], wire[41:]):
            seen.extend(parser.feed(chunk))
        self.assertEqual(seen, [first, second])

    def test_rejects_frame_without_following_header(self):
        import struct

        parser = FrameParser()
        wrong = b"\x00\x00" + struct.pack("<12H", *range(12)) + b"\x88\x88"
        self.assertEqual(parser.feed(wrong), [])
        self.assertGreater(parser.resyncs, 0)


class RelativeProjectorTests(unittest.TestCase):
    def test_tare_produces_six_zeros_and_channel_deltas(self):
        matrix = [[0.0] * 6 for _ in range(24)]
        for axis in range(6):
            matrix[axis][axis] = 1.0
        projector = RelativeProjector(matrix)
        raw = tuple(range(100, 112))
        projector.tare([raw, raw])
        axes, channels = projector.project(raw)
        self.assertEqual(axes, [0.0] * 6)
        self.assertEqual(channels, [0.0] * 12)
        loaded = tuple(value + 5 for value in raw)
        axes, channels = projector.project(loaded)
        self.assertEqual(axes, [5.0] * 6)
        self.assertEqual(channels, [5.0] * 12)


class DemoSourceRateTests(unittest.TestCase):
    def test_rate_is_not_biased_by_usb_batch_boundaries(self):
        source = DemoSource(replay="unused.csv")
        source.projector.baseline = [0.0] * 12
        source.tare_requested = False
        timestamps = [0.0] + [batch / 10 for batch in range(1, 201) for _ in range(20)]
        with patch("coinft_demo.time.monotonic", side_effect=timestamps):
            for _ in timestamps:
                source._consume((100,) * 12)
        self.assertEqual(source.snapshot()["rate"], 200.0)


class DemoSourceDisplayTests(unittest.TestCase):
    def make_source(self):
        source = DemoSource(replay="unused.csv")
        matrix = [[0.0] * 6 for _ in range(24)]
        matrix[0][0] = 1.0
        source.projector = RelativeProjector(matrix)
        source.projector.baseline = [1000.0] * 12
        source.tare_requested = False
        source.state["status"] = "live"
        return source

    def test_valid_frame_restores_live_status_after_waiting(self):
        source = self.make_source()
        source.state["status"] = "waiting"
        source._consume((1000,) * 12)
        self.assertEqual(source.snapshot()["status"], "live")

    def test_quiet_axis_display_is_smoothed_but_raw_channels_remain_unfiltered(self):
        source = self.make_source()
        for n in range(50):
            value = 1100 if n % 2 == 0 else 900
            source._consume((value,) + (1000,) * 11)
        state = source.snapshot()
        self.assertLess(abs(state["axes"][0]), 5)
        self.assertEqual(state["channels"][0], -100.0)

    def test_sustained_force_reaches_display_within_quarter_second(self):
        source = self.make_source()
        for _ in range(50):
            source._consume((1100,) + (1000,) * 11)
        self.assertAlmostEqual(source.snapshot()["axes"][0], 100.0, delta=1.0)

    def test_single_plausible_range_corrupt_frame_does_not_spike_axis(self):
        source = self.make_source()
        for _ in range(50):
            source._consume((1000,) * 12)
        source._consume((30000,) + (1000,) * 11)
        self.assertAlmostEqual(source.snapshot()["axes"][0], 0.0, delta=1.0)

    def test_out_of_range_frame_is_reported_without_changing_display(self):
        source = self.make_source()
        source._consume((1100,) + (1000,) * 11)
        before = source.snapshot()
        source._consume((65535,) + (1000,) * 11)
        after = source.snapshot()
        self.assertEqual(after["axes"], before["axes"])
        self.assertEqual(after["channels"], before["channels"])
        self.assertEqual(after["raw"], before["raw"])
        self.assertEqual(after["invalid_frames"], 1)
        self.assertEqual(after["invalid_recent"], 1)

    def test_out_of_range_frame_does_not_contaminate_tare(self):
        source = DemoSource(replay="unused.csv")
        for _ in range(399):
            source._consume((10000,) * 12)
        source._consume((65535,) + (10000,) * 11)
        self.assertEqual(source.snapshot()["tare_progress"], 100)
        self.assertTrue(source.tare_requested)
        source._consume((10000,) * 12)
        self.assertFalse(source.tare_requested)
        self.assertEqual(source.projector.baseline, [10000.0] * 12)

    def test_tare_is_robust_to_a_plausible_range_corrupt_frame(self):
        source = DemoSource(replay="unused.csv")
        for _ in range(399):
            source._consume((10000,) * 12)
        source._consume((30000,) + (10000,) * 11)
        self.assertEqual(source.projector.baseline, [10000.0] * 12)


if __name__ == "__main__":
    unittest.main()
