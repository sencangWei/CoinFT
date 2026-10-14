# Task 1 report — qualitative demo profile

Status: DONE. No hardware operations or Task 2 changes were performed.

## Changed files

- `calibration/build_qualitative_demo_profile.py` — validates eight labeled captures, adjusts each group by its local empty baseline, fits the signed qualitative shear model, and writes a new profile exclusively.
- `tests/test_qualitative_demo_profile.py` — synthetic offset, directional separation, and malformed evidence tests.
- `demo_web/shear_demo_profile.json` — generated from the eight specified existing captures.

`calibration/fit_demo_profile.py` and strict `demo_web/shear_profile.json` were not changed.

## TDD and verification evidence

Red command, before builder existed:

```text
> D:\conda\python.exe -m unittest tests.test_qualitative_demo_profile -v
test_qualitative_demo_profile (unittest.loader._FailedTest.test_qualitative_demo_profile) ... ERROR
ModuleNotFoundError: No module named 'calibration.build_qualitative_demo_profile'
Ran 1 test in 0.001s
FAILED (errors=1)
exit 1
```

Green command, after implementation:

```text
> D:\conda\python.exe -m unittest tests.test_qualitative_demo_profile -v
test_bad_or_missing_evidence_is_rejected (tests.test_qualitative_demo_profile.QualitativeDemoProfileTests.test_bad_or_missing_evidence_is_rejected) ... ok
test_offsets_cancel_and_directions_separate (tests.test_qualitative_demo_profile.QualitativeDemoProfileTests.test_offsets_cancel_and_directions_separate) ... ok
test_zero_left_action_is_rejected (tests.test_qualitative_demo_profile.QualitativeDemoProfileTests.test_zero_left_action_is_rejected) ... ok
Ran 3 tests in 0.031s
OK
exit 0
```

Generation command and exact summary:

```text
> D:\conda\python.exe calibration\build_qualitative_demo_profile.py --out demo_web\shear_demo_profile.json
{"threshold": 99.11124275398228, "rightMedian": 336.39410148532386, "leftMedian": -165.16752582071882, "evidence": ["demo_train_empty_before_press_20260925.json", "demo_train_press_20260925.json", "demo_train_empty_after_press_20260925.json", "demo_train_empty_before_right_20260925.json", "demo_train_right_20260925.json", "demo_train_empty_after_right_20260925.json", "demo_diagnostic_empty_after_second_usb_20260925.json", "demo_diagnostic_left_demo_force_20260925.json"]}
exit 0
```

Full-suite command (HTTP access logging omitted; final output shown):

```text
> D:\conda\python.exe -m unittest discover -s tests -q
----------------------------------------------------------------------
Ran 58 tests in 32.406s

OK
exit 0
```

## Generated values and review

The JSON has `version: 1`, `mode: "qualitative"`, assembly `coinft-current-20260925`, labels `−X` and `+X`, normal threshold/span `100.0/600.0`, shear threshold `99.11124275398228`, shear span `128.5109264230957`, and all eight evidence basenames. Its eight shear weights are `[0.5119536167478967, -0.5584936703500715, -0.19694140021121337, 0.2151686779046843, -0.03406743093409363, -0.07274013968644583, 0.47086415199790316, -0.33576788411117126]`. It contains no force units.

Self-review: The model uses existing scoring primitives and the required threshold/span formulas. Each action and its empties are baseline adjusted to the same coordinate system used by the proposed browser page baseline. File creation uses exclusive `open("x")`, so rerunning generation will fail instead of replacing a profile. The real captures pass validation and separate in opposite directions without manual weight or threshold changes.

Concern: These eight captures include only one action window per direction and no independent holdout; this profile supports a qualitative demonstration only. It is not a force calibration or live hardware acceptance.
