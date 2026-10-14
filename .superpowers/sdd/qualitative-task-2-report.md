# Task 2 — qualitative grid baseline

Status: implemented within `demo_web/app.js`, `demo_web/surface.js`, `demo_web/index.html`, `demo_web/style.css`, and `tests/test_demo_ui.py`. No backend, firmware, profile, or hardware changes. No real `/api/tare` call was made; tare browser tests used the local fake server or intercepted the POST.

## Red / green evidence

- Red command: `D:\conda\python.exe -m unittest tests.test_demo_ui.DashboardWarningTests.test_qualitative_grid_requires_visual_zero_and_preserves_raw_readouts tests.test_demo_ui.DashboardWarningTests.test_strict_disabled_profile_prevents_qualitative_fallback -v`. Result: `Ran 2 tests in 62.041s`, `FAILED (errors=2)`. The first timed out waiting for `shearProfile.mode === 'qualitative'`; the second timed out finding `#demo-zero`.
- After the final caption adjustment, focused command: `D:\conda\python.exe -m unittest tests.test_demo_ui -v`. Result: `Ran 25 tests in 40.274s`, `OK`, exit 0.
- After the final caption adjustment, repository command: `D:\conda\python.exe -m unittest discover -s tests -q`. Result: `Ran 61 tests in 40.749s`, `OK`, exit 0.

## Behavior and self-review

- The strict profile is authoritative when present, including when its shear flag is disabled. The qualitative profile is fetched only on a strict 404 and must pass validation with `mode: "qualitative"`.
- Qualitative grid starts flat and requires an explicit visual zero. It takes channel medians from at least 10 fresh increasing good live frames spanning at least one second, measured from the first accepted sample to the last. Only the grid receives baseline-subtracted channels. Raw card values, G1–G6 group medians, and force/torque trend histories continue using the original channels.
- Waiting, degraded frames, repeated or regressed frames, malformed channels, HTTP failure, 500 ms stall, and device tare clear the baseline and grid; a new click is required. The demo button never posts to `/api/tare`. Qualitative shear uses one activation/release threshold; strict hysteresis and grid geometry remain unchanged.
- Existing browser tests that exercise the historical press-only fallback now explicitly route both profile files to 404. New tests cover the qualitative path, both shear signs, reduced motion, narrow layout, strict-profile precedence, and fault invalidation.
- The first repository-wide run had one transient browser wait timeout; a subsequent run passed all 61 tests. No remaining reproducible test failure is known.

## Visual evidence

Playwright screenshots under this directory: `task-2-mobile-{empty,press,right,left}.png` at 390×844 and `task-2-desktop-{empty,press,right,left}.png` at 1440×900. Inspected mobile left and desktop press: controls and captions remain visible, no horizontal clipping, and the raw cards/trend panels remain in place. Browser assertions also checked targets for all four states and scroll width at both viewport sizes. These are synthetic signals; live hardware direction smoke testing remains outside Task 2.

No remaining Task 2 work is pending.

## Reviewer follow-up: freshness and sample span

- New RED test `test_qualitative_repeated_good_frame_cancels_zero_and_requires_new_click`: combined run with the initial malformed test reported `Ran 2 tests in 3.584s`, `FAILED (failures=1)`; pending collection incorrectly stayed `[None, 1, 202]` instead of `[None, 0, -1]` after a repeated frame.
- The malformed test initially waited long enough for the old 500 ms stale timer to hide the bug. Tightened it to inspect the immediate poll. RED command `D:\conda\python.exe -m unittest tests.test_demo_ui.DashboardWarningTests.test_qualitative_malformed_channels_cancel_ready_baseline -v`: `Ran 1 test in 1.146s`, `FAILED (failures=1)` because `demoBaseline` retained twelve zeros after a short channel array. It now also exercises a null channel value and a null array.
- New RED test `test_qualitative_zero_needs_ten_frames_spanning_one_second`: `Ran 1 test in 2.332s`, `FAILED (failures=1)` because ten fast samples were accepted using the click timestamp (`demoZeroSamples.length` was 0 instead of at least 10 at the boundary). It also checks that fewer than ten snapshots remain insufficient after one second.
- The repeated-frame test now covers collection interrupted by a malformed channel value: pending samples clear, many later valid frames keep the grid flat without a click, and another click permits a complete baseline.
- Final GREEN command `D:\conda\python.exe -m unittest tests.test_demo_ui -v`: `Ran 28 tests in 48.892s`, `OK`, exit 0. Final repository command `D:\conda\python.exe -m unittest discover -s tests -q`: `Ran 64 tests in 49.921s`, `OK`, exit 0.
- Code change is confined to qualitative mode's baseline input gate and collection timing. Strict profile behavior and raw/group/trend paths remain unchanged. Synthetic Playwright tests used the local fake server; no hardware was operated.
