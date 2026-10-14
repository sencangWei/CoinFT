import copy
import json
import unittest
from pathlib import Path
try:
    from calibration import shear_refit_replay as refit
except ImportError:
    refit = None
from test_qualitative_demo_profile import make_windows


def windows():
    result = make_windows()
    # Remove synthetic acquisition offsets: one actual epoch/common baseline.
    for index, window in enumerate(result.values()):
        offset = [100+3*i if index < 6 else 900-2*i for i in range(12)]
        for sample in window["samples"]:
            sample["channels"] = [v-b for v, b in zip(sample["channels"], offset)]
        window["owner"] = {"pid": 7, "created": 123.0}
    return result


class ShearRefitReplayTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(refit, "offline refit behaviors are not implemented")

    def test_preserves_normal_and_replays_actual_surface(self):
        data = windows()
        root = Path(__file__).resolve().parents[1]
        old = json.loads((root / "demo_web/shear_demo_profile.json").read_text(encoding="utf-8"))
        candidate = refit.fit_candidate(data, old)
        self.assertEqual(candidate["normal"], old["normal"])
        result = refit.replay(candidate, old, data, [0]*12)
        self.assertTrue(refit.passes(result), result)
        self.assertTrue(result["normalUnchanged"])

    def test_normal_change_is_detected_and_rejected(self):
        data = windows()
        root = Path(__file__).resolve().parents[1]
        old = json.loads((root / "demo_web/shear_demo_profile.json").read_text(encoding="utf-8"))
        candidate = refit.fit_candidate(data, old)
        changed = copy.deepcopy(candidate)
        changed["normal"]["span"] = 1200
        report = refit.replay(changed, old, data, [0]*12)
        self.assertFalse(report["normalUnchanged"])
        self.assertFalse(refit.passes(report))

    def test_rejects_cross_window_epoch_and_frame_restart(self):
        old = {"normal": {"threshold": 100, "span": 600}}
        for field in ("owner", "frame"):
            data = windows()
            if field == "owner":
                data["left"]["owner"]["created"] += 1
            else:
                data["left"]["samples"][0]["f"] = 1
            with self.assertRaises(ValueError):
                refit.fit_candidate(data, old)

    def test_rejects_false_shear_or_wrong_direction(self):
        good = {"normalUnchanged": True, "poses": {
            "press_before": [0.0], "press": [0.0], "press_after": [0.0],
            "right_before": [0.0], "right": [0.3]*10,
            "right_after": [0.0], "left_before": [0.0], "left": [-0.3]*10}}
        self.assertTrue(refit.passes(good))
        for key, values in (("press", [0.06]), ("left", [0.3]),
                            ("right", [0.3]*7+[0.0]*3)):
            bad = copy.deepcopy(good)
            bad["poses"][key] = values
            self.assertFalse(refit.passes(bad))
        good["normalUnchanged"] = False
        self.assertFalse(refit.passes(good))


    def test_rejects_nonfinite_report_values(self):
        report = {"normalUnchanged": True, "poses": {
            "press_before": [0.0], "press": [0.0], "press_after": [0.0],
            "right_before": [0.0], "right": [0.3]*10,
            "right_after": [0.0], "left_before": [0.0], "left": [-0.3]*10}}
        for value in (float("nan"), float("inf"), -float("inf"), True, "0.3"):
            with self.subTest(value=value):
                bad = copy.deepcopy(report)
                bad["poses"]["right"][0] = value
                self.assertFalse(refit.passes(bad))
