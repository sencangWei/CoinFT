# Task 1: Qualitative animation transient auto-recovery

User approved transient auto recovery on 2026-09-26: a mid-demo interruption must not require repeated page zero. Diagnosis is in demo-drop-diagnosis-20260926.md. This is an intentional change to the old qualitative fault-invalidates-baseline contract.

## Ownership and global constraints

- Modify only demo_web/app.js and tests/test_demo_ui.py (a small separate new recovery test file is allowed if clearer). Do not change surface.js, templates, firmware, backend, thresholds, trends layout, or existing shear/pressure geometry.
- Completed qualitative demo baseline survives temporary invalid_recent/saturated_recent, malformed channels, waiting/error, HTTP failures/timeouts, and the 500 ms watchdog. Motion clears promptly on the fault; label shows paused/auto-recovery waiting. Resume only on a new healthy, finite 12-channel frame with zero recent-invalid/saturated counts. Reuse exactly the previous baseline, not a newly estimated one. Never automatic POST tare or auto-zero.
- Partial zero collection must still abort on faults and cannot automatically resume. The initial zero still requires at least 10 distinct valid frames spanning at least 1000 ms from the FIRST valid sample.
- Explicit device tare, status taring, or frame regression invalidate the baseline; require explicit page zero after genuine offset changes. Preserve a monotonic frame high-water across temporary clearDisplay/HTTP failures so stale/regressed frames cannot restore motion. A server restart invalidates and can establish a fresh frame epoch while disarmed, permitting a later explicit zero.
- Strict profile mode keeps its previous fault rules. Qualitative fallback only for strict profile HTTP 404 remains unchanged. Normal repeated snapshots are skipped, not counted as fresh; they do not postpone the watchdog.
- Existing tare generation/race protections stay intact. Disconnection is not displayed as successful measurement; paused grid is flat, never frozen at the previous loaded deformation.
- Do not operate live hardware or the live port 8765. Tests use isolated HTTP servers/Chromium. This is NOT a Git repository: no init/commit/worktree; use Copy-Item before snapshots and a no-index diff artifact.

## Steps / acceptance

1. Read app.js and relevant browser tests; capture pre-edit snapshots under .superpowers/sdd/auto-recovery-before-*. Write tests FIRST and run focused tests to prove RED before production editing.
2. Implement the smallest pause-versus-invalidate split. A ready baseline is preserved on transient failures, but a pending collection is cancelled. Track pause label consistently; valid newer frames restore motion without any zero click. Do not lose epoch detection when displays clear.
3. Revise old contract tests explicitly, not by deleting safeguards. Tests must cover nonzero retained baseline under load, invalid/saturation recovery, malformed-channel recovery, HTTP/stall recovery, same-frame non-recovery, regression after HTTP failure, status taring/explicit tare invalidation, pending-zero abort, and ordinary duplicate handling. Assert no automatic tare requests and no baseline recomputation. Existing strict tests must remain passing.
4. Run D:\conda\python.exe -m unittest tests.test_demo_ui -v, then D:\conda\python.exe -m unittest discover -s tests -q once. Self-review surgical scope and lifecycle guards.
5. Write .superpowers/sdd/auto-recovery-task-1-report.md with RED/GREEN command+outputs, files changed, tests and any concerns. Generate a review-package text file using before snapshots and diffs (apply_patch or a normal evidence-generation script; no shell writes to source). Return only status, one-line results, report path, concerns.

Stop at DONE only when tests prove fault -> flat pause -> valid new frame -> loaded animation restored using unchanged baseline, plus hard-offset events remain disarmed. Real hardware fault reproduction is separate from synthetic automated acceptance.
