# Task 3 UI handoff — 2026-09-25

## Result

Implemented the approved normal and signed single-axis shear grid in the browser. The dashboard reads `/shear_profile.json` once with `cache: "no-store"`; an absent or invalid profile uses CH9–CH12 press-only fallback and visibly states `剪切方向未验证`. The browser does not infer a physical direction or create calibration data.

## Changed files

- `demo_web/surface.js`: kept legacy `surfaceLevel`; added finite-input guarded normal and signed shear helpers, independent targets/current levels, release hysteresis, bounded x shift and y tilt, immediate reset and reduced-motion handling.
- `demo_web/app.js`: added one-time profile schema validation, disabled fallback, fresh-frame quality gate, 500 ms no-new-frame clearing, and profile-fed surface updates. Trends, bars, and channel display code were not changed.
- `demo_web/index.html`: changed only grid caption/ARIA to `正压／剪切响应示意（相对响应，非标定力值）` and added the disabled-direction caption state.
- `tests/test_demo_ui.py`: added synthetic-profile browser tests for press leakage, opposite signed shear and measured canvas x centroid movement, combined input, invalid/saturated/stale/tare/503 clearing, invalid/missing profile fallback, and invalid version rejection. Updated the old caption assertion and isolated its direct animation test from the new live stale-frame gate.

## RED/GREEN evidence

1. RED: `D:\conda\python.exe -m unittest tests.test_demo_ui.DashboardWarningTests.test_signed_surface_profile_and_safe_states tests.test_demo_ui.DashboardWarningTests.test_missing_profile_disables_shear_and_labels_it -v` → 2 tests, exit 1. Signed helper timed out because `shearLevel` was absent; missing-profile test found `shearTarget` undefined (`None != 0`).
2. GREEN after implementation: same command → 2 tests, `OK`.
3. Additional RED: `D:\conda\python.exe -m unittest tests.test_demo_ui.DashboardWarningTests.test_score_helpers_reject_wrong_profile_version -v` → exit 1, actual `[1, 1]` versus expected `[0, 0]`.
4. GREEN after version guard: focused version, signed-state, and reduced-motion tests → 3 tests, `OK`.
5. First full UI run: 16 tests, one failure in the old direct animation test because the app's frozen fake stream correctly triggered the new stale-frame reset. The test now uses an independent `createSurface` instance for its media-setting behavior.
6. After adding invalid-profile and signed-503 assertions, focused run → 2 tests, `OK`.
7. Final full verification: `D:\conda\python.exe -m unittest discover -s tests -v` → **46 tests, `OK`, exit 0** (26.012 s). This includes prior core/fitter tests and browser checks at 1440×900 and 390×844.

## Self-review and limits

- No firmware, backend, fitter, calibration JSON, trend formula/chart data, G1–G6 bars, 12-channel formatting, stylesheet, or project log edits were made. No COM10 access or Git operation occurred.
- Positive shear follows the profile's operator-labeled screen-right training sign. The browser checks only schema integrity and the fitted `enabled` flag; acceptance of real direction still depends on independent capture/gate and later hardware verification.
- Profile coefficients are cached until page reload. The 500 ms stale-frame threshold clears only the grid; the existing dashboard data path is unchanged.
- The missing-profile 404 in test logs is expected and exercises the safe fallback. No real `demo_web/shear_profile.json` was created for this task.

## Review follow-up: stale request and tare race

Two review findings were reproduced with browser tests before the fix:

- `D:\conda\python.exe -m unittest tests.test_demo_ui.DashboardWarningTests.test_stalled_state_request_clears_surface_and_recovers tests.test_demo_ui.DashboardWarningTests.test_tare_discards_inflight_live_response_until_taring_cycle -v` → exit 1. A hung state request left the grid deformed past the 700 ms test limit; a held pre-tare live reply restored `[target, level]` to `[1, 1]` after the tare click.
- Root cause: stale clearing only ran inside `poll()` after its 1500 ms request settled, and the tare click cleared the grid without invalidating an already started poll.

`demo_web/app.js` now checks the last fresh surface frame on an independent 50 ms timer and flattens at 500 ms even while fetching. Tare increments a request generation; old responses are discarded. New live replies remain suppressed until the page observes `taring` and receives a frame newer than the one at the click. The surface resets immediately at the click. Trend and bar calculations were not edited.

The focused regression command above then passed (2 tests, exit 0). A further focused run covering both regressions and the synthetic signed-surface test passed (3 tests, exit 0). Final `D:\conda\python.exe -m unittest discover -s tests -v` passed **47 tests, 0 failures, exit 0** (29.477 s). The new tare test also verifies that a same-frame live reply after taring stays flat and a newer frame restores the grid.

## Final review follow-up: frame high-water and tare recovery

Added three browser regressions first, then observed RED with `D:\conda\python.exe -m unittest tests.test_demo_ui.DashboardWarningTests.test_older_frame_cannot_lower_surface_high_water tests.test_demo_ui.DashboardWarningTests.test_failed_tare_post_releases_gate_and_button tests.test_demo_ui.DashboardWarningTests.test_fast_taring_cycle_hidden_by_poll_recovers_after_ack -v`: exit 1. Frame 199 lowered `latestFrame` from 200; a 503 tare POST left `tarePending` and the button disabled; an unobserved fast taring cycle left the surface flat indefinitely.

In `demo_web/app.js`, `latestFrame` now advances only on a greater integer frame. A failed tare POST releases the pending gate and re-enables the button while leaving the grid flat until a newer frame. A successful POST records acknowledgement; if polling missed the whole taring cycle, only a request started after that acknowledgement with a frame newer than the tare-click frame can restore the surface. A request started before the click is still rejected by its generation. The fast-cycle test now holds a pre-tare state request through the POST acknowledgement to exercise that race.

Focused GREEN: the three review regressions passed (exit 0); the held-fetch fast-cycle case also passed alone (exit 0). Final full verification: `D:\conda\python.exe -m unittest discover -s tests -v` → **52 tests, 0 failures, exit 0** (32.858 s). No changes to trends, bars, fallback profile, calibration data, backend, or hardware access.
