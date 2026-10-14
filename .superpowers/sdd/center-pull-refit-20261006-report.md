# Center −X pull profile-only refit report

Status: **DONE_WITH_CONCERNS**. An offline candidate was frozen, but it is not installed and has not received independent post-fit hardware validation.

## Outcome

- The required TDD RED was behavioral: installed profile replay on the full center −X pull produced 0/36 stable samples at shear ≥ 0.20; expected at least 80%. Normal output was unchanged.
- The strict normalized LP (`|background| <= 0.5`, signed loaded score `>= 1.1`, coefficient bounds `[-0.05, 0.05]`, 10 s limit) was infeasible with HiGHS status 2. This establishes only failure of that fitting surrogate, not global mathematical or hardware infeasibility.
- The single permitted soft-loaded LP succeeded. Total loaded slack was 1.5610967781, dominated by the short actual +X window (1.3923461471); no further attempts or threshold sweeps were made.
- The candidate keeps version 1, qualitative mode, assembly ID, labels/signs, normal threshold 100/span 600, and shear threshold/span 58.330169520837785. Its eight weights sum to approximately `1.39e-17`; jointly fitted pressure coefficient `c = dot(w, pressLeak) = 0.1573507222`.

## Replay results

The candidate passed all nine saved actual-page diagnostic windows through the unchanged `demo_web/surface.js` with cold-start filtering. The full center −X window was 36/36 active, the short +X window was 5/6 active (the fixed 80% gate), every other −X window was fully active, and idle/purepress had zero samples with `abs(shear) > 0.05`. There were no reverse-direction samples and normal output was exactly identical to installed profile output for every replayed sample.

The separate historical fixed-raw regression also passed all eight long windows: right 36/36, left 36/36, and all six background/press windows had zero spurious samples. These windows use `feature_basis.common_raw_baseline` from `shear-refit-fresh-right-20261005.json`; they are historical regression evidence, **not independent validation after this fit**, and are not asserted to share the actual-page basis.

Short actual-page windows and the later full pull/control windows belong to different recovery epochs and retain their own captured page baselines. Replay has no captured filter prehistory. Independent physical capture and acceptance are still required before any installation.

## TDD and verification

RED command:

```text
python .superpowers\sdd\test_center_pull_refit_20261006.py -v
AssertionError: 0.0 not greater than or equal to 0.8
Ran 1 test ... FAILED (failures=1)
```

GREEN command:

```text
python .superpowers\sdd\test_center_pull_refit_20261006.py -v
Ran 3 tests in 1.544s
OK
```

Final artifacts and hashes:

- Candidate: `.superpowers/sdd/center-pull-refit-20261006-candidate.json` — `1df74f4570f5119f180f9e7830120abe555bd6c37cc33ab3dbc33b8dba5a6020`
- Fitter/evaluator source: `.superpowers/sdd/center-pull-refit-20261006.py` — `f6d35ec0649b62d5d3b71adec7a1f021f4f9c07cbc3bd8423d03403950215801`
- Regression test: `.superpowers/sdd/test_center_pull_refit_20261006.py` — `531ce7e5866dd071134f4ed130cde71fd8b8b3826a84c3f796974d5df5786ac9`
- Installed profile before/after: `af13756949ff0bb047392c183117298ea1b070106e3f2edc0553c075e25be150`
- Unchanged surface.js: `d7ad21efd772367e0a63a9b1fceac466da481ece2abcc185505e1a63ee1fedbf`

The JSON report contains the complete candidate, both bounded attempts, provenance distinctions, and per-window replay counts/ranges. No live endpoint, COM port, tare, capture, production profile, firmware, or UI was touched.

## Reviewer-focused provenance verification

Focused read-only verification after the provenance amendment produced:

```text
source_hashes 17 match; mismatches 0
fixed_baseline_exact True
fresh_report_hash_match True
validation_report_hash_match True
all_sample_background_windows 9
all_sample_background_max_abs 0
candidate_sha256 1df74f4570f5119f180f9e7830120abe555bd6c37cc33ab3dbc33b8dba5a6020
production_sha256 af13756949ff0bb047392c183117298ea1b070106e3f2edc0553c075e25be150
```

The 17 inputs are the nine actual-page diagnostic files and eight historical fixed-raw files now recorded with path and SHA256. The authoritative fixed baseline is byte-source-traced to `.superpowers/sdd/shear-refit-fresh-right-20261005.json` (`feature_basis.common_raw_baseline`) and is numerically identical element-for-element to the saved report array. The nine all-sample background checks combine three actual-page idle/press diagnostics with six historical fixed-raw background/press windows; they include samples before 600 ms but preserve the distinction between the two coordinate bases.
