# Root verification and first fitting attempt

2026-09-28. Task3 preparation independently approved; physical fitting not complete.

- Fresh final command: D:/conda/python.exe -m unittest discover -s tests -v.
- Result: 148 tests in 82.151s, OK, exit0. The previous browser timeout is retained
  in the preparation report; this passing run does not establish its root cause.
- After tests/capture, all14 protected files and backend remained unchanged.
- No firmware, UI, profile, serial parameters, service control, tare or zero changes.

User explicitly confirmed empty. Controller announced start, executed the exact
reviewed one-pose command, then first notified stop/no force before parsing.
Tool wall6.995s/exit1; seven complete observations, actual first-last0.5607492s.
Failure: byte/frame observation not advancing. Full failed evidence preserved at
calibration/shear_refit_20260928/fit/press_before.failed.json; never fitting input.

Across first six snapshots frame1640059->1640168 and byte/parsed counters advanced.
The seventh repeated frame1640168 and identical byte/parsed/read counters, still
live. Serial read completion timestamps preceding it were spaced about108-111ms;
the configured HTTP interval is100ms, while the unchanged backend uses
serial.Serial timeout0.1 and read4096, publishing completed batches. Thus ordinary
batch/poll cadence aliasing is supported; this short evidence does not prove a
device stall. Separate four-state diagnostic read below confirms continued live
frame/byte progress, unchanged invalid62 and recovery3/2; not fitting evidence.

Proposed narrow plan amendment: HTTP observation interval0.125s instead of0.1s.
Keep5s actual valid sample span, >=40 increasing snapshots, true request timeout,
all owner/quality/replay gates. No protected backend/firmware change. Not applied;
await operator choice before changing the mandated plan parameter/retrying.
