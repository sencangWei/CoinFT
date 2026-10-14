# CoinFT Stream Diagnostics Implementation Plan

> Execution: subagent-driven-development for one isolated task, followed by task and final read-only reviews. No Git operations because this directory is not a repository.

**Goal:** identify serial silence vs parser failure at the next real waiting event.

**Architecture:** additive diagnostics in existing DemoSource state/API, lock-protected scalar counters with copied snapshots; the serial read loop is the sole updater. No changes to start/stop/tare or visuals.

**Tech Stack:** Python unittest, existing pyserial and FrameParser.

## Global constraints

Only add serial diagnostic counters to the existing API. Preserve existing status, frames, channels, axes, zero/tare and startup i/s behavior. No automatic retries, restart endpoint, device writes, firmware changes, raw byte file logging, frontend changes or direction-template fitting are introduced. Never open COM10 or restart any live service in tests.

### Task 1: serial counters and snapshot isolation

Full exact requirements, implementation steps/schema and TDD cases: .superpowers/sdd/stream-diagnostics-task-1-brief.md. Owned production file coinft_demo.py; new test file tests/test_serial_diagnostics.py.

- [x] Write failing read-loop tests; focused RED: 5 expected missing-key failures, 0.007s, exit 1.
- [x] Add precise state schema, copied snapshots and per-read counter updates; focused GREEN: 5 pass, 0.005s, exit 0.
- [x] Full worker suite: 86 pass, 62.823s, exit 0; source frozen.
- [x] Task and final whole-change reviews: no Critical/Important/Minor findings.
- [x] Root fresh full suite: 86 pass, 63.053s, exit 0; UI/profile hashes unchanged; PROJECT_LOG updated and manual restart handoff prepared.
- [x] Operator restart and live API verification: PID54804 now includes diagnostics. Four startup samples and 20 idle samples all live, incoming bytes and parsed/valid frames advance, zero recent invalid/saturation/discard. Idle first-to-last 19.216s, +3849 frames (200.300Hz). Deployment/window only passed; no fault event captured or root-cause resolution claimed.
- [x] Actual waiting event captured 2026-09-28 PID44864: 3.0518s reads+28, no byte/parsed/valid-frame increment; diagnostic boundary is no incoming bytes at Python serial reader. Not a root-cause or direction acceptance claim.
- [ ] Confirm operator actions since startup, then select further upstream diagnostic evidence; no automatic restart/firmware change.
