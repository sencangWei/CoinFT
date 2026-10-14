# Mechanical capture interval amendment report

## Commands and results

RED, after the test amendment and before the command change:

```text
python -m pytest -q tests/test_refit_capture_command.py
exit code: 1
2 failed, 4 passed, 15 subtests passed in 6.03s
```

The expected success case failed while the command still requested 0.1 seconds. The owner-change case also exhausted its fixture at that old cadence.

GREEN, after changing the command interval:

```text
python -m pytest -q tests/test_refit_capture_command.py
exit code: 0
6 passed, 15 subtests passed in 5.77s
```

No full-suite or live capture was run.

## Changed lines

- `.superpowers/sdd/shear-refit-capture-command.py:55`: capture interval `0.1` to `0.125` seconds.
- `tests/test_refit_capture_command.py:48`: select every 25th dense fixture state.
- `tests/test_refit_capture_command.py:106`: require exactly 41 successful observations.
- `tests/test_refit_capture_command.py:125`: equal-previous parsed frame mutation now uses 51.

## SHA-256

- `.superpowers/sdd/shear-refit-capture-command.py`: `96C2F490DA7FD320914DD21C3D28C2285BD485F453FD95EEEEAAA958F9D49876`
- `tests/test_refit_capture_command.py`: `4FEBBEECF2B0AE0DF5D07E2439B38E800C8DE8BA8F215566865F4B62F35DFCCD`

## Self-review

Only the two owned files were changed. The requested 0.125-second cadence and exact 41-observation assertion are covered; the existing output target, 5-second span and frame-rate checks, all unsafe cases, and the unchanged quality gates remain intact. No unrelated files, dependencies, live services, or Git state were touched.
