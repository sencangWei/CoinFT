# Mid-demo baseline loss diagnosis — 2026-09-26

Scope: user asked why display stops and requires zero; diagnosis only, no production fix authorized or applied. Used systematic-debugging; read actual front/back-end and read-only live HTTP checks, no serial/tare.

## Established mechanism

- app.js updateStatus computes good = live AND invalid_recent===0 AND saturated_recent===0; otherwise calls invalidateDemoZero. This permanently sets demoBaseline=null, clears zero samples and shape. Returning to healthy live state does not restore the old baseline.
- poll's invalid data/regressed/status/HTTP handling and independent >=500ms new-accepted-frame watchdog also invalidate baseline. A silent stalled page request can thus require zero even if service later recovers.
- Backend rejects any raw value >33782 and publishes invalid_recent as a rolling two-second count; one rejected frame leaves the historical window nonzero for up to two seconds, so subsequent good snapshots can still invalidate the grid.
- Fresh existing synthetic browser test test_qualitative_baseline_invalidates_on_stream_faults_and_tare PASSED (1 test,2.574s), explicitly demonstrating even invalid_recent=1 or saturated_recent=1 clears ready baseline. No live hardware used by test.

## Actual live evidence and uncertainty

Controlled visible page exec1341 probe: frame22225552, baseline=null, normal/shear targets and levels0, normal status, no JS errors. Thus current page is already disarmed despite healthy service; trigger-time browser trace is unavailable.

Backend cumulative invalid count133 vs112 in previous live screenshot, proving new rejected frames occurred between inspections, but NOT proving which exact event cleared this page. Brief stats cannot distinguish malformed frame origin (transport/electrical/other).

Read-only30-second HTTP recording:484 samples, frame22235079→22241057 (+5978), all live/200Hz, invalid_recent0, saturated_recent0, resyncs0, invalid_frames remains133, max HTTP127.4ms. No fresh failure occurred within this observation window. Immediate failure timing/root of occasional raw rejection was not captured; cannot rule out earlier500ms stall, saturation, or HTTP error.

## Recommendation requiring approval

For qualitative demonstrations, separate temporary motion suppression from baseline invalidation: short bad-data interruptions should pause/clear unsafe motion but preserve known baseline, recover only on valid healthy data; actual reconnect/new tare/regressed epoch must invalidate to prevent mixing offsets. No automatically learned baseline under load. Exact recovery/duration contracts need user approval and regression tests before implementation. Strict validation mode must not be silently relaxed.

No app.js/surface.js/backend/profile changes, no zero/restart/firmware action. Diagnostic script diagnose_demo_drop_20260926.py only GETs current service.
