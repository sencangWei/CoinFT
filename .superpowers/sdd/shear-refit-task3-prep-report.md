# Task 3 preparation report — 2026-09-28

Status: DONE_WITH_CONCERNS. Preparation only; no physical evidence was acquired, no fitting/validation was performed, and Task 3 remains pending with the controller.

## Files

- `.superpowers/sdd/shear-refit-capture-command.py`: verbatim first Python block from the Task 3 brief, fixed to the first `press_before` fitting window. Compact stdout evidence only; no writes, new CLI, next-pose loop, POST or serial operation.
- `tests/test_refit_capture_command.py`: six mocked dry-run tests, invoking the real Task 1 capture implementation through runpy. HTTP URL opening, psutil ownership inputs, wall time, monotonic time, sleep and evidence existence checks are patched. No real capture service or devices were contacted by these tests.
- `calibration/shear_refit_20260928/fit/.keep` and `validation/.keep`: prepared evidence directories, each marker is one newline.
- This report. No other source/test/profile/firmware files edited; no Git operations.

## RED

Command: `D:/conda/python.exe -m unittest discover -s tests -p test_refit_capture_command.py`

Before creating the command, output ended:

```text
Ran 6 tests in 0.004s
FAILED (failures=14)
AssertionError: False is not true : single-pose capture command is not prepared
```

All failures were explicit file-presence assertions (including subtests), not import/setup errors. This establishes the missing prepared command as the failing case.

## GREEN and broader verification

Same focused command after preparing the exact command: `Ran 6 tests in 0.107s`, `OK`.

Same focused command after completing the representative state fixture: `Ran 6 tests in 0.110s`, `OK`.

Verified behavior: fresh selected fitting path; complete success observations and samples; owner identity and aggregate rate; nested historical recovery.last_fault diagnostics retained; bad COM/mode/tare/cumulative fault/recovery/byte advance/parser discard and unsafe status abort immediately on the fourth mocked URL response, retaining that response; owner change rejected after capture; duplicate owner or mismatched listener prevents capture; existing evidence prevents owner probing and capture. Representative fields match the backend state schema, including axes, message, updated_at, all diagnostics fields and nested last_fault.

PowerShell normalized-newline comparison of the command against the brief's first Python block returned `True`. No command execution against the live endpoint occurred.

Mock output measurement: 52 complete observations (and samples), 65,348 UTF-8 JSON bytes. Binary floating-point 0.1-second additions require the 52nd observation to exceed five seconds in this mock. All observations are preserved and serialized. A deliberately conservative byte-sized output budget is about 65,348 tokens; this is an estimate, not a tokenizer count or tool transport guarantee. The controller separately owns the actual transport check; its reported check is in `.superpowers/sdd/shear-refit-stdout-transport-check.md` (70 full states, 99,817 characters / 24,955 reported tokens, 70/70 retained). This worker did not rerun that check.

Full command (once, after final code/test edits): `D:/conda/python.exe -m unittest discover -s tests`.

```text
ERROR: test_surface_animates_on_live_press_and_release
       (test_demo_ui.DashboardWarningTests.test_surface_animates_on_live_press_and_release)
  File "D:\semg.claude\coinft\tests\test_demo_ui.py", line 1038
    page.wait_for_function(
      "surfaceView.target === 0 && surfaceView.level > 0 && surfaceView.level < 1")
playwright._impl._errors.TimeoutError: Page.wait_for_function: Timeout 30000ms exceeded.
Ran 148 tests in 106.035s
FAILED (errors=1)
```

147 tests passed. The error is an existing browser animation test outside the owned preparation files. Its cause has not been diagnosed; it is not claimed to be pre-existing or flaky. No unrelated fix or repeat full-suite run was made. Existing suite tests issue GET/POST requests to their own local HTTP fixtures; the prepared command tests use mocked URL input throughout and no physical acquisition/service action was initiated.

## Self-review, limitations and concerns

Every new command line is required by the approved brief; it matches exactly. Test scaffolding verifies bounded one-shot preparation with realistic full-state retention and immediate callback rejection. No production behavior was widened. The command is intentionally executable at top level; it must be run only after explicit operator pose confirmation and controller preflight, not imported as a library. Preflight owner errors happen outside the JSON failure handler, as the exact brief specifies; controller must preserve their process output. The command is prepared only for the first pose and does not persist JSON itself. Controller owns physical requests, completion/release notification, full stdout persistence and subsequent steps. Full-suite browser timeout remains the concern; capture prep focused checks are green.

## SHA256

```text
BD16CEB2FD7EF04529B5E4C0460286484D4DE27C28B62DCD151E1EBC5829B8CF  .superpowers/sdd/shear-refit-capture-command.py
2CA2171D26F697B6918630B4E87B7E50B80525B664AEFA9B4137C2D754F1F782  tests/test_refit_capture_command.py
01BA4719C80B6FE911B091A7C05124B64EEECE964E09C058EF8F9805DACA546B  calibration/shear_refit_20260928/fit/.keep
01BA4719C80B6FE911B091A7C05124B64EEECE964E09C058EF8F9805DACA546B  calibration/shear_refit_20260928/validation/.keep
```

The report's own hash is supplied in the worker handoff rather than embedded recursively in this report.

## Preparation review fixes — 2026-09-28

Status: DONE_WITH_CONCERNS, preparation only. Changed only `tests/test_refit_capture_command.py` and appended this report. No production/prepared-command/Task 1/Task 2 edits, Git operations, real HTTP, serial, service or hardware actions.

The command test now obtains successful core states directly from `CaptureValidSpanTests.run_capture(observer=...)` in `tests/test_capture_valid_span.py`, under that helper's fully mocked URL/time inputs. It selects every twentieth state from its 0.004-second successful fixture so the unchanged core frame counters advance by 20 per command observation, matching the command's mocked 0.1-second/200-Hz aggregate check. Core status, rate, channels, raw, recent counters and resyncs are reused rather than reconstructed. Task 3 adds only its port/mode/tare, historical cumulative counters and full diagnostics/recovery fields. The Task 1 `bad_frame=-1` fixture is also collected through its observer, with its expected frame-validation failure, and replayed as the fourth command observation. No Task 1 helper logic is copied or altered.

Added unsafe variants for cumulative saturated/resyncs, recovery.successes and nonadvancing parsed_frames (41, equal to the preceding observation). All thirteen unsafe variants preserve the rejected observation and abort after exactly four mocked command requests. The actual prepared command and actual capture implementation remain exercised.

RED/GREEN: this is fixture reuse and coverage repair for already implemented rejection behavior; no new production defect or failing behavioral RED is claimed. First amended command run used a direct TestCase import, unintentionally collecting the thirteen Task 1 tests too: `D:/conda/python.exe -m unittest discover -s tests -p test_refit_capture_command.py` reported `Ran 19 tests in 11.737s`, `OK`. Changed the import to a module alias to keep focused discovery scoped.

Final verification:

- `D:/conda/python.exe -m unittest discover -s tests -p test_refit_capture_command.py`: `Ran 6 tests in 5.642s`, `OK`.
- `D:/conda/python.exe -m unittest discover -s tests -p test_capture_valid_span.py`: `Ran 13 tests in 6.076s`, `OK`.

No full-suite rerun was made. Self-review: each changed test line supports existing-fixture reuse or requested missing fault coverage; existing full-state serialization, owner checks and immediate abort assertions remain. The extra fixture sampling adds about five seconds to the focused test run. Physical Task 3, real direction validation and installation remain pending; no physical fix is claimed. The earlier full-suite browser timeout and controller obligations remain as documented above.

Final SHA256:

```text
C8FB82B76A15AB9524F2791F0784FFDF44F4CF19DD50B574CB775A2686BE5249  tests/test_refit_capture_command.py
BD16CEB2FD7EF04529B5E4C0460286484D4DE27C28B62DCD151E1EBC5829B8CF  .superpowers/sdd/shear-refit-capture-command.py (unchanged)
```
