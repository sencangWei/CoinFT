# CoinFT qualitative demo aggregate code review

No Git repository; Task 1 new-file diffs and Task 2 baseline-to-final no-index diffs follow.

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

# Task 2 re-review package

No Git repository: complete no-index diff from pre-task snapshots after fixes.
diff --git "a/D:\\semg.claude\\coinft\\.superpowers\\sdd\\qualitative-task-2-before\\app.js" "b/demo_web\\app.js"
index 0b0a8ea..7a6acff 100644
--- "a/D:\\semg.claude\\coinft\\.superpowers\\sdd\\qualitative-task-2-before\\app.js"
+++ "b/demo_web\\app.js"
@@ -9,6 +9,7 @@ const torqueCanvas = document.getElementById("torque-chart");
 const surfaceView = createSurface(document.getElementById("surface-canvas"));
 let shearProfile = disabledSurfaceProfile;
 let lastSurfaceFrameAt = 0;
+let demoBaseline = null, demoZeroSamples = [], demoZeroStartedAt = 0, demoZeroFrame = -1;
 let tareGeneration = 0;
 let tareFrame = -1;
 let tarePending = false;
@@ -37,6 +38,17 @@ function validShearProfile(profile) {
 async function loadShearProfile() {
   try {
     const response = await fetch("/shear_profile.json", { cache: "no-store" });
+    if (response.status === 404) {
+      const demoResponse = await fetch("/shear_demo_profile.json", { cache: "no-store" });
+      if (!demoResponse.ok) throw new Error(`HTTP ${demoResponse.status}`);
+      const demoProfile = await demoResponse.json();
+      if (!validShearProfile(demoProfile) || demoProfile.mode !== "qualitative")
+        throw new Error("Invalid qualitative profile");
+      shearProfile = demoProfile;
+      surfaceView.clear();
+      updateDemoZero(lastSurfaceFrameAt > 0 && performance.now() - lastSurfaceFrameAt < 500);
+      return;
+    }
     if (!response.ok) throw new Error(`HTTP ${response.status}`);
     const profile = await response.json();
     if (!validShearProfile(profile)) throw new Error("Invalid shear profile");
@@ -47,6 +59,7 @@ async function loadShearProfile() {
   } catch (_) {
     shearProfile = disabledSurfaceProfile;
   }
+  updateDemoZero();
 }
 loadShearProfile();
 const histories = Array.from({ length: 6 }, () => []);
@@ -59,6 +72,23 @@ let lastChannels = Array(12).fill(0);
 let fetching = false;
 let displayCleared = false;
 
+function updateDemoZero(ready = false) {
+  const qualitative = shearProfile.mode === "qualitative";
+  document.getElementById("demo-zero").disabled = !qualitative || !ready || tarePending;
+  if (qualitative) document.querySelector(".surface-label").textContent =
+    `定性演示 · 非标定力值 · 方向未经过独立验收 · ${demoBaseline ? "画面已归零" :
+      demoZeroFrame >= 0 ? "采集空载中" : "未归零"}`;
+}
+
+function invalidateDemoZero() {
+  demoBaseline = null;
+  demoZeroSamples = [];
+  demoZeroStartedAt = 0;
+  demoZeroFrame = -1;
+  surfaceView.clear();
+  updateDemoZero();
+}
+
 groupWindows.forEach((_, i) => {
   const row = document.createElement("div");
   row.className = "axis-row";
@@ -113,6 +143,7 @@ function paintBars(axes, groups, channels) {
 }
 
 function clearDisplay() {
+  invalidateDemoZero();
   surfaceView.clear();
   lastSurfaceFrameAt = 0;
   latestFrame = -1;
@@ -167,6 +198,9 @@ function drawChart(canvas, start) {
 }
 
 function updateStatus(data) {
+  const good = data.status === "live" && data.invalid_recent === 0 &&
+    data.saturated_recent === 0;
+  if (!good) invalidateDemoZero();
   const pill = document.getElementById("status-pill");
   pill.classList.toggle("good", data.status === "live" && !data.invalid_recent && !data.saturated_recent);
   pill.classList.toggle("bad", data.status === "error" || data.invalid_recent > 0 || data.saturated_recent > 0);
@@ -223,12 +257,39 @@ async function poll() {
       }
     }
     updateStatus(data);
+    if (shearProfile.mode === "qualitative" && data.status === "live" &&
+        (!Array.isArray(data.channels) || data.channels.length !== 12 ||
+         !data.channels.every(Number.isFinite))) {
+      invalidateDemoZero();
+      lastSurfaceFrameAt = 0;
+      return;
+    }
     if (data.status === "live" && data.frames !== latestFrame) {
       if (Number.isInteger(data.frames) && data.frames > latestFrame &&
           data.invalid_recent === 0 && data.saturated_recent === 0) {
-        surfaceView.set(data.channels, shearProfile);
+        if (shearProfile.mode === "qualitative") {
+          if (demoZeroFrame >= 0 && data.frames > demoZeroFrame) {
+            if (!demoZeroSamples.length) demoZeroStartedAt = performance.now();
+            demoZeroSamples.push([...data.channels]);
+            demoZeroFrame = data.frames;
+            if (demoZeroSamples.length >= 10 &&
+                performance.now() - demoZeroStartedAt >= 1000) {
+              demoBaseline = Array.from({ length: 12 }, (_, i) =>
+                median(demoZeroSamples.map(sample => sample[i])));
+              demoZeroSamples = [];
+              demoZeroStartedAt = 0;
+              demoZeroFrame = -1;
+              updateDemoZero(true);
+            }
+          }
+          if (demoBaseline) surfaceView.set(data.channels.map((value, i) =>
+            value - demoBaseline[i]), shearProfile);
+          else surfaceView.clear();
+        } else surfaceView.set(data.channels, shearProfile);
         lastSurfaceFrameAt = performance.now();
+        updateDemoZero(true);
       } else {
+        invalidateDemoZero();
         surfaceView.clear();
         lastSurfaceFrameAt = 0;
       }
@@ -249,12 +310,16 @@ async function poll() {
       drawChart(forceCanvas, 0);
       drawChart(torqueCanvas, 3);
     } else if (data.status === "live" &&
-               (data.invalid_recent !== 0 || data.saturated_recent !== 0 ||
+               (shearProfile.mode === "qualitative" ||
+                data.invalid_recent !== 0 || data.saturated_recent !== 0 ||
                 !lastSurfaceFrameAt || performance.now() - lastSurfaceFrameAt > 500)) {
+      invalidateDemoZero();
       surfaceView.clear();
+      if (shearProfile.mode === "qualitative") lastSurfaceFrameAt = 0;
     }
   } catch (error) {
     if (requestGeneration !== tareGeneration) return;
+    invalidateDemoZero();
     document.getElementById("status-label").textContent = "页面与采集服务断开";
     document.getElementById("foot-status").textContent = String(error);
     document.getElementById("stream-tag").textContent = "SIGNAL STANDBY";
@@ -279,7 +344,16 @@ gainInput.addEventListener("input", () => {
   drawChart(forceCanvas, 0);
   drawChart(torqueCanvas, 3);
 });
+document.getElementById("demo-zero").addEventListener("click", () => {
+  demoBaseline = null;
+  demoZeroSamples = [];
+  demoZeroStartedAt = 0;
+  demoZeroFrame = latestFrame;
+  surfaceView.clear();
+  updateDemoZero(true);
+});
 document.getElementById("tare").addEventListener("click", async () => {
+  invalidateDemoZero();
   const button = document.getElementById("tare");
   button.disabled = true;
   tareGeneration += 1;
@@ -302,6 +376,7 @@ document.getElementById("tare").addEventListener("click", async () => {
     sawTaring = false;
     button.disabled = displayCleared;
   }
+  invalidateDemoZero();
 });
 document.getElementById("fullscreen").addEventListener("click", () => {
   if (document.fullscreenElement) document.exitFullscreen(); else document.documentElement.requestFullscreen();
@@ -320,6 +395,7 @@ poll();
 setInterval(poll, 50);
 setInterval(() => {
   if (lastSurfaceFrameAt && performance.now() - lastSurfaceFrameAt >= 500) {
+    invalidateDemoZero();
     surfaceView.clear();
     lastSurfaceFrameAt = 0;
   }
diff --git "a/D:\\semg.claude\\coinft\\.superpowers\\sdd\\qualitative-task-2-before\\surface.js" "b/demo_web\\surface.js"
index 21139f3..c3f440e 100644
--- "a/D:\\semg.claude\\coinft\\.superpowers\\sdd\\qualitative-task-2-before\\surface.js"
+++ "b/demo_web\\surface.js"
@@ -46,7 +46,7 @@ function shearLevel(channels, profile = disabledSurfaceProfile, active = false)
   const normal = normalScore(channels);
   const score = channels.slice(0, 8).reduce((sum, value, i) =>
     sum + shear.weights[i] * (value - avg - shear.pressLeak[i] * normal), 0);
-  const threshold = shear.threshold * (active ? 0.7 : 1);
+  const threshold = shear.threshold * (profile.mode === "qualitative" ? 1 : (active ? 0.7 : 1));
   return Math.sign(score) * Math.max(0,
     Math.min(1, (Math.abs(score) - threshold) / shear.span));
 }
diff --git "a/D:\\semg.claude\\coinft\\.superpowers\\sdd\\qualitative-task-2-before\\index.html" "b/demo_web\\index.html"
index 7acf819..84a8bd0 100644
--- "a/D:\\semg.claude\\coinft\\.superpowers\\sdd\\qualitative-task-2-before\\index.html"
+++ "b/demo_web\\index.html"
@@ -55,6 +55,7 @@
             <label for="gain"><span>趋势显示灵敏度</span><strong id="gain-value">2.0×</strong></label>
             <input id="gain" type="range" min="0.5" max="5" step="0.1" value="2" aria-label="显示灵敏度">
             <button id="tare" type="button" disabled>空载归零 <span>↺</span></button>
+            <button id="demo-zero" type="button" disabled>演示归零（仅画面）</button>
           </div>
         </section>
       </div>
diff --git "a/D:\\semg.claude\\coinft\\.superpowers\\sdd\\qualitative-task-2-before\\style.css" "b/demo_web\\style.css"
index 7216277..f0b3e69 100644
--- "a/D:\\semg.claude\\coinft\\.superpowers\\sdd\\qualitative-task-2-before\\style.css"
+++ "b/demo_web\\style.css"
@@ -5,3 +5,4 @@
 .channel-card.over-range{border-color:#db9b6b;box-shadow:inset 0 0 0 1px #db9b6b66}.channel-card.over-range .channel-top strong{color:#ffd4b2}
 #surface-canvas{position:absolute;inset:0;width:100%;height:100%;margin:0}
 .surface-label{color:#dceea3!important;letter-spacing:.14em!important}
+.controls button + button{margin-top:8px}
diff --git "a/D:\\semg.claude\\coinft\\.superpowers\\sdd\\qualitative-task-2-before\\test_demo_ui.py" "b/tests\\test_demo_ui.py"
index 746bc97..4b0d757 100644
--- "a/D:\\semg.claude\\coinft\\.superpowers\\sdd\\qualitative-task-2-before\\test_demo_ui.py"
+++ "b/tests\\test_demo_ui.py"
@@ -23,6 +23,403 @@ class FakeSource:
 
 
 class DashboardWarningTests(unittest.TestCase):
+    def test_qualitative_repeated_good_frame_cancels_zero_and_requires_new_click(self):
+        class Source(FakeSource):
+            frames = 200
+            automatic = False
+            channels = [700] * 12
+
+            def snapshot(self):
+                if self.automatic:
+                    self.frames += 1
+                state = super().snapshot()
+                state.update(frames=self.frames, channels=self.channels, invalid_recent=0)
+                return state
+
+        profile = {
+            "version": 1, "mode": "qualitative", "assemblyId": "synthetic",
+            "normal": {"threshold": 100, "span": 600},
+            "shear": {"enabled": True, "weights": [0.125] * 4 + [-0.125] * 4,
+                      "pressLeak": [0] * 8, "threshold": 20, "span": 80},
+            "rightLabel": "−X", "leftLabel": "+X", "evidence": ["synthetic.json"],
+        }
+        source = Source()
+        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(source))
+        threading.Thread(target=server.serve_forever, daemon=True).start()
+        try:
+            with sync_playwright() as playwright:
+                browser = playwright.chromium.launch(headless=True)
+                page = browser.new_page(reduced_motion="reduce")
+                page.add_init_script("""(() => {
+                    const original = window.setInterval;
+                    window.setInterval = (callback, delay) => {
+                        const id = original(callback, delay);
+                        if (callback.name === 'poll') window.testPollTimer = id;
+                        return id;
+                    };
+                })()""")
+                page.route("**/shear_profile.json", lambda route: route.fulfill(status=404))
+                page.route("**/shear_demo_profile.json", lambda route: route.fulfill(
+                    status=200, content_type="application/json", body=json.dumps(profile)))
+                page.goto(f"http://127.0.0.1:{server.server_port}/")
+                page.wait_for_function("shearProfile.mode === 'qualitative'")
+                page.evaluate("clearInterval(testPollTimer)")
+                source.frames += 1
+                page.evaluate("poll()")
+                self.assertFalse(page.locator("#demo-zero").is_disabled())
+                page.locator("#demo-zero").click()
+                source.frames += 1
+                page.evaluate("poll()")
+                self.assertEqual(page.evaluate("demoZeroSamples.length"), 1)
+                page.evaluate("poll()")
+                self.assertEqual(page.evaluate("[demoBaseline, demoZeroSamples.length, demoZeroFrame]"),
+                                 [None, 0, -1])
+                source.automatic = True
+                page.evaluate("poll()")
+                page.locator("#demo-zero").click()
+                for _ in range(24):
+                    page.wait_for_timeout(55)
+                    page.evaluate("poll()")
+                    if page.evaluate("demoBaseline !== null"):
+                        break
+                self.assertIsNotNone(page.evaluate("demoBaseline"))
+                source.automatic = False
+                page.evaluate("poll()")
+                self.assertIsNone(page.evaluate("demoBaseline"))
+                self.assertEqual(page.evaluate("[surfaceView.target, surfaceView.shearTarget]"), [0, 0])
+
+                source.automatic = True
+                page.evaluate("poll()")
+                page.locator("#demo-zero").click()
+                page.evaluate("poll()")
+                self.assertEqual(page.evaluate("demoZeroSamples.length"), 1)
+                source.channels = [None] + [700] * 11
+                page.evaluate("poll()")
+                self.assertEqual(page.evaluate("[demoBaseline, demoZeroSamples.length, demoZeroFrame]"),
+                                 [None, 0, -1])
+                source.channels = [700] * 12
+                for _ in range(24):
+                    page.wait_for_timeout(55)
+                    page.evaluate("poll()")
+                self.assertIsNone(page.evaluate("demoBaseline"))
+                self.assertEqual(page.evaluate("[surfaceView.target, surfaceView.shearTarget]"), [0, 0])
+                page.locator("#demo-zero").click()
+                for _ in range(24):
+                    page.wait_for_timeout(55)
+                    page.evaluate("poll()")
+                    if page.evaluate("demoBaseline !== null"):
+                        break
+                self.assertIsNotNone(page.evaluate("demoBaseline"))
+                browser.close()
+        finally:
+            server.shutdown()
+            server.server_close()
+
+    def test_qualitative_malformed_channels_cancel_ready_baseline(self):
+        class Source(FakeSource):
+            frames = 200
+            channels = [700] * 12
+
+            def snapshot(self):
+                state = super().snapshot()
+                state.update(frames=self.frames, channels=self.channels, invalid_recent=0)
+                return state
+
+        profile = {
+            "version": 1, "mode": "qualitative", "assemblyId": "synthetic",
+            "normal": {"threshold": 100, "span": 600},
+            "shear": {"enabled": True, "weights": [0.125] * 4 + [-0.125] * 4,
+                      "pressLeak": [0] * 8, "threshold": 20, "span": 80},
+            "rightLabel": "−X", "leftLabel": "+X", "evidence": ["synthetic.json"],
+        }
+        source = Source()
+        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(source))
+        threading.Thread(target=server.serve_forever, daemon=True).start()
+        try:
+            with sync_playwright() as playwright:
+                browser = playwright.chromium.launch(headless=True)
+                page = browser.new_page(reduced_motion="reduce")
+                page.route("**/shear_profile.json", lambda route: route.fulfill(status=404))
+                page.route("**/shear_demo_profile.json", lambda route: route.fulfill(
+                    status=200, content_type="application/json", body=json.dumps(profile)))
+                page.goto(f"http://127.0.0.1:{server.server_port}/")
+                page.wait_for_function("shearProfile.mode === 'qualitative'")
+                for malformed in ([700] * 11, [None] + [700] * 11, None):
+                    source.channels = [700] * 12
+                    source.frames += 1
+                    page.wait_for_function(f"latestFrame === {source.frames}")
+                    page.evaluate("demoBaseline = Array(12).fill(0)")
+                    source.frames += 1
+                    page.wait_for_function("surfaceView.target === 1")
+                    source.channels = malformed
+                    source.frames += 1
+                    page.wait_for_function("!fetching")
+                    page.evaluate("poll()")
+                    self.assertIsNone(page.evaluate("demoBaseline"))
+                    self.assertEqual(page.evaluate("surfaceView.target"), 0)
+                    self.assertIn("未归零", page.locator(".surface-label").inner_text())
+                browser.close()
+        finally:
+            server.shutdown()
+            server.server_close()
+
+    def test_qualitative_zero_needs_ten_frames_spanning_one_second(self):
+        class Source(FakeSource):
+            frames = 200
+
+            def snapshot(self):
+                state = super().snapshot()
+                state.update(frames=self.frames, channels=[250] * 12, invalid_recent=0)
+                return state
+
+        profile = {
+            "version": 1, "mode": "qualitative", "assemblyId": "synthetic",
+            "normal": {"threshold": 100, "span": 600},
+            "shear": {"enabled": True, "weights": [0.125] * 4 + [-0.125] * 4,
+                      "pressLeak": [0] * 8, "threshold": 20, "span": 80},
+            "rightLabel": "−X", "leftLabel": "+X", "evidence": ["synthetic.json"],
+        }
+        source = Source()
+        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(source))
+        threading.Thread(target=server.serve_forever, daemon=True).start()
+        try:
+            with sync_playwright() as playwright:
+                browser = playwright.chromium.launch(headless=True)
+                page = browser.new_page(reduced_motion="reduce")
+                page.add_init_script("""(() => {
+                    const original = window.setInterval;
+                    window.setInterval = (callback, delay) => {
+                        const id = original(callback, delay);
+                        if (callback.name === 'poll') window.testPollTimer = id;
+                        return id;
+                    };
+                })()""")
+                page.route("**/shear_profile.json", lambda route: route.fulfill(status=404))
+                page.route("**/shear_demo_profile.json", lambda route: route.fulfill(
+                    status=200, content_type="application/json", body=json.dumps(profile)))
+                page.goto(f"http://127.0.0.1:{server.server_port}/")
+                page.wait_for_function("shearProfile.mode === 'qualitative' && latestFrame === 200")
+                page.evaluate("clearInterval(testPollTimer)")
+
+                def next_frame(delay=0):
+                    page.wait_for_timeout(delay)
+                    source.frames += 1
+                    page.evaluate("poll()")
+
+                page.locator("#demo-zero").click()
+                page.evaluate("window.testClickAt = performance.now()")
+                page.wait_for_timeout(350)
+                for _ in range(10):
+                    next_frame(50)
+                while page.evaluate("performance.now() - testClickAt < 1100"):
+                    next_frame(100)
+                self.assertGreaterEqual(page.evaluate("demoZeroSamples.length"), 10)
+                self.assertIsNone(page.evaluate("demoBaseline"))
+                while page.evaluate("demoBaseline === null"):
+                    next_frame(100)
+                self.assertEqual(page.evaluate("demoBaseline"), [250] * 12)
+
+                page.locator("#demo-zero").click()
+                for _ in range(4):
+                    next_frame(350)
+                self.assertGreaterEqual(page.evaluate("performance.now() - demoZeroStartedAt"), 1000)
+                self.assertEqual(page.evaluate("demoZeroSamples.length"), 4)
+                self.assertIsNone(page.evaluate("demoBaseline"))
+                browser.close()
+        finally:
+            server.shutdown()
+            server.server_close()
+
+    def test_qualitative_grid_requires_visual_zero_and_preserves_raw_readouts(self):
+        class Source(FakeSource):
+            frames = 200
+            channels = [250.0] * 12
+            status = "live"
+
+            def snapshot(self):
+                self.frames += 1
+                state = super().snapshot()
+                state.update(frames=self.frames, channels=self.channels, status=self.status,
+                             invalid_recent=0)
+                return state
+
+        profile = {
+            "version": 1, "mode": "qualitative", "assemblyId": "synthetic",
+            "normal": {"threshold": 100, "span": 600},
+            "shear": {"enabled": True, "weights": [0.125] * 4 + [-0.125] * 4,
+                      "pressLeak": [0] * 8, "threshold": 20, "span": 80},
+            "rightLabel": "−X", "leftLabel": "+X", "evidence": ["synthetic.json"],
+        }
+        source = Source()
+        evidence = Path(__file__).resolve().parents[1] / ".superpowers" / "sdd"
+        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(source))
+        threading.Thread(target=server.serve_forever, daemon=True).start()
+        try:
+            with sync_playwright() as playwright:
+                browser = playwright.chromium.launch(headless=True)
+                page = browser.new_page(reduced_motion="reduce", viewport={"width": 390, "height": 844})
+                page.route("**/shear_profile.json", lambda route: route.fulfill(status=404))
+                page.route("**/shear_demo_profile.json", lambda route: route.fulfill(
+                    status=200, content_type="application/json", body=json.dumps(profile)))
+                page.goto(f"http://127.0.0.1:{server.server_port}/")
+                page.wait_for_function("shearProfile.mode === 'qualitative' && latestFrame > 200")
+                self.assertEqual(page.evaluate("[surfaceView.target, surfaceView.shearTarget]"), [0, 0])
+                self.assertIn("未经过独立验收", page.locator(".surface-label").inner_text())
+                self.assertFalse(page.locator("#demo-zero").is_disabled())
+                page.screenshot(path=str(evidence / "task-2-mobile-empty.png"), full_page=True)
+                page.locator("#demo-zero").click()
+                page.wait_for_function("demoBaseline !== null", timeout=2500)
+                self.assertEqual(page.evaluate("demoBaseline"), [250] * 12)
+                source.channels = [250] * 8 + [950] * 4
+                source.frames += 1
+                page.wait_for_function("surfaceView.target > 0 && surfaceView.shearTarget === 0")
+                page.screenshot(path=str(evidence / "task-2-mobile-press.png"), full_page=True)
+                self.assertEqual(page.locator(".channel-card strong").nth(8).inner_text(), "+950")
+                page.wait_for_function("document.querySelectorAll('.axis-value')[4].textContent === '950'")
+                self.assertEqual(page.locator(".axis-value").nth(4).inner_text(), "950")
+                self.assertEqual(page.evaluate("histories[0].at(-1)"), 0)
+                source.channels = [350] * 4 + [150] * 4 + [250] * 4
+                source.frames += 1
+                page.wait_for_function("surfaceView.shearTarget > 0 && surfaceView.shearLevel === surfaceView.shearTarget")
+                page.screenshot(path=str(evidence / "task-2-mobile-right.png"), full_page=True)
+                source.channels = [150] * 4 + [350] * 4 + [250] * 4
+                source.frames += 1
+                page.wait_for_function("surfaceView.shearTarget < 0 && surfaceView.shearLevel === surfaceView.shearTarget")
+                page.screenshot(path=str(evidence / "task-2-mobile-left.png"), full_page=True)
+                page.set_viewport_size({"width": 1440, "height": 900})
+                page.screenshot(path=str(evidence / "task-2-desktop-left.png"), full_page=True)
+                self.assertLessEqual(page.evaluate("document.documentElement.scrollWidth"), 1440)
+                source.channels = [350] * 4 + [150] * 4 + [250] * 4
+                source.frames += 1
+                page.wait_for_function("surfaceView.shearTarget > 0")
+                page.screenshot(path=str(evidence / "task-2-desktop-right.png"), full_page=True)
+                source.channels = [250] * 8 + [950] * 4
+                source.frames += 1
+                page.wait_for_function("surfaceView.target > 0 && surfaceView.shearTarget === 0")
+                page.screenshot(path=str(evidence / "task-2-desktop-press.png"), full_page=True)
+                source.channels = [250] * 12
+                source.frames += 1
+                page.wait_for_function("surfaceView.target === 0 && surfaceView.shearTarget === 0")
+                page.screenshot(path=str(evidence / "task-2-desktop-empty.png"), full_page=True)
+                source.status = "waiting"
+                page.wait_for_function("demoBaseline === null && surfaceView.shearTarget === 0")
+                source.status = "live"
+                source.frames += 1
+                page.wait_for_function("document.getElementById('status-label').textContent === '数据正常'")
+                self.assertEqual(page.evaluate("[surfaceView.target, surfaceView.shearTarget]"), [0, 0])
+                page.set_viewport_size({"width": 390, "height": 844})
+                self.assertLessEqual(page.evaluate("document.documentElement.scrollWidth"), 390)
+                browser.close()
+        finally:
+            server.shutdown()
+            server.server_close()
+
+    def test_strict_disabled_profile_prevents_qualitative_fallback(self):
+        strict = {
+            "version": 1, "assemblyId": "strict", "normal": {"threshold": 100, "span": 600},
+            "shear": {"enabled": False, "weights": [0] * 8, "pressLeak": [0] * 8,
+                      "threshold": 1, "span": 1}, "rightLabel": "right", "leftLabel": "left",
+            "evidence": ["strict.json"],
+        }
+        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(FakeSource()))
+        threading.Thread(target=server.serve_forever, daemon=True).start()
+        try:
+            with sync_playwright() as playwright:
+                browser = playwright.chromium.launch(headless=True)
+                page = browser.new_page()
+                calls = []
+                page.route("**/shear_profile.json", lambda route: route.fulfill(
+                    status=200, content_type="application/json", body=json.dumps(strict)))
+                page.route("**/shear_demo_profile.json", lambda route: calls.append(1) or route.abort())
+                page.goto(f"http://127.0.0.1:{server.server_port}/")
+                page.wait_for_function("shearProfile.assemblyId === 'strict'")
+                self.assertEqual(calls, [])
+                self.assertTrue(page.locator("#demo-zero").is_disabled())
+                browser.close()
+        finally:
+            server.shutdown()
+            server.server_close()
+
+    def test_qualitative_baseline_invalidates_on_stream_faults_and_tare(self):
+        class Source(FakeSource):
+            frames = 200
+            status = "live"
+            invalid_recent = 0
+            saturated_recent = 0
+
+            def snapshot(self):
+                state = super().snapshot()
+                state.update(frames=self.frames, status=self.status,
+                             channels=[700] * 12, invalid_recent=self.invalid_recent,
+                             saturated_recent=self.saturated_recent)
+                return state
+
+        profile = {
+            "version": 1, "mode": "qualitative", "assemblyId": "synthetic",
+            "normal": {"threshold": 100, "span": 600},
+            "shear": {"enabled": True, "weights": [0.125] * 4 + [-0.125] * 4,
+                      "pressLeak": [0] * 8, "threshold": 20, "span": 80},
+            "rightLabel": "−X", "leftLabel": "+X", "evidence": ["synthetic.json"],
+        }
+        source = Source()
+        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(source))
+        threading.Thread(target=server.serve_forever, daemon=True).start()
+        try:
+            with sync_playwright() as playwright:
+                browser = playwright.chromium.launch(headless=True)
+                page = browser.new_page(reduced_motion="reduce")
+                page.route("**/shear_profile.json", lambda route: route.fulfill(status=404))
+                page.route("**/shear_demo_profile.json", lambda route: route.fulfill(
+                    status=200, content_type="application/json", body=json.dumps(profile)))
+                page.goto(f"http://127.0.0.1:{server.server_port}/")
+                page.wait_for_function("shearProfile.mode === 'qualitative' && latestFrame === 200")
+
+                def seed_grid():
+                    source.status = "live"
+                    source.invalid_recent = source.saturated_recent = 0
+                    source.frames += 1
+                    page.wait_for_function(f"latestFrame === {source.frames}")
+                    page.evaluate("demoBaseline = Array(12).fill(0)")
+                    source.frames += 1
+                    page.wait_for_function("surfaceView.target === 1")
+
+                def assert_invalidated():
+                    page.wait_for_function("demoBaseline === null && surfaceView.target === 0")
+                    self.assertEqual(page.evaluate("[surfaceView.level, surfaceView.shearTarget]"), [0, 0])
+                    self.assertIn("未归零", page.locator(".surface-label").inner_text())
+
+                seed_grid()
+                source.status = "waiting"
+                assert_invalidated()
+                seed_grid()
+                source.invalid_recent = 1
+                source.frames += 1
+                assert_invalidated()
+                seed_grid()
+                source.saturated_recent = 1
+                source.frames += 1
+                assert_invalidated()
+                seed_grid()
+                source.frames -= 1
+                assert_invalidated()
+                source.frames += 2
+                seed_grid()
+                page.route("**/api/state", lambda route: route.fulfill(status=503))
+                assert_invalidated()
+                page.unroute("**/api/state")
+                seed_grid()
+                page.route("**/api/tare", lambda route: route.fulfill(status=503))
+                page.locator("#tare").click()
+                assert_invalidated()
+                source.frames += 1
+                seed_grid()
+                page.wait_for_function("demoBaseline === null && surfaceView.target === 0", timeout=2000)
+                self.assertTrue(page.locator("#demo-zero").is_disabled())
+                browser.close()
+        finally:
+            server.shutdown()
+            server.server_close()
+
     def test_older_frame_cannot_lower_surface_high_water(self):
         class ChangingSource(FakeSource):
             frames = 200
@@ -41,6 +438,7 @@ class DashboardWarningTests(unittest.TestCase):
             with sync_playwright() as playwright:
                 browser = playwright.chromium.launch(headless=True)
                 page = browser.new_page(reduced_motion="reduce")
+                page.route("**/shear_demo_profile.json", lambda route: route.fulfill(status=404))
                 page.goto(f"http://127.0.0.1:{server.server_port}/")
                 page.wait_for_function("surfaceView.target === 1 && latestFrame === 200")
                 source.frames = 199
@@ -73,6 +471,7 @@ class DashboardWarningTests(unittest.TestCase):
             with sync_playwright() as playwright:
                 browser = playwright.chromium.launch(headless=True)
                 page = browser.new_page(reduced_motion="reduce")
+                page.route("**/shear_demo_profile.json", lambda route: route.fulfill(status=404))
                 page.goto(f"http://127.0.0.1:{server.server_port}/")
                 page.wait_for_function("surfaceView.target === 1 && latestFrame === 200")
                 page.route("**/api/tare", lambda route: route.fulfill(status=503))
@@ -106,6 +505,7 @@ class DashboardWarningTests(unittest.TestCase):
             with sync_playwright() as playwright:
                 browser = playwright.chromium.launch(headless=True)
                 page = browser.new_page(reduced_motion="reduce")
+                page.route("**/shear_demo_profile.json", lambda route: route.fulfill(status=404))
                 page.goto(f"http://127.0.0.1:{server.server_port}/")
                 page.wait_for_function("surfaceView.target === 1 && latestFrame === 200")
                 page.evaluate("""() => {
@@ -250,6 +650,7 @@ class DashboardWarningTests(unittest.TestCase):
                 browser = playwright.chromium.launch(headless=True)
                 page = browser.new_page(reduced_motion="reduce")
                 page.route("**/shear_profile.json", lambda route: route.fulfill(status=404))
+                page.route("**/shear_demo_profile.json", lambda route: route.fulfill(status=404))
                 page.goto(f"http://127.0.0.1:{server.server_port}/")
                 page.evaluate("surfaceView.set([200,200,200,200,-200,-200,-200,-200,0,0,0,0])")
                 self.assertEqual(page.evaluate("surfaceView.shearTarget"), 0)
@@ -328,6 +729,7 @@ class DashboardWarningTests(unittest.TestCase):
             with sync_playwright() as playwright:
                 browser = playwright.chromium.launch(headless=True)
                 page = browser.new_page(reduced_motion="reduce")
+                page.route("**/shear_demo_profile.json", lambda route: route.fulfill(status=404))
                 page.goto(f"http://127.0.0.1:{server.server_port}/")
                 page.wait_for_function("surfaceView.target === 1 && surfaceView.level === 1")
                 page.evaluate("""() => {
@@ -373,6 +775,7 @@ class DashboardWarningTests(unittest.TestCase):
             with sync_playwright() as playwright:
                 browser = playwright.chromium.launch(headless=True)
                 page = browser.new_page(reduced_motion="reduce")
+                page.route("**/shear_demo_profile.json", lambda route: route.fulfill(status=404))
                 page.goto(f"http://127.0.0.1:{server.server_port}/")
                 page.wait_for_function("surfaceView.target === 0.5")
                 page.evaluate("""() => {
@@ -458,6 +861,7 @@ class DashboardWarningTests(unittest.TestCase):
                 browser = playwright.chromium.launch(headless=True)
                 page = browser.new_page(viewport={"width": 1440, "height": 900},
                                         reduced_motion="no-preference")
+                page.route("**/shear_demo_profile.json", lambda route: route.fulfill(status=404))
                 errors = []
                 page.on("pageerror", lambda error: errors.append(str(error)))
                 page.goto(f"http://127.0.0.1:{server.server_port}/")
@@ -521,6 +925,7 @@ class DashboardWarningTests(unittest.TestCase):
                     source.status = "live"
                     page = browser.new_page(viewport={"width": width, "height": height},
                                             reduced_motion="reduce")
+                    page.route("**/shear_demo_profile.json", lambda route: route.fulfill(status=404))
                     errors = []
                     page.on("pageerror", lambda error: errors.append(str(error)))
                     page.goto(f"http://127.0.0.1:{server.server_port}/")
@@ -586,6 +991,7 @@ class DashboardWarningTests(unittest.TestCase):
                 browser = playwright.chromium.launch(headless=True)
                 page = browser.new_page(viewport={"width": 390, "height": 844},
                                         reduced_motion="reduce")
+                page.route("**/shear_demo_profile.json", lambda route: route.fulfill(status=404))
                 errors = []
                 page.on("pageerror", lambda error: errors.append(str(error)))
                 page.goto(f"http://127.0.0.1:{server.server_port}/")
@@ -617,6 +1023,7 @@ class DashboardWarningTests(unittest.TestCase):
             with sync_playwright() as playwright:
                 browser = playwright.chromium.launch(headless=True)
                 page = browser.new_page()
+                page.route("**/shear_demo_profile.json", lambda route: route.fulfill(status=404))
                 page.goto(f"http://127.0.0.1:{server.server_port}/")
                 page.wait_for_function("surfaceView.target === 0")
                 source.channels = [400.0] * 12
@@ -645,6 +1052,7 @@ class DashboardWarningTests(unittest.TestCase):
             with sync_playwright() as playwright:
                 browser = playwright.chromium.launch(headless=True)
                 page = browser.new_page()
+                page.route("**/shear_demo_profile.json", lambda route: route.fulfill(status=404))
                 page.goto(f"http://127.0.0.1:{server.server_port}/")
                 self.assertEqual(page.locator("#surface-canvas").count(), 1)
                 self.assertIn("正压／剪切响应示意", page.locator(".surface-label").inner_text())
