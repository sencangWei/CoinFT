# CoinFT Stream Recovery Implementation Plan

> For agentic workers: REQUIRED SUB-SKILL: use subagent-driven-development in this session; execute the bounded task below with TDD, independent task review, then whole-change review.

Goal: make a silent live serial stream recover automatically in the same server process without replacing established PC or frontend demo baselines.

Architecture: retain DemoSource's single reader and current FrameParser/RelativeProjector. Add monotonic connection progress tracking, interruptible same-port reconnect scheduling and a separate nested recovery API field. Existing frontend pause/resume consumes new live frames unchanged.

Tech stack: Python, pyserial, threading.Event, unittest fake transports/clock; existing Playwright UI regression tests.

Approved design: docs/superpowers/specs/2026-09-28-coinft-stream-recovery-design.md, approved in writing by user on 2026-09-28.

## Global Constraints

- Change only the PC serial acquisition behavior in `coinft_demo.py` and its covering tests. Reuse the existing frontend's pause/resume behavior; do not edit chart layout, `app.js`, `surface.js`, force matrix, shear profile or gain settings.
- The current serial reader remains the sole owner/writer of the configured raw port, currently COM6. Do not open diagnostic COM8 for writes, introduce another serial-writer thread, or hardcode new port discovery.
- No Teensy/CoinFT firmware, tuning table, voltage, power cycle, USB unplug or startup-batch change. No device t command. Current NUM1/1Mbps/12-channel parameters remain intact.
- No assistant bypass of existing service process-control restrictions. Deployment is an operator-controlled service restart after software verification.
- Both raw-byte and parsed-frame progress must be absent for at least 2.0 seconds, measured monotonically, before silence recovery. Constant frames, saturation, invalid-range frames or continuous garbage alone do not trigger reconnect.
- Automatic attempts, including failed opens, start at least 5.0 seconds apart. Stop must interrupt cooldown/startup waits and prevent subsequent open/s once cancellation is observed.
- Preserve established PC baseline, pending initial/manual tare acquisition, frame epoch, serial diagnostics totals/timestamps and parser resync totals. Recovery never calls request_tare automatically.
- Recovery API initially: `{"attempts": 0, "successes": 0, "last_fault": null}`. Fault captures reason, observation time, frame count and copied existing diagnostics before clearing pending bytes. Success is new valid data returning to live, at most one success per attempt. Deeply isolate nested recovery snapshots; keep old diagnostics schema unchanged.
- No real COM opens/commands, service process control, firmware uploads or live fault injection during implementation/tests.
- This directory has no Git metadata. Do not initialize, commit, branch or create a worktree. Controller records exact before-file snapshots plus protected hashes and generates a no-index review package. Preserve other users' changes.

## Baseline and evidence prerequisites (controller)

- [x] Serial diagnostics baseline: 5 tests PASS.
- [x] Core baseline: 11 tests PASS.
- [x] Save byte-content snapshots of coinft_demo.py and tests/test_serial_diagnostics.py, plus protected-file hashes before worker dispatch.
- [x] Record plan/spec approvals in progress-stream-recovery.md.
- [x] Self-review: one atomic reader/API/test task avoids concurrent edits or incoherent interim serial logic. No constraint conflicts; recovery counters are additive, not changes to existing diagnostics.

### Task 1: Preserve-baseline single-reader recovery and deterministic tests

Files:
- Modify: coinft_demo.py (DemoSource.__init__, snapshot, _run_serial and a small fault-record helper if needed).
- Create: tests/test_serial_recovery.py.
- Modify tests/test_serial_diagnostics.py only if the old fake wait/clock fixture or new fault timestamps require legitimate accommodation; retain its exact existing diagnostics expectations.
- Report: .superpowers/sdd/stream-recovery-task-1-report.md.

Read the approved spec first. This task is the entire production implementation; no UI or firmware changes.

- [x] RED: Write deterministic tests driving the real _run_serial, FrameParser and _consume via fake pyserial and time. Do not mock the behavior being tested. Fail before changing production.
- [x] Fake transport validates TEST_ONLY port, baud 115200, timeout 0.1, records open/close/reset/write/read timestamps. Clock advances on read/wait; Event wait remains cancelable and no real sleeps. Bound tests so a regression cannot hang indefinitely.
- [x] Cover silence at just below/exact 2 seconds; newly parsed frames and nonempty chunks refresh independent monotonic progress. Validate no extra commands for constant valid frames, sustained load, saturation, invalid frames or continuous garbage.
- [x] Cover silent recovery command/order and only same-port ownership. Startup remains i, wait 0.2, input reset, s. Final best-effort i is allowed but no t/tuning/reset commands.
- [x] Cover repeated silent/failed-open attempts and start-to-start intervals at least 5 seconds; initial open excluded. OS read/open/write exceptions remain visible and retry with bounded spacing.
- [x] Cover stopping during startup and retry cooldown: no later s/open; handles close. Record failed-cleanup behavior as needed without swallowing primary fault.
- [x] Cover established baseline identity/value preservation and nonzero held-load channels after valid recovery. Preserve monotonically increasing frames, resyncs/discard/byte/parsed counts and observation timestamps. Capture old pending bytes before clear.
- [x] Cover initial400 valid-frame acquisition split across reconnect and explicit manual tare split across reconnect; no automatic request_tare and no successful recovery before pending acquisition becomes live. Invalid recovered frames/open/write/cached snapshots are not successes.
- [x] Cover recovery snapshot isolation including nested last_fault diagnostics, and at most one success per automatic attempt.
- [x] Run RED command and record actual failures and reasons in report:
  `& 'D:\conda\python.exe' -m unittest discover -s tests -p 'test_serial_recovery.py' -v`.
- [x] GREEN: Add separate recovery state in DemoSource and isolate it in snapshot. A small fault helper locks, freezes reason/time/frame/diagnostics, and never clears history.
- [x] Track whether this is an automatic reopen and previous automatic attempt start. Before each automatic open, wait only the required remaining cooldown using stop_event.wait; guard open and s after cancellation. Increment attempts at automatic open start even if it fails.
- [x] On open, clear only parser.buffer (retain parser.resyncs), set pending count0/reset rate window. Set waiting until new data rather than reuse live cached state. Preserve projector baseline, tare_frames/tare_requested and current axes/history.
- [x] Replace noninterruptible time.sleep(0.2) with stop_event.wait(0.2), checking cancellation before buffer reset/start. Existing normal startup command protocol remains.
- [x] Initialize last raw/frame monotonic progress after s. Update diagnostics exactly as before on each successful read; consume each newly parsed frame. Use valid raw plus live source status to count one pending attempt success, not cached live after invalid input.
- [x] When both progress timers reach 2 seconds, capture fault, expose waiting, close old connection, then schedule same-port recovery. Keep existing frame-wait reporting for corrupt/partial traffic without falsely triggering silence recovery.
- [x] On serial OS errors capture the fault before clearing pending parser state, expose error and schedule recovery with the same cooldown. Best-effort idle/close must not mask the original fault.
- [x] Preserve explicit tare request semantics during cooldown/reconnect. Do not change replay logic or defaults outside task scope.
- [x] Run GREEN focused commands:
  `& 'D:\conda\python.exe' -m unittest discover -s tests -p 'test_serial_recovery.py' -v`
  `& 'D:\conda\python.exe' -m unittest discover -s tests -p 'test_serial_diagnostics.py' -v`
  `& 'D:\conda\python.exe' -m unittest discover -s tests -p 'test_demo_core.py' -v`
- [x] Self-review edge cases, shutdown ownership, tests' meaningful assertions and scope. Full report carries RED/GREEN commands, relevant outputs, exact files, result/concerns. No Git commit.

## Independent validation and handoff (controller, after Task1)

- [x] Generate review package from exact before snapshots with full-context diffs for changed backend/test files and the complete new test file. Add report/protected manifest paths.
- [x] Dispatch fresh task reviewer for spec compliance AND task code quality; resolve Critical/Important findings with scoped fix worker and rerun covering tests before rereview.
- [x] Fresh controller focused tests plus `& 'D:\conda\python.exe' -m unittest discover -s tests -v` once. Existing full suite previously110 tests; report actual new total, don't assume.
- [x] Verify app.js/surface.js/START_DEMO.bat/matrix/shear profile and Teensy/CoinFT/IMU protected source/build hashes exactly unchanged.
- [x] Dispatch fresh whole-change reviewer; resolve findings, gather final verdict. Code/spec APPROVE + independent architecture CLEAR; software APPROVE. No merge/PR/branch operation because no repository.
- [x] Update PROJECT_LOG and progress ledger with truthful software evidence, remaining live acceptance and operator manual deployment instruction.
- [ ] Handoff: user closes original acquisition console and starts START_DEMO.bat once. Process restart may need intentional page demo zero once, distinct from runtime recovery which must preserve it.
- [ ] Hardware acceptance remains pending until user deployment and real same-process stall/recovery with new host+UART frames. No forced physical disconnect or diagnostic writes. No permanent root-cause/force calibration claims.

## Plan self-review

Approved scope is serial continuity only. Both independent progress timers and bounded retry cadence are explicit; counter success and tare rules are internally consistent. One owner writes the serial protocol. Test clock models elapsed waits rather than constant fake time. No conflicting Git/UI/firmware instructions are executable in this project. Self-review PASS; execute without further design approval prompts.
