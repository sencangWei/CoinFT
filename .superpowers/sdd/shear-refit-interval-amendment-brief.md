# Approved mechanical capture interval correction

User approved0.125s HTTP observation cadence and asks to proceed quickly.
No backend/firmware/serial parameter/profile/UI changes.

Ownership: only .superpowers/sdd/shear-refit-capture-command.py and
tests/test_refit_capture_command.py, plus interval amendment report.

- Change command capture interval0.1 to0.125. It must match updated Task3 brief.
- Reuse existing Task1 success/unsafe fixtures exactly as before. In the command
  test, select every25th dense0.004s fixture state instead of every20th, preserving
  mock200Hz at0.125s. Update the success count requirement51 to40, retaining full
  output/every-observation checks and actual5s-span checks.
- The equal-previous parsed_frames mutation must track the new third core frame
  (51 rather than41); preserve all remaining unsafe cases/quality gates.
- Add an explicit assertion that exactly41 successful observations were read,
  so the amended command cadence is tested, not only its unchanged minimum.
- RED run focused test after test amendment but before command change; GREEN
  run same focused test after command change. No full-suite rerun or live capture.
- Report command/output/hashes/changed lines/self-review at
  .superpowers/sdd/shear-refit-interval-amendment-report.md.

Physical acquisition is controller-owned after review. Preserve original failed
evidence, no automatic next pose, no extra refactors/dependencies/Git actions.
