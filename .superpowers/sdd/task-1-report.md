# Task 1 report — independently rendered grid surface

Status: DONE

## Implemented

- Replaced only the left-panel orb children with `#surface-canvas` and the explicit “响应形变示意” / “非实际力值” caption.
- Loaded `/surface.js` before `/app.js`.
- Replaced the old orb-specific CSS declarations with the Canvas sizing and label override; left chart, channel, and responsive rules intact.
- Added `surfaceLevel(channels)` using median absolute counts across 12 finite channels, clamped linearly from 100 to 700 counts, plus `createSurface(canvas)` with a fixed-center 18×18 grid, smooth animation, reduced-motion handling, clear, and resize.
- Removed only the two obsolete `#sensor-orb` style assignments in `paintBars` to keep the intermediate dashboard functional.

## Red and green evidence

- Red: `D:\conda\python.exe -m unittest tests.test_demo_ui.DashboardWarningTests.test_surface_uses_robust_counts_and_is_labeled_illustration -v` exited 1: `AssertionError: 0 != 1` for absent `#surface-canvas`.
- Green: same command exited 0, `Ran 1 test ... OK`.
- Full suite after the `app.js` cleanup: `D:\conda\python.exe -m unittest discover -s tests -v` exited 0, `Ran 18 tests ... OK`.
- Browser visual check: invoked `createSurface(document.getElementById("surface-canvas"))` on the page at 1440×900. The Canvas bitmap was 360×392 px. The flat grid, semantic label, and activity readout were visible in `.superpowers/sdd/task-1-flat-grid.png`.

## Files

- `demo_web/surface.js` — new renderer.
- `demo_web/index.html` — left-panel markup and script order.
- `demo_web/style.css` — orb-specific CSS replacement.
- `demo_web/app.js` — exactly two obsolete orb style writes removed.
- `tests/test_demo_ui.py` — new browser test.
- `.superpowers/sdd/task-1-flat-grid.png` — visual-check evidence.

## Self-review and concerns

- The new surface reads only channel counts. Its center is fixed; the label and accessibility text say this is an illustration and do not claim localization or calibrated force.
- Existing charts, display sensitivity, activity index, G1–G6, and all raw channel cards remained covered by the passing suite.
- The Canvas is intentionally not connected to live `/api/state` data in Task 1. Task 2 owns that wiring and disconnect behavior.
- No known blockers or outstanding test failures.

## Review follow-up: clipped grid corners

The original x projection factor `.34` painted into both outer Canvas columns. I added a browser regression that creates the flat surface and checks those columns have zero nontransparent pixels. I changed only that factor to `.23`; the refreshed `.superpowers/sdd/task-1-flat-grid.png` visibly shows all four grid corners inside the Canvas. The existing scale test now also covers all-negative and mixed-sign channel arrays, both yielding 0.5 from median absolute counts.

Red command: `D:\conda\python.exe -m unittest tests.test_demo_ui.DashboardWarningTests.test_flat_surface_grid_does_not_touch_canvas_edges -v` (exit 1)

```text
test_flat_surface_grid_does_not_touch_canvas_edges (tests.test_demo_ui.DashboardWarningTests.test_flat_surface_grid_does_not_touch_canvas_edges) ... 127.0.0.1 - - [24/Sep/2026 20:57:43] "GET / HTTP/1.1" 200 -
127.0.0.1 - - [24/Sep/2026 20:57:43] "GET /style.css HTTP/1.1" 200 -
127.0.0.1 - - [24/Sep/2026 20:57:43] "GET /surface.js HTTP/1.1" 200 -
127.0.0.1 - - [24/Sep/2026 20:57:43] "GET /app.js HTTP/1.1" 200 -
FAIL

======================================================================
FAIL: test_flat_surface_grid_does_not_touch_canvas_edges (tests.test_demo_ui.DashboardWarningTests.test_flat_surface_grid_does_not_touch_canvas_edges)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "D:\semg.claude\coinft\tests\test_demo_ui.py", line 69, in test_flat_surface_grid_does_not_touch_canvas_edges
    self.assertEqual(edge_ink, [0, 0])
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^
AssertionError: Lists differ: [46, 46] != [0, 0]

First differing element 0:
46
0

- [46, 46]
+ [0, 0]

----------------------------------------------------------------------
Ran 1 test in 1.040s

FAILED (failures=1)
```

Green command: `D:\conda\python.exe -m unittest tests.test_demo_ui.DashboardWarningTests.test_flat_surface_grid_does_not_touch_canvas_edges tests.test_demo_ui.DashboardWarningTests.test_surface_uses_robust_counts_and_is_labeled_illustration -v` (exit 0)

```text
test_flat_surface_grid_does_not_touch_canvas_edges (tests.test_demo_ui.DashboardWarningTests.test_flat_surface_grid_does_not_touch_canvas_edges) ... 127.0.0.1 - - [24/Sep/2026 20:57:57] "GET / HTTP/1.1" 200 -
127.0.0.1 - - [24/Sep/2026 20:57:57] "GET /style.css HTTP/1.1" 200 -
127.0.0.1 - - [24/Sep/2026 20:57:57] "GET /surface.js HTTP/1.1" 200 -
127.0.0.1 - - [24/Sep/2026 20:57:57] "GET /app.js HTTP/1.1" 200 -
ok
test_surface_uses_robust_counts_and_is_labeled_illustration (tests.test_demo_ui.DashboardWarningTests.test_surface_uses_robust_counts_and_is_labeled_illustration) ... 127.0.0.1 - - [24/Sep/2026 20:57:58] "GET / HTTP/1.1" 200 -
127.0.0.1 - - [24/Sep/2026 20:57:58] "GET /style.css HTTP/1.1" 200 -
127.0.0.1 - - [24/Sep/2026 20:57:58] "GET /surface.js HTTP/1.1" 200 -
127.0.0.1 - - [24/Sep/2026 20:57:58] "GET /app.js HTTP/1.1" 200 -
ok

----------------------------------------------------------------------
Ran 2 tests in 2.009s

OK
```

Full-suite command: `D:\conda\python.exe -m unittest discover -s tests -v` (exit 0)

```text
test_out_of_range_frame_does_not_contaminate_tare (test_demo_core.DemoSourceDisplayTests.test_out_of_range_frame_does_not_contaminate_tare) ... ok
test_out_of_range_frame_is_reported_without_changing_display (test_demo_core.DemoSourceDisplayTests.test_out_of_range_frame_is_reported_without_changing_display) ... ok
test_quiet_axis_display_is_smoothed_but_raw_channels_remain_unfiltered (test_demo_core.DemoSourceDisplayTests.test_quiet_axis_display_is_smoothed_but_raw_channels_remain_unfiltered) ... ok
test_single_plausible_range_corrupt_frame_does_not_spike_axis (test_demo_core.DemoSourceDisplayTests.test_single_plausible_range_corrupt_frame_does_not_spike_axis) ... ok
test_sustained_force_reaches_display_within_quarter_second (test_demo_core.DemoSourceDisplayTests.test_sustained_force_reaches_display_within_quarter_second) ... ok
test_tare_is_robust_to_a_plausible_range_corrupt_frame (test_demo_core.DemoSourceDisplayTests.test_tare_is_robust_to_a_plausible_range_corrupt_frame) ... ok
test_valid_frame_restores_live_status_after_waiting (test_demo_core.DemoSourceDisplayTests.test_valid_frame_restores_live_status_after_waiting) ... ok
test_rate_is_not_biased_by_usb_batch_boundaries (test_demo_core.DemoSourceRateTests.test_rate_is_not_biased_by_usb_batch_boundaries) ... ok
test_accepts_split_frames_and_skips_misaligned_bytes (test_demo_core.FrameParserTests.test_accepts_split_frames_and_skips_misaligned_bytes) ... ok
test_rejects_frame_without_following_header (test_demo_core.FrameParserTests.test_rejects_frame_without_following_header) ... ok
test_tare_produces_six_zeros_and_channel_deltas (test_demo_core.RelativeProjectorTests.test_tare_produces_six_zeros_and_channel_deltas) ... ok
test_channel_bars_are_linear_and_show_overflow (test_demo_ui.DashboardWarningTests.test_channel_bars_are_linear_and_show_overflow) ... 127.0.0.1 - - [24/Sep/2026 20:58:06] "GET / HTTP/1.1" 200 -
127.0.0.1 - - [24/Sep/2026 20:58:06] "GET /surface.js HTTP/1.1" 200 -
127.0.0.1 - - [24/Sep/2026 20:58:06] "GET /style.css HTTP/1.1" 200 -
127.0.0.1 - - [24/Sep/2026 20:58:06] "GET /app.js HTTP/1.1" 200 -
ok
test_disconnected_service_clears_stale_readings (test_demo_ui.DashboardWarningTests.test_disconnected_service_clears_stale_readings) ... 127.0.0.1 - - [24/Sep/2026 20:58:07] "GET / HTTP/1.1" 200 -
127.0.0.1 - - [24/Sep/2026 20:58:07] "GET /style.css HTTP/1.1" 200 -
127.0.0.1 - - [24/Sep/2026 20:58:07] "GET /surface.js HTTP/1.1" 200 -
127.0.0.1 - - [24/Sep/2026 20:58:07] "GET /app.js HTTP/1.1" 200 -
ok
test_flat_surface_grid_does_not_touch_canvas_edges (test_demo_ui.DashboardWarningTests.test_flat_surface_grid_does_not_touch_canvas_edges) ... 127.0.0.1 - - [24/Sep/2026 20:58:08] "GET / HTTP/1.1" 200 -
127.0.0.1 - - [24/Sep/2026 20:58:08] "GET /style.css HTTP/1.1" 200 -
127.0.0.1 - - [24/Sep/2026 20:58:08] "GET /surface.js HTTP/1.1" 200 -
127.0.0.1 - - [24/Sep/2026 20:58:08] "GET /app.js HTTP/1.1" 200 -
ok
test_force_chart_uses_three_times_wider_display_scale_only (test_demo_ui.DashboardWarningTests.test_force_chart_uses_three_times_wider_display_scale_only) ... 127.0.0.1 - - [24/Sep/2026 20:58:09] "GET / HTTP/1.1" 200 -
127.0.0.1 - - [24/Sep/2026 20:58:09] "GET /style.css HTTP/1.1" 200 -
127.0.0.1 - - [24/Sep/2026 20:58:09] "GET /surface.js HTTP/1.1" 200 -
127.0.0.1 - - [24/Sep/2026 20:58:09] "GET /app.js HTTP/1.1" 200 -
ok
test_invalid_frames_are_visible_as_an_error (test_demo_ui.DashboardWarningTests.test_invalid_frames_are_visible_as_an_error) ... 127.0.0.1 - - [24/Sep/2026 20:58:10] "GET / HTTP/1.1" 200 -
127.0.0.1 - - [24/Sep/2026 20:58:10] "GET /style.css HTTP/1.1" 200 -
127.0.0.1 - - [24/Sep/2026 20:58:10] "GET /surface.js HTTP/1.1" 200 -
127.0.0.1 - - [24/Sep/2026 20:58:10] "GET /app.js HTTP/1.1" 200 -
ok
test_one_group_spike_does_not_change_five_poll_median (test_demo_ui.DashboardWarningTests.test_one_group_spike_does_not_change_five_poll_median) ... 127.0.0.1 - - [24/Sep/2026 20:58:12] "GET / HTTP/1.1" 200 -
127.0.0.1 - - [24/Sep/2026 20:58:12] "GET /style.css HTTP/1.1" 200 -
127.0.0.1 - - [24/Sep/2026 20:58:12] "GET /surface.js HTTP/1.1" 200 -
127.0.0.1 - - [24/Sep/2026 20:58:12] "GET /app.js HTTP/1.1" 200 -
ok
test_response_groups_do_not_replace_historical_trends (test_demo_ui.DashboardWarningTests.test_response_groups_do_not_replace_historical_trends) ... 127.0.0.1 - - [24/Sep/2026 20:58:13] "GET / HTTP/1.1" 200 -
127.0.0.1 - - [24/Sep/2026 20:58:13] "GET /style.css HTTP/1.1" 200 -
127.0.0.1 - - [24/Sep/2026 20:58:13] "GET /surface.js HTTP/1.1" 200 -
127.0.0.1 - - [24/Sep/2026 20:58:13] "GET /app.js HTTP/1.1" 200 -
ok
test_surface_uses_robust_counts_and_is_labeled_illustration (test_demo_ui.DashboardWarningTests.test_surface_uses_robust_counts_and_is_labeled_illustration) ... 127.0.0.1 - - [24/Sep/2026 20:58:14] "GET / HTTP/1.1" 200 -
127.0.0.1 - - [24/Sep/2026 20:58:14] "GET /style.css HTTP/1.1" 200 -
127.0.0.1 - - [24/Sep/2026 20:58:14] "GET /surface.js HTTP/1.1" 200 -
127.0.0.1 - - [24/Sep/2026 20:58:14] "GET /app.js HTTP/1.1" 200 -
ok

----------------------------------------------------------------------
Ran 19 tests in 8.658s

OK
```
