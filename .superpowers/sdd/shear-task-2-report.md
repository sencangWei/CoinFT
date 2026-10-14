# Task 2 offline fitter report — 2026-09-25

Status: **DONE_WITH_CONCERNS**. The software fitter and synthetic acceptance gate are implemented. Real capture windows have not been fitted here; no `demo_web/shear_profile.json` or live report was generated.

## Changed files

- `calibration/fit_demo_profile.py` — validates 18 labeled windows, fits in the browser's direct tare-relative channel coordinates, uses adjacent empty windows as background evidence, applies the frozen holdout gate, and offers a date-explicit CLI that exclusively creates outputs.
- `tests/test_demo_profile.py` — appended fitter tests; existing capture tests retained unchanged.

## RED / GREEN evidence

1. RED: `D:\conda\python.exe -m unittest tests.test_demo_profile.FitterTests -v` exited 1, with `ModuleNotFoundError: No module named 'calibration.fit_demo_profile'`.
2. First GREEN attempt: same focused command ran 3 fitter tests; 2 failed because the synthetic fixture accidentally reversed the default held-out left direction. Corrected that fixture.
3. GREEN: `D:\conda\python.exe -m unittest tests.test_demo_profile -v` exited 0: 12 tests, `OK`.
4. Validation RED: added malformed quality and numeric overflow case; focused command exited 1 on overflow. The attempted overflow case still yielded a finite disabled profile, so that expectation was removed. The fitter now rejects nonfinite derived JSON and Boolean quality counters. This case was a test assumption error, not a production failure.
5. Final focused GREEN: `D:\conda\python.exe -m unittest tests.test_demo_profile -v` exited 0: 14 tests, `OK`. Added noise-only holdout and direct raw-capture API coverage; both pass.
6. Full suite: `D:\conda\python.exe -m unittest discover -s tests -q` exited 0: **39 tests, OK**, 21.358 s. HTTP fixture request logs appeared; no test failure.

## Gate and self-review

- Every capture must match its pose, share one nonempty assembly ID, have at least 30 samples, increasing frame IDs and timezone-aware increasing host times, live status, positive finite rate, zero integer invalid/saturated counts, nonnegative integer resync, and finite 12-channel/raw vectors.
- Train-only press sets the leakage vector in direct `/api/state` channel coordinates; train-only right-minus-left residual sets the signed unit template. Adjacent empty windows remain in the train and holdout background sets. The train normal/shear thresholds use sorted linear interpolation and the specified p95/p10 midpoint rules.
- Holdout press normal and both signed pushes must each reach 80%; holdout empty and press spurious fractions must each stay below 20%. Failure zeroes shear weights and leak without changing fitted normal threshold. Report includes fractions and reasons.
- CLI requires an explicit `--date` and reads only the 18 exact `demo_<pose>_<date>.json` paths. It checks output/report existence and uses exclusive create, so it will not overwrite prior artifacts.
- Direct `fit_profile` calls accept untouched Task 1 capture dictionaries with empty `evidence`; the CLI attaches the actual 18 filenames. No file provenance is invented for in-memory calls.

## Limits / next step

- Synthetic tests establish the software gate, not the current assembly's physical sign or separability. Root should run the CLI only after all current-assembly train and independent holdout windows exist and the operator confirms physical right/left labels.
- CLI output and report are created sequentially with exclusive opens. The report is written first, so a report failure cannot leave an enabled profile. A later profile-write failure can leave an orphaned report; inspect both artifacts before use.

## Reviewer follow-up — 2026-09-25

The reviewer identified missing cross-window chronology and unsafe profile-before-report write order. These are now fixed in the owned fitter and tests.

- The 18 windows must follow declared `POSES` order. The first host timestamp and frame ID of each window must be strictly later than the last timestamp and frame ID of its predecessor. This also rejects relabeled copies of a training capture in the holdout round, and catches an empty-after window relabeled as empty-before.
- The synthetic fixture now uses globally increasing timezone-aware host timestamps and frame IDs across all 18 windows.
- The CLI writes the gate report before the profile. A simulated report storage failure raises and leaves no profile.
- RED: `D:\conda\python.exe -m unittest tests.test_demo_profile.FitterTests -v` exited 1: reused holdout and misordered adjacent-empty tests failed to raise; report safety test initially had a mock binding error. After fixing the mock, `D:\conda\python.exe -m unittest tests.test_demo_profile.FitterTests.test_report_write_failure_cannot_leave_profile -v` exited 1 because the profile file existed.
- GREEN: `D:\conda\python.exe -m unittest tests.test_demo_profile -v` exited 0: **17 tests, OK**.
- Full suite: `D:\conda\python.exe -m unittest discover -s tests -q` exited 0: **42 tests, OK**, 21.164 s.
- No hardware data was fitted and no demo web profile was published.

## Integrated review follow-up — runtime coordinates and capture duration

The prior per-action empty subtraction was incompatible with the browser, which scores direct tare-relative `/api/state` channels. The fitter now uses the captured `channels` unchanged for training and the frozen holdout gate. Each adjacent empty window contributes its actual samples to the background distribution. This keeps training and runtime score primitives in the same coordinate system without changing the UI schema or the 80%/20% gate.

- RED: `D:\conda\python.exe -m unittest tests.test_demo_profile.FitterTests.test_differential_empty_offsets_are_safe_in_runtime_coordinates -v` exited 1. The old fit enabled shear but an empty window's direct runtime signed score exceeded its profile threshold.
- GREEN: `D:\conda\python.exe -m unittest tests.test_demo_profile -v` exited 0: 18 tests, `OK`. The differential-offset case now either disables shear or, if enabled, verifies all empty windows remain below threshold and held-out right/left scores have the correct sign beyond threshold.
- Additional RED: `D:\conda\python.exe -m unittest tests.test_demo_profile.FitterTests.test_rejects_thirty_near_instant_snapshots -v` exited 1 because a 30-frame, 0.29-second window was accepted. The fitter now requires each window's measured first-to-last host timestamp span to be at least 4.0 seconds.
- Final focused GREEN: `D:\conda\python.exe -m unittest tests.test_demo_profile -v` exited 0: **19 tests, OK**.
- Final full suite: `D:\conda\python.exe -m unittest discover -s tests -q` exited 0: **52 tests, OK**, 32.984 s. Expected missing-profile HTTP 404 fixture logs appeared.
- No actual hardware windows were fitted or profile published.

Design/spec wording for root to correct: the Task 2 plan's instruction to subtract each pose's adjacent-empty midpoint is no longer compatible with the fixed browser scorer unless a matching runtime baseline is added to the profile/UI. The current implementation intentionally keeps direct channel coordinates and retains empty windows as gate evidence.

## Re-review follow-up — independent empty windows and hysteresis

The holdout gate now requires each of the six empty windows independently to have **less than 20%** spurious shear at the activation threshold `T` and at the browser's active release threshold `0.7*T`. Holdout press must independently stay below 20% at both thresholds. The aggregate empty fractions remain in the report for context; the report also includes per-window fractions and the exact release threshold. All checks use frozen training weights, leakage, and thresholds.

- RED: `D:\conda\python.exe -m unittest tests.test_demo_profile.FitterTests.test_one_contaminated_holdout_empty_window_fails_individually tests.test_demo_profile.FitterTests.test_empty_response_between_release_and_activation_threshold_fails tests.test_demo_profile.FitterTests.test_press_response_between_release_and_activation_threshold_fails -v` exited 1 with three expected failures: the old gate enabled shear in each case.
- GREEN: `D:\conda\python.exe -m unittest tests.test_demo_profile -v` exited 0: 22 tests, `OK`.
- Report-field RED: the isolated release-threshold test failed with `KeyError: 'releaseThreshold'`; the train report now records that numeric value.
- Final focused GREEN: `D:\conda\python.exe -m unittest tests.test_demo_profile -q` exited 0: **22 tests, OK**.
- Final full suite: `D:\conda\python.exe -m unittest discover -s tests -q` exited 0: **55 tests, OK**, 33.452 s. Expected missing-profile HTTP 404 fixture logs appeared.
- No hardware data was fitted and no active profile was published.
