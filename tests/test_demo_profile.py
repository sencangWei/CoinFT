"""Tests for one-pose HTTP evidence capture and offline profile fitting."""

import io
import json
import math
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from calibration.capture_demo_pose import capture, main
from calibration.fit_demo_profile import fit_profile, main as fit_main, signed_score


def state(frame):
    return {
        "status": "live",
        "frames": frame,
        "rate": 199.5,
        "invalid_recent": 0,
        "saturated_recent": 0,
        "resyncs": 2,
        "channels": [float(frame)] * 12,
        "raw": [1000 + frame] * 12,
    }


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.now += seconds


class CaptureTests(unittest.TestCase):
    def run_capture(self, states, seconds=5, interval=0.125):
        clock = FakeClock()
        urls = []
        responses = iter(states)
        start = datetime(2026, 9, 28, tzinfo=timezone.utc)

        class ClockDate:
            @classmethod
            def now(cls):
                return start + timedelta(seconds=clock.now)

            @staticmethod
            def fromisoformat(value):
                return datetime.fromisoformat(value)

        def urlopen(url, timeout):
            urls.append((url, timeout))
            return io.BytesIO(json.dumps(next(responses)).encode("utf-8"))

        with patch("calibration.capture_demo_pose.urllib.request.urlopen", side_effect=urlopen), \
             patch("calibration.capture_demo_pose.time.monotonic", side_effect=clock.monotonic), \
             patch("calibration.capture_demo_pose.time.sleep", side_effect=clock.sleep), \
             patch("calibration.capture_demo_pose.datetime", ClockDate):
            result = capture("http://example.test", "train_press", "assembly-A", seconds, interval)
        return result, urls

    def test_collects_distinct_http_snapshots_with_provenance(self):
        result, urls = self.run_capture([state(i) for i in range(1, 44)])
        self.assertGreaterEqual(len(result["samples"]), 40)
        self.assertEqual(result["pose"], "train_press")
        self.assertEqual(result["assemblyId"], "assembly-A")
        self.assertEqual(result["source"], "http://example.test")
        self.assertEqual(result["sample_kind"], "http_snapshot")
        self.assertEqual([sample["f"] for sample in result["samples"]], list(range(1, 42)))
        self.assertTrue(all(len(sample["channels"]) == 12 for sample in result["samples"]))
        self.assertTrue(all(set(sample) == {"host", "f", "channels", "raw", "status", "rate", "invalid", "saturated", "resync"} for sample in result["samples"]))
        self.assertTrue(all(url == "http://example.test/api/state" and timeout == 1.5 for url, timeout in urls))

    def test_rejects_regressing_frame_without_skipping_it(self):
        states = [state(i) for i in range(1, 44)]
        states[8] = state(7)
        with self.assertRaisesRegex(ValueError, "frame not increasing.*previous=8.*current=7"):
            self.run_capture(states)

    def test_rejects_invalid_recent_without_skipping_it(self):
        states = [state(i) for i in range(1, 44)]
        states[8]["invalid_recent"] = 1
        with self.assertRaisesRegex(ValueError, "invalid_recent=1"):
            self.run_capture(states)

    def test_rejects_other_bad_state_fields(self):
        cases = [
            ("status", "waiting"),
            ("rate", 0),
            ("rate", math.inf),
            ("saturated_recent", 1),
            ("channels", [0.0] * 11),
            ("raw", [0] * 11),
            ("channels", [math.nan] + [0.0] * 11),
            ("raw", [math.inf] + [0] * 11),
            ("resyncs", math.nan),
            ("resyncs", math.inf),
            ("resyncs", "2"),
            ("resyncs", -1),
        ]
        for key, value in cases:
            with self.subTest(key=key, value=value):
                states = [state(i) for i in range(1, 44)]
                states[8][key] = value
                with self.assertRaises(ValueError):
                    self.run_capture(states)

    def test_rejects_nonfinite_or_nonpositive_capture_timing_before_request(self):
        cases = [(math.inf, 0.125), (math.nan, 0.125), (5, math.inf),
                 (5, math.nan), (0, 0.125), (5, -0.125)]
        for seconds, interval in cases:
            with self.subTest(seconds=seconds, interval=interval):
                with patch("calibration.capture_demo_pose.urllib.request.urlopen") as request:
                    with self.assertRaisesRegex(ValueError, "finite and positive"):
                        capture("http://example.test", "train_press", "assembly-A", seconds, interval)
                request.assert_not_called()

    def test_requires_thirty_distinct_snapshots(self):
        with self.assertRaises(ValueError):
            self.run_capture([state(i) for i in range(1, 30)],
                             seconds=3.625, interval=0.2)

    def test_cli_preserves_existing_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "evidence.json"
            output.write_text("original", encoding="utf-8")
            args = ["--pose", "train_press", "--assembly-id", "assembly-A", "--out", str(output)]
            with patch("calibration.capture_demo_pose.capture") as mocked:
                with self.assertRaises(FileExistsError):
                    main(args)
            mocked.assert_not_called()
            self.assertEqual(output.read_text(encoding="utf-8"), "original")

    def test_cli_writes_only_after_successful_capture(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "evidence.json"
            args = ["--pose", "train_press", "--assembly-id", "assembly-A", "--out", str(output)]
            with patch("calibration.capture_demo_pose.capture", side_effect=ValueError("bad state")):
                with self.assertRaises(ValueError):
                    main(args)
            self.assertFalse(output.exists())

    def test_cli_does_not_overwrite_file_created_during_serialization(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "evidence.json"
            args = ["--pose", "train_press", "--assembly-id", "assembly-A", "--out", str(output)]
            evidence = {"samples": [{"f": 1, "rate": 200, "invalid": 0,
                                     "saturated": 0, "resync": 0}]}
            original_dumps = json.dumps

            def create_competing_file(*values, **options):
                output.write_text("other evidence", encoding="utf-8")
                return original_dumps(*values, **options)

            with patch("calibration.capture_demo_pose.capture", return_value=evidence), \
                 patch("calibration.capture_demo_pose.json.dumps", side_effect=create_competing_file):
                with self.assertRaises(FileExistsError):
                    main(args)
            self.assertEqual(output.read_text(encoding="utf-8"), "other evidence")


PATTERN = [90, 70, 40, 20, -20, -40, -70, -90]
LEAK = [16, 12, 8, 4, -4, -8, -12, -16]


def fitted_windows(holdout_left=1):
    windows = {}
    window_index = 0
    start = datetime(2026, 9, 25, 10, tzinfo=timezone(timedelta(hours=8)))
    for round_name in ("train", "holdout"):
        for action in ("press", "right", "left"):
            for pose in (f"empty_before_{action}", action, f"empty_after_{action}"):
                name = f"{round_name}_{pose}"
                samples = []
                for index in range(40):
                    drift = (index % 3) - 1
                    base = 30 if pose.startswith("empty_after") else 20
                    channels = [base + drift] * 12
                    if pose == "press":
                        channels = [base + drift + x for x in LEAK] + [base + 200 + drift] * 4
                    elif pose in ("right", "left"):
                        sign = 1 if pose == "right" else -1
                        if round_name == "holdout" and pose == "left":
                            sign *= holdout_left
                        channels = [base + drift + sign * x for x in PATTERN] + [base + drift] * 4
                    samples.append({"host": (start + timedelta(seconds=window_index * 60 + index)).isoformat(),
                                    "f": window_index * 100 + index + 1,
                                    "channels": channels, "raw": [1000] * 12, "status": "live",
                                    "rate": 200, "invalid": 0, "saturated": 0, "resync": 0})
                windows[name] = {"pose": name, "assemblyId": "assembly-A", "samples": samples,
                                 "evidence": f"demo_{name}_20260925.json"}
                window_index += 1
    return windows


def set_window_signed_score(window, target, shear):
    for sample in window["samples"]:
        channels = sample["channels"]
        base = signed_score(channels, shear["pressLeak"], shear["weights"])
        shifted = [value + pattern for value, pattern in zip(channels[:8], PATTERN)] + channels[8:]
        slope = signed_score(shifted, shear["pressLeak"], shear["weights"]) - base
        scale = (target - base) / slope
        sample["channels"] = [value + scale * pattern for value, pattern in zip(channels[:8], PATTERN)] + channels[8:]


class FitterTests(unittest.TestCase):
    def test_one_contaminated_holdout_empty_window_fails_individually(self):
        windows = fitted_windows()
        trained, _ = fit_profile(windows, "right", "left")
        name = "holdout_empty_after_right"
        set_window_signed_score(windows[name], 1.5 * trained["shear"]["threshold"], trained["shear"])
        profile, report = fit_profile(windows, "right", "left")
        self.assertFalse(profile["shear"]["enabled"])
        self.assertLess(report["holdout"]["emptySpurious"], 0.2)
        self.assertEqual(report["holdout"]["emptySpuriousByWindow"][name], 1.0)
        self.assertIn(name, " ".join(report["reasons"]))

    def test_empty_response_between_release_and_activation_threshold_fails(self):
        windows = fitted_windows()
        trained, _ = fit_profile(windows, "right", "left")
        name = "holdout_empty_before_left"
        set_window_signed_score(windows[name], 0.85 * trained["shear"]["threshold"], trained["shear"])
        profile, report = fit_profile(windows, "right", "left")
        self.assertFalse(profile["shear"]["enabled"])
        self.assertAlmostEqual(report["train"]["releaseThreshold"], 0.7 * report["train"]["shearThreshold"])
        self.assertEqual(report["holdout"]["emptySpuriousByWindow"][name], 0.0)
        self.assertEqual(report["holdout"]["emptyReleaseSpuriousByWindow"][name], 1.0)
        self.assertIn(name, " ".join(report["reasons"]))

    def test_press_response_between_release_and_activation_threshold_fails(self):
        windows = fitted_windows()
        trained, _ = fit_profile(windows, "right", "left")
        set_window_signed_score(windows["holdout_press"], 0.85 * trained["shear"]["threshold"], trained["shear"])
        profile, report = fit_profile(windows, "right", "left")
        self.assertFalse(profile["shear"]["enabled"])
        self.assertEqual(report["holdout"]["pressSpurious"], 0.0)
        self.assertEqual(report["holdout"]["pressReleaseSpurious"], 1.0)
        self.assertIn("press_release", " ".join(report["reasons"]))

    def test_rejects_thirty_near_instant_snapshots(self):
        windows = fitted_windows()
        samples = windows["train_press"]["samples"][:30]
        start = datetime.fromisoformat(samples[0]["host"])
        for index, sample in enumerate(samples):
            sample["host"] = (start + timedelta(milliseconds=10 * index)).isoformat()
        windows["train_press"]["samples"] = samples
        with self.assertRaisesRegex(ValueError, "duration|span|seconds"):
            fit_profile(windows, "right", "left")

    def test_differential_empty_offsets_are_safe_in_runtime_coordinates(self):
        windows = fitted_windows()
        for name, window in windows.items():
            if name.endswith("_right") or name.endswith("_left"):
                sign = 1 if name.endswith("_right") else -1
                for sample in window["samples"]:
                    sample["channels"][:8] = [value + sign * 1.5 * pattern
                                                 for value, pattern in zip(sample["channels"][:8], PATTERN)]
        profile, report = fit_profile(windows, "right", "left")
        if profile["shear"]["enabled"]:
            shear = profile["shear"]
            def score(sample):
                return signed_score(sample["channels"], shear["pressLeak"], shear["weights"])
            for name, window in windows.items():
                if "empty_" in name:
                    self.assertTrue(all(abs(score(sample)) < shear["threshold"] for sample in window["samples"]))
            self.assertGreater(min(score(sample) for sample in windows["holdout_right"]["samples"]), shear["threshold"])
            self.assertLess(max(score(sample) for sample in windows["holdout_left"]["samples"]), -shear["threshold"])
        else:
            self.assertFalse(report["passed"])
            self.assertEqual(profile["shear"]["weights"], [0.0] * 8)

    def test_rejects_reused_training_capture_as_holdout(self):
        windows = fitted_windows()
        windows["holdout_right"]["samples"] = json.loads(json.dumps(windows["train_right"]["samples"]))
        with self.assertRaisesRegex(ValueError, "chronological|overlap"):
            fit_profile(windows, "right", "left")

    def test_rejects_misordered_adjacent_empty_window(self):
        windows = fitted_windows()
        windows["train_empty_before_right"]["samples"], windows["train_empty_after_right"]["samples"] = (
            windows["train_empty_after_right"]["samples"], windows["train_empty_before_right"]["samples"])
        with self.assertRaisesRegex(ValueError, "chronological|overlap"):
            fit_profile(windows, "right", "left")

    def test_report_write_failure_cannot_leave_profile(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for pose, window in fitted_windows().items():
                (root / f"demo_{pose}_20260925.json").write_text(json.dumps(window), encoding="utf-8")
            profile_path = root / "profile.json"
            report_path = root / "report.json"
            original_open = Path.open

            def fail_report(path, *args, **kwargs):
                if path == report_path:
                    raise OSError("report storage failure")
                return original_open(path, *args, **kwargs)

            args = ["--input-dir", str(root), "--date", "20260925", "--output", str(profile_path),
                    "--report", str(report_path), "--right-label", "right", "--left-label", "left"]
            with patch("calibration.fit_demo_profile.Path.open", autospec=True, side_effect=fail_report):
                with self.assertRaisesRegex(OSError, "report storage failure"):
                    fit_main(args)
            self.assertFalse(profile_path.exists())

    def test_raw_capture_dictionaries_need_no_filename_metadata(self):
        windows = fitted_windows()
        for window in windows.values():
            del window["evidence"]
        profile, report = fit_profile(windows, "right", "left")
        self.assertTrue(profile["shear"]["enabled"])
        self.assertEqual(profile["evidence"], [])
        self.assertEqual(report["evidence"], [])

    def test_clean_opposite_patterns_and_press_leak_pass(self):
        profile, report = fit_profile(fitted_windows(), "physical east", "physical west")
        self.assertTrue(profile["shear"]["enabled"])
        self.assertTrue(report["passed"])
        self.assertEqual((profile["rightLabel"], profile["leftLabel"]), ("physical east", "physical west"))
        self.assertEqual(len(profile["evidence"]), 18)
        self.assertGreater(signed_score(PATTERN + [0] * 4, profile["shear"]["pressLeak"], profile["shear"]["weights"]), 0)
        self.assertLess(signed_score([-x for x in PATTERN] + [0] * 4, profile["shear"]["pressLeak"], profile["shear"]["weights"]), 0)
        self.assertLess(abs(signed_score(LEAK + [200] * 4, profile["shear"]["pressLeak"], profile["shear"]["weights"])), profile["shear"]["threshold"])

    def test_holdout_reversal_disables_shear_without_refitting(self):
        trained, _ = fit_profile(fitted_windows(), "right", "left")
        failed, report = fit_profile(fitted_windows(holdout_left=-1), "right", "left")
        self.assertFalse(failed["shear"]["enabled"])
        self.assertEqual(failed["shear"]["weights"], [0.0] * 8)
        self.assertEqual(report["train"]["shearThreshold"], trained["shear"]["threshold"])
        self.assertIn("holdout_left", " ".join(report["reasons"]))

    def test_noise_only_holdout_left_disables_shear(self):
        windows = fitted_windows()
        for sample in windows["holdout_left"]["samples"]:
            sample["channels"] = [20 + sample["f"] % 3 - 1] * 12
        profile, report = fit_profile(windows, "right", "left")
        self.assertFalse(profile["shear"]["enabled"])
        self.assertEqual(report["holdout"]["left"], 0)

    def test_rejects_missing_bad_samples_and_mixed_assemblies(self):
        for mutation in ("missing", "short", "mixed", "bad_time", "bad_frame", "bad_quality"):
            windows = fitted_windows()
            if mutation == "missing":
                del windows["holdout_left"]
            elif mutation == "short":
                windows["train_press"]["samples"][0]["channels"] = [1] * 11
            elif mutation == "mixed":
                windows["holdout_left"]["assemblyId"] = "assembly-B"
            elif mutation == "bad_time":
                windows["train_press"]["samples"][0]["host"] = "nonsense"
            elif mutation == "bad_quality":
                windows["train_press"]["samples"][0]["invalid"] = True
            else:
                windows["train_press"]["samples"][1]["f"] = 1
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                fit_profile(windows, "right", "left")
