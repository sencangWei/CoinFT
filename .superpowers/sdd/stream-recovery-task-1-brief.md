# Task brief

Read approved spec: docs/superpowers/specs/2026-09-28-coinft-stream-recovery-design.md. Its full constraints bind this task.

### Task 1: Preserve-baseline single-reader recovery and deterministic tests

Files:
- Modify: coinft_demo.py (DemoSource.__init__, snapshot, _run_serial and a small fault-record helper if needed).
- Create: tests/test_serial_recovery.py.
- Modify tests/test_serial_diagnostics.py only if the old fake wait/clock fixture or new fault timestamps require legitimate accommodation; retain its exact existing diagnostics expectations.
- Report: .superpowers/sdd/stream-recovery-task-1-report.md.

Read the approved spec first. This task is the entire production implementation; no UI or firmware changes.

- [ ] RED: Write deterministic tests driving the real _run_serial, FrameParser and _consume via fake pyserial and time. Do not mock the behavior being tested. Fail before changing production.
- [ ] Fake transport validates TEST_ONLY port, baud 115200, timeout 0.1, records open/close/reset/write/read timestamps. Clock advances on read/wait; Event wait remains cancelable and no real sleeps. Bound tests so a regression cannot hang indefinitely.
- [ ] Cover silence at just below/exact 2 seconds; newly parsed frames and nonempty chunks refresh independent monotonic progress. Validate no extra commands for constant valid frames, sustained load, saturation, invalid frames or continuous garbage.
- [ ] Cover silent recovery command/order and only same-port ownership. Startup remains i, wait 0.2, input reset, s. Final best-effort i is allowed but no t/tuning/reset commands.
- [ ] Cover repeated silent/failed-open attempts and start-to-start intervals at least 5 seconds; initial open excluded. OS read/open/write exceptions remain visible and retry with bounded spacing.
- [ ] Cover stopping during startup and retry cooldown: no later s/open; handles close. Record failed-cleanup behavior as needed without swallowing primary fault.
- [ ] Cover established baseline identity/value preservation and nonzero held-load channels after valid recovery. Preserve monotonically increasing frames, resyncs/discard/byte/parsed counts and observation timestamps. Capture old pending bytes before clear.
- [ ] Cover initial400 valid-frame acquisition split across reconnect and explicit manual tare split across reconnect; no automatic request_tare and no successful recovery before pending acquisition becomes live. Invalid recovered frames/open/write/cached snapshots are not successes.
- [ ] Cover recovery snapshot isolation including nested last_fault diagnostics, and at most one success per automatic attempt.
- [ ] Run RED command and record actual failures and reasons in report:
  `& 'D:\conda\python.exe' -m unittest discover -s tests -p 'test_serial_recovery.py' -v`.
- [ ] GREEN: Add separate recovery state in DemoSource and isolate it in snapshot. A small fault helper locks, freezes reason/time/frame/diagnostics, and never clears history.
- [ ] Track whether this is an automatic reopen and previous automatic attempt start. Before each automatic open, wait only the required remaining cooldown using stop_event.wait; guard open and s after cancellation. Increment attempts at automatic open start even if it fails.
- [ ] On open, clear only parser.buffer (retain parser.resyncs), set pending count0/reset rate window. Set waiting until new data rather than reuse live cached state. Preserve projector baseline, tare_frames/tare_requested and current axes/history.
- [ ] Replace noninterruptible time.sleep(0.2) with stop_event.wait(0.2), checking cancellation before buffer reset/start. Existing normal startup command protocol remains.
- [ ] Initialize last raw/frame monotonic progress after s. Update diagnostics exactly as before on each successful read; consume each newly parsed frame. Use valid raw plus live source status to count one pending attempt success, not cached live after invalid input.
- [ ] When both progress timers reach 2 seconds, capture fault, expose waiting, close old connection, then schedule same-port recovery. Keep existing frame-wait reporting for corrupt/partial traffic without falsely triggering silence recovery.
- [ ] On serial OS errors capture the fault before clearing pending parser state, expose error and schedule recovery with the same cooldown. Best-effort idle/close must not mask the original fault.
- [ ] Preserve explicit tare request semantics during cooldown/reconnect. Do not change replay logic or defaults outside task scope.
- [ ] Run GREEN focused commands:
  `& 'D:\conda\python.exe' -m unittest discover -s tests -p 'test_serial_recovery.py' -v`
  `& 'D:\conda\python.exe' -m unittest discover -s tests -p 'test_serial_diagnostics.py' -v`
  `& 'D:\conda\python.exe' -m unittest discover -s tests -p 'test_demo_core.py' -v`
- [ ] Self-review edge cases, shutdown ownership, tests' meaningful assertions and scope. Full report carries RED/GREEN commands, relevant outputs, exact files, result/concerns. No Git commit.


