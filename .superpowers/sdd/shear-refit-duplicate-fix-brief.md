# Approved bounded healthy-duplicate acquisition correction

User explicitly approved this change and asks to finish promptly.
Requirements: retain all HTTP states; healthy exact repeated frame is not a new
sample and not itself a fault. All real quality/owner/timeout gates stay fixed.

Ownership ONLY:
- calibration/capture_demo_pose.py
- .superpowers/sdd/shear-refit-capture-command.py
- tests/test_capture_valid_span.py
- tests/test_refit_capture_command.py
- .superpowers/sdd/shear-refit-duplicate-fix-report.md

**Resolved legacy-test conflict:** explicit approved duplicate policy supersedes
tests/test_demo_profile.py::CaptureTests.test_rejects_duplicate_frame_without_skipping_it.
Extend ownership solely to that one method: rename to regression rejection, use
states[8]=state(7) (after previous frame8), assert previous=8/current=7 rejection.
All other profile tests/fixtures untouched. Positive healthy-duplicate behavior
is tested in the new capture/command cases. Run all22 profile tests and the3
qualitative profile tests, then one full suite; no additional approval needed
for this directly related expectation update.

Implementation guidance (keep surgical, no new framework/CLI/dependency):

1. Keep valid_state/invalid_reasons public behavior strict. After on_state,
   capture can recognize duplicate only when previous_frame>=0, incoming frame
   exactly equals it, and all OTHER existing validation passes (e.g. validating
   against previous_frame-1). Malformed/status/recent-invalid/nonfinite data must
   still reject; regression must still reject. Do not append/count duplicates;
   still run normal pacing/deadline logic, not busy-loop continue.
2. Optional minimum_samples=None on capture, solely for fitting command40.
   Default None preserves original completion timing/30-floor/errors, including
   too-few-count tests. Non-None must be integer>=30 (not bool). With40, success
   waits for BOTH host/monotonic>=5s spans AND >=40 accepted samples, still under
   the original6s admission/1.5s request budgets. No count/timeout weakening.
3. Command calls capture(...,5.0,0.125,on_state=observe,minimum_samples=40).
   In observe preserve every state BEFORE checking. Always retain original
   port/mode/tare/cumulative/recovery/parser checks. Byte/parsed counter regression
   always rejects; unchanged counters may be tolerated only when frame exactly
   repeats previous observation; fresh frames still require both advance.
4. Preserve original return/sample/evidence schemas, exclusive writes and unsafe
   observer/late HTTP isolation; no backend, serial, firmware, profile or UI edit.

TDD required, focused RED before source; GREEN covering:
- healthy duplicate omitted from samples but every observation retained;
- invalid duplicated state and decreasing frame still immediately abort;
- unchanged frame forever hits existing deadline, no further request after;
- requested40 snapshots may require >5s but complete within original deadline;
  if40 cannot be obtained, fail, never duplicate/interpolate timestamps/samples;
- generic existing30 policy/too-few error unchanged; bad minimum rejects pre-HTTP;
- full exact command duplicate paths: multiple cached states are preserved and
  excluded, complete40/5s still succeeds; real diagnostics regression rejects,
  and existing unsafe cases remain covered.

Reuse existing fully mocked Task1 fixture helpers where sensible; extend them
minimally for duplicate behavior without copying capture implementation. No real
HTTP/serial/psutil probe/hardware/service actions. Do not edit unrelated tests.
Run focused command/capture/profile tests while iterating; full unittest once
after final edits (root may independently verify focused rather than duplicate
full run). D:/conda/python.exe. Preserve all failed real evidence.

Report exact RED/GREEN/full commands+outputs, files/hashes, selfreview/limits;
return only DONE/etc, concise tests/concerns/report path. No Git repository/actions.
Physical capture remains controller-owned after independent review.
