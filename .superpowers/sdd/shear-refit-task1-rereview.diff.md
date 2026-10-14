# Task 1 refreshed no-Git review package (aggregate timeout fix)

Base: byte-preserving pre-task1 source snapshots. Head: current after initial implementation and approved timeout fix.
Review all current changes below; implementer reports full137/75.481s/exit0.

## calibration/capture_demo_pose.py

~~~diff
warning: in the working copy of 'D:\semg.claude\coinft\.superpowers\sdd\shear-refit-before-20260928\capture_demo_pose.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'D:\semg.claude\coinft\calibration\capture_demo_pose.py', LF will be replaced by CRLF the next time Git touches it
diff --git "a/D:\\semg.claude\\coinft\\.superpowers\\sdd\\shear-refit-before-20260928\\capture_demo_pose.py" "b/D:\\semg.claude\\coinft\\calibration\\capture_demo_pose.py"
index b04f611..706ddf8 100644
--- "a/D:\\semg.claude\\coinft\\.superpowers\\sdd\\shear-refit-before-20260928\\capture_demo_pose.py"
+++ "b/D:\\semg.claude\\coinft\\calibration\\capture_demo_pose.py"
@@ -1,15 +1,17 @@
 """Capture one operator-held pose from the CoinFT demo HTTP state endpoint."""
 
 import argparse
 import json
 import math
+import queue
+import threading
 import time
 import urllib.request
 from datetime import datetime
 from pathlib import Path
 
 
 def valid_state(state, previous_frame):
     return not invalid_reasons(state, previous_frame)
 
 
@@ -37,48 +39,89 @@ def invalid_reasons(state, previous_frame):
         values = state.get(name)
         if not isinstance(values, list) or len(values) != 12:
             reasons.append(f"{name} is not a 12-element list")
         else:
             for index, value in enumerate(values):
                 if not isinstance(value, (int, float)) or not math.isfinite(value):
                     reasons.append(f"{name}[{index}] is not finite: {value!r}")
     return reasons
 
 
-def capture(url: str, pose: str, assembly_id: str, seconds: float, interval: float) -> dict:
+def _request_state(url, started, deadline):
+    result = queue.Queue(maxsize=1)
+
+    def receive():
+        try:
+            if time.monotonic() >= min(deadline, started + 1.5):
+                raise TimeoutError("HTTP state request admission deadline reached")
+            with urllib.request.urlopen(url, timeout=1.5) as response:
+                state = json.load(response)
+            result.put((True, state))
+        except Exception as error:
+            result.put((False, error))
+
+    threading.Thread(target=receive, daemon=True).start()
+    try:
+        success, value = result.get(timeout=max(0, started + 1.5 - time.monotonic()))
+    except queue.Empty:
+        raise TimeoutError("HTTP state request exceeded total 1.5 seconds") from None
+    if time.monotonic() >= started + 1.5:
+        raise TimeoutError("HTTP state request exceeded total 1.5 seconds")
+    if not success:
+        raise value
+    return value
+
+
+def capture(url: str, pose: str, assembly_id: str, seconds: float,
+            interval: float, on_state=None) -> dict:
     if not all(math.isfinite(value) and value > 0 for value in (seconds, interval)):
         raise ValueError("seconds and interval must be finite and positive")
 
     samples = []
     previous_frame = -1
-    deadline = time.monotonic() + seconds
+    first_valid = None
+    deadline = time.monotonic() + seconds + 1.0
+    complete = False
     while time.monotonic() < deadline:
         started = time.monotonic()
-        with urllib.request.urlopen(f"{url.rstrip('/')}/api/state", timeout=1.5) as response:
-            state = json.load(response)
+        if started >= deadline:
+            break
+        state = _request_state(f"{url.rstrip('/')}/api/state", started, deadline)
+        if on_state is not None:
+            on_state(state)
         if not valid_state(state, previous_frame):
             raise ValueError(f"unsafe state during {pose}: {'; '.join(invalid_reasons(state, previous_frame))}")
+        received = time.monotonic()
+        if first_valid is None:
+            first_valid = received
         previous_frame = state["frames"]
         samples.append({
             "host": datetime.now().astimezone().isoformat(),
             "f": previous_frame,
             "channels": state["channels"],
             "raw": state["raw"],
             "status": state["status"],
             "rate": state["rate"],
             "invalid": state["invalid_recent"],
             "saturated": state["saturated_recent"],
             "resync": state["resyncs"],
         })
-        elapsed = time.monotonic() - started
-        time.sleep(max(0, interval - elapsed))
+        host_span = (datetime.fromisoformat(samples[-1]["host"]) -
+                     datetime.fromisoformat(samples[0]["host"])).total_seconds()
+        if received - first_valid >= seconds and host_span >= seconds:
+            complete = True
+            break
+        time.sleep(min(max(0, interval - (time.monotonic() - started)),
+                       max(0, deadline - time.monotonic())))
 
+    if not complete:
+        raise ValueError("capture deadline reached before valid sample span")
     if len(samples) < 30:
         raise ValueError(f"too few distinct snapshots: {len(samples)} < 30")
     return {
         "pose": pose,
         "assemblyId": assembly_id,
         "source": url,
         "sample_kind": "http_snapshot",
         "samples": samples,
     }
 

~~~

## tests/test_demo_profile.py

~~~diff
warning: in the working copy of 'D:\semg.claude\coinft\.superpowers\sdd\shear-refit-before-20260928\test_demo_profile.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'D:\semg.claude\coinft\tests\test_demo_profile.py', LF will be replaced by CRLF the next time Git touches it
diff --git "a/D:\\semg.claude\\coinft\\.superpowers\\sdd\\shear-refit-before-20260928\\test_demo_profile.py" "b/D:\\semg.claude\\coinft\\tests\\test_demo_profile.py"
index bcb66d6..4536f43 100644
--- "a/D:\\semg.claude\\coinft\\.superpowers\\sdd\\shear-refit-before-20260928\\test_demo_profile.py"
+++ "b/D:\\semg.claude\\coinft\\tests\\test_demo_profile.py"
@@ -35,39 +35,50 @@ class FakeClock:
 
     def sleep(self, seconds):
         self.now += seconds
 
 
 class CaptureTests(unittest.TestCase):
     def run_capture(self, states, seconds=5, interval=0.125):
         clock = FakeClock()
         urls = []
         responses = iter(states)
+        start = datetime(2026, 9, 28, tzinfo=timezone.utc)
+
+        class ClockDate:
+            @classmethod
+            def now(cls):
+                return start + timedelta(seconds=clock.now)
+
+            @staticmethod
+            def fromisoformat(value):
+                return datetime.fromisoformat(value)
 
         def urlopen(url, timeout):
             urls.append((url, timeout))
             return io.BytesIO(json.dumps(next(responses)).encode("utf-8"))
 
         with patch("calibration.capture_demo_pose.urllib.request.urlopen", side_effect=urlopen), \
              patch("calibration.capture_demo_pose.time.monotonic", side_effect=clock.monotonic), \
-             patch("calibration.capture_demo_pose.time.sleep", side_effect=clock.sleep):
+             patch("calibration.capture_demo_pose.time.sleep", side_effect=clock.sleep), \
+             patch("calibration.capture_demo_pose.datetime", ClockDate):
             result = capture("http://example.test", "train_press", "assembly-A", seconds, interval)
         return result, urls
 
     def test_collects_distinct_http_snapshots_with_provenance(self):
         result, urls = self.run_capture([state(i) for i in range(1, 44)])
         self.assertGreaterEqual(len(result["samples"]), 40)
         self.assertEqual(result["pose"], "train_press")
         self.assertEqual(result["assemblyId"], "assembly-A")
         self.assertEqual(result["source"], "http://example.test")
         self.assertEqual(result["sample_kind"], "http_snapshot")
-        self.assertEqual([sample["f"] for sample in result["samples"]], list(range(1, 41)))
+        self.assertEqual([sample["f"] for sample in result["samples"]], list(range(1, 42)))
         self.assertTrue(all(len(sample["channels"]) == 12 for sample in result["samples"]))
         self.assertTrue(all(set(sample) == {"host", "f", "channels", "raw", "status", "rate", "invalid", "saturated", "resync"} for sample in result["samples"]))
         self.assertTrue(all(url == "http://example.test/api/state" and timeout == 1.5 for url, timeout in urls))
 
     def test_rejects_duplicate_frame_without_skipping_it(self):
         states = [state(i) for i in range(1, 44)]
         states[8] = state(8)
         with self.assertRaisesRegex(ValueError, "frame not increasing.*previous=8.*current=8"):
             self.run_capture(states)
 
@@ -104,21 +115,22 @@ class CaptureTests(unittest.TestCase):
                  (5, math.nan), (0, 0.125), (5, -0.125)]
         for seconds, interval in cases:
             with self.subTest(seconds=seconds, interval=interval):
                 with patch("calibration.capture_demo_pose.urllib.request.urlopen") as request:
                     with self.assertRaisesRegex(ValueError, "finite and positive"):
                         capture("http://example.test", "train_press", "assembly-A", seconds, interval)
                 request.assert_not_called()
 
     def test_requires_thirty_distinct_snapshots(self):
         with self.assertRaises(ValueError):
-            self.run_capture([state(i) for i in range(1, 30)], seconds=3.625)
+            self.run_capture([state(i) for i in range(1, 30)],
+                             seconds=3.625, interval=0.2)
 
     def test_cli_preserves_existing_evidence(self):
         with tempfile.TemporaryDirectory() as directory:
             output = Path(directory) / "evidence.json"
             output.write_text("original", encoding="utf-8")
             args = ["--pose", "train_press", "--assembly-id", "assembly-A", "--out", str(output)]
             with patch("calibration.capture_demo_pose.capture") as mocked:
                 with self.assertRaises(FileExistsError):
                     main(args)
             mocked.assert_not_called()

~~~

## tests/test_capture_valid_span.py (new)

~~~diff
--- /dev/null
+++ b/tests/test_capture_valid_span.py
@@ -0,0 +1,210 @@
+import io
+import json
+import threading
+import time
+import unittest
+from datetime import datetime, timedelta, timezone
+from unittest.mock import patch
+
+from calibration.capture_demo_pose import capture
+
+
+class CaptureValidSpanTests(unittest.TestCase):
+    def run_capture(self, delay=0.0, interval=0.125, observer=None,
+                    repeated_delay=0.0, bad_frame=None, host_rate=1.0):
+        tick = [0.0]
+        requested = []
+        self.requested, self.tick = requested, tick
+        stamp = datetime(2026, 9, 28, tzinfo=timezone.utc)
+
+        class ClockDate:
+            @classmethod
+            def now(cls):
+                return stamp + timedelta(seconds=tick[0] * host_rate)
+
+            @staticmethod
+            def fromisoformat(value):
+                return datetime.fromisoformat(value)
+
+        def receive(url, timeout):
+            requested.append(tick[0])
+            frame = len(requested)
+            tick[0] += delay if frame == 1 else repeated_delay
+            return io.BytesIO(json.dumps({
+                "status": "live", "frames": bad_frame if bad_frame is not None else frame,
+                "rate": 200.0, "invalid_recent": 0, "saturated_recent": 0,
+                "resyncs": 0, "channels": [0.0]*12, "raw": [24000]*12,
+            }).encode())
+
+        def sleep(seconds):
+            tick[0] += seconds
+
+        with patch("calibration.capture_demo_pose.time.monotonic",
+                   side_effect=lambda: tick[0]), \
+             patch("calibration.capture_demo_pose.time.sleep", side_effect=sleep), \
+             patch("calibration.capture_demo_pose.datetime", ClockDate), \
+             patch("calibration.capture_demo_pose.urllib.request.urlopen",
+                   side_effect=receive):
+            options = {} if observer is None else {"on_state": observer}
+            return capture("http://example.test", "press", "assembly-A",
+                           5.0, interval, **options), requested
+
+    def test_success_spans_five_seconds_between_valid_samples(self):
+        result, requested = self.run_capture()
+        samples = result["samples"]
+        span = (datetime.fromisoformat(samples[-1]["host"]) -
+                datetime.fromisoformat(samples[0]["host"])).total_seconds()
+        self.assertGreaterEqual(span, 5.0)
+        self.assertEqual(len(samples), 41)
+        self.assertTrue(all(t < 6 for t in requested))
+
+    def test_initial_http_delay_is_not_counted_as_sample_span(self):
+        result, requested = self.run_capture(delay=0.8, interval=0.125)
+        samples = result["samples"]
+        span = (datetime.fromisoformat(samples[-1]["host"]) -
+                datetime.fromisoformat(samples[0]["host"])).total_seconds()
+        self.assertGreaterEqual(span, 5.0)
+        self.assertGreaterEqual(len(samples), 40)
+        self.assertTrue(all(t < 6 for t in requested))
+
+    def test_slow_capture_fails_without_extending_request_deadline(self):
+        with self.assertRaisesRegex(ValueError, "too few distinct snapshots"):
+            self.run_capture(delay=1.49, repeated_delay=1.49, interval=0.01)
+        self.assertTrue(all(t < 6 for t in self.requested))
+        self.assertLessEqual(self.tick[0], 7.5)
+
+    def test_sparse_capture_fails_at_deadline(self):
+        with self.assertRaisesRegex(ValueError, "capture deadline"):
+            self.run_capture(interval=10.0)
+        self.assertEqual(self.requested, [0.0])
+        self.assertEqual(self.tick[0], 6.0)
+
+    def test_optional_observer_receives_all_distinct_observations(self):
+        seen = []
+        result, requested = self.run_capture(observer=seen.append)
+        self.assertEqual([s["frames"] for s in seen],
+                         [s["f"] for s in result["samples"]])
+        self.assertEqual(len(seen), len(requested))
+
+    def test_observer_receives_unsafe_state_before_validation(self):
+        seen = []
+        with self.assertRaisesRegex(ValueError, "frame not increasing"):
+            self.run_capture(observer=seen.append, bad_frame=-1)
+        self.assertEqual([state["frames"] for state in seen], [-1])
+
+    def test_observer_exception_stops_capture_immediately(self):
+        def fail(state):
+            raise RuntimeError("observer failed")
+
+        with self.assertRaisesRegex(RuntimeError, "observer failed"):
+            self.run_capture(observer=fail)
+        self.assertEqual(len(self.requested), 1)
+
+    def test_host_span_cannot_replace_monotonic_span(self):
+        result, requested = self.run_capture(host_rate=2.0)
+        self.assertEqual(len(result["samples"]), 41)
+        self.assertGreaterEqual(requested[-1] - requested[0], 5.0)
+
+    def test_monotonic_span_cannot_replace_host_span(self):
+        with self.assertRaisesRegex(ValueError, "capture deadline"):
+            self.run_capture(host_rate=0.5)
+        self.assertTrue(all(t < 6 for t in self.requested))
+        self.assertEqual(self.tick[0], 6.0)
+
+    def test_trickled_body_times_out_without_late_observation(self):
+        finished = threading.Event()
+        seen = []
+        worker_daemon = []
+        payload = json.dumps({"status": "live", "frames": 1,
+                              "rate": 200.0, "invalid_recent": 0,
+                              "saturated_recent": 0, "resyncs": 0,
+                              "channels": [0.0]*12, "raw": [24000]*12}).encode()
+
+        class TrickleResponse(io.BytesIO):
+            def read(self, *args):
+                worker_daemon.append(threading.current_thread().daemon)
+                # Each chunk arrives well within the 1.5s inactivity timeout,
+                # but the complete body takes 2s. No network is used.
+                for _ in range(20):
+                    time.sleep(0.1)
+                return super().read(*args)
+
+            def close(self):
+                super().close()
+                finished.set()
+
+        response = TrickleResponse(payload)
+        with patch("calibration.capture_demo_pose.urllib.request.urlopen",
+                   side_effect=[response, TimeoutError("second request")]) as request, \
+             patch("calibration.capture_demo_pose.valid_state") as validate:
+            started = time.monotonic()
+            with self.assertRaises(TimeoutError):
+                capture("http://example.test", "press", "assembly-A",
+                        5.0, 0.125, on_state=seen.append)
+            elapsed = time.monotonic() - started
+            # Allow 0.3s for OS scheduling; this is not a real-time guarantee.
+            self.assertLess(elapsed, 1.8)
+            self.assertEqual(request.call_count, 1)
+            self.assertEqual(seen, [])
+            validate.assert_not_called()
+            self.assertTrue(finished.wait(2.0))
+            self.assertEqual(seen, [])
+            validate.assert_not_called()
+            self.assertEqual(worker_daemon, [True])
+
+    def test_open_and_json_are_inside_total_timeout(self):
+        for stage in ("open", "json"):
+            with self.subTest(stage=stage):
+                finished = threading.Event()
+                seen = []
+
+                def slow():
+                    time.sleep(2.0)
+
+                class CompletedResponse(io.BytesIO):
+                    def close(self):
+                        super().close()
+                        finished.set()
+
+                def receive(url, timeout):
+                    if stage == "open":
+                        slow()
+                    return CompletedResponse(b"{}")
+
+                def decode(response):
+                    if stage == "json":
+                        slow()
+                    return {}
+
+                with patch("calibration.capture_demo_pose.urllib.request.urlopen",
+                           side_effect=receive) as request, \
+                     patch("calibration.capture_demo_pose.json.load",
+                           side_effect=decode), \
+                     patch("calibration.capture_demo_pose.valid_state") as validate:
+                    started = time.monotonic()
+                    with self.assertRaisesRegex(TimeoutError, "total 1.5"):
+                        capture("http://example.test", "press", "assembly-A",
+                                5.0, 0.125, on_state=seen.append)
+                    self.assertLess(time.monotonic() - started, 1.8)
+                    self.assertEqual(request.call_count, 1)
+                    self.assertTrue(finished.wait(2.0))
+                    self.assertEqual(seen, [])
+                    validate.assert_not_called()
+
+    def test_already_queued_late_result_is_rejected(self):
+        seen = []
+        with self.assertRaisesRegex(TimeoutError, "total 1.5"):
+            self.run_capture(delay=1.5, observer=seen.append)
+        self.assertEqual(len(self.requested), 1)
+        self.assertEqual(seen, [])
+
+    def test_request_is_not_admitted_when_start_reaches_deadline(self):
+        with patch("calibration.capture_demo_pose.time.monotonic",
+                   side_effect=[0.0, 5.999, 6.0, 6.0, 6.0, 6.0]), \
+             patch("calibration.capture_demo_pose.urllib.request.urlopen",
+                   side_effect=TimeoutError("request admitted")) as request:
+            try:
+                capture("http://example.test", "press", "assembly-A", 5.0, 0.125)
+            except (ValueError, TimeoutError):
+                pass
+            request.assert_not_called()
~~~

