# Recovery review and acceptance checklist

Approved source: docs/superpowers/specs/2026-09-28-coinft-stream-recovery-design.md.
Task requirements/report: stream-recovery-task-1-brief.md / stream-recovery-task-1-report.md.
Reviewers receive a normalized text no-index diff against saved before files; original byte hashes saved separately. No Git metadata/commit range.

## Spec and code gate

- Check dual monotonic progress tracking >=2.0 seconds, constant valid/saturated/invalid/garbage traffic not false silence.
- Check single same configured raw-port owner and i/wait0.2/reset/s only; no other port or device t/reset/tuning.
- Check >=5.0s start-to-start even on failed opens/repeated silence; cancel both startup/cooldown; no s/open after observed stop.
- Check established PC baseline + partial initial/manual tare preserved. No automatic request_tare, frame epoch/cumulative resync and diagnostic totals preserved.
- Check fault frozen before pending parser clear, reset only connection buffer/rate window. Snapshot last_fault diagnostics independent.
- Check new valid/live data needed for at-most-once success per automatic attempt; opening/writes/invalid/cached/tare-pending do not qualify.
- Check explicit manual tare while recovering still intentionally changes baseline only after400valid samples.
- Check meaningful assertions with actual reader/parser/consumer, advancing fake time, bounded transport, TEST_ONLYport; TDDRED before production.
- Check legitimate oldfixture accommodations, unchanged exactdiagnostics schema/counter assertions.

## Controller-only validation

- Existing UI test test_qualitative_baseline_recovers_on_transient_faults_and_invalidates_on_tare (tests/test_demo_ui.py:443) verifies waiting/error retain demoBaseline, unchanged frame cannot revive surface, new healthy frame restores it, taring/frame regression invalidates it, no API/tare requests. Full suite must pass unchanged.
- stream-recovery-protected-before.json holds14 protected source/build/UI/profile/matrix/batch/IMU files. Check exact currenthashes after implementation and report mismatches.
- Actual running service is NOT automatically reloaded by editing source. Operator manually restarts START_DEMO after softwarePASS, with sensor empty for initial400-frame startup acquisition.
- One deliberate demo zero after deployment/new process may be necessary; runtime automatic recovery must not request it.
- No realCOM opens/devicecommands/servicecontrol during unit/UI regression. Do not induce a physical livefault without specificoperatorapproval.
- Simulation PASS != actual hardware recovery PASS or permanent rootcause repair. Pending live acceptance needs newhostframes + UARTcounterprogress and same server/frame epoch/baseline.
