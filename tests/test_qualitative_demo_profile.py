"""Synthetic checks for the separately fitted qualitative demo profile."""

import copy
import unittest
from datetime import datetime, timedelta, timezone

from calibration.build_qualitative_demo_profile import build_profile
from calibration.fit_demo_profile import signed_score


KEYS = ("press_before", "press", "press_after", "right_before", "right",
        "right_after", "left_before", "left")
SHEAR = (120, -120, 80, -80, 100, -100, 60, -60)
LEAK = (28, -28, 21, -21, 14, -14, 7, -7)


def make_windows():
    windows = {}
    start = datetime(2026, 9, 25, tzinfo=timezone.utc)
    for index, key in enumerate(KEYS):
        offset = [100 + 3 * channel if index < 6 else 900 - 2 * channel
                  for channel in range(12)]
        samples = []
        for sample_index in range(40):
            noise = (sample_index % 5) - 2
            channels = [value + noise for value in offset]
            if key == "press":
                channels = [channels[i] + LEAK[i] for i in range(8)] + [
                    channels[i] + 700 for i in range(8, 12)]
            elif key in ("right", "left"):
                direction = 1 if key == "right" else -1
                channels = [channels[i] + direction * SHEAR[i] for i in range(8)] + channels[8:]
            samples.append({
                "host": (start + timedelta(minutes=index, milliseconds=150 * sample_index)).isoformat(),
                "f": 10000 * index + sample_index + 1,
                "channels": channels,
                "raw": [28000 + i for i in range(12)],
                "status": "live", "rate": 200.0, "invalid": 0,
                "saturated": 0, "resync": 0,
            })
        windows[key] = {"pose": key, "assemblyId": "test-assembly", "samples": samples,
                        "evidence": f"{key}.json"}
    return windows


class QualitativeDemoProfileTests(unittest.TestCase):
    def test_offsets_cancel_and_directions_separate(self):
        windows = make_windows()
        profile = build_profile(windows)
        self.assertEqual(profile["mode"], "qualitative")
        self.assertEqual(profile["evidence"], [f"{key}.json" for key in KEYS])
        self.assertEqual(profile["rightLabel"], "−X")
        self.assertEqual(profile["leftLabel"], "+X")

        def adjusted(key, before, after=None):
            before_values = [sample["channels"] for sample in windows[before]["samples"]]
            after_values = ([sample["channels"] for sample in windows[after]["samples"]]
                            if after else before_values)
            baseline = [(sorted(row[i] for row in before_values)[19] +
                         sorted(row[i] for row in before_values)[20] +
                         sorted(row[i] for row in after_values)[19] +
                         sorted(row[i] for row in after_values)[20]) / 4
                        for i in range(12)]
            return [[value - base for value, base in zip(sample["channels"], baseline)]
                    for sample in windows[key]["samples"]]

        right_increment = adjusted("right", "right_before", "right_after")[0]
        left_increment = adjusted("left", "left_before")[0]
        right_score = signed_score(right_increment, profile["shear"]["pressLeak"], profile["shear"]["weights"])
        left_score = signed_score(left_increment, profile["shear"]["pressLeak"], profile["shear"]["weights"])
        self.assertGreater(right_score, profile["shear"]["threshold"])
        self.assertLess(left_score, -profile["shear"]["threshold"])
        for key, before, after in (("press_before", "press_before", "press_after"),
                                   ("press", "press_before", "press_after"),
                                   ("press_after", "press_before", "press_after"),
                                   ("right_before", "right_before", "right_after"),
                                   ("right_after", "right_before", "right_after"),
                                   ("left_before", "left_before", None)):
            for increment in adjusted(key, before, after):
                score = signed_score(increment, profile["shear"]["pressLeak"], profile["shear"]["weights"])
                self.assertLess(abs(score), profile["shear"]["threshold"])

    def test_zero_left_action_is_rejected(self):
        windows = make_windows()
        for sample in windows["left"]["samples"]:
            sample["channels"] = copy.copy(windows["left_before"]["samples"][0]["channels"])
        with self.assertRaises(ValueError):
            build_profile(windows)

    def test_bad_or_missing_evidence_is_rejected(self):
        windows = make_windows()
        windows["right"]["samples"][5]["status"] = "waiting"
        with self.assertRaises(ValueError):
            build_profile(windows)
        windows = make_windows()
        del windows["left_before"]
        with self.assertRaises(ValueError):
            build_profile(windows)


if __name__ == "__main__":
    unittest.main()
