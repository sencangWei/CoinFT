# CoinFT 正压＋单轴双向剪切执行进度

- Plan: `docs/superpowers/plans/2026-09-25-coinft-normal-bidirectional-shear-demo.md`
- Baseline: 2026-09-25 `D:\conda\python.exe -m unittest discover -s tests -v`，25 tests passed；测试 HTTP 服务关闭期间有一条 ConnectionAbortedError 日志。
- Git: `D:\semg.claude\coinft` 非 Git 仓库；不初始化、不提交，审查改用明确文件清单和本地内容核对。
- Latest (2026-09-25): initial five-window capture archived under `calibration/demo_attempt_before_teensy_reconnect_20260925/` after accidental Program-button re-tare. Second attempt saved seven canonical train windows through `train_empty_before_left`; `train_left` aborted at waiting with COM10 still present and frames frozen at 3461954. USB reconnect restored stream. Diagnostic 6-second empty passed, and one ~1-second light +X push remained live (3513302→3513476); intermittent failure cause unknown. No valid real profile/report. Do not combine captures across re-tare.
- Software latest: direct-channel fitter/holdout per-window T and 0.7T gates, ≥4s evidence span, stale/tare/frame UI repairs independently reviewed approved. Root full test suite 55/55 PASS. Current app press-only fallback.
- Task 1 software: capture/failure diagnostics reviewed; integrated review requires ~5 s minimum evidence span (fix pending). Five canonical train windows captured through `train_right`; `train_empty_after_right` failed when COM10 stopped. An old pre-right attempt is preserved as `_attempt1` and excluded.
- Task 2 software: initial fitter passed focused 17/17, but integrated review found fitter adjacent-empty subtraction inconsistent with direct browser tare-relative input. Coordinate-system repair pending. No profile/report generated; real 18-window gate pending.
- Task 3: UI implemented, 47 tests reported by worker and initial UI re-review approved. Integrated review found old-frame high-water and tare failure/recovery cases; repair pending. Current app has no profile and remains press-only fallback.
- Hardware: operator declared −X = screen-right; COM10 stream halted at frame 3279912, then port disappeared and VID_16C0&PID_0478 bootloader appeared. Cause unknown, no flash/restart yet. Prior captures must not be spliced across reset without revalidation.
- Task 4: pending.
