# Task 1 review package

No Git repository: each listed file is new; diff is against /dev/null.

diff --git a/calibration/build_qualitative_demo_profile.py b/calibration/build_qualitative_demo_profile.py
new file mode 100644
index 0000000..92ede96
--- /dev/null
+++ b/calibration/build_qualitative_demo_profile.py
@@ -0,0 +1,164 @@
+"""Build a qualitative shear demo profile from eight labeled capture windows."""
+
+import argparse
+import json
+import math
+import statistics
+from datetime import datetime
+from pathlib import Path
+
+try:
+    from calibration.fit_demo_profile import contrast, normal_score, percentile, residual, signed_score
+except ModuleNotFoundError:  # direct script invocation from the project root
+    from fit_demo_profile import contrast, normal_score, percentile, residual, signed_score
+
+
+SOURCES = {
+    "press_before": "calibration/demo_attempt_before_second_usb_reconnect_20260925/demo_train_empty_before_press_20260925.json",
+    "press": "calibration/demo_attempt_before_second_usb_reconnect_20260925/demo_train_press_20260925.json",
+    "press_after": "calibration/demo_attempt_before_second_usb_reconnect_20260925/demo_train_empty_after_press_20260925.json",
+    "right_before": "calibration/demo_attempt_before_second_usb_reconnect_20260925/demo_train_empty_before_right_20260925.json",
+    "right": "calibration/demo_attempt_before_second_usb_reconnect_20260925/demo_train_right_20260925.json",
+    "right_after": "calibration/demo_attempt_before_second_usb_reconnect_20260925/demo_train_empty_after_right_20260925.json",
+    "left_before": "calibration/demo_diagnostic_empty_after_second_usb_20260925.json",
+    "left": "calibration/demo_diagnostic_left_demo_force_20260925.json",
+}
+
+
+def _validate(windows):
+    if not isinstance(windows, dict) or set(windows) != set(SOURCES):
+        raise ValueError("exactly eight qualitative windows are required")
+    assemblies = set()
+    evidence = []
+    for key in SOURCES:
+        window = windows[key]
+        if not isinstance(window, dict):
+            raise ValueError(f"invalid window: {key}")
+        assembly = window.get("assemblyId")
+        filename = window.get("evidence")
+        if not isinstance(assembly, str) or not assembly.strip():
+            raise ValueError(f"missing assembly ID: {key}")
+        if not isinstance(filename, str) or not filename or Path(filename).name != filename or not filename.endswith(".json"):
+            raise ValueError(f"invalid evidence filename: {key}")
+        assemblies.add(assembly)
+        evidence.append(filename)
+        samples = window.get("samples")
+        if not isinstance(samples, list) or len(samples) < 40:
+            raise ValueError(f"too few samples: {key}")
+        first_host = previous_host = None
+        previous_frame = -1
+        for sample in samples:
+            if not isinstance(sample, dict):
+                raise ValueError(f"invalid sample: {key}")
+            try:
+                host = datetime.fromisoformat(sample["host"])
+            except (KeyError, TypeError, ValueError):
+                raise ValueError(f"invalid timestamp: {key}") from None
+            frame = sample.get("f")
+            rate = sample.get("rate")
+            vectors = (sample.get("channels"), sample.get("raw"))
+            if (host.tzinfo is None or (previous_host is not None and host <= previous_host)
+                    or type(frame) is not int or frame <= previous_frame
+                    or sample.get("status") != "live"
+                    or type(rate) not in (int, float) or not math.isfinite(rate) or rate <= 0
+                    or type(sample.get("invalid")) is not int or sample["invalid"] != 0
+                    or type(sample.get("saturated")) is not int or sample["saturated"] != 0
+                    or type(sample.get("resync")) is not int or sample["resync"] < 0
+                    or any(not isinstance(vector, list) or len(vector) != 12
+                           or any(type(value) not in (int, float) or not math.isfinite(value)
+                                  for value in vector) for vector in vectors)):
+                raise ValueError(f"invalid live sample: {key}")
+            if first_host is None:
+                first_host = host
+            previous_host = host
+            previous_frame = frame
+        if (previous_host - first_host).total_seconds() < 5:
+            raise ValueError(f"capture duration below 5 seconds: {key}")
+    if len(assemblies) != 1 or len(set(evidence)) != len(evidence):
+        raise ValueError("mixed assemblies or duplicate evidence")
+    return assemblies.pop(), evidence
+
+
+def _median_channels(samples):
+    return [statistics.median(sample["channels"][i] for sample in samples) for i in range(12)]
+
+
+def build_profile(windows: dict[str, dict]) -> dict:
+    assembly, evidence = _validate(windows)
+    data = {}
+    empty = []
+    for action in ("press", "right", "left"):
+        before = _median_channels(windows[f"{action}_before"]["samples"])
+        after_key = f"{action}_after"
+        after = _median_channels(windows[after_key]["samples"]) if after_key in windows else before
+        baseline = [(a + b) / 2 for a, b in zip(before, after)]
+        for key in (f"{action}_before", action, after_key):
+            if key not in windows:
+                continue
+            data[key] = [[value - base for value, base in zip(sample["channels"], baseline)]
+                         for sample in windows[key]["samples"]]
+            if key != action:
+                empty.extend(data[key])
+
+    press = data["press"]
+    right = data["right"]
+    left = data["left"]
+    press_normal = max(statistics.median(normal_score(ch) for ch in press), 1)
+    press_leak = [statistics.median(contrast(ch)[i] for ch in press) / press_normal
+                  for i in range(8)]
+    difference = [statistics.mean(residual(ch, press_leak)[i] for ch in right)
+                  - statistics.mean(residual(ch, press_leak)[i] for ch in left)
+                  for i in range(8)]
+    magnitude = math.hypot(*difference)
+    if magnitude <= 0:
+        raise ValueError("no directional contrast")
+    weights = [value / magnitude for value in difference]
+    score = lambda ch: signed_score(ch, press_leak, weights)
+    threshold = max(1.0, 1.05 * percentile([abs(score(ch)) for ch in empty + press], 95))
+    right_scores, left_scores = [score(ch) for ch in right], [score(ch) for ch in left]
+    if statistics.median(right_scores) <= threshold or statistics.median(left_scores) >= -threshold:
+        raise ValueError("qualitative directions do not separate from background")
+    span = max(1.0, min(percentile([abs(v) for v in right_scores], 90),
+                        percentile([abs(v) for v in left_scores], 90)) - threshold)
+    profile = {"version": 1, "mode": "qualitative", "assemblyId": assembly,
+               "normal": {"threshold": 100.0, "span": 600.0},
+               "shear": {"enabled": True, "weights": weights, "pressLeak": press_leak,
+                         "threshold": threshold, "span": span},
+               "rightLabel": "−X", "leftLabel": "+X", "evidence": evidence}
+    json.dumps(profile, allow_nan=False)
+    return profile
+
+
+def main(argv=None):
+    parser = argparse.ArgumentParser(description=__doc__)
+    parser.add_argument("--out", type=Path, required=True)
+    args = parser.parse_args(argv)
+    root = Path(__file__).resolve().parents[1]
+    windows = {}
+    for key, relative in SOURCES.items():
+        source = root / relative
+        window = json.loads(source.read_text(encoding="utf-8"))
+        window["evidence"] = source.name
+        windows[key] = window
+    profile = build_profile(windows)
+    with args.out.open("x", encoding="utf-8") as output:
+        output.write(json.dumps(profile, ensure_ascii=False, indent=2, allow_nan=False))
+    print(json.dumps({"threshold": profile["shear"]["threshold"],
+                      "rightMedian": statistics.median(signed_score(ch, profile["shear"]["pressLeak"], profile["shear"]["weights"])
+                                                        for ch in _action_increments(windows, "right")),
+                      "leftMedian": statistics.median(signed_score(ch, profile["shear"]["pressLeak"], profile["shear"]["weights"])
+                                                       for ch in _action_increments(windows, "left")),
+                      "evidence": profile["evidence"]}, ensure_ascii=False))
+
+
+def _action_increments(windows, action):
+    before = _median_channels(windows[f"{action}_before"]["samples"])
+    after_key = f"{action}_after"
+    after = _median_channels(windows[after_key]["samples"]) if after_key in windows else before
+    baseline = [(a + b) / 2 for a, b in zip(before, after)]
+    return [[value - base for value, base in zip(sample["channels"], baseline)]
+            for sample in windows[action]["samples"]]
+
+
+if __name__ == "__main__":
+    main()
diff --git a/tests/test_qualitative_demo_profile.py b/tests/test_qualitative_demo_profile.py
new file mode 100644
index 0000000..c3e3c40
--- /dev/null
+++ b/tests/test_qualitative_demo_profile.py
@@ -0,0 +1,102 @@
+"""Synthetic checks for the separately fitted qualitative demo profile."""
+
+import copy
+import unittest
+from datetime import datetime, timedelta, timezone
+
+from calibration.build_qualitative_demo_profile import build_profile
+from calibration.fit_demo_profile import signed_score
+
+
+KEYS = ("press_before", "press", "press_after", "right_before", "right",
+        "right_after", "left_before", "left")
+SHEAR = (120, -120, 80, -80, 100, -100, 60, -60)
+LEAK = (28, -28, 21, -21, 14, -14, 7, -7)
+
+
+def make_windows():
+    windows = {}
+    start = datetime(2026, 9, 25, tzinfo=timezone.utc)
+    for index, key in enumerate(KEYS):
+        offset = [100 + 3 * channel if index < 6 else 900 - 2 * channel
+                  for channel in range(12)]
+        samples = []
+        for sample_index in range(40):
+            noise = (sample_index % 5) - 2
+            channels = [value + noise for value in offset]
+            if key == "press":
+                channels = [channels[i] + LEAK[i] for i in range(8)] + [
+                    channels[i] + 700 for i in range(8, 12)]
+            elif key in ("right", "left"):
+                direction = 1 if key == "right" else -1
+                channels = [channels[i] + direction * SHEAR[i] for i in range(8)] + channels[8:]
+            samples.append({
+                "host": (start + timedelta(minutes=index, milliseconds=150 * sample_index)).isoformat(),
+                "f": 10000 * index + sample_index + 1,
+                "channels": channels,
+                "raw": [28000 + i for i in range(12)],
+                "status": "live", "rate": 200.0, "invalid": 0,
+                "saturated": 0, "resync": 0,
+            })
+        windows[key] = {"pose": key, "assemblyId": "test-assembly", "samples": samples,
+                        "evidence": f"{key}.json"}
+    return windows
+
+
+class QualitativeDemoProfileTests(unittest.TestCase):
+    def test_offsets_cancel_and_directions_separate(self):
+        windows = make_windows()
+        profile = build_profile(windows)
+        self.assertEqual(profile["mode"], "qualitative")
+        self.assertEqual(profile["evidence"], [f"{key}.json" for key in KEYS])
+        self.assertEqual(profile["rightLabel"], "−X")
+        self.assertEqual(profile["leftLabel"], "+X")
+
+        def adjusted(key, before, after=None):
+            before_values = [sample["channels"] for sample in windows[before]["samples"]]
+            after_values = ([sample["channels"] for sample in windows[after]["samples"]]
+                            if after else before_values)
+            baseline = [(sorted(row[i] for row in before_values)[19] +
+                         sorted(row[i] for row in before_values)[20] +
+                         sorted(row[i] for row in after_values)[19] +
+                         sorted(row[i] for row in after_values)[20]) / 4
+                        for i in range(12)]
+            return [[value - base for value, base in zip(sample["channels"], baseline)]
+                    for sample in windows[key]["samples"]]
+
+        right_increment = adjusted("right", "right_before", "right_after")[0]
+        left_increment = adjusted("left", "left_before")[0]
+        right_score = signed_score(right_increment, profile["shear"]["pressLeak"], profile["shear"]["weights"])
+        left_score = signed_score(left_increment, profile["shear"]["pressLeak"], profile["shear"]["weights"])
+        self.assertGreater(right_score, profile["shear"]["threshold"])
+        self.assertLess(left_score, -profile["shear"]["threshold"])
+        for key, before, after in (("press_before", "press_before", "press_after"),
+                                   ("press", "press_before", "press_after"),
+                                   ("press_after", "press_before", "press_after"),
+                                   ("right_before", "right_before", "right_after"),
+                                   ("right_after", "right_before", "right_after"),
+                                   ("left_before", "left_before", None)):
+            for increment in adjusted(key, before, after):
+                score = signed_score(increment, profile["shear"]["pressLeak"], profile["shear"]["weights"])
+                self.assertLess(abs(score), profile["shear"]["threshold"])
+
+    def test_zero_left_action_is_rejected(self):
+        windows = make_windows()
+        for sample in windows["left"]["samples"]:
+            sample["channels"] = copy.copy(windows["left_before"]["samples"][0]["channels"])
+        with self.assertRaises(ValueError):
+            build_profile(windows)
+
+    def test_bad_or_missing_evidence_is_rejected(self):
+        windows = make_windows()
+        windows["right"]["samples"][5]["status"] = "waiting"
+        with self.assertRaises(ValueError):
+            build_profile(windows)
+        windows = make_windows()
+        del windows["left_before"]
+        with self.assertRaises(ValueError):
+            build_profile(windows)
+
+
+if __name__ == "__main__":
+    unittest.main()
diff --git a/demo_web/shear_demo_profile.json b/demo_web/shear_demo_profile.json
new file mode 100644
index 0000000..800f3f8
--- /dev/null
+++ b/demo_web/shear_demo_profile.json
@@ -0,0 +1,46 @@
+{
+  "version": 1,
+  "mode": "qualitative",
+  "assemblyId": "coinft-current-20260925",
+  "normal": {
+    "threshold": 100.0,
+    "span": 600.0
+  },
+  "shear": {
+    "enabled": true,
+    "weights": [
+      0.5119536167478967,
+      -0.5584936703500715,
+      -0.19694140021121337,
+      0.2151686779046843,
+      -0.03406743093409363,
+      -0.07274013968644583,
+      0.47086415199790316,
+      -0.33576788411117126
+    ],
+    "pressLeak": [
+      -0.1520362353695687,
+      0.06697931697931699,
+      -0.10433702100368768,
+      0.1590909090909091,
+      0.08678050344717012,
+      0.2626663459996793,
+      -0.013427930094596762,
+      -0.302348885682219
+    ],
+    "threshold": 99.11124275398228,
+    "span": 128.5109264230957
+  },
+  "rightLabel": "−X",
+  "leftLabel": "+X",
+  "evidence": [
+    "demo_train_empty_before_press_20260925.json",
+    "demo_train_press_20260925.json",
+    "demo_train_empty_after_press_20260925.json",
+    "demo_train_empty_before_right_20260925.json",
+    "demo_train_right_20260925.json",
+    "demo_train_empty_after_right_20260925.json",
+    "demo_diagnostic_empty_after_second_usb_20260925.json",
+    "demo_diagnostic_left_demo_force_20260925.json"
+  ]
+}
\ No newline at end of file
