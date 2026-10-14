# Task 2 report — live surface lifecycle

## Result

- Added `surfaceView` in `demo_web/app.js` and connected fresh live frames to `surfaceView.set(data.channels)`.
- Clear the surface when the display clears for nonlive status or a failed poll, and immediately on tare. Resize it with the existing chart canvases.
- Added `test_surface_follows_new_frame_and_clears_on_disconnect` to `tests/test_demo_ui.py`. It checks levels for 0, 400, and 700 counts, the unchanged raw channel reading, and reset after a 503 response.

## TDD evidence

Red command:

```text
D:\conda\python.exe -m unittest tests.test_demo_ui.DashboardWarningTests.test_surface_follows_new_frame_and_clears_on_disconnect -v
ERROR: test_surface_follows_new_frame_and_clears_on_disconnect (tests.test_demo_ui.DashboardWarningTests.test_surface_follows_new_frame_and_clears_on_disconnect)
playwright._impl._errors.Error: Page.wait_for_function: ReferenceError: surfaceView is not defined
Ran 1 test in 1.054s
FAILED (errors=1)
```

Green command, after the `app.js` changes:

```text
D:\conda\python.exe -m unittest tests.test_demo_ui.DashboardWarningTests.test_surface_follows_new_frame_and_clears_on_disconnect -v
test_surface_follows_new_frame_and_clears_on_disconnect (tests.test_demo_ui.DashboardWarningTests.test_surface_follows_new_frame_and_clears_on_disconnect) ... ok
Ran 1 test in 1.201s
OK
```

Full regression command:

```text
D:\conda\python.exe -m unittest discover -s tests -v
Ran 20 tests in 9.844s
OK
```

## Self-review

- The new surface uses only `data.channels` on the existing fresh-live-frame branch. It does not alter force or torque axes, histories, group windows, gain, activity, or raw channel formatting.
- The existing `clearDisplay()` paths cover nonlive status and failed polling; `surfaceView.clear()` synchronously resets both `target` and `level` to zero. The tare handler clears before its POST. The resize listener still redraws both charts.
- Existing browser regressions for chart scale, G1–G6, channel scales/readings, warning and disconnect behavior pass in the full suite. No backend, firmware, calibration, project log, or plan files were modified. No Git operations were run.
- Concern: the added test directly covers disconnect reset; tare, nonlive reset, and resize are covered by code review but have no new dedicated browser assertion in this task.
