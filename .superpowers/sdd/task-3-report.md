# Task 3 browser acceptance — 2026-09-24

## Result

PASS for local Chromium simulation. No production files changed. Added three browser tests in `tests/test_demo_ui.py`.

## Checks and outcomes

- `D:\conda\python.exe -m unittest tests.test_demo_ui.DashboardWarningTests.test_surface_fits_mobile_and_reduced_motion -v` — PASS. At 390×844 with reduced motion, setting twelve channels to 700 made `surfaceView.level` equal 1 immediately; no page error or horizontal overflow.
- `D:\conda\python.exe -m unittest tests.test_demo_ui.DashboardWarningTests.test_surface_visual_states_at_desktop_and_mobile_sizes -v` — PASS. At 1440×900 and 390×844, checked unloaded (0 counts), loaded (700 counts), and cleared (tare/taring) states. Confirmed 2 trend canvases, 6 response rows, and 12 channel cards; loaded channel text was `+700`; tare cleared the surface and readings. Resizing each viewport 20 px narrower and back resized the Canvas while retaining level 1. No page errors or horizontal overflow in the tested states.
- `D:\conda\python.exe -m unittest tests.test_demo_ui.DashboardWarningTests.test_surface_animates_on_live_press_and_release -v` — PASS. With normal motion enabled, live frames transitioned 0→700→0 counts. `surfaceView.level` passed through an intermediate value while rising, reached above 0.99, passed through an intermediate value while falling, then reached exactly 0. Status remained `数据正常`, the released raw channel read `+0`, and Chromium emitted no page errors.
- `D:\conda\python.exe -m unittest discover -s tests -v` — PASS, 23 tests, 0 failures/errors (rerun after adding normal-motion coverage).
- Visually inspected desktop and mobile screenshots. The unloaded grid is planar, the loaded grid has a centered cyan-green indentation, and the cleared grid is planar again. Caption, charts, group panel, and channel cards remain visible without observed clipping or overlap. The caption labels the surface as an illustration and the activity index as a non-force value.

## Screenshots

All paths are under `D:\semg.claude\coinft\.superpowers\sdd\`:

| Viewport | Unloaded | Loaded | Cleared |
|---|---|---|---|
| Desktop 1440×900, full page | `task-3-desktop-unloaded.png` | `task-3-desktop-loaded.png` | `task-3-desktop-cleared.png` |
| Desktop, surface Canvas | `task-3-desktop-grid-unloaded.png` | `task-3-desktop-grid-loaded.png` | `task-3-desktop-grid-cleared.png` |
| Mobile 390×844, full page | `task-3-mobile-unloaded.png` | `task-3-mobile-loaded.png` | `task-3-mobile-cleared.png` |
| Mobile, surface Canvas | `task-3-mobile-grid-unloaded.png` | `task-3-mobile-grid-loaded.png` | `task-3-mobile-grid-cleared.png` |

Normal-motion desktop evidence: `task-3-normal-motion-grid-loaded.png`, `task-3-normal-motion-grid-released.png`, and full-page `task-3-normal-motion-released.png`. Visual inspection confirms the live release returns the indented grid to a planar grid while the dashboard stays live.

## Limitations and self-review

- The server used a mutable `FakeSource`; no live serial, COM device, physical sensor, or calibrated force/torque was exercised.
- The tests cover reduced-motion immediate rendering, normal-motion rise and decay on live frames, resize handling, tare clearing, and the existing disconnect test. No frame-rate or hardware-latency claim is made.
- Changes are confined to Task 3 tests and evidence. Existing charts, groups, controls, and channel readouts were retained. No backend, firmware, calibration, plan, or project log file was edited.
