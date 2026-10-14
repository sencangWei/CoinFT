# Task 1: Reproducible, one-pose-at-a-time evidence capture

Work in `D:\semg.claude\coinft`. You own only `calibration/capture_demo_pose.py` and capture-related tests in `tests/test_demo_profile.py`. Other agents may work in this shared workspace: do not revert their edits; accommodate overlapping changes. Do not edit firmware, `coinft_demo.py`, front-end files, prior calibration data, or `PROJECT_LOG.md`.

The approved design is `docs/superpowers/specs/2026-09-25-coinft-normal-bidirectional-shear-demo-design.md`; the task comes from Task 1 of `docs/superpowers/plans/2026-09-25-coinft-normal-bidirectional-shear-demo.md`. The capture makes evidence for a later fitter. Do not collect physical data yourself yet; the root agent will cue the operator after code review. Do not resume the stopped 200 g repeatability series.

## Interface

Implement `capture(url: str, pose: str, assembly_id: str, seconds: float, interval: float) -> dict`. Return `{pose, assemblyId, source, sample_kind, samples}`. Each sample contains `host`, `f`, `channels`, `raw`, `status`, `rate`, `invalid`, `saturated`, `resync`. The input is GET `<url>/api/state` from `coinft_demo.py` (default URL `http://127.0.0.1:8765`). Require one stable pose named on CLI; never switch or control hardware.

## Acceptance and safety

- About 5 seconds with default interval 0.125 seconds; require at least 30 distinct, increasing frame IDs. Do not present HTTP snapshots as 200 Hz raw frames.
- Before appending, reject non-live state, non-increasing frame ID, bad/zero rate, `invalid_recent>0`, `saturated_recent>0`, 12-element `channels`/`raw` missing, or any nonfinite value. Abort the entire capture rather than silently skipping invalid samples.
- `argparse` requires `--pose`, `--assembly-id`, `--out`; accepts `--url`, `--seconds`, `--interval` defaults above. Only write JSON after a fully successful capture. Do not overwrite existing evidence. File UTF-8, `ensure_ascii=False`, `indent=2`.
- Metadata should record assembly label, source URL, pose name, sample kind, and timestamps. Use `datetime.now().astimezone().isoformat()` for host timestamp.
- Use standard library only. Use `apply_patch` for source/test edits. TDD: add focused failing tests, run and observe expected RED, implement, then rerun focused and full suite. Existing full baseline is 25 passing tests; a pre-existing test server ConnectionAbortedError can appear when Chromium closes.
- No Git repository here. Do not initialize Git, commit, reset, or alter unrelated user files.

## Required report

Write `D:\semg.claude\coinft\.superpowers\sdd\shear-task-1-report.md` with changed files, exact RED/GREEN test commands and relevant output, full-suite result, self-review, and limitations. Return only status `DONE`, `DONE_WITH_CONCERNS`, `BLOCKED`, or `NEEDS_CONTEXT`, one-line test summary, concerns, and report path. If physical capture is the only remaining step, report `DONE_WITH_CONCERNS`: root owns operator prompts and capture.
