# Final-review fix report — 2026-09-24

## Result

The dashboard now clears a stale surface and readings when `/api/state` or its JSON body stalls for 1.5 seconds. Polling resumes after the service responds again. Switching to reduced motion during an animation now cancels its RAF and draws the current target immediately.

## Files changed

- `demo_web/app.js`: one 1.5-second timeout covers fetch and `response.json()` through a shared `Promise.race`; the timeout aborts the request, enters the existing disconnect/clear path, and `finally` clears the timer and in-flight guard.
- `demo_web/surface.js`: the media-query `change` event uses the same immediate finish behavior as `set()` under reduced motion.
- `tests/test_demo_ui.py`: browser tests for a stalled state request, clearing and recovery, and for changing reduced-motion preference during interpolation.

No backend, firmware, API, hardware, chart, or tuning files were edited. No Git commit was created; this directory is not a Git repository.

## Verification

Focused test commands used `D:\conda\python.exe -m unittest tests.test_demo_ui.DashboardWarningTests.<test_name> -v`.

| Test | Red before fix | Green after fix |
| --- | --- | --- |
| `test_stalled_state_request_clears_surface_and_recovers` | Exit 1: disconnect label absent after 3000 ms while fetch remained pending | Exit 0: 1 test, OK; stale surface and readings cleared, then live frame restored |
| `test_switching_to_reduced_motion_finishes_current_animation` | Exit 1: level was `0.2`, expected `1` | Exit 0: 1 test, OK; level became target after media-query change |

After the first stalled-request green run, the browser fixture was adjusted to intercept `fetch` in-page instead of leaving a Playwright route unresolved. This removed route-cancellation exceptions; the final focused run remained green.

Full suite: `D:\conda\python.exe -m unittest discover -s tests -v` exited 0: **25 tests, OK**, in 21.264 seconds.

## Self-review and remaining limits

- The timeout is a wall-clock bound across both request and JSON reading. A late completion cannot update the UI because the race result has already rejected. `AbortController` stops a real in-flight network request where supported.
- The browser test directly exercises a hung fetch and recovery. A separately hung `response.json()` is not simulated, though it uses the same bounded race. Browser-only behavior was checked in Chromium; other engines were not run.
- The full-suite log included a `GET /null` 404 during the synthetic hang test and a local `ConnectionAbortedError` in an existing animation test when the browser closed during polling. Both are local test-server request logs; the suite had no test failures or browser JS-error assertions. Test server and browser contexts were closed.

## Final test-fixture follow-up

The fetch restore in `tests/test_demo_ui.py` now passes an arrow function to `page.evaluate`, so Playwright executes the assignment without treating the returned native `fetch` function as another evaluation target. No production code changed in this follow-up.

- `D:\conda\python.exe -m unittest tests.test_demo_ui.DashboardWarningTests.test_stalled_state_request_clears_surface_and_recovers -v`: exit 0, 1 test OK, 4.199 seconds. No `GET /null` appeared.
- `D:\conda\python.exe -m unittest discover -s tests -v`: exit 0, 25 tests OK, 21.089 seconds. No `GET /null` appeared. One `ConnectionAbortedError` appeared while the browser closed during the existing `test_one_group_spike_does_not_change_five_poll_median`; the test passed, so this remains local test-server shutdown noise.
