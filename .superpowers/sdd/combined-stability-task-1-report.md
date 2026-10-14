# Combined stability implementation report

Scope: demo_web/surface.js signal computation, new tests/test_surface_stability.py, one geometry harness line in tests/test_surface_drag.py. No app/backend/profile/geometry formulas/colors/layout edits. No hardware/live-port operations, deployment, git initialization or commits. Before snapshot: surface.before-combined-stability.js. Review package: combined-stability-review-package.txt (full-context no-index source diff and new test source).

Qualitative targets use per-instance signed-score EMA with tau180ms, alpha=1-exp(-max(0, elapsedMs)/180), first valid score initialized directly. Start threshold remains original threshold; continuation is0.6*threshold for the same sign only; reverse requires original threshold. Active amplitude sign*clamp((abs(filtered)-0.6*threshold)/(0.85*span),0,1). Clear, invalid input/profile, disabled shear, profile identity and mode change reset state. Drawing/normal arithmetic unchanged. shearLevel helper retains original qualitative/strict formulas including strict active0.7 gate; weighted score validation/computation extracted once.

TDD RED command: D:\conda\python.exe -m unittest discover -s tests -p test_surface_stability.py -q. Against snapshot code: 5 tests,3 expected failures:120 score produced0.1 rather than60/170;230 produced0.65 rather than1;120→80 dropped to0 rather than continuing. No syntax/setup errors. The other lifecycle/strict tests passed as expected.

Focused GREEN before final additions: same command6 tests OK (1.008s); geometry command -p test_surface_drag.py7 tests OK (3.446s). All old mirror/material/pixel assertions preserved; only clear() before each independent pose isolates temporal history. Sequential reversal/continuation covered separately in new tests. Final suite outcome recorded below.

Actual Chromium deterministic-clock replay reads combined_press_minusx_retry_20260926.json, subtracts its stored baseline from channels, uses demo_web/shear_demo_profile.json and sample.elapsed*1000. Old helper zeros24/45; new targets zeros15/45. Total variation sum(abs(target[i]-target[i-1]))10.410640929680575→6.729936486137544 (35.36% reduction). Normal targets45/45 exactly1. Synthetic alternating120/80 at100ms checks fewer than24 zero windows and lower temporal variation; exact first target60/170 and second filtered(80+40exp(-100/180)-60)/170 asserted. Lifecycle tests cover below-start neutral combined press, continued80, reverse80 blocked, release and reversal within six100ms updates, clipping, clear/fault/disabled/identity/mode/normal profile invalid resets, pure press/shear, strict behavior, per-instance isolation, motion preference.

Limitations: replay is qualitative rendering evidence, not calibrated force/reconstruction or proof of physical combined-axis validity. EMA only advances on valid set() updates; no timer/poll fake input. No live operator verification yet. A saturated target caused by an arbitrarily huge unbounded raw score can require longer release than the tested full-scale input230 (threshold100/span200); EMA follows signed score per contract, without hidden score clipping.

Full suite: D:\conda\python.exe -m unittest discover -s tests -q, direct command, exit0;79 tests in62.617s, OK. Existing72 tests plus7 new. Expected test-server HTTP404/profile/access logs present; one client-close ConnectionAbortedError in test-server request thread did not fail unittest. No old animation assertion changes or failures.

## Approved limiter amendment

User approved display-only overrange bound before EMA. Qualitative input now clamps to +/-max(threshold,0.6*threshold+0.85*span). Shared raw projection, helpers, strict mode and raw channels remain unchanged. This supersedes the unbounded-overrange limitation above for current real template and threshold100/span200 synthetic fixture; no600ms guarantee for arbitrary pathological threshold/span ratios.

New TDD RED (same focused command):9 tests,3 expected failures before limiter: synthetic AND real-profile score10000 release stayed target1 after600ms; exact37ms post-overrange target1 vs expected0.7486165756497578. Strong reverse10000→-10000 tested for both profiles too (already passed before limiter). GREEN after two-line limiter:9 tests in1.276s OK; geometry7 tests in3.402s OK. Added exact zero-elapsed hold and37/211ms irregular EMA checks. Real profile extreme channels synthesized from centered real weights so projection is10000 with zero normal pressure, rather than replacing the real template.

Updated actual Chromium capture replay: zeros24/45→15/45; variation10.410640929680575→6.240847099088214 (~40.05% reduction); all45 normal targets1. No old test assertions changed.

Post-amendment full suite: D:\conda\python.exe -m unittest discover -s tests -q, direct command, exit0;81 tests in62.937s, OK (existing72 plus9 new). No old assertions altered and no failures. Source/tests frozen for independent review; no live deployment.
