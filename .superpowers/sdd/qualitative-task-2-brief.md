### Task 2: Require one visual-only empty baseline before qualitative grid motion

**Files:** Modify `demo_web/app.js`, `demo_web/surface.js`, `demo_web/index.html`, `demo_web/style.css`, `tests/test_demo_ui.py`.

**Interfaces:** `loadShearProfile()` keeps strict `/shear_profile.json` precedence and consults `/shear_demo_profile.json` only on strict 404; `demoBaseline: number[12] | null`; `demoZeroSamples: number[12][]`; `surfaceView.set(adjustedChannels, shearProfile)` is called only with a ready baseline in qualitative mode.

- [ ] **Step 1: Write failing browser tests.** Route strict profile to 404 and qualitative profile to a synthetic valid JSON. With synthetic `live` frames, assert before clicking `#demo-zero` both grid targets are 0 and label says “未经独立验收”; click it under empty while increasing frames for ≥1 second and ≥10 snapshots, then supply press, right and left vectors and assert `target>0,shearTarget==0` for press and opposite shear signs for right/left. Assert 12 raw card values and group/trend counts still use original unadjusted channels. Repeat with `waiting`, HTTP failure, frame regression, invalid/saturated, existing `#tare`, and 500 ms stalled state: grid clears, baseline becomes null, and user must click demo-zero again. Assert reduced-motion immediate levels, narrow/fullscreen layout remains usable. Also assert a present strict disabled profile prevents qualitative fallback.

- [ ] **Step 2: Verify red.** Run `D:\conda\python.exe -m unittest tests.test_demo_ui -v`; expect new `#demo-zero`/baseline assertions to fail while existing tests remain green.

- [ ] **Step 3: Implement the narrow UI path.** Add `<button id="demo-zero" type="button" disabled>演示归零（仅画面）</button>` after the existing `#tare`, styled with `.controls button + button { margin-top: 8px; }`. In `app.js`, add `let demoBaseline=null, demoZeroSamples=[], demoZeroStartedAt=0, demoZeroFrame=-1;` and a click handler that sets them to null/empty/current `performance.now()`/`latestFrame`, clears the grid, and does **not** send `/api/tare`. Collect only fresh accepted `live` frames with zero recent invalid/saturation; once ≥1 second and ≥10 snapshots, set:

  ```javascript
  demoBaseline = Array.from({length: 12}, (_, i) =>
    median(demoZeroSamples.map(sample => sample[i])));
  demoZeroSamples = [];
  ```

  In the existing accepted-frame branch, preserve all existing `paintBars`, `histories` and `groupResponses(data.channels)` calls, but for qualitative mode send only `data.channels.map((value, i) => value - demoBaseline[i])` to `surfaceView.set` when the baseline exists; otherwise `surfaceView.clear()`. A single `invalidateDemoZero()` helper sets baseline null, empties pending samples, clears the grid and updates button/caption. Call it on non-live/degraded/regressed/stale/HTTP-failure state and before/after device tare. Only enable `#demo-zero` while a qualitative profile and good live stream are available. Strict mode retains its existing `surfaceView.set(data.channels, profile)` path and caption.

  In `surface.js`, change only the threshold choice to `shear.threshold * (profile.mode === "qualitative" ? 1 : (active ? 0.7 : 1))`; retain the strict fitter behavior and the existing geometry/animation.

- [ ] **Step 4: Verify green and UI regression.** Run `D:\conda\python.exe -m unittest tests.test_demo_ui -v` and `D:\conda\python.exe -m unittest discover -s tests -q`; expect all pass. Run Playwright at 1440×900 and 390×844 using synthetic states; inspect empty/press/right/left, reduced motion, no clipping, and unchanged trends/cards. Do not call the real `/api/tare` during browser tests.

