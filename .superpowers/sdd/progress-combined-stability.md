# Combined stability progress

## Latest status: implementation and offline acceptance COMPLETE; physical acceptance pending

- User-approved display-input limit now precedes the qualitative-only 180 ms EMA, same-sign hysteresis and modest display gain. Strict/normal paths, geometry, trends, backend, profile and firmware remain unchanged.
- Extreme-input RED reproduced before the amendment; focused stability 9 + geometry 7 tests passed. Root freshly ran full suite: 81 tests, 62.587 seconds, OK, exit 0. Task and final reviews both approved with no outstanding blockers.
- Actual captured 45-snapshot Chromium replay: zero targets 24 -> 15; total variation 10.410640929680575 -> 6.240847099088214 (40.05% reduction); all normal targets stay 1. This is offline evidence, not fresh physical acceptance.
- Visible live Edge session 38434 reloaded; frame 22961934, data normal, baseline null, no JS errors. No automatic demo zero or device tare. Served and local surface.js SHA256 match: D7AD21EFD772367E0A63A9B1FCEAC466DA481ECE2ABCC185505E1A63EE1FEDBF.
- Next operator step: completely unload and click demo zero once, then test combined press/shear. Prepare measurement before requesting any held action. Previous stored baseline/capture command must not be reused after this reload.

## Historical progress (superseded by latest status above)

- Task1 implementation DONE but acceptance PENDING USER DESIGN RESOLUTION; focused13PASS, workerfull79/62.617s exit0. ActualChromiumreplay zero24→15/45, totalvariation10.41064→6.72994, normal45/45=1. Root has not freshly rerun full because important design ambiguity remains. No deployment.
- Actual capture combined_press_minusx_retry_20260926.json valid5.09s,45distinct snapshots, normal1all, shear24zeros; previous late capture invalid for stable-load claims.
- Existing live Edge38434, baseline already established by user. Reload only after reviewed tests; no automatic pagezero/device tare.
- Task review Spec❌/Needsfixes: exact unbounded signed-score EMA conflicts with universal600ms release after any saturated input. Score10000 at threshold100/span200 leaves target1 after600ms zero; finalreview treats nominal230 guarantee as qualifier but root will not silently narrow. User must choose display input limiting before smoothing (recommended to avoid hidden overrange memory) or preserve unbounded score and accept long tails. Source presently unbounded180msEMA; do not change until resolution. Drawing/trends/backend/template/firmware remain untouched.
- Minor review items: exact irregular-time/zero-delta EMA assertion; existing client-close ConnectionAbortedError test-server log on workerfull. No old animation assertions relaxed.
- 2026-09-26 Operator explicitly approved display-input limiter before EMA to remove overrange memory. Brief/spec amended to bound +/-max(threshold,.6threshold+.85span) qual-only;600ms tested for currentreal + synthetictestprofiles, not arbitrary pathological ratios. Implementer to add extreme-score RED then fix, focused/fulltests, amended replay and report/diff. Prior unbounded implementation must not deploy.
