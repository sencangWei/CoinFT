# Approved duplicate-batching fix: no-index diff from before fix

diff --git a/.superpowers/sdd/zero_fix_before_app_20260926.js b/demo_web/app.js
index 7a6acff..992592a 100644
--- a/.superpowers/sdd/zero_fix_before_app_20260926.js
+++ b/demo_web/app.js
@@ -303,22 +303,21 @@ async function poll() {
       });
       lastGroups = groupWindows.map(median);
       paintBars(data.axes, lastGroups, data.channels);
       data.axes.forEach((value, i) => {
         histories[i].push(value);
         if (histories[i].length > 180) histories[i].shift();
       });
       drawChart(forceCanvas, 0);
       drawChart(torqueCanvas, 3);
     } else if (data.status === "live" &&
-               (shearProfile.mode === "qualitative" ||
-                data.invalid_recent !== 0 || data.saturated_recent !== 0 ||
+               (data.invalid_recent !== 0 || data.saturated_recent !== 0 ||
                 !lastSurfaceFrameAt || performance.now() - lastSurfaceFrameAt > 500)) {
       invalidateDemoZero();
       surfaceView.clear();
       if (shearProfile.mode === "qualitative") lastSurfaceFrameAt = 0;
     }
   } catch (error) {
     if (requestGeneration !== tareGeneration) return;
     invalidateDemoZero();
     document.getElementById("status-label").textContent = "页面与采集服务断开";
     document.getElementById("foot-status").textContent = String(error);
diff --git a/.superpowers/sdd/zero_fix_before_tests_20260926.py b/tests/test_demo_ui.py
index 4b0d757..06e68cd 100644
--- a/.superpowers/sdd/zero_fix_before_tests_20260926.py
+++ b/tests/test_demo_ui.py
@@ -16,21 +16,21 @@ class FakeSource:
     def snapshot(self):
         return {
             "mode": "live", "status": "live", "message": "数据流正常", "port": "COM10",
             "axes": [0.0] * 6, "channels": [0.0] * 12, "raw": [10000] * 12,
             "rate": 200.0, "frames": 100, "resyncs": 0, "saturated_recent": 0,
             "invalid_frames": 3, "invalid_recent": 3, "tare_progress": 100,
         }
 
 
 class DashboardWarningTests(unittest.TestCase):
-    def test_qualitative_repeated_good_frame_cancels_zero_and_requires_new_click(self):
+    def test_qualitative_zero_survives_100ms_batches_and_50ms_duplicate_polls(self):
         class Source(FakeSource):
             frames = 200
             automatic = False
             channels = [700] * 12
 
             def snapshot(self):
                 if self.automatic:
                     self.frames += 1
                 state = super().snapshot()
                 state.update(frames=self.frames, channels=self.channels, invalid_recent=0)
@@ -64,38 +64,50 @@ class DashboardWarningTests(unittest.TestCase):
                 page.goto(f"http://127.0.0.1:{server.server_port}/")
                 page.wait_for_function("shearProfile.mode === 'qualitative'")
                 page.evaluate("clearInterval(testPollTimer)")
                 source.frames += 1
                 page.evaluate("poll()")
                 self.assertFalse(page.locator("#demo-zero").is_disabled())
                 page.locator("#demo-zero").click()
                 source.frames += 1
                 page.evaluate("poll()")
                 self.assertEqual(page.evaluate("demoZeroSamples.length"), 1)
+                first_sample_at, fresh_at = page.evaluate("[demoZeroStartedAt, lastSurfaceFrameAt]")
+                page.wait_for_timeout(50)
                 page.evaluate("poll()")
                 self.assertEqual(page.evaluate("[demoBaseline, demoZeroSamples.length, demoZeroFrame]"),
-                                 [None, 0, -1])
-                source.automatic = True
-                page.evaluate("poll()")
-                page.locator("#demo-zero").click()
-                for _ in range(24):
-                    page.wait_for_timeout(55)
+                                 [None, 1, source.frames])
+                self.assertEqual(page.evaluate("[demoZeroStartedAt, lastSurfaceFrameAt]"),
+                                 [first_sample_at, fresh_at])
+                for _ in range(14):
+                    page.wait_for_timeout(50)
+                    source.frames += 1
                     page.evaluate("poll()")
-                    if page.evaluate("demoBaseline !== null"):
-                        break
-                self.assertIsNotNone(page.evaluate("demoBaseline"))
-                source.automatic = False
+                    page.wait_for_timeout(50)
+                    page.evaluate("poll()")
+                self.assertEqual(page.evaluate("demoBaseline"), [700] * 12)
+                source.channels = [1400] * 12
+                source.frames += 1
+                page.evaluate("poll()")
+                self.assertEqual(page.evaluate("surfaceView.target"), 1)
+                fresh_at = page.evaluate("lastSurfaceFrameAt")
+                page.wait_for_timeout(50)
                 page.evaluate("poll()")
+                self.assertEqual(page.evaluate("demoBaseline"), [700] * 12)
+                self.assertEqual(page.evaluate("surfaceView.target"), 1)
+                self.assertEqual(page.evaluate("lastSurfaceFrameAt"), fresh_at)
+                page.wait_for_function("demoBaseline === null", timeout=1000)
                 self.assertIsNone(page.evaluate("demoBaseline"))
                 self.assertEqual(page.evaluate("[surfaceView.target, surfaceView.shearTarget]"), [0, 0])
 
                 source.automatic = True
+                source.channels = [700] * 12
                 page.evaluate("poll()")
                 page.locator("#demo-zero").click()
                 page.evaluate("poll()")
                 self.assertEqual(page.evaluate("demoZeroSamples.length"), 1)
                 source.channels = [None] + [700] * 11
                 page.evaluate("poll()")
                 self.assertEqual(page.evaluate("[demoBaseline, demoZeroSamples.length, demoZeroFrame]"),
                                  [None, 0, -1])
                 source.channels = [700] * 12
                 for _ in range(24):
@@ -103,20 +115,86 @@ class DashboardWarningTests(unittest.TestCase):
                     page.evaluate("poll()")
                 self.assertIsNone(page.evaluate("demoBaseline"))
                 self.assertEqual(page.evaluate("[surfaceView.target, surfaceView.shearTarget]"), [0, 0])
                 page.locator("#demo-zero").click()
                 for _ in range(24):
                     page.wait_for_timeout(55)
                     page.evaluate("poll()")
                     if page.evaluate("demoBaseline !== null"):
                         break
                 self.assertIsNotNone(page.evaluate("demoBaseline"))
+                page.locator("#demo-zero").click()
+                page.evaluate("poll()")
+                self.assertEqual(page.evaluate("demoZeroSamples.length"), 1)
+                page.wait_for_function("demoZeroFrame === -1 && demoZeroSamples.length === 0",
+                                       timeout=800)
+                page.evaluate("poll()")
+                self.assertIsNone(page.evaluate("demoBaseline"))
+                self.assertEqual(page.evaluate("[surfaceView.target, surfaceView.shearTarget]"), [0, 0])
+                browser.close()
+        finally:
+            server.shutdown()
+            server.server_close()
+
+    def test_qualitative_ready_duplicate_and_stalled_request_watchdog(self):
+        class Source(FakeSource):
+            frames = 200
+
+            def snapshot(self):
+                state = super().snapshot()
+                state.update(frames=self.frames, channels=[700] * 12, invalid_recent=0)
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
+                page.evaluate("demoBaseline = Array(12).fill(0)")
+                source.frames += 1
+                page.evaluate("poll()")
+                self.assertEqual(page.evaluate("surfaceView.target"), 1)
+                page.wait_for_timeout(50)
+                page.evaluate("poll()")
+                self.assertEqual(page.evaluate("demoBaseline"), [0] * 12)
+                self.assertEqual(page.evaluate("surfaceView.target"), 1)
+                page.evaluate("""() => {
+                    window.fetch = () => new Promise(() => {});
+                    void poll();
+                }""")
+                page.wait_for_function("fetching && demoBaseline === null && surfaceView.target === 0",
+                                       timeout=800)
+                self.assertEqual(page.evaluate("demoZeroSamples.length"), 0)
+                self.assertTrue(page.locator("#demo-zero").is_disabled())
                 browser.close()
         finally:
             server.shutdown()
             server.server_close()
 
     def test_qualitative_malformed_channels_cancel_ready_baseline(self):
         class Source(FakeSource):
             frames = 200
             channels = [700] * 12
 
@@ -145,21 +223,20 @@ class DashboardWarningTests(unittest.TestCase):
                 page.goto(f"http://127.0.0.1:{server.server_port}/")
                 page.wait_for_function("shearProfile.mode === 'qualitative'")
                 for malformed in ([700] * 11, [None] + [700] * 11, None):
                     source.channels = [700] * 12
                     source.frames += 1
                     page.wait_for_function(f"latestFrame === {source.frames}")
                     page.evaluate("demoBaseline = Array(12).fill(0)")
                     source.frames += 1
                     page.wait_for_function("surfaceView.target === 1")
                     source.channels = malformed
-                    source.frames += 1
                     page.wait_for_function("!fetching")
                     page.evaluate("poll()")
                     self.assertIsNone(page.evaluate("demoBaseline"))
                     self.assertEqual(page.evaluate("surfaceView.target"), 0)
                     self.assertIn("未归零", page.locator(".surface-label").inner_text())
                 browser.close()
         finally:
             server.shutdown()
             server.server_close()
 
