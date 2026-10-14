# Approved fix: ordinary duplicate HTTP snapshots

Operator approved on 2026-09-26: skip ordinary repeated snapshots without counting them as baseline samples; invalidate only when no accepted fresh frame for >=500 ms, or on bad/malformed/degraded/status failure, frame regression, HTTP failure, or device tare.

Evidence: `live_zero_20260926_153355.json` contains 139 HTTP snapshots with 73 adjacent duplicates, frame advance 1412, all live and zero recent invalid/saturation. Backend serial reads batch about 100 ms while UI polls 50 ms. Immediate duplicate invalidation prevents successful baseline capture and makes any ready baseline unusable.

Scope: ONLY `demo_web/app.js` and `tests/test_demo_ui.py`. No backend, firmware, thresholds/weights, raw/trend/group behavior, profile generation, or HTML/CSS changes. Strict-profile path unchanged.

Requirements:
- Healthy same-frame snapshots before 500 ms do not append samples, reset the first-sample timestamp, clear pending samples, invalidate a ready baseline, or refresh the last-fresh-frame timestamp.
- >=10 distinct increasing good frames spanning >=1 second from the first accepted sample are still required; ordinary duplicates may occur in between.
- >=500 ms without new accepted frames still clears pending/ready baseline and the grid, including when HTTP stalls; fresh data after invalidation requires explicit re-click.
- Bad channels/status/degraded, regressed frame numbers, HTTP failure, or device tare still invalidate immediately, even with same frame number.
- Reproduce before fixing with RED browser tests for 100 ms backend batches interleaved with 50 ms duplicate polls, during collection and after readiness; test duplicate no-count and true stalled response watchdog separately.
- Update obsolete duplicate-immediate-failure tests to the new operator-approved behavior. Run focused tests and full suite once, report exact red/green output.
- Do not restore or alter archived profile; root does that after code verification.
- Write report `.superpowers/sdd/zero-batching-fix-report.md`.

No Git repository, so no worktree/commit/init. Use apply_patch. You are not alone; preserve unrelated edits.
