# CoinFT Center Press and Bidirectional Shear Demo Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the existing live grid show a central indentation under normal press and opposite lateral deformation under verified, opposite one-axis PCB pushes.

**Architecture:** Keep the COM10 → `/api/state` → `app.js` path and the current dashboard. A short operator-labeled capture produces training and held-out snapshots; a deterministic offline fitter writes a validated local profile. The browser uses that profile only for the grid, falling back to central indentation with shear disabled if the profile is missing or fails validation.

**Tech Stack:** Windows PowerShell, Python 3 standard library, vanilla JavaScript/Canvas 2D, Python `unittest`, Playwright Chromium.

## Global Constraints

- Follow `docs/superpowers/specs/2026-09-25-coinft-normal-bidirectional-shear-demo-design.md` and `DESIGN.md`; this plan supersedes contact-location inference, not the current dashboard layout.
- Do not change firmware, serial protocol, `coinft_demo.py` API, historical 24×6 matrix, trends, G1–G6, 12 channel numbers, or display sensitivity.
- Use only the current assembly's labeled actions for the sign. Never infer screen-left/right from channel numbering or call a visualization score calibrated N/N·m.
- Collect one stable pose at a time after explicit operator confirmation; about 5 seconds and ~40 distinct `/api/state` snapshots per pose, with adjacent empty poses. Stop the capture when data are stale, non-live, invalid, or saturated.
- Round 2 is independent validation, never training. Enable signed shear only if training background `p95(abs(score)) < p10(abs(score))` for both pushes, and held-out empty/press do not trigger persistent shear while at least 80% of each held-out push has correct sign above threshold; held-out press indentation must trigger in at least 80% of snapshots.
- Missing/invalid/unvalidated profile means **no lateral animation**. Stale frames, tare, waiting, error, invalid/saturated samples, and HTTP failure flatten both effects; reduced-motion mode jumps directly to target.
- Preserve unrelated changes. `D:\semg.claude\coinft` is not a Git repository; omit commit steps and do not initialize Git.

## File structure and interfaces

| File | Responsibility |
|---|---|
| `calibration/capture_demo_pose.py` (new) | Capture one explicitly named, stable HTTP window with metadata and distinct frame IDs. Never control the hardware or switch poses. |
| `calibration/fit_demo_profile.py` (new) | Read exactly labeled train/holdout windows, score the same `/api/state` tare-relative channels consumed by the browser, use adjacent empty windows as background evidence, learn normal threshold and signed CH1–CH8 contrast, print gate results, write an enabled/disabled JSON profile. |
| `tests/test_demo_profile.py` (new) | Synthetic fitter tests, including sign, press cross-talk, holdout rejection, and malformed samples. |
| `demo_web/shear_profile.json` (new, generated) | Local profile: schema version, enabled flag, weights/thresholds, physical right/left labels, evidence filenames; no prevalidated coefficients. |
| `demo_web/surface.js` (modify) | Pure `normalLevel(channels, profile)` and `shearLevel(channels, profile)` helpers plus existing Canvas renderer. Keep `target`, `level`, `set`, `clear`, `resize`; add `shearTarget`, `shearLevel` properties. |
| `demo_web/app.js` (modify) | Load profile once with safe disabled fallback; pass it only to the surface on fresh live data; clear on degraded data. |
| `demo_web/index.html` (modify) | Identify grid as “正压／剪切响应示意”; retain every other dashboard section. |
| `tests/test_demo_ui.py` (modify) | Synthetic browser states, Canvas geometry, stale/degraded behavior, trends/bars/readout regression. |
| `PROJECT_LOG.md` (modify) | Record actual capture, gate outcome, and live verification; do not claim shear works before measured evidence. |

The profile interface is `{"version":1,"assemblyId":string,"normal":{"threshold":number,"span":number},"shear":{"enabled":boolean,"weights":number[8],"pressLeak":number[8],"threshold":number,"span":number},"rightLabel":string,"leftLabel":string,"evidence":string[]}`. `channels` are 12 relative-baseline counts from `/api/state`; invalid array lengths/nonfinite values produce zero levels. `pressLeak` is the fitted CH1–CH8 common-mode-removed center-press pattern per unit normal score. `shearLevel` returns signed `[-1,1]`; positive means the operator-labeled screen-right push. If no profile is available, the fallback is exactly `normal: {threshold:100, span:600}`, `shear.enabled:false`; only CH9–CH12 can indent the grid in that mode.

---

### Task 1: Reproducible, one-pose-at-a-time evidence capture

**Files:** Create `calibration/capture_demo_pose.py`; create `tests/test_demo_profile.py` with capture tests.

**Interfaces:** `capture(url: str, pose: str, assembly_id: str, seconds: float, interval: float) -> dict` returns `{pose, assemblyId, source, sample_kind, samples}`; each sample has `host`, `f`, `channels`, `raw`, `status`, `rate`, `invalid`, `saturated`, `resync`.

- [ ] **Step 1: Write the failing test.** In `tests/test_demo_profile.py`, create a local fake `urlopen` context returning 43 valid states with increasing `frames`, then assert `capture(..., seconds=5, interval=0.125)` returns 40+ distinct frames with 12 channels and rejects a repeated frame or `invalid_recent>0`. Use `unittest.mock.patch` for `urllib.request.urlopen`, `time.monotonic`, `time.sleep`, and `datetime` only as needed; the test must make no network call.
- [ ] **Step 2: Verify red.** Run `D:\conda\python.exe -m unittest tests.test_demo_profile -v` from `D:\semg.claude\coinft`. Expected: import failure for `calibration.capture_demo_pose`.
- [ ] **Step 3: Implement the capture.** Use `urllib.request.urlopen(f"{url}/api/state", timeout=1.5)` per sample, `json.load`, `time.monotonic` deadline, `time.sleep(max(0, interval-elapsed))`, and `datetime.now().astimezone().isoformat()`. Reject non-live, bad counters, malformed/nonfinite 12-element `channels`/`raw`, frame IDs not increasing, or fewer than 30 distinct snapshots. `argparse` requires `--pose`, `--assembly-id`, `--out`, `--url` (default `http://127.0.0.1:8765`), `--seconds` (default 5), and `--interval` (default 0.125). Write output only after successful capture using `Path.write_text(json.dumps(..., ensure_ascii=False, indent=2), encoding="utf-8")`; do not overwrite an existing evidence file.

  The acceptance predicate is exact; call it for every HTTP response before appending:

  ```python
  def valid_state(state, previous_frame):
      vectors = (state.get("channels"), state.get("raw"))
      return (state.get("status") == "live"
              and isinstance(state.get("frames"), int)
              and state["frames"] > previous_frame
              and isinstance(state.get("rate"), (int, float))
              and math.isfinite(state["rate"]) and state["rate"] > 0
              and state.get("invalid_recent") == 0
              and state.get("saturated_recent") == 0
              and all(isinstance(v, list) and len(v) == 12
                      and all(isinstance(x, (int, float)) and math.isfinite(x)
                              for x in v) for v in vectors))
  ```
- [ ] **Step 4: Verify green.** Run `D:\conda\python.exe -m unittest tests.test_demo_profile -v`. Expected: capture tests PASS. Read the script's `--help`; expected: all five flags and no hardware-write operation.
- [ ] **Step 5: Capture only after operator confirmation.** For each of `train_empty_before_press`, `train_press`, `train_empty_after_press`, `train_empty_before_right`, `train_right`, `train_empty_after_right`, `train_empty_before_left`, `train_left`, `train_empty_after_left`, and independent `holdout_*` equivalents, ask for one pose, wait for confirmation, then run `D:\conda\python.exe calibration\capture_demo_pose.py --pose <pose> --assembly-id <current-assembly-label> --out calibration\demo_<pose>_20260925.json`. Confirm physically which push is screen-right before the first right capture. Each run prints snapshot count and frame/rate/quality; stop if any run fails. Do not restart the stopped 200 g repeatability series. The date suffix should match the actual capture date if performed later.

### Task 2: Fit the profile and enforce an independent acceptance gate

**Files:** Create `calibration/fit_demo_profile.py`; modify `tests/test_demo_profile.py`; generate `demo_web/shear_profile.json` only after the real capture.

**Interfaces:** `fit_profile(windows: dict[str,dict], right_label: str, left_label: str) -> tuple[dict,dict]` yields the profile and a report. Each window is the raw capture dictionary from Task 1. The fitter validates sample status/frame quality and scores the captured `channels` directly, in the same tare-relative coordinate system as the browser. Adjacent empty windows measure actual background and drift; they must not be subtracted only in the fitter. The UI consumes the JSON schema stated above.

- [ ] **Step 1: Write failing synthetic tests.** Create training/holdout windows with CH9–CH12 `+200` for press, with CH1–CH8 center-press leakage, and opposite zero-mean patterns for right/left. Assert a passed profile has `shear.enabled == True`, right score `>0`, left score `<0`, press shear score below threshold, and a held-out reversed or noise-only left push makes `shear.enabled == False`. Assert malformed 12-channel vectors raise `ValueError` and the holdout windows never modify trained weights or thresholds.
- [ ] **Step 2: Verify red.** Run `D:\conda\python.exe -m unittest tests.test_demo_profile -v`. Expected: fitter import or assertion failure.
- [ ] **Step 3: Implement the small deterministic fitter.** Use only stdlib `json`, `math`, `statistics`, `argparse`, `pathlib`. Keep the adjacent `empty_before`/`empty_after` samples for background checks, but score every captured `channels` vector directly because the browser receives the same tare-relative vectors; fitter-only midpoint subtraction would make the learned threshold incompatible with live display. Define normal score as `median(CH9..CH12)` clipped below at 0. Define CH1–CH8 contrast `x_i = channel_i - mean(CH1..CH8)`; learn `pressLeak_i = median(press_x_i)/max(median(press_normal),1)`. Residual `r_i=x_i-pressLeak_i*normal_score`. Unit template is normalized `mean(right_r)-mean(left_r)`; signed score is dot(template, residual). Orient template so training right median is positive and left median negative; if that cannot be achieved, disable shear. Derive normal threshold midpoint between training empty p95 and press p10; shear threshold midpoint between `p95(abs(empty,press signed scores))` and the lower of right/left `p10(abs(score))`; `span` is the positive difference between action p90 and threshold (minimum 1). Percentiles use deterministic sorted linear interpolation. If required inequalities fail, set shear `enabled=false` and avoid storing fabricated weights.

  Use these exact score primitives in the fitter and mirror them in the browser:

  ```python
  def normal_score(ch):
      return max(0.0, statistics.median(ch[8:12]))

  def contrast(ch):
      avg = statistics.mean(ch[:8])
      return [value - avg for value in ch[:8]]

  def residual(ch, press_leak):
      n = normal_score(ch)
      return [value - leak * n for value, leak in zip(contrast(ch), press_leak)]

  def signed_score(ch, press_leak, weights):
      return sum(a * b for a, b in zip(residual(ch, press_leak), weights))
  ```
- [ ] **Step 4: Apply held-out gate and record reasons.** With frozen trained parameters, count the fraction of held-out press snapshots above normal threshold and each push's correctly signed score above shear threshold; require each at least 0.8. Require held-out empty/press shear above-threshold fraction below 0.2. On any failure, write a disabled shear profile and a report with observed fractions and failing condition. CLI requires `--input-dir calibration`, `--output demo_web/shear_profile.json`, `--report calibration/demo_shear_gate_20260925.json`, `--right-label`, `--left-label`; include exact evidence filenames in both outputs. Refuse to enable if any required capture is missing, malformed, stale, invalid, saturated, or marked as a different assembly. Do not mix rounds to recover a failure.
- [ ] **Step 5: Verify green.** Run `D:\conda\python.exe -m unittest tests.test_demo_profile -v`. Expected: all fitter tests PASS. Run fitter on the captured windows only after Task 1; read report and show operator the pass/fail numbers. Do not change threshold criteria to force PASS.

### Task 3: Drive the existing grid with independently gated normal and shear levels

**Files:** Modify `demo_web/surface.js`, `demo_web/app.js`, `demo_web/index.html`, and `tests/test_demo_ui.py`.

**Interfaces:** `normalLevel(channels, profile): number` in `[0,1]`; `shearLevel(channels, profile, active=false): number` in `[-1,1]`; `createSurface(canvas).set(channels, profile)` updates normal `target` and signed `shearTarget`. `active` is true only while a previous frame's signed shear remains above its release threshold; it changes the dead-zone threshold from `T` to `0.7*T`, not the learned weights or sign. Keep `surfaceLevel(channels)` for existing compatibility tests, but do not use it as the live normal signal after this task.

- [ ] **Step 1: Write failing browser tests.** Serve a synthetic *validated* profile through a route for `/shear_profile.json`. Assert pressing with CH9–CH12 high and fitted CH1–CH8 leakage gives `target>0` and `shearTarget===0`; right/left patterns give opposite signs; combining press+right gives both; clearing, invalid/saturated state, tare, stale request, and HTTP 503 zero both; `prefers-reduced-motion` makes `shearLevel===shearTarget` immediately. Capture canvases and assert a grid reference vertex moves in opposite x directions for right versus left. Retain assertions for both charts, six groups, 12 channel cards, narrow layout and fullscreen.
- [ ] **Step 2: Verify red.** Run `D:\conda\python.exe -m unittest tests.test_demo_ui -v`. Expected: new signed-shear assertions FAIL while existing tests still pass.
- [ ] **Step 3: Add pure score helpers to `surface.js`.** Validate 12 finite counts and profile schema/version. `normalLevel` uses `median(channels.slice(8))`, positive threshold/span and clamp. `shearLevel` returns 0 when disabled; otherwise subtract the mean of CH1–CH8, subtract `pressLeak[i]*normalScore`, dot with eight weights, apply a symmetric dead zone around threshold, clamp by span. `set()` passes `active = Math.abs(surface.shearTarget)>0`, implementing a release threshold of `0.7*T` without altering the learned sign; no path may turn disabled shear on. Keep both targets independent.

  Add these helpers beside the existing `surfaceLevel` and use them only for the new live surface path:

  ```javascript
  function validSurfaceChannels(ch) {
    return Array.isArray(ch) && ch.length === 12 && ch.every(Number.isFinite);
  }
  function normalScore(ch) {
    const a = ch.slice(8).sort((x, y) => x - y);
    return Math.max(0, (a[1] + a[2]) / 2);
  }
  function normalLevel(ch, profile) {
    if (!validSurfaceChannels(ch)) return 0;
    const p = profile.normal;
    return Math.max(0, Math.min(1, (normalScore(ch) - p.threshold) / p.span));
  }
  function shearLevel(ch, profile, active = false) {
    if (!validSurfaceChannels(ch) || !profile.shear.enabled) return 0;
    const s = profile.shear;
    const avg = ch.slice(0, 8).reduce((a, b) => a + b, 0) / 8;
    const n = normalScore(ch);
    const score = ch.slice(0, 8).reduce((sum, value, i) =>
      sum + s.weights[i] * (value - avg - s.pressLeak[i] * n), 0);
    const threshold = s.threshold * (active ? 0.7 : 1);
    return Math.sign(score) * Math.max(0,
      Math.min(1, (Math.abs(score) - threshold) / s.span));
  }
  ```
- [ ] **Step 4: Extend only the grid's geometry/animation.** In `point(i,j)`, retain the current central Gaussian indentation but add a bounded x translation proportional to signed `shearLevel` and a small linear-in-`u` y tilt; ensure the outer vertices stay within canvas margins at `-1` and `+1`. Animate normal and shear with the existing short interpolation; `clear()` resets both target/current pairs; reduced motion calls `finish()` for both. Use the same Canvas colors and current trends untouched.

  The point transformation should be exactly this bounded addition to the existing return expressions (the original `bump` and colors remain):

  ```javascript
  const shift = surface.shearLevel;
  return [w * (0.5 + (u - v) * 0.23 + shift * 0.02),
          h * (0.34 + (u + v) * 0.105 + bump * surface.level * 0.17
               + u * shift * 0.018), bump];
  ```
- [ ] **Step 5: Wire profile and quality gate.** Fetch `/shear_profile.json` once on startup with `cache:"no-store"`; validate version, array lengths, finite coefficients, positive spans/thresholds, and `enabled`; on failure use a local disabled profile and expose clear status copy. Pass profile to `surfaceView.set(data.channels, profile)` only when `data.status==="live"`, frame increased, and `invalid_recent===0 && saturated_recent===0`; otherwise clear the surface. Change only the surface caption/ARIA to “正压／剪切响应示意（相对响应，非标定力值）” and indicate “剪切方向未验证” when disabled.
- [ ] **Step 6: Verify green and visual regressions.** Run `D:\conda\python.exe -m unittest discover -s tests -v`; expected: all tests PASS. Run Playwright at 1440×900 and 390×844, reduced-motion and ordinary motion. Compare empty/press/right/left/combined screenshots, verify grid never clips, and verify all trends/bars/channel cards retain their prior counts and data. No backend/firmware edits.

### Task 4: Current-assembly live verification and handoff

**Files:** Modify `PROJECT_LOG.md`; save screenshots/videos and raw state snapshots under `calibration/` or `.superpowers/sdd/` without overwriting earlier evidence.

**Interfaces:** Accept only the profile from Task 2 and the UI from Task 3; no retuning from observed demo behavior.

- [ ] **Step 1: Before live use, inspect the generated profile/report.** Check `version=1`, `shear.enabled=true`, both physical labels, every named train/holdout file, and the frozen gate values. If false, demonstrate center indentation only and explain the measured failure; do not synthesize or manually flip a direction.
- [ ] **Step 2: Verify on hardware one action at a time.** Confirm empty and tare → center press → release → physical right push → release → physical left push → release. Take one raw-count snapshot and a screenshot/video for each pose; confirm opposite displayed displacement matches the operator's declared right/left and returns flat. If the assembly, orientation, power/tuning, or tare reference changed since capture, re-run the two-round gate first.
- [ ] **Step 3: Record the outcome.** Add a dated top entry to `PROJECT_LOG.md` with profile/report paths, train/holdout counts, each gate percentage, actual browser test result, live visual result, and any limitations. Explicitly distinguish “synthetic UI passed” from “real shear direction passed.” Stop if either real direction is wrong or noisy; disable shear in the profile and leave press-only mode.

## Plan review

- Spec coverage: data provenance and held-out gate (Tasks 1–2), press/shear rendering and reset/reduced motion (Task 3), existing dashboard regression and live evidence (Tasks 3–4).
- No step alters serial protocol, firmware, API, force matrix, weight calibration, or the stopped third repeatability round.
- The implementation must keep `shear.enabled=false` until real current-assembly evidence exists. A synthetic test passing is not permission to claim hardware direction works.
