# Healthy cached-duplicate acquisition correction review

No Git repository. Complete source/test changes against controller snapshots taken before implementation. User approved retaining duplicate observations but excluding them from sample count; fixed40/5s/all real faults/6s/1.5s deadlines remain. The one legacy test expectation is explicitly superseded by approval and becomes regression rejection; all other legacy tests unchanged.


## calibration/capture_demo_pose.py (154 -> 161 lines)

~~~diff
--- before/calibration/capture_demo_pose.py
+++ current/calibration/capture_demo_pose.py
@@ full contextual change @@
 """Capture one operator-held pose from the CoinFT demo HTTP state endpoint."""
 
 import argparse
 import json
 import math
 import queue
 import threading
 import time
 import urllib.request
 from datetime import datetime
 from pathlib import Path
 
 
 def valid_state(state, previous_frame):
     return not invalid_reasons(state, previous_frame)
 
 
 def invalid_reasons(state, previous_frame):
     if not isinstance(state, dict):
         return ["state is not an object"]
     reasons = []
     if state.get("status") != "live":
         reasons.append(f"status={state.get('status')!r}")
     frame = state.get("frames")
     if not isinstance(frame, int):
         reasons.append(f"frame is not an integer: {frame!r}")
     elif frame <= previous_frame:
         reasons.append(f"frame not increasing: previous={previous_frame}, current={frame}")
     rate = state.get("rate")
     if not isinstance(rate, (int, float)) or not math.isfinite(rate) or rate <= 0:
         reasons.append(f"rate is not finite and positive: {rate!r}")
     for name in ("invalid_recent", "saturated_recent"):
         if state.get(name) != 0:
             reasons.append(f"{name}={state.get(name)!r}")
     resyncs = state.get("resyncs")
     if type(resyncs) is not int or resyncs < 0:
         reasons.append(f"resyncs is not a nonnegative integer: {resyncs!r}")
     for name in ("channels", "raw"):
         values = state.get(name)
         if not isinstance(values, list) or len(values) != 12:
             reasons.append(f"{name} is not a 12-element list")
         else:
             for index, value in enumerate(values):
                 if not isinstance(value, (int, float)) or not math.isfinite(value):
                     reasons.append(f"{name}[{index}] is not finite: {value!r}")
     return reasons
 
 
 def _request_state(url, started, deadline):
     result = queue.Queue(maxsize=1)
 
     def receive():
         try:
             if time.monotonic() >= min(deadline, started + 1.5):
                 raise TimeoutError("HTTP state request admission deadline reached")
             with urllib.request.urlopen(url, timeout=1.5) as response:
                 state = json.load(response)
             result.put((True, state))
         except Exception as error:
             result.put((False, error))
 
     threading.Thread(target=receive, daemon=True).start()
     try:
         success, value = result.get(timeout=max(0, started + 1.5 - time.monotonic()))
     except queue.Empty:
         raise TimeoutError("HTTP state request exceeded total 1.5 seconds") from None
     if time.monotonic() >= started + 1.5:
         raise TimeoutError("HTTP state request exceeded total 1.5 seconds")
     if not success:
         raise value
     return value
 
 
 def capture(url: str, pose: str, assembly_id: str, seconds: float,
+            interval: float, on_state=None, minimum_samples=None) -> dict:
-            interval: float, on_state=None) -> dict:
     if not all(math.isfinite(value) and value > 0 for value in (seconds, interval)):
         raise ValueError("seconds and interval must be finite and positive")
+    if minimum_samples is not None and (type(minimum_samples) is not int or minimum_samples < 30):
+        raise ValueError("minimum_samples must be an integer >= 30")
 
     samples = []
     previous_frame = -1
     first_valid = None
     deadline = time.monotonic() + seconds + 1.0
     complete = False
     while time.monotonic() < deadline:
         started = time.monotonic()
         if started >= deadline:
             break
         state = _request_state(f"{url.rstrip('/')}/api/state", started, deadline)
         if on_state is not None:
             on_state(state)
+        duplicate = (previous_frame >= 0 and isinstance(state, dict) and
+                     state.get("frames") == previous_frame)
+        validation_frame = previous_frame - 1 if duplicate else previous_frame
+        if not valid_state(state, validation_frame):
+            raise ValueError(f"unsafe state during {pose}: {'; '.join(invalid_reasons(state, validation_frame))}")
+        if not duplicate:
+            received = time.monotonic()
+            if first_valid is None:
+                first_valid = received
+            previous_frame = state["frames"]
+            samples.append({
+                "host": datetime.now().astimezone().isoformat(),
+                "f": previous_frame,
+                "channels": state["channels"],
+                "raw": state["raw"],
+                "status": state["status"],
+                "rate": state["rate"],
+                "invalid": state["invalid_recent"],
+                "saturated": state["saturated_recent"],
+                "resync": state["resyncs"],
+            })
+            host_span = (datetime.fromisoformat(samples[-1]["host"]) -
+                         datetime.fromisoformat(samples[0]["host"])).total_seconds()
+            if (received - first_valid >= seconds and host_span >= seconds and
+                    (minimum_samples is None or len(samples) >= minimum_samples)):
+                complete = True
+                break
-        if not valid_state(state, previous_frame):
-            raise ValueError(f"unsafe state during {pose}: {'; '.join(invalid_reasons(state, previous_frame))}")
-        received = time.monotonic()
-        if first_valid is None:
-            first_valid = received
-        previous_frame = state["frames"]
-        samples.append({
-            "host": datetime.now().astimezone().isoformat(),
-            "f": previous_frame,
-            "channels": state["channels"],
-            "raw": state["raw"],
-            "status": state["status"],
-            "rate": state["rate"],
-            "invalid": state["invalid_recent"],
-            "saturated": state["saturated_recent"],
-            "resync": state["resyncs"],
-        })
-        host_span = (datetime.fromisoformat(samples[-1]["host"]) -
-                     datetime.fromisoformat(samples[0]["host"])).total_seconds()
-        if received - first_valid >= seconds and host_span >= seconds:
-            complete = True
-            break
         time.sleep(min(max(0, interval - (time.monotonic() - started)),
                        max(0, deadline - time.monotonic())))
 
     if not complete:
         raise ValueError("capture deadline reached before valid sample span")
     if len(samples) < 30:
         raise ValueError(f"too few distinct snapshots: {len(samples)} < 30")
     return {
         "pose": pose,
         "assemblyId": assembly_id,
         "source": url,
         "sample_kind": "http_snapshot",
         "samples": samples,
     }
 
 
 def main(argv=None):
     parser = argparse.ArgumentParser(description=__doc__)
     parser.add_argument("--pose", required=True, help="one stable operator-held pose name")
     parser.add_argument("--assembly-id", required=True, help="current physical assembly label")
     parser.add_argument("--out", required=True, type=Path, help="new evidence JSON path")
     parser.add_argument("--url", default="http://127.0.0.1:8765")
     parser.add_argument("--seconds", type=float, default=5.0)
     parser.add_argument("--interval", type=float, default=0.125)
     args = parser.parse_args(argv)
 
     if args.out.exists():
         raise FileExistsError(args.out)
     evidence = capture(args.url, args.pose, args.assembly_id, args.seconds, args.interval)
     if args.out.exists():
         raise FileExistsError(args.out)
     content = json.dumps(evidence, ensure_ascii=False, indent=2)
     with args.out.open("x", encoding="utf-8") as output:
         output.write(content)
     samples = evidence["samples"]
     print(f"{args.pose}: {len(samples)} HTTP snapshots; frames {samples[0]['f']}..{samples[-1]['f']}; "
           f"rate {samples[-1]['rate']}; invalid {samples[-1]['invalid']}; "
           f"saturated {samples[-1]['saturated']}; resync {samples[-1]['resync']}")
 
 
 if __name__ == "__main__":
     main()
~~~

## .superpowers/sdd/shear-refit-capture-command.py (72 -> 74 lines)

~~~diff
--- before/.superpowers/sdd/shear-refit-capture-command.py
+++ current/.superpowers/sdd/shear-refit-capture-command.py
@@ full contextual change @@
 import json
 import time
 from datetime import datetime
 from pathlib import Path
 import psutil
 from calibration.capture_demo_pose import capture
 
 def owner():
     candidates = []
     for proc in psutil.process_iter(["pid", "create_time", "cmdline"]):
         args = proc.info["cmdline"] or []
         if any(Path(a).name == "coinft_demo.py" for a in args):
             candidates.append(proc.info)
     listeners = [c for c in psutil.net_connections(kind="tcp")
                  if c.status == psutil.CONN_LISTEN and c.laddr.port == 8765]
     if len(candidates) != 1 or len(listeners) != 1:
         raise ValueError("not exactly one HTTP capture owner")
     p = candidates[0]
     if listeners[0].pid != p["pid"]:
         raise ValueError("listener does not belong to capture owner")
     return {"pid": p["pid"], "created": p["create_time"]}
 
 pose = "press_before"
 out = Path("calibration/shear_refit_20260928/fit/press_before.json")
 if out.exists():
     raise FileExistsError(out)
 who = owner()
 observations = []
 def observe(state):
     observations.append({"host": datetime.now().astimezone().isoformat(),
                          "monotonic": time.monotonic(), "state": state})
     if state.get("port") != "COM6" or state.get("mode") != "live":
         raise ValueError("wrong port/mode")
     if state.get("tare_progress") != 100:
         raise ValueError("tare/baseline epoch not stable")
     if not state.get("diagnostics") or not state.get("recovery"):
         raise ValueError("missing stream quality evidence")
     if len(observations) > 1:
         first, previous = observations[0]["state"], observations[-2]["state"]
         for key in ("invalid_frames", "saturated", "resyncs"):
             if state[key] != first[key]:
                 raise ValueError("new cumulative quality fault: "+key)
         for key in ("attempts", "successes"):
             if state["recovery"][key] != first["recovery"][key]:
                 raise ValueError("stream recovery changed epoch")
         for key in ("serial_bytes", "parsed_frames"):
+            if (state["diagnostics"][key] < previous["diagnostics"][key] or
+                    (state["diagnostics"][key] == previous["diagnostics"][key] and
+                     state["frames"] != previous["frames"])):
-            if state["diagnostics"][key] <= previous["diagnostics"][key]:
                 raise ValueError("byte/frame observation not advancing")
         if (state["diagnostics"]["parser_discarded_bytes"] !=
                 first["diagnostics"]["parser_discarded_bytes"]):
             raise ValueError("parser discarded bytes increased")
 
 try:
     data = capture("http://127.0.0.1:8765", pose,
+                   "coinft-current-20260925", 5.0, 0.125, on_state=observe, minimum_samples=40)
-                   "coinft-current-20260925", 5.0, 0.125, on_state=observe)
     if len(data["samples"]) < 40 or owner() != who:
         raise ValueError("insufficient samples or owner changed")
     a, b = observations[0], observations[-1]
     rate = (b["state"]["frames"]-a["state"]["frames"])/(b["monotonic"]-a["monotonic"])
     if not 150 <= rate <= 250:
         raise ValueError("aggregate frame rate outside150–250Hz")
     data.update(owner=who, evidence=out.name, observations=observations,
                 aggregate_rate=rate, capture_ok=True)
     print(json.dumps({"out": str(out), "evidence": data},
                      ensure_ascii=False, allow_nan=False, separators=(",", ":")))
 except Exception as exc:
     print(json.dumps({"out": str(out.with_suffix(".failed.json")),
                       "evidence": {"capture_ok": False, "pose": pose,
                                    "owner": who, "error": repr(exc),
                                    "observations": observations}},
                      ensure_ascii=False, separators=(",", ":")))
     raise SystemExit(1)
~~~

## tests/test_capture_valid_span.py (210 -> 276 lines)

~~~diff
--- before/tests/test_capture_valid_span.py
+++ current/tests/test_capture_valid_span.py
@@ full contextual change @@
 import io
 import json
 import threading
 import time
 import unittest
 from datetime import datetime, timedelta, timezone
 from unittest.mock import patch
 
 from calibration.capture_demo_pose import capture
 
 
 class CaptureValidSpanTests(unittest.TestCase):
     def run_capture(self, delay=0.0, interval=0.125, observer=None,
+                    repeated_delay=0.0, bad_frame=None, host_rate=1.0,
+                    duplicates=(), unsafe=None, minimum_samples=None):
-                    repeated_delay=0.0, bad_frame=None, host_rate=1.0):
         tick = [0.0]
         requested = []
         self.requested, self.tick = requested, tick
         stamp = datetime(2026, 9, 28, tzinfo=timezone.utc)
 
         class ClockDate:
             @classmethod
             def now(cls):
                 return stamp + timedelta(seconds=tick[0] * host_rate)
 
             @staticmethod
             def fromisoformat(value):
                 return datetime.fromisoformat(value)
 
         def receive(url, timeout):
             requested.append(tick[0])
             frame = len(requested)
             tick[0] += delay if frame == 1 else repeated_delay
+            state = {
+                "status": "live", "frames": bad_frame if bad_frame is not None else
+                frame - sum(index <= frame for index in duplicates),
-            return io.BytesIO(json.dumps({
-                "status": "live", "frames": bad_frame if bad_frame is not None else frame,
                 "rate": 200.0, "invalid_recent": 0, "saturated_recent": 0,
                 "resyncs": 0, "channels": [0.0]*12, "raw": [24000]*12,
+            }
+            if unsafe is not None and frame == 4:
+                unsafe(state)
+            return io.BytesIO(json.dumps(state).encode())
-            }).encode())
 
         def sleep(seconds):
             tick[0] += seconds
 
         with patch("calibration.capture_demo_pose.time.monotonic",
                    side_effect=lambda: tick[0]), \
              patch("calibration.capture_demo_pose.time.sleep", side_effect=sleep), \
              patch("calibration.capture_demo_pose.datetime", ClockDate), \
              patch("calibration.capture_demo_pose.urllib.request.urlopen",
                    side_effect=receive):
             options = {} if observer is None else {"on_state": observer}
+            if minimum_samples is not None:
+                options["minimum_samples"] = minimum_samples
             return capture("http://example.test", "press", "assembly-A",
                            5.0, interval, **options), requested
 
+    def test_healthy_duplicates_are_observed_but_not_samples(self):
+        seen = []
+        result, requested = self.run_capture(observer=seen.append, duplicates=(2, 3, 4))
+        self.assertEqual(len(seen), len(requested))
+        self.assertEqual([state['frames'] for state in seen[:4]], [1, 1, 1, 1])
+        self.assertEqual(len(result['samples']), len(seen) - 3)
+        self.assertEqual([sample['f'] for sample in result['samples']], list(range(1, 39)))
+
+    def test_invalid_duplicate_and_regression_abort_after_observation(self):
+        mutations = [lambda s: s.update(status='waiting'),
+                     lambda s: s.update(invalid_recent=1),
+                     lambda s: s.update(saturated_recent=1),
+                     lambda s: s.update(rate=float('nan')),
+                     lambda s: s.update(raw=[]),
+                     lambda s: s.update(channels=[float('inf')] * 12),
+                     lambda s: s.update(frames=0)]
+        for mutation in mutations:
+            with self.subTest(mutation=mutation):
+                seen = []
+                with self.assertRaisesRegex(ValueError, 'unsafe state'):
+                    self.run_capture(observer=seen.append, duplicates=(2, 3, 4), unsafe=mutation)
+                self.assertEqual(len(seen), 4)
+                self.assertEqual(len(self.requested), 4)
+
+    def test_unchanged_frame_times_out_with_normal_pacing(self):
+        seen = []
+        with self.assertRaisesRegex(ValueError, 'capture deadline'):
+            self.run_capture(observer=seen.append, bad_frame=1)
+        self.assertEqual(len(seen), 48)
+        self.assertEqual(self.requested, [index * 0.125 for index in range(48)])
+        self.assertEqual(self.tick[0], 6.0)
+
+    def test_minimum_forty_waits_past_five_seconds_for_distinct_samples(self):
+        seen = []
+        result, requested = self.run_capture(observer=seen.append, duplicates=(2, 3, 4, 5),
+                                             minimum_samples=40)
+        self.assertEqual(len(result['samples']), 40)
+        self.assertEqual(len(seen), 44)
+        self.assertEqual(requested[-1], 5.375)
+        self.assertEqual(len({sample['host'] for sample in result['samples']}), 40)
+        self.assertEqual(len({sample['f'] for sample in result['samples']}), 40)
+
+    def test_minimum_forty_cannot_be_replaced_by_thirty_or_duplicates(self):
+        for options in ({'interval': 0.175}, {'duplicates': tuple(range(2, 12))}):
+            with self.subTest(options=options):
+                with self.assertRaisesRegex(ValueError, 'capture deadline'):
+                    self.run_capture(minimum_samples=40, **options)
+                self.assertTrue(all(t < 6 for t in self.requested))
+                self.assertEqual(self.tick[0], 6.0)
+
+    def test_bad_minimum_rejects_before_http(self):
+        for minimum in (True, False, 29, 0, -1, 40.0, '40'):
+            with self.subTest(minimum=minimum), \
+                 patch('calibration.capture_demo_pose.urllib.request.urlopen') as request:
+                with self.assertRaisesRegex(ValueError, 'minimum_samples'):
+                    capture('http://example.test', 'press', 'assembly-A', 5.0, 0.125,
+                            minimum_samples=minimum)
+                request.assert_not_called()
+
     def test_success_spans_five_seconds_between_valid_samples(self):
         result, requested = self.run_capture()
         samples = result["samples"]
         span = (datetime.fromisoformat(samples[-1]["host"]) -
                 datetime.fromisoformat(samples[0]["host"])).total_seconds()
         self.assertGreaterEqual(span, 5.0)
         self.assertEqual(len(samples), 41)
         self.assertTrue(all(t < 6 for t in requested))
 
     def test_initial_http_delay_is_not_counted_as_sample_span(self):
         result, requested = self.run_capture(delay=0.8, interval=0.125)
         samples = result["samples"]
         span = (datetime.fromisoformat(samples[-1]["host"]) -
                 datetime.fromisoformat(samples[0]["host"])).total_seconds()
         self.assertGreaterEqual(span, 5.0)
         self.assertGreaterEqual(len(samples), 40)
         self.assertTrue(all(t < 6 for t in requested))
 
     def test_slow_capture_fails_without_extending_request_deadline(self):
         with self.assertRaisesRegex(ValueError, "too few distinct snapshots"):
             self.run_capture(delay=1.49, repeated_delay=1.49, interval=0.01)
         self.assertTrue(all(t < 6 for t in self.requested))
         self.assertLessEqual(self.tick[0], 7.5)
 
     def test_sparse_capture_fails_at_deadline(self):
         with self.assertRaisesRegex(ValueError, "capture deadline"):
             self.run_capture(interval=10.0)
         self.assertEqual(self.requested, [0.0])
         self.assertEqual(self.tick[0], 6.0)
 
     def test_optional_observer_receives_all_distinct_observations(self):
         seen = []
         result, requested = self.run_capture(observer=seen.append)
         self.assertEqual([s["frames"] for s in seen],
                          [s["f"] for s in result["samples"]])
         self.assertEqual(len(seen), len(requested))
 
     def test_observer_receives_unsafe_state_before_validation(self):
         seen = []
         with self.assertRaisesRegex(ValueError, "frame not increasing"):
             self.run_capture(observer=seen.append, bad_frame=-1)
         self.assertEqual([state["frames"] for state in seen], [-1])
 
     def test_observer_exception_stops_capture_immediately(self):
         def fail(state):
             raise RuntimeError("observer failed")
 
         with self.assertRaisesRegex(RuntimeError, "observer failed"):
             self.run_capture(observer=fail)
         self.assertEqual(len(self.requested), 1)
 
     def test_host_span_cannot_replace_monotonic_span(self):
         result, requested = self.run_capture(host_rate=2.0)
         self.assertEqual(len(result["samples"]), 41)
         self.assertGreaterEqual(requested[-1] - requested[0], 5.0)
 
     def test_monotonic_span_cannot_replace_host_span(self):
         with self.assertRaisesRegex(ValueError, "capture deadline"):
             self.run_capture(host_rate=0.5)
         self.assertTrue(all(t < 6 for t in self.requested))
         self.assertEqual(self.tick[0], 6.0)
 
     def test_trickled_body_times_out_without_late_observation(self):
         finished = threading.Event()
         seen = []
         worker_daemon = []
         payload = json.dumps({"status": "live", "frames": 1,
                               "rate": 200.0, "invalid_recent": 0,
                               "saturated_recent": 0, "resyncs": 0,
                               "channels": [0.0]*12, "raw": [24000]*12}).encode()
 
         class TrickleResponse(io.BytesIO):
             def read(self, *args):
                 worker_daemon.append(threading.current_thread().daemon)
                 # Each chunk arrives well within the 1.5s inactivity timeout,
                 # but the complete body takes 2s. No network is used.
                 for _ in range(20):
                     time.sleep(0.1)
                 return super().read(*args)
 
             def close(self):
                 super().close()
                 finished.set()
 
         response = TrickleResponse(payload)
         with patch("calibration.capture_demo_pose.urllib.request.urlopen",
                    side_effect=[response, TimeoutError("second request")]) as request, \
              patch("calibration.capture_demo_pose.valid_state") as validate:
             started = time.monotonic()
             with self.assertRaises(TimeoutError):
                 capture("http://example.test", "press", "assembly-A",
                         5.0, 0.125, on_state=seen.append)
             elapsed = time.monotonic() - started
             # Allow 0.3s for OS scheduling; this is not a real-time guarantee.
             self.assertLess(elapsed, 1.8)
             self.assertEqual(request.call_count, 1)
             self.assertEqual(seen, [])
             validate.assert_not_called()
             self.assertTrue(finished.wait(2.0))
             self.assertEqual(seen, [])
             validate.assert_not_called()
             self.assertEqual(worker_daemon, [True])
 
     def test_open_and_json_are_inside_total_timeout(self):
         for stage in ("open", "json"):
             with self.subTest(stage=stage):
                 finished = threading.Event()
                 seen = []
 
                 def slow():
                     time.sleep(2.0)
 
                 class CompletedResponse(io.BytesIO):
                     def close(self):
                         super().close()
                         finished.set()
 
                 def receive(url, timeout):
                     if stage == "open":
                         slow()
                     return CompletedResponse(b"{}")
 
                 def decode(response):
                     if stage == "json":
                         slow()
                     return {}
 
                 with patch("calibration.capture_demo_pose.urllib.request.urlopen",
                            side_effect=receive) as request, \
                      patch("calibration.capture_demo_pose.json.load",
                            side_effect=decode), \
                      patch("calibration.capture_demo_pose.valid_state") as validate:
                     started = time.monotonic()
                     with self.assertRaisesRegex(TimeoutError, "total 1.5"):
                         capture("http://example.test", "press", "assembly-A",
                                 5.0, 0.125, on_state=seen.append)
                     self.assertLess(time.monotonic() - started, 1.8)
                     self.assertEqual(request.call_count, 1)
                     self.assertTrue(finished.wait(2.0))
                     self.assertEqual(seen, [])
                     validate.assert_not_called()
 
     def test_already_queued_late_result_is_rejected(self):
         seen = []
         with self.assertRaisesRegex(TimeoutError, "total 1.5"):
             self.run_capture(delay=1.5, observer=seen.append)
         self.assertEqual(len(self.requested), 1)
         self.assertEqual(seen, [])
 
     def test_request_is_not_admitted_when_start_reaches_deadline(self):
         with patch("calibration.capture_demo_pose.time.monotonic",
                    side_effect=[0.0, 5.999, 6.0, 6.0, 6.0, 6.0]), \
              patch("calibration.capture_demo_pose.urllib.request.urlopen",
                    side_effect=TimeoutError("request admitted")) as request:
             try:
                 capture("http://example.test", "press", "assembly-A", 5.0, 0.125)
             except (ValueError, TimeoutError):
                 pass
             request.assert_not_called()
~~~

## tests/test_refit_capture_command.py (161 -> 218 lines)

~~~diff
--- before/tests/test_refit_capture_command.py
+++ current/tests/test_refit_capture_command.py
@@ full contextual change @@
 import contextlib
 import io
 import json
 import runpy
 import unittest
 from datetime import datetime, timedelta, timezone
 from pathlib import Path
 from types import SimpleNamespace
 from unittest.mock import patch
 
 import test_capture_valid_span as capture_fixtures
 
 
 COMMAND = Path(__file__).resolve().parents[1] / '.superpowers/sdd/shear-refit-capture-command.py'
 
 
 class RefitCaptureCommandTests(unittest.TestCase):
     def test_prepared_command_exists(self):
         self.assertTrue(COMMAND.is_file(), 'single-pose capture command is not prepared')
 
     def run_command(self, unsafe=None, owners=None, listeners=None, exists=False,
+                    bad_frame=None, duplicates=(), duplicate_forever=False):
-                    bad_frame=None):
         self.assertTrue(COMMAND.is_file(), 'single-pose capture command is not prepared')
         fixture = capture_fixtures.CaptureValidSpanTests()
         core_states = []
         fixture.run_capture(interval=0.004, observer=core_states.append)
         unsafe_states = []
         if bad_frame is not None:
             with self.assertRaisesRegex(ValueError, 'frame not increasing'):
                 fixture.run_capture(observer=unsafe_states.append, bad_frame=bad_frame)
         tick = [0.0]
         self.states, self.requests = [], []
         stamp = datetime(2026, 9, 28, tzinfo=timezone.utc)
 
         class ClockDate:
             @classmethod
             def now(cls):
                 return stamp + timedelta(seconds=tick[0])
 
             @staticmethod
             def fromisoformat(value):
                 return datetime.fromisoformat(value)
 
         def receive(url, timeout):
             self.requests.append((url, timeout))
             index = len(self.requests) - 1
             state = dict(unsafe_states[0] if unsafe_states and index == 3
                          else core_states[index * 25])
             state.update({
                 'mode': 'live', 'port': 'COM6',
                 'tare_progress': 100, 'invalid_frames': 3, 'saturated': 2,
                 'axes': [0.0] * 6, 'message': '数据流正常', 'updated_at': stamp.timestamp() + tick[0],
                 'diagnostics': {'serial_bytes': 2000 + index * 600,
                                 'serial_reads': 100 + index * 20,
                                 'parsed_frames': state['frames'],
                                 'parser_discarded_bytes': 7,
                                 'parser_pending_bytes': 0,
                                 'last_byte_at': stamp.timestamp() + tick[0],
                                 'last_parsed_frame_at': stamp.timestamp() + tick[0]},
                 'recovery': {'attempts': 1, 'successes': 1, 'last_fault':
                              {'reason': 'historical timeout', 'observed_at': stamp.timestamp() - 10,
                               'frames': 20, 'diagnostics': {'serial_reads': 20,
                               'serial_bytes': 600, 'parsed_frames': 20,
                               'last_byte_at': stamp.timestamp() - 10,
                               'last_parsed_frame_at': stamp.timestamp() - 10,
                               'parser_pending_bytes': 0, 'parser_discarded_bytes': 7}}},
             })
+            if index in duplicates or (duplicate_forever and index > 0):
+                state = json.loads(json.dumps(self.states[-1]))
             if unsafe is not None and index == 3:
                 unsafe(state)
             self.states.append(state)
             return io.BytesIO(json.dumps(state).encode())
 
         proc = SimpleNamespace(info={'pid': 321, 'create_time': 123.0,
                                      'cmdline': ['python', 'coinft_demo.py']})
         listener = SimpleNamespace(status='LISTEN', laddr=SimpleNamespace(port=8765), pid=321)
         output = io.StringIO()
         self.failure = None
         with patch('psutil.process_iter', side_effect=owners or [[proc], [proc]]) as process, \
              patch('psutil.net_connections', return_value=listeners or [listener]), \
              patch('pathlib.Path.exists', return_value=exists), \
              patch('calibration.capture_demo_pose.urllib.request.urlopen', side_effect=receive), \
              patch('time.monotonic', side_effect=lambda: tick[0]), \
              patch('time.sleep', side_effect=lambda seconds: tick.__setitem__(0, tick[0] + seconds)), \
              patch('calibration.capture_demo_pose.datetime', ClockDate), \
              patch('calibration.capture_demo_pose.capture', wraps=__import__(
                  'calibration.capture_demo_pose', fromlist=['capture']).capture) as capture, \
              contextlib.redirect_stdout(output):
             with patch('datetime.datetime', ClockDate):
                 try:
                     runpy.run_path(str(COMMAND))
                 except (SystemExit, ValueError, FileExistsError) as exc:
                     self.failure = exc
             self.capture_count, self.owner_count = capture.call_count, process.call_count
+            self.capture_kwargs = capture.call_args.kwargs if capture.called else {}
         self.output = output.getvalue()
         return json.loads(self.output) if self.output else None
 
+    def test_cached_duplicates_are_retained_and_forty_distinct_samples_complete(self):
+        result = self.run_command(duplicates=(1, 2, 3, 4))
+        self.assertIsNone(self.failure)
+        evidence = result['evidence']
+        self.assertTrue(evidence['capture_ok'])
+        self.assertEqual(self.capture_kwargs['minimum_samples'], 40)
+        self.assertEqual(len(evidence['observations']), 44)
+        self.assertEqual([o['state'] for o in evidence['observations']], self.states)
+        self.assertTrue(all(state == self.states[0] for state in self.states[:5]))
+        self.assertEqual(len(evidence['samples']), 40)
+        self.assertEqual(len({s['f'] for s in evidence['samples']}), 40)
+        self.assertEqual(len({s['host'] for s in evidence['samples']}), 40)
+        self.assertEqual(evidence['observations'][-1]['monotonic'], 5.375)
+        self.assertAlmostEqual(evidence['aggregate_rate'], 200)
+
+    def test_cached_duplicate_quality_faults_are_retained_and_rejected(self):
+        mutations = [lambda s: s.update(port='COM8'), lambda s: s.update(mode='waiting'),
+                     lambda s: s.update(tare_progress=0), lambda s: s.update(invalid_frames=4),
+                     lambda s: s.update(saturated=3), lambda s: s.update(resyncs=1),
+                     lambda s: s['recovery'].update(attempts=2),
+                     lambda s: s['recovery'].update(successes=2),
+                     lambda s: s['diagnostics'].update(parser_discarded_bytes=8),
+                     lambda s: s.update(status='waiting'), lambda s: s.update(invalid_recent=1)]
+        for mutation in mutations:
+            with self.subTest(mutation=mutation):
+                result = self.run_command(duplicates=(1, 2, 3), unsafe=mutation)
+                self.assertFalse(result['evidence']['capture_ok'])
+                self.assertEqual(len(self.requests), 4)
+                self.assertEqual([o['state'] for o in result['evidence']['observations']], self.states)
+
+    def test_cached_duplicate_diagnostic_regression_still_rejects(self):
+        for key in ('serial_bytes', 'parsed_frames'):
+            with self.subTest(key=key):
+                result = self.run_command(duplicates=(1, 2, 3),
+                    unsafe=lambda s: s['diagnostics'].update({key: s['diagnostics'][key] - 1}))
+                self.assertIn('byte/frame observation not advancing', result['evidence']['error'])
+                self.assertEqual(len(result['evidence']['observations']), 4)
+
+    def test_fresh_frame_with_unchanged_diagnostic_counter_rejects(self):
+        for key, value in (('serial_bytes', 3200), ('parsed_frames', 51)):
+            with self.subTest(key=key):
+                result = self.run_command(unsafe=lambda s: s['diagnostics'].update({key: value}))
+                self.assertIn('byte/frame observation not advancing', result['evidence']['error'])
+                self.assertEqual(len(self.requests), 4)
+
+    def test_cached_frame_forever_reaches_original_deadline(self):
+        result = self.run_command(duplicate_forever=True)
+        self.assertFalse(result['evidence']['capture_ok'])
+        self.assertIn('capture deadline', result['evidence']['error'])
+        observations = result['evidence']['observations']
+        self.assertEqual(len(observations), 48)
+        self.assertEqual([o['monotonic'] for o in observations],
+                         [index * 0.125 for index in range(48)])
+
     def test_success_serializes_complete_observations_and_fresh_path(self):
         result = self.run_command()
         self.assertIsNone(self.failure)
         evidence = result['evidence']
         self.assertTrue(evidence['capture_ok'])
         self.assertEqual(Path(result['out']), Path('calibration/shear_refit_20260928/fit/press_before.json'))
         self.assertEqual(evidence['pose'], 'press_before')
         self.assertEqual(evidence['owner'], {'pid': 321, 'created': 123.0})
         self.assertEqual(len(evidence['observations']), len(self.requests))
         self.assertEqual(len(evidence['observations']), 41)
         self.assertEqual([o['state'] for o in evidence['observations']], self.states)
         self.assertAlmostEqual(evidence['aggregate_rate'], 200)
         self.assertGreaterEqual(evidence['observations'][-1]['monotonic'], 5)
         self.assertTrue(all(url == 'http://127.0.0.1:8765/api/state' and timeout == 1.5
                             for url, timeout in self.requests))
         self.assertEqual(evidence['observations'][-1]['state']['recovery']['last_fault'],
                          self.states[-1]['recovery']['last_fault'])
 
     def test_unsafe_final_observation_is_retained_and_aborts(self):
         mutations = [lambda s: s.update(port='COM8'),
                      lambda s: s.update(mode='waiting'),
                      lambda s: s.update(tare_progress=0),
                      lambda s: s.update(invalid_frames=4),
                      lambda s: s.update(saturated=3),
                      lambda s: s.update(resyncs=1),
                      lambda s: s['recovery'].update(attempts=2),
                      lambda s: s['recovery'].update(successes=2),
                      lambda s: s['diagnostics'].update(serial_bytes=0),
                      lambda s: s['diagnostics'].update(parsed_frames=51),
                      lambda s: s['diagnostics'].update(parser_discarded_bytes=8),
                      lambda s: s.update(status='waiting')]
         for options in [{'unsafe': mutation} for mutation in mutations] + [{'bad_frame': -1}]:
             with self.subTest(options=options):
                 result = self.run_command(**options)
                 self.assertIsInstance(self.failure, SystemExit)
                 self.assertEqual(self.failure.code, 1)
                 self.assertFalse(result['evidence']['capture_ok'])
                 self.assertEqual(len(self.requests), 4)
                 self.assertEqual([o['state'] for o in result['evidence']['observations']], self.states)
                 self.assertTrue(result['out'].endswith('press_before.failed.json'))
 
     def test_owner_change_rejects_completed_window(self):
         first = SimpleNamespace(info={'pid': 321, 'create_time': 123.0, 'cmdline': ['coinft_demo.py']})
         changed = SimpleNamespace(info={**first.info, 'create_time': 124.0})
         result = self.run_command(owners=[[first], [changed]])
         self.assertFalse(result['evidence']['capture_ok'])
         self.assertIn('owner changed', result['evidence']['error'])
         self.assertEqual(len(result['evidence']['observations']), len(self.requests))
 
     def test_duplicate_owner_or_wrong_listener_prevents_capture(self):
         proc = SimpleNamespace(info={'pid': 321, 'create_time': 123.0, 'cmdline': ['coinft_demo.py']})
         wrong = SimpleNamespace(status='LISTEN', laddr=SimpleNamespace(port=8765), pid=999)
         for options in ({'owners': [[proc, proc]]}, {'listeners': [wrong]}):
             with self.subTest(options=options):
                 self.assertIsNone(self.run_command(**options))
                 self.assertIsInstance(self.failure, ValueError)
                 self.assertEqual(self.capture_count, 0)
                 self.assertEqual(self.requests, [])
 
     def test_preexisting_evidence_prevents_owner_probe_and_capture(self):
         self.assertIsNone(self.run_command(exists=True))
         self.assertIsInstance(self.failure, FileExistsError)
         self.assertEqual(self.capture_count, 0)
         self.assertEqual(self.owner_count, 0)
         self.assertEqual(self.requests, [])
~~~

## tests/test_demo_profile.py (362 -> 362 lines)

~~~diff
--- before/tests/test_demo_profile.py
+++ current/tests/test_demo_profile.py
@@ full contextual change @@
         self.assertGreaterEqual(len(result["samples"]), 40)
         self.assertEqual(result["pose"], "train_press")
         self.assertEqual(result["assemblyId"], "assembly-A")
         self.assertEqual(result["source"], "http://example.test")
         self.assertEqual(result["sample_kind"], "http_snapshot")
         self.assertEqual([sample["f"] for sample in result["samples"]], list(range(1, 42)))
         self.assertTrue(all(len(sample["channels"]) == 12 for sample in result["samples"]))
         self.assertTrue(all(set(sample) == {"host", "f", "channels", "raw", "status", "rate", "invalid", "saturated", "resync"} for sample in result["samples"]))
         self.assertTrue(all(url == "http://example.test/api/state" and timeout == 1.5 for url, timeout in urls))
 
+    def test_rejects_regressing_frame_without_skipping_it(self):
-    def test_rejects_duplicate_frame_without_skipping_it(self):
         states = [state(i) for i in range(1, 44)]
+        states[8] = state(7)
+        with self.assertRaisesRegex(ValueError, "frame not increasing.*previous=8.*current=7"):
-        states[8] = state(8)
-        with self.assertRaisesRegex(ValueError, "frame not increasing.*previous=8.*current=8"):
             self.run_capture(states)
 
     def test_rejects_invalid_recent_without_skipping_it(self):
         states = [state(i) for i in range(1, 44)]
         states[8]["invalid_recent"] = 1
         with self.assertRaisesRegex(ValueError, "invalid_recent=1"):
             self.run_capture(states)
 
     def test_rejects_other_bad_state_fields(self):
         cases = [
~~~
