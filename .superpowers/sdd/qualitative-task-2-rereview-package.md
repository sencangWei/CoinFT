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
