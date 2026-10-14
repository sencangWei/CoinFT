# Local drag task 1 report — 2026-09-26

Status: DONE / GREEN. Exact approved drawing formula implemented. Operator explicitly replied `保留`, approving original pressure preservation and material-space nonfolding/nonintersection acceptance. Original RED/conflict evidence below is retained as history and superseded by the approved amendment; focused7/7 and full72/72 pass.

## Scope and self-review

Changed only draw's point calculation and four-corner intensity in `demo_web/surface.js`. Added `tests/test_surface_drag.py` and this report, diagnostic script and five local-drag screenshots. Preserved normal/shear processing, all API members, smoothing, clear, resize and reduced-motion handling. No edits to app.js, index.html, style.css, profiles, acquisition or firmware. No live COM10/8765 operations, Git initialization, commits or worktrees. Existing tests use isolated fake HTTP servers; their `/api/tare` logs do not refer to live hardware.

Tests intercept real Chromium Canvas methods while forwarding calls to the actual drawing context; production has no test-only API. Material diagnostics reconstruct coordinates from captured Canvas vertices by removing the documented height and inverting projection, rather than testing a separate displacement formula alone.

## Commands and observed output

Working directory: `D:\semg.claude\coinft`.

1. Baseline: `D:\conda\python.exe -m unittest tests.test_demo_ui.DashboardWarningTests.test_signed_surface_profile_and_safe_states -v`
   Output: `Ran 1 test in 2.131s`, `OK`.
2. RED before production edits: `D:\conda\python.exe -m unittest tests.test_surface_drag -v`
   Output: `Ran 6 tests in 1.350s`, `FAILED (failures=5)`.
   Meaningful failures: edge `[312,44.8]` differs from flat `[300,52]`; grid-line cross product exactly0 rather than >100; pure shear has1 color rather than >3; mirror y differs14.4; projected orientation product -6682.879865 at p1/s-1/cell155. Original pressure/resize test passes.
3. After exact formula: same focused command.
   Output: `Ran 6 tests in 1.398s`, `FAILED (failures=1)`.
   Fixed boundary/local displacement, bend, mirror, color/clear exact pixels, preserved original pressure/resize all pass. Remaining failure: `p=1,s=-1,cell=205,corners=(0,1,2)` signed-area product `-1003.6360760958094`.
4. Full regression: `D:\conda\python.exe -m unittest discover -s tests -q`
   Output: `Ran 71 tests in 55.319s`, `FAILED (failures=1)`.
   All65 pre-existing tests pass;5/6 new tests pass. Only failure is the new conflicting projected-orientation condition. Existing pixel-direction assertions were not changed.
5. Evidence: `D:\conda\python.exe .superpowers/sdd/local-drag-diagnostics.py`
   Exit0. Random isolated HTTP port31935 first run,14354 final run. Replay fake source and visible banner `模拟验收，非实时设备 · SYNTHETIC LOCAL DRAG`. Outputs `local-drag-right.png`, `local-drag-left.png`, `local-drag-normal.png`, `local-drag-combined.png`, `local-drag-clear.png` here. Screenshot input uses synthetic profile and channels, never actual hardware. Root visually reviewed right and combined; review confirmed visible nonlinear local drag and shifted combined dent.

## Geometry conflict evidence

648 projected triangles per state:

|p|s|negative projected areas|min projected area|max projected area|min material area|material crossings|
|---|---|---|---|---|---|---|
|0|-1|0|12.2103838|289.197116|0.00105334574|0|
|0|0|0|143.111111|143.111111|0.0123456790|0|
|0|1|0|12.2103838|289.197116|0.00105334574|0|
|1|-1|58|-141.683195|291.556359|0.00105334574|0|
|1|0|50|-169.374012|455.596235|0.0123456790|0|
|1|1|58|-141.683195|291.556359|0.00105334574|0|

Pressure-only must preserve the original Gaussian height/amplitude, which produces50 reversed *projected* triangles even without shear. Therefore preserving that normal-only shape and requiring every projected triangle to match the flat orientation cannot both hold. Positive material areas and zero nonadjacent segment crossings show that this projection condition is distinct from material folding. Diagnostic examines both triangles of all324 cells and every nonadjacent pair among684 material grid segments (strict proper crossings with1e-12 tolerance).

## Limitations and log noise

At the initial check this was not GREEN pending operator resolution; the approved amendment and final validation follow below. No live refresh or zero performed by this worker; root owns live window, operator must confirm unloaded and click visual zero. Qualitative illustration only, not calibrated force/contact reconstruction.

Browser HTTP tests print ordinary request logs, expected missing-profile404s, fake `/api/tare` requests and one existing `/null`404. No browser runtime error was observed in evidence generation. An initial read attempted nonexistent `tests/test_surface_signed.py`; actual baseline test was located in `tests/test_demo_ui.py` and passed as above.

## Operator-approved amendment and GREEN

Operator answer `保留` explicitly authorizes retaining the original pressure dent and checking material-space topology instead of requiring every projected triangle to keep flat orientation. Main amended spec/plan/brief. Production drawing formulas remained unchanged during this amendment.

Replaced only the conflicting test criterion with all648 reconstructed material triangle areas positive and zero intersections among nonadjacent grid segments for each p=0/1,s=-1/0/1 state. Shared test/diagnostic helper removes documented height from actual captured Canvas vertices and inverts the camera; it checks proper crossings plus collinear contact/overlap, excluding adjacency by material vertex identity. Tolerance1e-12 applies to intersection predicates.

Test-side mutation evidence: moving reconstructed real captured center vertex `(9,9)` onto vertex `(11,9)` produces minimum signed area `-0.012345679012345696` and19 nonadjacent intersections. The new mutation regression asserts both detectors reject this distorted mesh. No production mutation was performed.

Focused command: `D:\conda\python.exe -m unittest tests.test_surface_drag -v`.
Output: `Ran 7 tests in 3.500s`, `OK`. Includes all-six-state geometry checks and mutation detector check.

Full command after approved amendment (run once): `D:\conda\python.exe -m unittest discover -s tests -q`.
Output: `Ran 72 tests in 57.208s`, `OK`, exit0. All65 existing tests and7 new tests pass. Same expected fake HTTP request/404 log noise described above; no test failures.

Remaining limitations: pressure can create overlapping screen projection (50 pressure-only and58 combined reversed projected triangles), which is accepted as a view/height effect; material geometry does not fold/intersect. Illustration remains qualitative. Root reviewed all five synthetic screenshots and owns final live page handling.
