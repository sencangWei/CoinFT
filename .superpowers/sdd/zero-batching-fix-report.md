# Zero batching fix — 2026-09-26

Status: DONE. Changed only `demo_web/app.js` and `tests/test_demo_ui.py`, plus this requested report. No hardware, backend, firmware, profile, HTML/CSS, or Git operations.

## RED evidence

Before implementation:

`D:\conda\python.exe -m unittest tests.test_demo_ui.DashboardWarningTests.test_qualitative_zero_survives_100ms_batches_and_50ms_duplicate_polls -v`

```text
AssertionError: Lists differ: [None, 0, -1] != [None, 1, 202]
Ran 1 test in 1.953s
FAILED (failures=1)
```

This reproduced pending collection being erased by the duplicate poll 50 ms after a fresh backend batch.

`D:\conda\python.exe -m unittest tests.test_demo_ui.DashboardWarningTests.test_qualitative_ready_duplicate_and_stalled_request_watchdog -v`

```text
AssertionError: None != [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]
Ran 1 test in 1.143s
FAILED (failures=1)
```

This reproduced a ready baseline being erased by one healthy duplicate.

## Change and coverage

Removed the unconditional qualitative-mode condition from the unchanged-frame invalidation branch. Healthy duplicates now skip the accepted-frame branch and leave pending samples, first-sample time, ready baseline, grid targets, and last-fresh-frame time unchanged. Strict behavior is unchanged. The existing 500 ms watchdog remains active independently of HTTP completion.

The updated batching test sends fresh frames about every 100 ms with duplicate polls after 50 ms; it checks no duplicate sample count, no first-sample timestamp reset, no freshness timestamp refresh, successful zeroing, and ready deformation preservation. It also checks ready and pending watchdog clearing, malformed collection interruption, flat recovery before re-click, and successful re-click. The separate hung-request test confirms the grid and baseline clear while `fetching` is still true, before the 1500 ms HTTP timeout. The malformed-ready test now sends malformed channels with the same frame number, exercising validation before duplicate skipping.

All existing threshold/sample-span, bad status/degraded, regression, HTTP failure, tare, raw/group/trend, strict-profile, animation, and layout checks remain in the suite.

## GREEN evidence

Focused new tests:

```text
Ran 2 tests in 7.903s
OK
```

Final focused UI command: `D:\conda\python.exe -m unittest tests.test_demo_ui -v`

```text
Ran 29 tests in 52.882s
OK
```

Final repository command: `D:\conda\python.exe -m unittest discover -s tests -q`

```text
Ran 65 tests in 53.482s
OK
```

Both final commands exited 0. No remaining code/test concern. Live re-zero is left to the root agent after review, as requested.
