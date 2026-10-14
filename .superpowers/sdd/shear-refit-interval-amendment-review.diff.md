# Approved interval amendment review

No Git repository. Before/after changed lines with three lines of context, from complete files stored before implementation. Only source interval and cadence test values/one assertion changed. Preparation review already approved the unchanged whole command/test scaffolding.


## .superpowers/sdd/shear-refit-capture-command.py

~~~diff
--- before/.superpowers/sdd/shear-refit-capture-command.py
+++ current/.superpowers/sdd/shear-refit-capture-command.py
@@ context @@
 
 try:
     data = capture("http://127.0.0.1:8765", pose,
+                   "coinft-current-20260925", 5.0, 0.125, on_state=observe)
-                   "coinft-current-20260925", 5.0, 0.1, on_state=observe)
     if len(data["samples"]) < 40 or owner() != who:
         raise ValueError("insufficient samples or owner changed")
     a, b = observations[0], observations[-1]
~~~

## tests/test_refit_capture_command.py

~~~diff
--- before/tests/test_refit_capture_command.py
+++ current/tests/test_refit_capture_command.py
@@ context @@
             self.requests.append((url, timeout))
             index = len(self.requests) - 1
             state = dict(unsafe_states[0] if unsafe_states and index == 3
+                         else core_states[index * 25])
-                         else core_states[index * 20])
             state.update({
                 'mode': 'live', 'port': 'COM6',
                 'tare_progress': 100, 'invalid_frames': 3, 'saturated': 2,
@@ context @@
         self.assertEqual(evidence['pose'], 'press_before')
         self.assertEqual(evidence['owner'], {'pid': 321, 'created': 123.0})
         self.assertEqual(len(evidence['observations']), len(self.requests))
+        self.assertEqual(len(evidence['observations']), 41)
-        self.assertGreaterEqual(len(evidence['observations']), 51)
         self.assertEqual([o['state'] for o in evidence['observations']], self.states)
         self.assertAlmostEqual(evidence['aggregate_rate'], 200)
         self.assertGreaterEqual(evidence['observations'][-1]['monotonic'], 5)
@@ context @@
                      lambda s: s['recovery'].update(attempts=2),
                      lambda s: s['recovery'].update(successes=2),
                      lambda s: s['diagnostics'].update(serial_bytes=0),
+                     lambda s: s['diagnostics'].update(parsed_frames=51),
-                     lambda s: s['diagnostics'].update(parsed_frames=41),
                      lambda s: s['diagnostics'].update(parser_discarded_bytes=8),
                      lambda s: s.update(status='waiting')]
         for options in [{'unsafe': mutation} for mutation in mutations] + [{'bad_frame': -1}]:
~~~
