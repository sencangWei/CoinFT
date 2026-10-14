# Task 1 capture utility report

Status: DONE_WITH_CONCERNS. The software capture utility is implemented and verified with simulated HTTP states. No physical capture was attempted; the root agent owns operator confirmation and later evidence collection.

## Changed files

- `calibration/capture_demo_pose.py` — one-pose `/api/state` polling, strict per-response quality gate, distinct frame requirement, timestamped snapshot metadata, and CLI JSON output.
- `tests/test_demo_profile.py` — nine capture tests using fake HTTP responses and a fake clock. No network or hardware access.

## RED / GREEN evidence

Working directory: `D:\semg.claude\coinft`.

1. RED command: `D:\conda\python.exe -m unittest tests.test_demo_profile -v`. Exit code 1; `ModuleNotFoundError: No module named 'calibration.capture_demo_pose'`. This is the expected missing-implementation failure.
2. GREEN command: `D:\conda\python.exe -m unittest tests.test_demo_profile -v`. Exit code 0; `Ran 7 tests in 0.032s` and `OK`.
3. CLI check: `D:\conda\python.exe calibration\capture_demo_pose.py --help`. Exit code 0; help lists required `--pose`, `--assembly-id`, `--out`, plus optional `--url`, `--seconds`, `--interval`.
4. Initial full suite: `D:\conda\python.exe -m unittest discover -s tests -v`. Exit code 0; `Ran 32 tests in 21.286s` and `OK` (25 previous tests plus 7 capture tests).
5. Exclusive-create RED command: `D:\conda\python.exe -m unittest tests.test_demo_profile.CaptureTests.test_cli_does_not_overwrite_file_created_during_serialization -v`. Exit code 1; `AssertionError: FileExistsError not raised`. The old writer overwrote a file created after its last existence check.
6. Exclusive-create GREEN command: `D:\conda\python.exe -m unittest tests.test_demo_profile -v`. Exit code 0; `Ran 8 tests in 0.026s` and `OK`.
7. Final full suite: `D:\conda\python.exe -m unittest discover -s tests -v`. Exit code 0; `Ran 33 tests in 21.143s` and `OK` (25 previous tests plus 8 capture tests).

## Reviewer fixes: resync metadata and capture timing

Changed files: `calibration/capture_demo_pose.py`, `tests/test_demo_profile.py`.

8. RED command: `D:\conda\python.exe -m unittest tests.test_demo_profile.CaptureTests.test_rejects_other_bad_state_fields tests.test_demo_profile.CaptureTests.test_rejects_nonfinite_or_nonpositive_capture_timing_before_request -v`. Exit code 1; `Ran 2 tests` with `FAILED (failures=7, errors=3)`. Resync values `NaN`, infinity, string, and negative number were accepted; infinite timing reached the HTTP request, while NaN/zero/negative timing failed for the wrong reason.
9. GREEN command: `D:\conda\python.exe -m unittest tests.test_demo_profile -v`. Exit code 0; `Ran 9 tests in 0.048s` and `OK`.
10. Full suite after reviewer fixes: `D:\conda\python.exe -m unittest discover -s tests -v`. Exit code 0; `Ran 34 tests in 24.347s` and `OK` (25 previous tests plus 9 capture tests).

The per-response gate now requires a nonnegative integer `resyncs` counter before it can enter evidence JSON. Capture rejects nonfinite or nonpositive `seconds` and `interval` before issuing an HTTP request, preventing an infinite deadline or sleep interval. No physical capture was attempted.

## Diagnostic-only follow-up for live aborts

Changed files: `calibration/capture_demo_pose.py` and only the capture assertions in `tests/test_demo_profile.py`. The fitter test class added by Task 2 was preserved.

11. RED command: `D:\conda\python.exe -m unittest tests.test_demo_profile.CaptureTests.test_rejects_duplicate_frame_without_skipping_it tests.test_demo_profile.CaptureTests.test_rejects_invalid_recent_without_skipping_it -v`. Exit code 1; `Ran 2 tests` and `FAILED (failures=2)`. Both received the old generic message, which lacked the failing predicate.
12. GREEN command: `D:\conda\python.exe -m unittest tests.test_demo_profile -v`. Exit code 0; `Ran 14 tests in 0.116s` and `OK` (9 capture plus 5 fitter tests).
13. Full suite: `D:\conda\python.exe -m unittest discover -s tests -v`. Exit code 0; `Ran 39 tests in 20.965s` and `OK`.

`valid_state` now evaluates the same acceptance conditions through a deterministic ordered list of reasons. An invalid response still aborts immediately. The error identifies status, non-increasing or malformed frame, rate, recent invalid/saturated counters, resync count, and malformed or nonfinite channel/raw entries as applicable. It includes the previous/current frame IDs for a repeated frame. No condition was relaxed, no sample is skipped, and this follow-up did not access hardware.

## Self-review

- `capture` requests only `/api/state` with a 1.5-second timeout. It has no hardware-control operation or pose transition.
- The default 5-second, 0.125-second interval yields 40 HTTP snapshots in the fake-clock test. The returned `sample_kind` is `http_snapshot`; the 200 Hz device rate is stored only as state metadata.
- Every response is checked before append: live status, increasing integer frame ID, finite positive rate, zero recent invalid/saturated counts, and finite 12-element channel/raw arrays. A failed check aborts capture; fewer than 30 snapshots also fails.
- Each sample stores an ISO local host timestamp, frame ID, channel/raw values, status, rate, quality counters, and resync count. Top-level metadata stores pose, assembly label, and source URL.
- The CLI checks that the output path does not exist before and after capture. It serializes with `ensure_ascii=False` and indentation only after capture succeeds, then uses UTF-8 mode `x` exclusive creation to prevent overwriting a file introduced between the checks and the write. This deliberately replaces the plan's illustrative `Path.write_text` call to satisfy the stronger non-overwrite requirement.

## Limitations and handoff

- No current-assembly data, profile, or physical direction claim exists from this task. Capture each labeled pose only after the operator confirms a stable pose and the physical screen-right direction.
- HTTP or JSON failures propagate and prevent output. The script does not perform automatic retries because an uninterrupted, valid window is required.
