# Task 2 implementation report

Status: DONE. Implemented only the ordered offline input, candidate fit, unchanged production JavaScript replay, and fixed acceptance gate from the corrected Task 2 brief.

## Owned changes

- `calibration/shear_refit_replay.py`: new, 113 lines. Exact brief interfaces `fit_candidate(windows, old)`, `replay(profile, old, windows, baseline)`, `passes(report)` and ordered owner/time/frame checks. Existing eight-window builder/validator reused without edits.
- `tests/test_shear_refit_replay.py`: new, 83 lines. Four corrected brief tests plus finite-report rejection coverage (NaN, both infinities, bool, string).
- This report. No existing production files or profiles edited. No Git operations.

## Commands and observed output

Working directory: `D:\semg.claude\coinft`. Commands ran in this order.

### RED before implementation

```powershell
& 'D:\conda\python.exe' -m unittest discover -s tests -p test_shear_refit_replay.py -v
```

Exit 1. All five tests failed through the guarded missing-module assertion in `setUp`, without import or syntax errors. Exact failure message and run summary:

```text
AssertionError: unexpectedly None : offline refit behaviors are not implemented
Ran 5 tests in 0.002s
FAILED (failures=5)
```

Failing tests: `test_normal_change_is_detected_and_rejected`, `test_preserves_normal_and_replays_actual_surface`, `test_rejects_cross_window_epoch_and_frame_restart`, `test_rejects_false_shear_or_wrong_direction`, `test_rejects_nonfinite_report_values`.

### GREEN after implementation

```powershell
& 'D:\conda\python.exe' -m unittest discover -s tests -p test_shear_refit_replay.py -v
```

Exit 0, each of the five tests `ok`:

```text
Ran 5 tests in 1.500s
OK
```

```powershell
& 'D:\conda\python.exe' -m unittest discover -s tests -p test_qualitative_demo_profile.py -v
```

Exit 0:

```text
Ran 3 tests in 0.035s
OK
```

### Full suite, once after stable GREEN

```powershell
& 'D:\conda\python.exe' -m unittest discover -s tests -v
```

Exit 0:

```text
Ran 142 tests in 77.427s
OK
```

Existing UI tests use their own loopback HTTP fixtures and print expected fixture 404/request logs; no live application service, hardware, or serial device was accessed. Existing firmware tests compile/run offline host fixtures. Task 2 replay itself loads the local unchanged `surface.js` with Playwright Chromium and uses no HTTP.

## Acceptance and scope self-review

The test loads the actual existing `demo_web/shear_demo_profile.json` as the old profile and compares each old/new normal target through two instances of the real `createSurface`. A copied candidate with normal span 1200 is detected and rejected. The candidate retains normal threshold 100/span 600. Version 1, qualitative mode, right label −X and left label +X come from the existing builder.

Replay applies one explicit common twelve-channel baseline (`[0]*12` in the synthetic acceptance test), and records all per-sample normal/shear values. Stable samples begin at 600 ms. Gates remain idle/press abs <=0.05; right >=0.20 for >=80% with no value <-0.05; left <=-0.20 for >=80% with no value >0.05; all normal targets identical. Owner identity and strictly increasing cross-window host/frame sequence are checked after the existing validator; its >=40 samples and >=5-second first/last requirements remain intact.

Every implementation line corresponds to the corrected brief. Extra test lines cover the brief's finite-report gate. No abstraction, production installation, capture, UI change, normal mapping change, or gate relaxation added. Only the three owned new files were written by this task; Python/test infrastructure can create ordinary caches and temporary fixture artifacts.

## SHA256

```text
calibration/shear_refit_replay.py
D8E9A685EFB96F4C721CB97361C6E940D0CD0F7BD8DFECA608C7390638FAA9FA
tests/test_shear_refit_replay.py
0ADD5F57DF63034295965F1B50BF43891263DB496E51E63D9422487657B64C53
```

Read-only reference hashes observed (these files were not written by this task):

```text
demo_web/surface.js
D7AD21EFD772367E0A63A9B1FCEAC466DA481ECE2ABCC185505E1A63EE1FEDBF
demo_web/shear_demo_profile.json
FAE3EA39D65D105795B6CEA8E34B999D939A9AB9AFBF0495AB5E15614B728E83
```

## Follow-ups noted but not done

No out-of-scope defects identified. Production profile/evidence replacement and live orchestration belong to later authorized tasks. Project-level handoff update remains with the supervising agent, outside this task's file ownership.
