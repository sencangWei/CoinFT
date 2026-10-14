# Task 1 auto-recovery implementation report

Status: DONE; approved scope implemented and verified, including review correction.

## Scope and behavior

Changed only `demo_web/app.js` and `tests/test_demo_ui.py`; evidence files are under `.superpowers/sdd`. No backend, firmware, surface geometry, thresholds, templates, or profile changes. No hardware/live-port operation and no Git repository initialization or commit.

`pauseDemoZero` preserves a completed qualitative baseline, clears the grid immediately, disables page zero until healthy new data, and labels the surface `已暂停，等待自动恢复`. Without a completed baseline it cancels pending zero collection. Existing hard invalidation still handles explicit device tare, observed status taring, and frame regression. Temporary display clears retain the frame high-water. A qualitative regression disarms and starts a new server frame epoch, allowing later explicit zero.

Newer healthy finite 12-channel frames restore motion by subtracting the exact retained baseline; ordinary duplicate snapshots do not collect samples, refresh the watchdog, or restore paused motion. Strict-profile behavior and tare generation/ack/inflight guards remain covered by existing browser tests.

## RED evidence (before app.js changes)

Command:
`D:\conda\python.exe -m unittest tests.test_demo_ui.DashboardWarningTests.test_qualitative_baseline_recovers_on_transient_faults_and_invalidates_on_tare tests.test_demo_ui.DashboardWarningTests.test_qualitative_malformed_channels_pause_ready_baseline -v`

Observed output: `Ran 2 tests in 5.163s; FAILED (failures=2)`, exit 1. Both failed on expected behavior assertions: `demoBaseline` was `None`, expected retained `[250] * 12` or `[0] * 12`. This proved the old transient fault contract invalidated ready baselines.

## GREEN and test coverage

Focused recovery/timing/watchdog command:
`D:\conda\python.exe -m unittest tests.test_demo_ui.DashboardWarningTests.test_qualitative_baseline_recovers_on_transient_faults_and_invalidates_on_tare tests.test_demo_ui.DashboardWarningTests.test_qualitative_ready_duplicate_and_stalled_request_watchdog tests.test_demo_ui.DashboardWarningTests.test_qualitative_zero_survives_100ms_batches_and_50ms_duplicate_polls -v`

Observed: `Ran 3 tests in 12.554s; OK`, exit 0. Epoch re-zero extension separately: `Ran 1 test in 5.145s; OK`, exit 0.

Coverage includes a genuinely collected nonzero baseline `[700] * 12`, array identity retention across watchdog/recovery under `[1400] * 12` load, invalid/saturation/waiting/error pause and new-frame recovery, malformed channel lengths/nulls, same-frame refusal, no automatic tare requests, HTTP recovery, regression after HTTP failure, restart epoch explicit zero, status taring, explicit failed tare, pending collection abort, first-valid-sample timing, 10 distinct samples, and ordinary repeated snapshots. The stalled-fetch test spans watchdog pause, 1500 ms timeout/catch/finally gate release, same-frame non-recovery, and new-frame recovery.

An initial broad run had one test seed race: checking only `surfaceView.target > 0` returned before the newly seeded frame arrived, so the nominal regressed frame equaled the high-water. The test now waits for the exact seeded frame and loaded surface. The focused rerun passed. A captured full UI run then reported `Ran 29 tests in 54.755s; OK`; PowerShell's native stderr/Tee pipeline returned shell exit 1 despite the unittest OK output, so final verification uses direct unpiped commands.

Pre-review direct UI run: `D:\conda\python.exe -m unittest tests.test_demo_ui -v` reported `Ran 29 tests in 56.457s; OK`, actual exit 0. Final amended UI and full-discovery results will be appended below.

## Review correction: strict reconnect frame reset

Reviewer identified that retaining latestFrame for every profile changed strict HTTP/server-restart behavior. Added a strict HTTP-outage/restart-at-frame-1 assertion before the fix. RED: same `test_older_frame_cannot_lower_surface_high_water` command reported `Ran 1 test in 1.522s; FAILED (failures=1)`, exit 1, with `[surfaceView.target, latestFrame]` actual `[0, 201]`, expected `[1, 1]`.

Production correction is one conditional in clearDisplay: reset latestFrame for non-qualitative profiles only. Focused strict + qualitative commands reported `Ran 2 tests in 6.570s; OK`, exit 0. Also added strict waiting/restart-at-frame-0 coverage. Updated review diffs and combined package after the amendment. Qualitative continuity remains intact.

Amended full UI run reported `Ran 29 tests in 86.314s; FAILED (errors=1)`, exit 1. All recovery and strict restart tests passed. The unchanged `test_surface_animates_on_live_press_and_release` timed out observing an intermediate release-animation level (line 1038). Focused rerun of that exact test immediately passed: `Ran 1 test in 2.282s; OK`, exit 0. That existing test takes a loaded screenshot while its source emits a constant frame; snapshot overhead/browser contention can exhaust the 500 ms watchdog budget before release observation. This is a timing explanation, not a proven root cause. Root discovery was concurrently exercising browsers, so final broad confirmation is coordinated sequentially. No animation code or unrelated test alteration was made.

Final amended full-discovery verification (root-executed, exec session 34015):
`D:\conda\python.exe -m unittest discover -s tests -q`
reported `Ran 72 tests in 61.522s; OK`, exit 0. This includes all 29 UI tests and the unchanged animation test. Root confirmed no Critical/Important findings in final review; the prior strict reconnect finding is resolved. Root explicitly accepted the previous broad UI failure documentation, isolated animation pass, and fresh complete discovery pass as sufficient without another duplicate full UI run.

Optional reviewer observation: an exact unsaturated target assertion would strengthen detection of future accidental baseline subtraction changes. Current evidence proves array identity retention on a genuinely collected nonzero baseline and retained baseline values/recovery at nonzero load; no extra implementation changes were made for this minor suggestion.

## Review package

Pre-edit snapshots: `auto-recovery-before-app.js`, `auto-recovery-before-test_demo_ui.py` (Copy-Item).

Review diffs: `auto-recovery-app-review.diff` (80 lines context), `auto-recovery-tests-review.diff` (15 lines context), combined `auto-recovery-review-package.txt`. Generated with Git no-index diff only; expected diff exit 1 means changed files, not a validation failure.

## Known limitation

Frontend invalidates when it observes a tare command/status or frame regression. A long HTTP outage can conceal an entire backend reconnect tare while the backend keeps its cumulative frame counter; the existing state protocol exposes no durable tare generation. This patch cannot detect that unobserved offset change and does not claim all genuine reconnect offset changes are detected. Root explicitly kept this patch within the approved observable tare/taring/regression scope, without adding raw-minus-channels heuristics or backend changes. Synthetic automated acceptance is not a real hardware fault reproduction.
