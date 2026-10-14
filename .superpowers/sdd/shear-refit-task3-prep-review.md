# Task 3 preparation independent review

2026-09-28. Exact prepared command and preparation-only production scope comply.
Review verdict: Needs fixes; physical acquisition remains pending.

- Critical: none.
- Important: tests/test_refit_capture_command.py:36 constructs a separate core
  success fixture and :108 a separate unsafe table, rather than reusing Task 1
  successful/unsafe fixtures as required by the brief. Reuse while retaining the
  extra full diagnostic/recovery fields needed by this command.
- Minor: extend the unsafe variants with cumulative saturated/resyncs, recovery
  successes, and nonadvancing parsed_frames.
- Controller obligations: physical confirmation, release before analysis,
  complete persistence, cross-window chronology/epoch, fitting, independent real
  validation and installation are not proved by this preparation diff.

Reviewer read all four additions once; no test rerun or hardware/service action.
The reviewer's named unchanged-fixture check used a nonexistent
tests/test_capture_demo_pose.py path. Controller inspected the actual
tests/test_capture_valid_span.py helper: run_capture exposes successful/unsafe
states through its observer argument; there is no standalone state factory.
This permits fixture reuse without editing Task 1 source/tests.

Controller fresh checks on the reviewed snapshot: new focused six tests passed
in 0.112s, command/test hashes match report. The full-suite browser timeout was
then tested in isolation, and its unchanged test passed in 2.342s. That does
not erase the earlier 147/148 full run or establish the intermittent root cause.
No browser test/production source was changed.
