### Task 1: Build a separate qualitative profile from existing labeled evidence

**Files:** Create `calibration/build_qualitative_demo_profile.py`, `tests/test_qualitative_demo_profile.py`; generate `demo_web/shear_demo_profile.json` only after tests pass.

**Interfaces:** `build_profile(windows: dict[str,dict]) -> dict`. Required keys are `press_before`, `press`, `press_after`, `right_before`, `right`, `right_after`, `left_before`, `left`. Each value is the raw capture JSON dict plus an `evidence` basename. `main()` reads only these exact existing files:

| Key | Exact source path |
|---|---|
| `press_before` | `calibration/demo_attempt_before_second_usb_reconnect_20260925/demo_train_empty_before_press_20260925.json` |
| `press` | `calibration/demo_attempt_before_second_usb_reconnect_20260925/demo_train_press_20260925.json` |
| `press_after` | `calibration/demo_attempt_before_second_usb_reconnect_20260925/demo_train_empty_after_press_20260925.json` |
| `right_before` | `calibration/demo_attempt_before_second_usb_reconnect_20260925/demo_train_empty_before_right_20260925.json` |
| `right` | `calibration/demo_attempt_before_second_usb_reconnect_20260925/demo_train_right_20260925.json` |
| `right_after` | `calibration/demo_attempt_before_second_usb_reconnect_20260925/demo_train_empty_after_right_20260925.json` |
| `left_before` | `calibration/demo_diagnostic_empty_after_second_usb_20260925.json` |
| `left` | `calibration/demo_diagnostic_left_demo_force_20260925.json` |

- [ ] **Step 1: Write failing pure tests.** Use 40 timestamped 12-channel snapshots per window, with center press CH9–12 +700 and a reproducible CH1–8 leak; right/left get opposite zero-mean patterns. Add different fixed 12-channel offsets to the first six versus last two windows. Assert `build_profile` yields `mode == "qualitative"`, right signed score > threshold, left signed score < −threshold, and all adjusted empty/press scores below threshold. A second test makes the left action zero and asserts `ValueError`; a third makes one sample `waiting`/bad or leaves a window out and asserts `ValueError`.

  The scoring assertion must call the existing primitives instead of duplicating the formula:

  ```python
  from calibration.fit_demo_profile import signed_score
  right_score = signed_score(right_increment, profile["shear"]["pressLeak"], profile["shear"]["weights"])
  left_score = signed_score(left_increment, profile["shear"]["pressLeak"], profile["shear"]["weights"])
  self.assertGreater(right_score, profile["shear"]["threshold"])
  self.assertLess(left_score, -profile["shear"]["threshold"])
  ```

- [ ] **Step 2: Verify red.** Run `D:\conda\python.exe -m unittest tests.test_qualitative_demo_profile -v` from `D:\semg.claude\coinft`; expect import failure for `calibration.build_qualitative_demo_profile`.

- [ ] **Step 3: Implement the minimal builder.** Validate exactly eight keys, one nonblank assembly ID, each ≥30 samples spanning ≥4 seconds with increasing frame/host, `live`, finite 12-channel values, positive rate, invalid/saturated 0. Reject any malformed evidence before output. For each channel use the midpoint of median press/right before/after empties; left uses the median of its one empty. Subtract that baseline from the corresponding action and empty vectors; this is intentional because the browser also subtracts an explicit per-page empty baseline. Reuse `normal_score`, `contrast`, `residual`, `signed_score`, `percentile` from `fit_demo_profile.py`. Compute:

  ```python
  press_leak = [statistics.median(contrast(ch)[i] for ch in press) /
                max(statistics.median(normal_score(ch) for ch in press), 1)
                for i in range(8)]
  difference = [statistics.mean(residual(ch, press_leak)[i] for ch in right) -
                statistics.mean(residual(ch, press_leak)[i] for ch in left)
                for i in range(8)]
  magnitude = math.hypot(*difference)
  if magnitude <= 0: raise ValueError("no directional contrast")
  weights = [value / magnitude for value in difference]
  score = lambda ch: signed_score(ch, press_leak, weights)
  threshold = max(1.0, 1.05 * percentile([abs(score(ch)) for ch in empty + press], 95))
  right_scores, left_scores = [score(ch) for ch in right], [score(ch) for ch in left]
  if statistics.median(right_scores) <= threshold or statistics.median(left_scores) >= -threshold:
      raise ValueError("qualitative directions do not separate from background")
  span = max(1.0, min(percentile([abs(v) for v in right_scores], 90),
                      percentile([abs(v) for v in left_scores], 90)) - threshold)
  ```

  Return the exact profile schema above with computed arrays/threshold/span and all eight evidence basenames. CLI writes using `Path.open("x", encoding="utf-8")` and `json.dumps(..., allow_nan=False)`; never overwrite a profile. Keep `calibration/fit_demo_profile.py` unchanged.

- [ ] **Step 4: Verify green, then generate.** Run `D:\conda\python.exe -m unittest tests.test_qualitative_demo_profile -v`; expect all tests PASS. Run `D:\conda\python.exe calibration\build_qualitative_demo_profile.py --out demo_web\shear_demo_profile.json`; expect a printed summary of threshold, right/left score medians and eight evidence names, then inspect JSON and confirm `mode:"qualitative"`, ±X labels and no force units. If the builder rejects the real evidence, stop—do not hand-edit weights or lower the threshold to force enablement.

