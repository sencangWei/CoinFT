# Task 2: Fit profile and independent acceptance gate

Work in `D:\semg.claude\coinft`. You own only new `calibration/fit_demo_profile.py` and fitter-related additions to existing `tests/test_demo_profile.py`. Another agent finished the capture utility and its tests; preserve them. You are not alone in the workspace: do not revert others' edits and accommodate overlapping changes. Do not touch `demo_web/*`, firmware, `coinft_demo.py`, earlier calibration evidence, or `PROJECT_LOG.md`. No live hardware capture, no real profile generation yet.

Read Task 2 in `docs/superpowers/plans/2026-09-25-coinft-normal-bidirectional-shear-demo.md` and its Global Constraints first; this brief adds execution boundaries. Approved design: `docs/superpowers/specs/2026-09-25-coinft-normal-bidirectional-shear-demo-design.md`.

## Interface and schema

Implement `fit_profile(windows: dict[str, dict], right_label: str, left_label: str) -> tuple[dict, dict]`, where each value is a capture dictionary from Task 1 (`pose`, `assemblyId`, `samples` with distinct increasing `f`, 12 finite `channels` and `raw`, live/status/quality fields). Input includes train and holdout sets of `empty_before_press`, `press`, `empty_after_press`, and analogous right/left windows. All windows must carry one identical nonempty `assemblyId`. No holdout sample participates in fitting.

Return a profile with `version=1`, `assemblyId`, `normal:{threshold,span}`, `shear:{enabled,weights[8],pressLeak[8],threshold,span}`, `rightLabel`, `leftLabel`, and `evidence` filenames. Return a separate report with train/holdout gate values, pass/fail and reasons. A disabled shear profile must use all-zero weights and no fabricated direction. A profile may still carry a trained normal threshold if shear fails. All numbers finite JSON numbers, never NaN/Infinity.

## Signal/gate details

- For each action, subtract midpoint of its adjacent empty-before/empty-after channel medians; preserve empty samples in the background set using the same local midpoint. Do not subtract one global baseline across all poses.
- Normal score `max(0, median(CH9..CH12))`; contrast CH1..CH8 minus their mean; learn press cross-talk per unit normal score from train press only; residual contrast subtracts that leak; signed shear projection uses normalized `mean(train_right_residual) - mean(train_left_residual)`. Screen-right must score positive and screen-left negative on training medians; never guess sign from channel indices.
- Percentile is sorted linear interpolation. Train normal threshold is midpoint of empty p95 and press p10 if separated; shear threshold is midpoint between train background (empty+press) p95 of absolute scores and the lesser of right/left p10 of absolute scores. Require strict background < each action; positive finite spans. If no clean separation, mark shear disabled.
- Frozen holdout gate: `>=80%` press snapshots above normal threshold; `>=80%` each right/left snapshots with correct sign and above shear threshold; `<20%` holdout empty and press snapshots spuriously above shear threshold. Any failure disables shear without refitting. Record fractions and reasons.
- Validate captures thoroughly: required windows, correct pose names, one assembly ID, timestamps/evidence names, monotonic frames, valid finite 12-vectors, live samples, rate positive, invalid/saturated 0, nonnegative integer resyncs, at least 30 samples per window. Reject malformed input before fitting. CLI reads only `calibration/demo_<pose>_<date>.json` for one explicit date or unambiguous manifest; avoid globbing across dates/assemblies. CLI requires `--input-dir`, `--output`, `--report`, `--right-label`, `--left-label` and may add `--date` to select one capture set. Never overwrite earlier evidence. Do not write real profile/report until root confirms all actual capture windows are ready.

## TDD/report

Add synthetic tests to `tests/test_demo_profile.py` without changing Task 1 capture tests. Test clean opposite patterns, press-only cross-talk, held-out direction reversal/noise causing disabled shear, missing/malformed input, one-assembly check, and frozen training parameters. Run failing focused tests before production code, then focused GREEN, then full suite once. Use `apply_patch` for source/test changes, standard library only. No Git repository; do not initialize or commit.

Write detailed RED/GREEN commands/output, full-suite result, changed files, self-review, and limitations to `D:\semg.claude\coinft\.superpowers\sdd\shear-task-2-report.md`. Return only status, one-line tests, concerns, report path. If actual hardware capture is the only missing step, report `DONE_WITH_CONCERNS`; root owns operator coordination.
