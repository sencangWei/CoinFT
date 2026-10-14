# CoinFT Qualitative Shear Demo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Use the already captured CoinFT center-press and opposite one-axis push responses for a clearly labeled qualitative live grid, with one per-page empty-only visual zero.

**Architecture:** A separate offline script derives a qualitative profile from action-minus-adjacent-empty counts, never pretending mixed USB/tare sessions form a strict 18-window validation set. The browser loads it only when no strict profile exists, requires an explicit in-page empty baseline before applying it to the grid, and invalidates that baseline on bad/stale data or hardware tare. Trends, group bars, raw counts, firmware, backend and strict fitter remain unchanged.

**Tech Stack:** Windows PowerShell, Python 3 standard library and `unittest`, vanilla JavaScript/Canvas, Playwright Chromium.

**Operator-approved amendment (2026-09-26):** ordinary healthy repeated HTTP snapshots are skipped, never counted or used to refresh last-fresh-frame time; they preserve pending/ready visual zero until at least 500 ms without a fresh frame. Bad/degraded/malformed/regressed/status-failure/tare/HTTP-failure still invalidate immediately. This supersedes the earlier immediate-repeat rule; live serial batching is about 100 ms while UI polling is 50 ms. See `.superpowers/sdd/zero-batching-fix-brief.md` for focused fix and tests.

## Global Constraints

- Follow `docs/superpowers/specs/2026-09-25-coinft-qualitative-shear-demo-design.md`; this is **not** an N/N·m calibration or independent direction acceptance.
- Physical labels: −X is screen-right, +X is screen-left. Use the actual labeled files, never infer signs from electrode numbering.
- Do not change `coinft_demo.py`, firmware, serial protocol, old `calibration/fit_demo_profile.py`, historical 24×6 matrix, existing trends, G1–G6, or 12 raw readouts.
- `D:\semg.claude\coinft` is not a Git repository: omit commit commands and do not initialize Git. Preserve the two archived capture attempts and other user files.
- Missing/invalid evidence, non-separating direction, missing visual zero, stale/degraded data, or failed smoke test must leave lateral animation off. The UI must visibly say “定性演示／非标定力值／方向未独立验收”.

## File structure and interfaces

| File | Responsibility |
|---|---|
| `calibration/build_qualitative_demo_profile.py` (new) | Validate eight named evidence windows, subtract each action's own empty, build and exclusively write one qualitative profile. |
| `tests/test_qualitative_demo_profile.py` (new) | Verify opposite signs, fixed offsets across two tare sessions, conservative background threshold and refusal on unsafe/missing evidence. |
| `demo_web/shear_demo_profile.json` (generated) | Local `version:1`, `mode:"qualitative"` profile with labels, weights, threshold/span and exact evidence names; no force units or validated claim. |
| `demo_web/app.js` (modify) | Strict-profile precedence; explicit in-page baseline capture from fresh live snapshots; only subtract it for the grid; invalidate on degradation. |
| `demo_web/surface.js` (modify) | Use identical activation/release threshold for qualitative mode; keep strict mode's existing 0.7× release threshold. |
| `demo_web/index.html`, `demo_web/style.css` (modify) | Add “演示归零（仅画面）” next to device tare, plus explicit qualitative status copy. |
| `tests/test_demo_ui.py` (modify) | Synthetic browser regression: no baseline means flat, zero/±X/press, stale/tare/reconnect, existing charts/bars/cards/fullscreen/mobile/reduced motion. |
| `PROJECT_LOG.md` (modify) | Record generated profile, actual smoke-test result and limitations without claiming calibrated force. |

The profile keeps the existing numeric fields consumed by `surface.js`: `version:1`, `mode:"qualitative"`, `assemblyId:"coinft-current-20260925"`, `normal:{threshold:100,span:600}`, `shear:{enabled:true,weights:number[8],pressLeak:number[8],threshold:positive number,span:positive number}`, `rightLabel:"-X"`, `leftLabel:"+X"`, and eight exact evidence basenames. Task 1 computes every nonconstant coefficient from evidence; there are no manually chosen weights. The browser's qualitative input is always `data.channels.map((v,i) => v - demoBaseline[i])`. `demoBaseline` exists only after an explicit empty click and at least ten distinct good snapshots spanning at least one second; it is never applied to trend/bar/raw displays.

---

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

### Task 2: Require one visual-only empty baseline before qualitative grid motion

**Files:** Modify `demo_web/app.js`, `demo_web/surface.js`, `demo_web/index.html`, `demo_web/style.css`, `tests/test_demo_ui.py`.

**Interfaces:** `loadShearProfile()` keeps strict `/shear_profile.json` precedence and consults `/shear_demo_profile.json` only on strict 404; `demoBaseline: number[12] | null`; `demoZeroSamples: number[12][]`; `surfaceView.set(adjustedChannels, shearProfile)` is called only with a ready baseline in qualitative mode.

- [ ] **Step 1: Write failing browser tests.** Route strict profile to 404 and qualitative profile to a synthetic valid JSON. With synthetic `live` frames, assert before clicking `#demo-zero` both grid targets are 0 and label says “未经独立验收”; click it under empty while increasing frames for ≥1 second and ≥10 snapshots, then supply press, right and left vectors and assert `target>0,shearTarget==0` for press and opposite shear signs for right/left. Assert 12 raw card values and group/trend counts still use original unadjusted channels. Repeat with `waiting`, HTTP failure, frame regression, invalid/saturated, existing `#tare`, and 500 ms stalled state: grid clears, baseline becomes null, and user must click demo-zero again. Assert reduced-motion immediate levels, narrow/fullscreen layout remains usable. Also assert a present strict disabled profile prevents qualitative fallback.

- [ ] **Step 2: Verify red.** Run `D:\conda\python.exe -m unittest tests.test_demo_ui -v`; expect new `#demo-zero`/baseline assertions to fail while existing tests remain green.

- [ ] **Step 3: Implement the narrow UI path.** Add `<button id="demo-zero" type="button" disabled>演示归零（仅画面）</button>` after the existing `#tare`, styled with `.controls button + button { margin-top: 8px; }`. In `app.js`, add `let demoBaseline=null, demoZeroSamples=[], demoZeroStartedAt=0, demoZeroFrame=-1;` and a click handler that resets them to null/empty/0/`latestFrame`, clears the grid, and does **not** send `/api/tare`. Set `demoZeroStartedAt` when the **first accepted good snapshot** arrives (operator decision, 2026-09-25); collect only fresh accepted `live` frames with zero recent invalid/saturation, and require the first-to-last accepted sample span to be ≥1 second plus ≥10 distinct snapshots before setting:

  ```javascript
  demoBaseline = Array.from({length: 12}, (_, i) =>
    median(demoZeroSamples.map(sample => sample[i])));
  demoZeroSamples = [];
  ```

  In the existing accepted-frame branch, preserve all existing `paintBars`, `histories` and `groupResponses(data.channels)` calls, but for qualitative mode send only `data.channels.map((value, i) => value - demoBaseline[i])` to `surfaceView.set` when the baseline exists; otherwise `surfaceView.clear()`. A single `invalidateDemoZero()` helper sets baseline null, empties pending samples, clears the grid and updates button/caption. Call it on non-live/degraded/regressed/stale/HTTP-failure state and before/after device tare. Only enable `#demo-zero` while a qualitative profile and good live stream are available. Strict mode retains its existing `surfaceView.set(data.channels, profile)` path and caption.

  In `surface.js`, change only the threshold choice to `shear.threshold * (profile.mode === "qualitative" ? 1 : (active ? 0.7 : 1))`; retain the strict fitter behavior and the existing geometry/animation.

- [ ] **Step 4: Verify green and UI regression.** Run `D:\conda\python.exe -m unittest tests.test_demo_ui -v` and `D:\conda\python.exe -m unittest discover -s tests -q`; expect all pass. Run Playwright at 1440×900 and 390×844 using synthetic states; inspect empty/press/right/left, reduced motion, no clipping, and unchanged trends/cards. Do not call the real `/api/tare` during browser tests.

### Task 3: Live qualitative smoke test and safe handoff

**Files:** Update `PROJECT_LOG.md`; save non-overwriting evidence under `calibration/` or `.superpowers/sdd/` as needed.

**Interfaces:** Consumes Task 1's generated `demo_web/shear_demo_profile.json` and Task 2's browser UI. Does not alter firmware, backend, strict fitted profile, or historical evidence.

- [ ] **Step 1: Preflight.** Read the generated JSON: require `mode:"qualitative"`, `shear.enabled:true`, `rightLabel:"-X"`, `leftLabel:"+X"`, eight exact source basenames, finite coefficients, threshold above recorded empty/press p95. Confirm no strict profile exists or takes precedence. Query `/api/state` twice ~0.5 s apart; require `live`, increasing frames, positive rate, zero recent invalid/saturation. If not, stop.

- [ ] **Step 2: Operator-guided smoke test, one pose at a time.** Ask the operator to leave CoinFT empty, click “演示归零”, wait for ready status, and verify grid flat. After explicit confirmation, guide center press → release → −X push → release → +X push → release; never auto-advance. Record one browser screenshot or short video and raw state evidence per pose. Confirm center press indents without persistent shear, −X shifts screen-right, +X screen-left, and each release returns flat. Verify trends, G1–G6, 12 raw numbers still update without baseline subtraction.

- [ ] **Step 3: Stop safely on failure; document actual result.** If either sign is wrong, empty sticks, baseline is not reproducible, or USB/serial stalls, move the generated qualitative profile to a uniquely named archive inside `calibration/` after resolving/checking both paths, leaving no enabled demo profile; the app falls back to press-only. Do not edit numeric coefficients to force a pass. Add a dated `PROJECT_LOG.md` entry distinguishing synthetic tests, one-pose offline evidence and actual live outcome; explicitly state no independent validation or N/N·m calibration. If smoke passes, leave profile enabled but label it qualitative and require visual zero on every page open.

## Plan self-review targets

- Spec coverage: measured one-pose relative template, independent qualitative file, visual-only zero, no raw/trend changes, stale/tare reset, explicit warning, smoke stop rule.
- Non-Git environment: no commit/worktree commands; all archive operations must be recoverable and bounded to named calibration files.
- No partial claims: passing unit/browser tests or opposite offline medians alone never proves the live physical direction.
