# CoinFT stream recovery task 1 report

Date: 2026-09-28

Result: **DONE_WITH_CONCERNS** — deterministic software recovery policy is implemented and all requested focused tests pass. Actual hardware/service acceptance remains pending and was intentionally not attempted.

## Scope and files

- Modified `coinft_demo.py`:
  - added isolated `recovery` state (`attempts`, `successes`, copied `last_fault`);
  - added locked serial-fault freezing before connection-local parser state is cleared;
  - changed the existing single reader into a same-port close/reopen loop with dual monotonic progress timers, exact 2.0 s silence eligibility, and 5.0 s automatic-attempt start spacing;
  - made the 0.2 s startup delay cancelable;
  - preserved parser resync totals, diagnostics, frame epoch, established projector baseline, partial initial/manual tare acquisition, axes/history, and intentional tare state;
  - counted recovery only after new valid data makes the source live, at most once per automatic attempt.
- Added `tests/test_serial_recovery.py` with bounded fake serial, fake monotonic/wall clock, and cancelable fake event waits. It validates only `TEST_ONLY`, baud 115200, timeout 0.1 and never opens hardware.
- Modified `tests/test_serial_diagnostics.py` only to add the explicit `close()` supported by the real reader cleanup and to account for the new frozen host fault timestamp. Existing diagnostics values/schema assertions were retained.
- Added this report.
- No UI, firmware, profile, calibration, `START_DEMO.bat`, IMU, or service-control files were edited.

## TDD RED evidence

Production code was unchanged when this command was first run:

```powershell
& 'D:\conda\python.exe' -m unittest discover -s tests -p 'test_serial_recovery.py' -v
```

Actual result:

```text
Ran 9 tests in 0.068s
FAILED (failures=5, errors=8)
```

Expected missing-behavior failures were observed:

- `KeyError: 'recovery'` for the absent additive recovery snapshot;
- only one `TEST_ONLY` open at the exact 2.0 s silence boundary;
- startup cancellation still sent `s` because the old delay used `time.sleep`;
- initial/manual tare and established baseline continuity failed because every open called `request_tare()`;
- incomplete acquisitions therefore did not become live across reconnect.

There were no real COM accesses, service operations, device commands, or unbounded hangs. After the initial RED, additional required edge assertions were added before final handoff (repeated silence spacing, automatic-start cancellation, cooldown manual tare, silence pending/resync capture, and incomplete-tare success gating) and exercised against the implementation.

## GREEN evidence

Final requested focused commands:

```powershell
& 'D:\conda\python.exe' -m unittest discover -s tests -p 'test_serial_recovery.py' -v
& 'D:\conda\python.exe' -m unittest discover -s tests -p 'test_serial_diagnostics.py' -v
& 'D:\conda\python.exe' -m unittest discover -s tests -p 'test_demo_core.py' -v
```

Actual results:

```text
test_serial_recovery.py: Ran 13 tests in 0.089s — OK
test_serial_diagnostics.py: Ran 5 tests in 0.005s — OK
test_demo_core.py: Ran 11 tests in 0.184s — OK
```

Final syntax check also exited 0 with no output:

```powershell
& 'D:\conda\python.exe' -m py_compile coinft_demo.py tests\test_serial_recovery.py tests\test_serial_diagnostics.py
```

An earlier GREEN iteration produced 12/13 recovery passes because the held-load test expected a nonzero 50-frame median-smoothed axis after only three recovered frames. The test was corrected to provide 30 recovered load frames; raw held-load channels and the established baseline remained the behavior under test. One diagnostic compatibility iteration also confirmed that primary-fault connections should close without an extra cleanup `i`, preserving the existing exact command assertion; normal orderly stop/startup cancellation retains best-effort `i`.

## Coverage and self-review

- Silence is ineligible at 1.999 s and eligible at the exact 2.0 s boundary; a timestamp assertion proves the reopen did not start early.
- Raw-byte and parsed-frame monotonic progress are independent. Constant valid frames, sustained batches, saturation, invalid frames, and continuous garbage do not invoke silence recovery.
- Every fake open is the same `TEST_ONLY` port and validates 115200/0.1. Commands are limited to the original `i`, cancelable 0.2 s wait, input reset, `s`, plus allowed orderly-stop `i`; no `t`, reset, tuning, alternate port, thread, or writer was added.
- Repeated silent attempts and failed opens have at least 5.0 s start-to-start spacing. The initial open is excluded from `attempts`.
- Stop during initial or automatic startup prevents reset/`s`; stop during cooldown prevents a later open. Open/read/start-write faults remain in `last_fault` and retry through the same cadence.
- Fault capture occurs before parser-buffer clear and freezes wall observation time, frame count, and a diagnostics copy including pending/discard totals. Parser resync and cumulative diagnostic/frame counters remain monotonic across reconnect.
- Established baselines and nonzero held-load channels survive recovery. Initial 400-frame and explicit manual-tare acquisitions both continue across reconnect; a manual tare requested during cooldown is retained.
- Open, successful writes, cached state, invalid data, and incomplete tare do not count as success. Multiple valid frames in one recovered attempt still increment success once.
- Recovery and nested fault diagnostics returned by `snapshot()` are copy-isolated.
- Cleanup close failures cannot replace a previously frozen primary read/open/write/silence fault.

## Concerns and stop condition

- These tests establish deterministic PC software policy only. They do not prove that close/reopen plus `i/s` will recover the next physical CoinFT/Teensy stall or repair its hardware/protocol root cause.
- The running service was not restarted, no actual COM port was opened, and no hardware fault was induced. Operator-controlled deployment and same-process/same-baseline hardware acceptance remain pending under the approved design.
- Full UI/full-suite regression and protected-file hash comparison are controller-owned and were not run in this task, per the task brief.
- This project has no Git repository; no commit/worktree was created.

Stop condition reached: requested implementation is complete, production and test files compile through the executed unittest imports, and all three required focused suites pass with fresh evidence.

## Independent-review fix: automatic-attempt cancellation boundary

Date: 2026-09-28

Result: **DONE** - `recovery.attempts` is now incremented only when the adjacent automatic `serial.Serial(...)` construction is actually reached. The existing 5.0 s automatic-attempt spacing and cancellation guards are unchanged.

### Files changed

- `coinft_demo.py` - moved the automatic-attempt timestamp and counter update below the final stop guard, immediately before `serial.Serial(...)`.
- `tests/test_serial_recovery.py` - added a bounded fake-monotonic cancellation hook and a regression for a stop arriving during automatic-attempt timestamp assignment after an initial open failure.
- `.superpowers/sdd/stream-recovery-task-1-report.md` - appended this RED/GREEN fix record.

No UI, firmware, profile, batch, IMU, live COM, service-control, or Git operation was performed. `tests/test_serial_diagnostics.py` and `tests/test_demo_core.py` were not edited.

### RED evidence

Command run before the production change:

```powershell
& 'D:\conda\python.exe' -m unittest discover -s tests -p 'test_serial_recovery.py' -v
```

Actual relevant output:

```text
test_stop_at_automatic_open_boundary_counts_only_an_attempted_open ... FAIL

AssertionError: 1 != 0

Ran 14 tests in 0.090s
FAILED (failures=1)
```

The other 13 recovery tests passed. The failure reproduced the review finding exactly: the initial open was the only actual serial construction (`automatic_opens=0`), but the recovery state recorded one automatic attempt (`attempts=1`).

### GREEN evidence

Commands run after the production change and final test assertion review:

```powershell
& 'D:\conda\python.exe' -m unittest discover -s tests -p 'test_serial_recovery.py' -v
& 'D:\conda\python.exe' -m unittest discover -s tests -p 'test_serial_diagnostics.py' -v
& 'D:\conda\python.exe' -m unittest discover -s tests -p 'test_demo_core.py' -v
& 'D:\conda\python.exe' -m py_compile coinft_demo.py tests\test_serial_recovery.py
```

Actual output:

```text
test_serial_recovery.py: Ran 14 tests in 0.121s - OK
test_serial_diagnostics.py: Ran 5 tests in 0.007s - OK
test_demo_core.py: Ran 11 tests in 0.271s - OK
py_compile: exit 0, no output
```

The new regression explicitly proves the stop callback fired on the first monotonic timestamp assignment, one automatic serial construction then occurred, and `recovery.attempts == automatic_opens == 1`. Existing failed-open and repeated-silence tests continue to prove at least 5.0 s start-to-start spacing.

Concern unchanged: deterministic fake-serial tests establish PC recovery bookkeeping policy only; physical recovery acceptance remains pending and was not exercised by this fix.

### Controller whole-change evidence qualification

Final code/spec reviewer APPROVE. The statement that a close failure cannot replace a preceding primary fault is based on static inspection of the primary_fault guard, not an executed compound-error test: FakeSerial.close never raises. No dynamically tested close-failure claim is made. Final controller full regression after the fix:124 tests in68.249s, exit0;14 protected files unchanged. Actual hardware/service acceptance still pending.
