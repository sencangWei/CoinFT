# Task 3 preparation review package

No Git repository. Before this task all four task-owned new files were absent. This package contains complete additions; no production changes are included. Physical Task 3 and Task 4 remain pending.


## .superpowers/sdd/shear-refit-capture-command.py

~~~diff
--- /dev/null
+++ .superpowers/sdd/shear-refit-capture-command.py
@@ -0,0 +1,72 @@
+import json
+import time
+from datetime import datetime
+from pathlib import Path
+import psutil
+from calibration.capture_demo_pose import capture
+
+def owner():
+    candidates = []
+    for proc in psutil.process_iter(["pid", "create_time", "cmdline"]):
+        args = proc.info["cmdline"] or []
+        if any(Path(a).name == "coinft_demo.py" for a in args):
+            candidates.append(proc.info)
+    listeners = [c for c in psutil.net_connections(kind="tcp")
+                 if c.status == psutil.CONN_LISTEN and c.laddr.port == 8765]
+    if len(candidates) != 1 or len(listeners) != 1:
+        raise ValueError("not exactly one HTTP capture owner")
+    p = candidates[0]
+    if listeners[0].pid != p["pid"]:
+        raise ValueError("listener does not belong to capture owner")
+    return {"pid": p["pid"], "created": p["create_time"]}
+
+pose = "press_before"
+out = Path("calibration/shear_refit_20260928/fit/press_before.json")
+if out.exists():
+    raise FileExistsError(out)
+who = owner()
+observations = []
+def observe(state):
+    observations.append({"host": datetime.now().astimezone().isoformat(),
+                         "monotonic": time.monotonic(), "state": state})
+    if state.get("port") != "COM6" or state.get("mode") != "live":
+        raise ValueError("wrong port/mode")
+    if state.get("tare_progress") != 100:
+        raise ValueError("tare/baseline epoch not stable")
+    if not state.get("diagnostics") or not state.get("recovery"):
+        raise ValueError("missing stream quality evidence")
+    if len(observations) > 1:
+        first, previous = observations[0]["state"], observations[-2]["state"]
+        for key in ("invalid_frames", "saturated", "resyncs"):
+            if state[key] != first[key]:
+                raise ValueError("new cumulative quality fault: "+key)
+        for key in ("attempts", "successes"):
+            if state["recovery"][key] != first["recovery"][key]:
+                raise ValueError("stream recovery changed epoch")
+        for key in ("serial_bytes", "parsed_frames"):
+            if state["diagnostics"][key] <= previous["diagnostics"][key]:
+                raise ValueError("byte/frame observation not advancing")
+        if (state["diagnostics"]["parser_discarded_bytes"] !=
+                first["diagnostics"]["parser_discarded_bytes"]):
+            raise ValueError("parser discarded bytes increased")
+
+try:
+    data = capture("http://127.0.0.1:8765", pose,
+                   "coinft-current-20260925", 5.0, 0.1, on_state=observe)
+    if len(data["samples"]) < 40 or owner() != who:
+        raise ValueError("insufficient samples or owner changed")
+    a, b = observations[0], observations[-1]
+    rate = (b["state"]["frames"]-a["state"]["frames"])/(b["monotonic"]-a["monotonic"])
+    if not 150 <= rate <= 250:
+        raise ValueError("aggregate frame rate outside150–250Hz")
+    data.update(owner=who, evidence=out.name, observations=observations,
+                aggregate_rate=rate, capture_ok=True)
+    print(json.dumps({"out": str(out), "evidence": data},
+                     ensure_ascii=False, allow_nan=False, separators=(",", ":")))
+except Exception as exc:
+    print(json.dumps({"out": str(out.with_suffix(".failed.json")),
+                      "evidence": {"capture_ok": False, "pose": pose,
+                                   "owner": who, "error": repr(exc),
+                                   "observations": observations}},
+                     ensure_ascii=False, separators=(",", ":")))
+    raise SystemExit(1)
~~~

## tests/test_refit_capture_command.py

~~~diff
--- /dev/null
+++ tests/test_refit_capture_command.py
@@ -0,0 +1,149 @@
+import contextlib
+import io
+import json
+import runpy
+import unittest
+from datetime import datetime, timedelta, timezone
+from pathlib import Path
+from types import SimpleNamespace
+from unittest.mock import patch
+
+
+COMMAND = Path(__file__).resolve().parents[1] / '.superpowers/sdd/shear-refit-capture-command.py'
+
+
+class RefitCaptureCommandTests(unittest.TestCase):
+    def test_prepared_command_exists(self):
+        self.assertTrue(COMMAND.is_file(), 'single-pose capture command is not prepared')
+
+    def run_command(self, unsafe=None, owners=None, listeners=None, exists=False):
+        self.assertTrue(COMMAND.is_file(), 'single-pose capture command is not prepared')
+        tick = [0.0]
+        self.states, self.requests = [], []
+        stamp = datetime(2026, 9, 28, tzinfo=timezone.utc)
+
+        class ClockDate:
+            @classmethod
+            def now(cls):
+                return stamp + timedelta(seconds=tick[0])
+
+            @staticmethod
+            def fromisoformat(value):
+                return datetime.fromisoformat(value)
+
+        def receive(url, timeout):
+            self.requests.append((url, timeout))
+            index = len(self.requests) - 1
+            state = {
+                'status': 'live', 'mode': 'live', 'port': 'COM6',
+                'frames': 100 + 20 * index, 'rate': 200.0,
+                'tare_progress': 100, 'invalid_recent': 0,
+                'saturated_recent': 0, 'invalid_frames': 3,
+                'saturated': 2, 'resyncs': 1,
+                'channels': [float(i) for i in range(12)], 'raw': [24000] * 12,
+                'axes': [0.0] * 6, 'message': '数据流正常', 'updated_at': stamp.timestamp() + tick[0],
+                'diagnostics': {'serial_bytes': 2000 + index * 600,
+                                'serial_reads': 100 + index * 20,
+                                'parsed_frames': 100 + index * 20,
+                                'parser_discarded_bytes': 7,
+                                'parser_pending_bytes': 0,
+                                'last_byte_at': stamp.timestamp() + tick[0],
+                                'last_parsed_frame_at': stamp.timestamp() + tick[0]},
+                'recovery': {'attempts': 1, 'successes': 1, 'last_fault':
+                             {'reason': 'historical timeout', 'observed_at': stamp.timestamp() - 10,
+                              'frames': 20, 'diagnostics': {'serial_reads': 20,
+                              'serial_bytes': 600, 'parsed_frames': 20,
+                              'last_byte_at': stamp.timestamp() - 10,
+                              'last_parsed_frame_at': stamp.timestamp() - 10,
+                              'parser_pending_bytes': 0, 'parser_discarded_bytes': 7}}},
+            }
+            if unsafe is not None and index == 3:
+                unsafe(state)
+            self.states.append(state)
+            return io.BytesIO(json.dumps(state).encode())
+
+        proc = SimpleNamespace(info={'pid': 321, 'create_time': 123.0,
+                                     'cmdline': ['python', 'coinft_demo.py']})
+        listener = SimpleNamespace(status='LISTEN', laddr=SimpleNamespace(port=8765), pid=321)
+        output = io.StringIO()
+        self.failure = None
+        with patch('psutil.process_iter', side_effect=owners or [[proc], [proc]]) as process, \
+             patch('psutil.net_connections', return_value=listeners or [listener]), \
+             patch('pathlib.Path.exists', return_value=exists), \
+             patch('calibration.capture_demo_pose.urllib.request.urlopen', side_effect=receive), \
+             patch('time.monotonic', side_effect=lambda: tick[0]), \
+             patch('time.sleep', side_effect=lambda seconds: tick.__setitem__(0, tick[0] + seconds)), \
+             patch('calibration.capture_demo_pose.datetime', ClockDate), \
+             patch('calibration.capture_demo_pose.capture', wraps=__import__(
+                 'calibration.capture_demo_pose', fromlist=['capture']).capture) as capture, \
+             contextlib.redirect_stdout(output):
+            with patch('datetime.datetime', ClockDate):
+                try:
+                    runpy.run_path(str(COMMAND))
+                except (SystemExit, ValueError, FileExistsError) as exc:
+                    self.failure = exc
+            self.capture_count, self.owner_count = capture.call_count, process.call_count
+        self.output = output.getvalue()
+        return json.loads(self.output) if self.output else None
+
+    def test_success_serializes_complete_observations_and_fresh_path(self):
+        result = self.run_command()
+        self.assertIsNone(self.failure)
+        evidence = result['evidence']
+        self.assertTrue(evidence['capture_ok'])
+        self.assertEqual(Path(result['out']), Path('calibration/shear_refit_20260928/fit/press_before.json'))
+        self.assertEqual(evidence['pose'], 'press_before')
+        self.assertEqual(evidence['owner'], {'pid': 321, 'created': 123.0})
+        self.assertEqual(len(evidence['observations']), len(self.requests))
+        self.assertGreaterEqual(len(evidence['observations']), 51)
+        self.assertEqual([o['state'] for o in evidence['observations']], self.states)
+        self.assertAlmostEqual(evidence['aggregate_rate'], 200)
+        self.assertGreaterEqual(evidence['observations'][-1]['monotonic'], 5)
+        self.assertTrue(all(url == 'http://127.0.0.1:8765/api/state' and timeout == 1.5
+                            for url, timeout in self.requests))
+        self.assertEqual(evidence['observations'][-1]['state']['recovery']['last_fault'],
+                         self.states[-1]['recovery']['last_fault'])
+
+    def test_unsafe_final_observation_is_retained_and_aborts(self):
+        mutations = [lambda s: s.update(port='COM8'),
+                     lambda s: s.update(mode='waiting'),
+                     lambda s: s.update(tare_progress=0),
+                     lambda s: s.update(invalid_frames=4),
+                     lambda s: s['recovery'].update(attempts=2),
+                     lambda s: s['diagnostics'].update(serial_bytes=0),
+                     lambda s: s['diagnostics'].update(parser_discarded_bytes=8),
+                     lambda s: s.update(status='waiting')]
+        for mutation in mutations:
+            with self.subTest(mutation=mutation):
+                result = self.run_command(unsafe=mutation)
+                self.assertIsInstance(self.failure, SystemExit)
+                self.assertEqual(self.failure.code, 1)
+                self.assertFalse(result['evidence']['capture_ok'])
+                self.assertEqual(len(self.requests), 4)
+                self.assertEqual([o['state'] for o in result['evidence']['observations']], self.states)
+                self.assertTrue(result['out'].endswith('press_before.failed.json'))
+
+    def test_owner_change_rejects_completed_window(self):
+        first = SimpleNamespace(info={'pid': 321, 'create_time': 123.0, 'cmdline': ['coinft_demo.py']})
+        changed = SimpleNamespace(info={**first.info, 'create_time': 124.0})
+        result = self.run_command(owners=[[first], [changed]])
+        self.assertFalse(result['evidence']['capture_ok'])
+        self.assertIn('owner changed', result['evidence']['error'])
+        self.assertEqual(len(result['evidence']['observations']), len(self.requests))
+
+    def test_duplicate_owner_or_wrong_listener_prevents_capture(self):
+        proc = SimpleNamespace(info={'pid': 321, 'create_time': 123.0, 'cmdline': ['coinft_demo.py']})
+        wrong = SimpleNamespace(status='LISTEN', laddr=SimpleNamespace(port=8765), pid=999)
+        for options in ({'owners': [[proc, proc]]}, {'listeners': [wrong]}):
+            with self.subTest(options=options):
+                self.assertIsNone(self.run_command(**options))
+                self.assertIsInstance(self.failure, ValueError)
+                self.assertEqual(self.capture_count, 0)
+                self.assertEqual(self.requests, [])
+
+    def test_preexisting_evidence_prevents_owner_probe_and_capture(self):
+        self.assertIsNone(self.run_command(exists=True))
+        self.assertIsInstance(self.failure, FileExistsError)
+        self.assertEqual(self.capture_count, 0)
+        self.assertEqual(self.owner_count, 0)
+        self.assertEqual(self.requests, [])
~~~

## calibration/shear_refit_20260928/fit/.keep

~~~diff
--- /dev/null
+++ calibration/shear_refit_20260928/fit/.keep
@@ -0,0 +1,1 @@
+
~~~

## calibration/shear_refit_20260928/validation/.keep

~~~diff
--- /dev/null
+++ calibration/shear_refit_20260928/validation/.keep
@@ -0,0 +1,1 @@
+
~~~
