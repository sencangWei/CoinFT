# Healthy duplicate snapshot correction report

Status: DONE. Focused capture19/19, command11/11, profile25/25 and full159/159 checks GREEN. Full suite ran once, exit0 in88.524s. No physical capture performed.

Approved behavior: retain every observed HTTP state before validation; validate all quality fields even on equal frames; healthy equal frames are omitted from samples and use normal pacing/deadline. Public validation stays strict. Optional `minimum_samples=None` preserves legacy completion/30-floor behavior; requested integer >=30 applies to completion under the same budgets. Prepared command requires40 with5.0 seconds and0.125 seconds cadence; unchanged diagnostics allowed only for equal frames, regression always rejects.

## RED before source edits

Command: `D:/conda/python.exe -m unittest discover -s tests -p test_capture_valid_span.py`
Exit: 1

```text
.EEEEEEEE..FFFFFFFEEE..........F
======================================================================
ERROR: test_bad_minimum_rejects_before_http (test_capture_valid_span.CaptureValidSpanTests.test_bad_minimum_rejects_before_http) (minimum=True)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "D:\semg.claude\coinft\tests\test_capture_valid_span.py", line 114, in test_bad_minimum_rejects_before_http
    capture('http://example.test', 'press', 'assembly-A', 5.0, 0.125,
    ~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
            minimum_samples=minimum)
            ^^^^^^^^^^^^^^^^^^^^^^^^
TypeError: capture() got an unexpected keyword argument 'minimum_samples'

======================================================================
ERROR: test_bad_minimum_rejects_before_http (test_capture_valid_span.CaptureValidSpanTests.test_bad_minimum_rejects_before_http) (minimum=False)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "D:\semg.claude\coinft\tests\test_capture_valid_span.py", line 114, in test_bad_minimum_rejects_before_http
    capture('http://example.test', 'press', 'assembly-A', 5.0, 0.125,
    ~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
            minimum_samples=minimum)
            ^^^^^^^^^^^^^^^^^^^^^^^^
TypeError: capture() got an unexpected keyword argument 'minimum_samples'

======================================================================
ERROR: test_bad_minimum_rejects_before_http (test_capture_valid_span.CaptureValidSpanTests.test_bad_minimum_rejects_before_http) (minimum=29)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "D:\semg.claude\coinft\tests\test_capture_valid_span.py", line 114, in test_bad_minimum_rejects_before_http
    capture('http://example.test', 'press', 'assembly-A', 5.0, 0.125,
    ~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
            minimum_samples=minimum)
            ^^^^^^^^^^^^^^^^^^^^^^^^
TypeError: capture() got an unexpected keyword argument 'minimum_samples'

======================================================================
ERROR: test_bad_minimum_rejects_before_http (test_capture_valid_span.CaptureValidSpanTests.test_bad_minimum_rejects_before_http) (minimum=0)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "D:\semg.claude\coinft\tests\test_capture_valid_span.py", line 114, in test_bad_minimum_rejects_before_http
    capture('http://example.test', 'press', 'assembly-A', 5.0, 0.125,
    ~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
            minimum_samples=minimum)
            ^^^^^^^^^^^^^^^^^^^^^^^^
TypeError: capture() got an unexpected keyword argument 'minimum_samples'

======================================================================
ERROR: test_bad_minimum_rejects_before_http (test_capture_valid_span.CaptureValidSpanTests.test_bad_minimum_rejects_before_http) (minimum=-1)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "D:\semg.claude\coinft\tests\test_capture_valid_span.py", line 114, in test_bad_minimum_rejects_before_http
    capture('http://example.test', 'press', 'assembly-A', 5.0, 0.125,
    ~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
            minimum_samples=minimum)
            ^^^^^^^^^^^^^^^^^^^^^^^^
TypeError: capture() got an unexpected keyword argument 'minimum_samples'

======================================================================
ERROR: test_bad_minimum_rejects_before_http (test_capture_valid_span.CaptureValidSpanTests.test_bad_minimum_rejects_before_http) (minimum=40.0)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "D:\semg.claude\coinft\tests\test_capture_valid_span.py", line 114, in test_bad_minimum_rejects_before_http
    capture('http://example.test', 'press', 'assembly-A', 5.0, 0.125,
    ~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
            minimum_samples=minimum)
            ^^^^^^^^^^^^^^^^^^^^^^^^
TypeError: capture() got an unexpected keyword argument 'minimum_samples'

======================================================================
ERROR: test_bad_minimum_rejects_before_http (test_capture_valid_span.CaptureValidSpanTests.test_bad_minimum_rejects_before_http) (minimum='40')
----------------------------------------------------------------------
Traceback (most recent call last):
  File "D:\semg.claude\coinft\tests\test_capture_valid_span.py", line 114, in test_bad_minimum_rejects_before_http
    capture('http://example.test', 'press', 'assembly-A', 5.0, 0.125,
    ~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
            minimum_samples=minimum)
            ^^^^^^^^^^^^^^^^^^^^^^^^
TypeError: capture() got an unexpected keyword argument 'minimum_samples'

======================================================================
ERROR: test_healthy_duplicates_are_observed_but_not_samples (test_capture_valid_span.CaptureValidSpanTests.test_healthy_duplicates_are_observed_but_not_samples)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "D:\semg.claude\coinft\tests\test_capture_valid_span.py", line 61, in test_healthy_duplicates_are_observed_but_not_samples
    result, requested = self.run_capture(observer=seen.append, duplicates=(2, 3, 4))
                        ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "D:\semg.claude\coinft\tests\test_capture_valid_span.py", line 56, in run_capture
    return capture("http://example.test", "press", "assembly-A",
           ~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                   5.0, interval, **options), requested
                   ^^^^^^^^^^^^^^^^^^^^^^^^^
  File "D:\semg.claude\coinft\calibration\capture_demo_pose.py", line 92, in capture
    raise ValueError(f"unsafe state during {pose}: {'; '.join(invalid_reasons(state, previous_frame))}")
ValueError: unsafe state during press: frame not increasing: previous=1, current=1

======================================================================
ERROR: test_minimum_forty_cannot_be_replaced_by_thirty_or_duplicates (test_capture_valid_span.CaptureValidSpanTests.test_minimum_forty_cannot_be_replaced_by_thirty_or_duplicates) (options={'interval': 0.175})
----------------------------------------------------------------------
Traceback (most recent call last):
  File "D:\semg.claude\coinft\tests\test_capture_valid_span.py", line 105, in test_minimum_forty_cannot_be_replaced_by_thirty_or_duplicates
    self.run_capture(minimum_samples=40, **options)
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "D:\semg.claude\coinft\tests\test_capture_valid_span.py", line 56, in run_capture
    return capture("http://example.test", "press", "assembly-A",
           ~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                   5.0, interval, **options), requested
                   ^^^^^^^^^^^^^^^^^^^^^^^^^
TypeError: capture() got an unexpected keyword argument 'minimum_samples'

======================================================================
ERROR: test_minimum_forty_cannot_be_replaced_by_thirty_or_duplicates (test_capture_valid_span.CaptureValidSpanTests.test_minimum_forty_cannot_be_replaced_by_thirty_or_duplicates) (options={'duplicates': (2, 3, 4, 5, 6, 7, 8, 9, 10, 11)})
----------------------------------------------------------------------
Traceback (most recent call last):
  File "D:\semg.claude\coinft\tests\test_capture_valid_span.py", line 105, in test_minimum_forty_cannot_be_replaced_by_thirty_or_duplicates
    self.run_capture(minimum_samples=40, **options)
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "D:\semg.claude\coinft\tests\test_capture_valid_span.py", line 56, in run_capture
    return capture("http://example.test", "press", "assembly-A",
           ~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                   5.0, interval, **options), requested
                   ^^^^^^^^^^^^^^^^^^^^^^^^^
TypeError: capture() got an unexpected keyword argument 'minimum_samples'

======================================================================
ERROR: test_minimum_forty_waits_past_five_seconds_for_distinct_samples (test_capture_valid_span.CaptureValidSpanTests.test_minimum_forty_waits_past_five_seconds_for_distinct_samples)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "D:\semg.claude\coinft\tests\test_capture_valid_span.py", line 93, in test_minimum_forty_waits_past_five_seconds_for_distinct_samples
    result, requested = self.run_capture(observer=seen.append, duplicates=(2, 3, 4, 5),
                        ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                                         minimum_samples=40)
                                         ^^^^^^^^^^^^^^^^^^^
  File "D:\semg.claude\coinft\tests\test_capture_valid_span.py", line 56, in run_capture
    return capture("http://example.test", "press", "assembly-A",
           ~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
                   5.0, interval, **options), requested
                   ^^^^^^^^^^^^^^^^^^^^^^^^^
TypeError: capture() got an unexpected keyword argument 'minimum_samples'

======================================================================
FAIL: test_invalid_duplicate_and_regression_abort_after_observation (test_capture_valid_span.CaptureValidSpanTests.test_invalid_duplicate_and_regression_abort_after_observation) (mutation=<function CaptureValidSpanTests.test_invalid_duplicate_and_regression_abort_after_observation.<locals>.<lambda> at 0x000001181B8CF880>)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "D:\semg.claude\coinft\tests\test_capture_valid_span.py", line 80, in test_invalid_duplicate_and_regression_abort_after_observation
    self.assertEqual(len(seen), 4)
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^
AssertionError: 2 != 4

======================================================================
FAIL: test_invalid_duplicate_and_regression_abort_after_observation (test_capture_valid_span.CaptureValidSpanTests.test_invalid_duplicate_and_regression_abort_after_observation) (mutation=<function CaptureValidSpanTests.test_invalid_duplicate_and_regression_abort_after_observation.<locals>.<lambda> at 0x000001181D9B3CE0>)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "D:\semg.claude\coinft\tests\test_capture_valid_span.py", line 80, in test_invalid_duplicate_and_regression_abort_after_observation
    self.assertEqual(len(seen), 4)
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^
AssertionError: 2 != 4

======================================================================
FAIL: test_invalid_duplicate_and_regression_abort_after_observation (test_capture_valid_span.CaptureValidSpanTests.test_invalid_duplicate_and_regression_abort_after_observation) (mutation=<function CaptureValidSpanTests.test_invalid_duplicate_and_regression_abort_after_observation.<locals>.<lambda> at 0x000001181D9B3D80>)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "D:\semg.claude\coinft\tests\test_capture_valid_span.py", line 80, in test_invalid_duplicate_and_regression_abort_after_observation
    self.assertEqual(len(seen), 4)
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^
AssertionError: 2 != 4

======================================================================
FAIL: test_invalid_duplicate_and_regression_abort_after_observation (test_capture_valid_span.CaptureValidSpanTests.test_invalid_duplicate_and_regression_abort_after_observation) (mutation=<function CaptureValidSpanTests.test_invalid_duplicate_and_regression_abort_after_observation.<locals>.<lambda> at 0x000001181D9C4680>)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "D:\semg.claude\coinft\tests\test_capture_valid_span.py", line 80, in test_invalid_duplicate_and_regression_abort_after_observation
    self.assertEqual(len(seen), 4)
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^
AssertionError: 2 != 4

======================================================================
FAIL: test_invalid_duplicate_and_regression_abort_after_observation (test_capture_valid_span.CaptureValidSpanTests.test_invalid_duplicate_and_regression_abort_after_observation) (mutation=<function CaptureValidSpanTests.test_invalid_duplicate_and_regression_abort_after_observation.<locals>.<lambda> at 0x000001181D9C4180>)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "D:\semg.claude\coinft\tests\test_capture_valid_span.py", line 80, in test_invalid_duplicate_and_regression_abort_after_observation
    self.assertEqual(len(seen), 4)
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^
AssertionError: 2 != 4

======================================================================
FAIL: test_invalid_duplicate_and_regression_abort_after_observation (test_capture_valid_span.CaptureValidSpanTests.test_invalid_duplicate_and_regression_abort_after_observation) (mutation=<function CaptureValidSpanTests.test_invalid_duplicate_and_regression_abort_after_observation.<locals>.<lambda> at 0x000001181D9C4360>)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "D:\semg.claude\coinft\tests\test_capture_valid_span.py", line 80, in test_invalid_duplicate_and_regression_abort_after_observation
    self.assertEqual(len(seen), 4)
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^
AssertionError: 2 != 4

======================================================================
FAIL: test_invalid_duplicate_and_regression_abort_after_observation (test_capture_valid_span.CaptureValidSpanTests.test_invalid_duplicate_and_regression_abort_after_observation) (mutation=<function CaptureValidSpanTests.test_invalid_duplicate_and_regression_abort_after_observation.<locals>.<lambda> at 0x000001181D9C4720>)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "D:\semg.claude\coinft\tests\test_capture_valid_span.py", line 80, in test_invalid_duplicate_and_regression_abort_after_observation
    self.assertEqual(len(seen), 4)
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^
AssertionError: 2 != 4

======================================================================
FAIL: test_unchanged_frame_times_out_with_normal_pacing (test_capture_valid_span.CaptureValidSpanTests.test_unchanged_frame_times_out_with_normal_pacing)
----------------------------------------------------------------------
ValueError: unsafe state during press: frame not increasing: previous=1, current=1

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "D:\semg.claude\coinft\tests\test_capture_valid_span.py", line 85, in test_unchanged_frame_times_out_with_normal_pacing
    with self.assertRaisesRegex(ValueError, 'capture deadline'):
         ~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: "capture deadline" does not match "unsafe state during press: frame not increasing: previous=1, current=1"

----------------------------------------------------------------------
Ran 19 tests in 6.092s

FAILED (failures=8, errors=11)

```

Command: `D:/conda/python.exe -m unittest discover -s tests -p test_refit_capture_command.py`
Exit: 1

```text
Initial stdout chunk: FFFFFFFFFFFFFFF......
.
======================================================================
FAIL: test_cached_duplicate_diagnostic_regression_still_rejects (test_refit_capture_command.RefitCaptureCommandTests.test_cached_duplicate_diagnostic_regression_still_rejects) (key='serial_bytes')
----------------------------------------------------------------------
Traceback (most recent call last):
  File "D:\semg.claude\coinft\tests\test_refit_capture_command.py", line 136, in test_cached_duplicate_diagnostic_regression_still_rejects
    self.assertEqual(len(result['evidence']['observations']), 4)
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 2 != 4

======================================================================
FAIL: test_cached_duplicate_diagnostic_regression_still_rejects (test_refit_capture_command.RefitCaptureCommandTests.test_cached_duplicate_diagnostic_regression_still_rejects) (key='parsed_frames')
----------------------------------------------------------------------
Traceback (most recent call last):
  File "D:\semg.claude\coinft\tests\test_refit_capture_command.py", line 136, in test_cached_duplicate_diagnostic_regression_still_rejects
    self.assertEqual(len(result['evidence']['observations']), 4)
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 2 != 4

======================================================================
FAIL: test_cached_duplicate_quality_faults_are_retained_and_rejected (test_refit_capture_command.RefitCaptureCommandTests.test_cached_duplicate_quality_faults_are_retained_and_rejected) (mutation=<function RefitCaptureCommandTests.test_cached_duplicate_quality_faults_are_retained_and_rejected.<locals>.<lambda> at 0x00000192D44213A0>)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "D:\semg.claude\coinft\tests\test_refit_capture_command.py", line 127, in test_cached_duplicate_quality_faults_are_retained_and_rejected
    self.assertEqual(len(self.requests), 4)
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 2 != 4

======================================================================
FAIL: test_cached_duplicate_quality_faults_are_retained_and_rejected (test_refit_capture_command.RefitCaptureCommandTests.test_cached_duplicate_quality_faults_are_retained_and_rejected) (mutation=<function RefitCaptureCommandTests.test_cached_duplicate_quality_faults_are_retained_and_rejected.<locals>.<lambda> at 0x00000192D4425260>)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "D:\semg.claude\coinft\tests\test_refit_capture_command.py", line 127, in test_cached_duplicate_quality_faults_are_retained_and_rejected
    self.assertEqual(len(self.requests), 4)
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 2 != 4

======================================================================
FAIL: test_cached_duplicate_quality_faults_are_retained_and_rejected (test_refit_capture_command.RefitCaptureCommandTests.test_cached_duplicate_quality_faults_are_retained_and_rejected) (mutation=<function RefitCaptureCommandTests.test_cached_duplicate_quality_faults_are_retained_and_rejected.<locals>.<lambda> at 0x00000192D5341260>)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "D:\semg.claude\coinft\tests\test_refit_capture_command.py", line 127, in test_cached_duplicate_quality_faults_are_retained_and_rejected
    self.assertEqual(len(self.requests), 4)
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 2 != 4

======================================================================
FAIL: test_cached_duplicate_quality_faults_are_retained_and_rejected (test_refit_capture_command.RefitCaptureCommandTests.test_cached_duplicate_quality_faults_are_retained_and_rejected) (mutation=<function RefitCaptureCommandTests.test_cached_duplicate_quality_faults_are_retained_and_rejected.<locals>.<lambda> at 0x00000192D5340CC0>)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "D:\semg.claude\coinft\tests\test_refit_capture_command.py", line 127, in test_cached_duplicate_quality_faults_are_retained_and_rejected
    self.assertEqual(len(self.requests), 4)
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 2 != 4

======================================================================
FAIL: test_cached_duplicate_quality_faults_are_retained_and_rejected (test_refit_capture_command.RefitCaptureCommandTests.test_cached_duplicate_quality_faults_are_retained_and_rejected) (mutation=<function RefitCaptureCommandTests.test_cached_duplicate_quality_faults_are_retained_and_rejected.<locals>.<lambda> at 0x00000192D5341440>)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "D:\semg.claude\coinft\tests\test_refit_capture_command.py", line 127, in test_cached_duplicate_quality_faults_are_retained_and_rejected
    self.assertEqual(len(self.requests), 4)
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 2 != 4

======================================================================
FAIL: test_cached_duplicate_quality_faults_are_retained_and_rejected (test_refit_capture_command.RefitCaptureCommandTests.test_cached_duplicate_quality_faults_are_retained_and_rejected) (mutation=<function RefitCaptureCommandTests.test_cached_duplicate_quality_faults_are_retained_and_rejected.<locals>.<lambda> at 0x00000192D53413A0>)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "D:\semg.claude\coinft\tests\test_refit_capture_command.py", line 127, in test_cached_duplicate_quality_faults_are_retained_and_rejected
    self.assertEqual(len(self.requests), 4)
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 2 != 4

======================================================================
FAIL: test_cached_duplicate_quality_faults_are_retained_and_rejected (test_refit_capture_command.RefitCaptureCommandTests.test_cached_duplicate_quality_faults_are_retained_and_rejected) (mutation=<function RefitCaptureCommandTests.test_cached_duplicate_quality_faults_are_retained_and_rejected.<locals>.<lambda> at 0x00000192D53414E0>)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "D:\semg.claude\coinft\tests\test_refit_capture_command.py", line 127, in test_cached_duplicate_quality_faults_are_retained_and_rejected
    self.assertEqual(len(self.requests), 4)
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 2 != 4

======================================================================
FAIL: test_cached_duplicate_quality_faults_are_retained_and_rejected (test_refit_capture_command.RefitCaptureCommandTests.test_cached_duplicate_quality_faults_are_retained_and_rejected) (mutation=<function RefitCaptureCommandTests.test_cached_duplicate_quality_faults_are_retained_and_rejected.<locals>.<lambda> at 0x00000192D5341580>)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "D:\semg.claude\coinft\tests\test_refit_capture_command.py", line 127, in test_cached_duplicate_quality_faults_are_retained_and_rejected
    self.assertEqual(len(self.requests), 4)
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 2 != 4

======================================================================
FAIL: test_cached_duplicate_quality_faults_are_retained_and_rejected (test_refit_capture_command.RefitCaptureCommandTests.test_cached_duplicate_quality_faults_are_retained_and_rejected) (mutation=<function RefitCaptureCommandTests.test_cached_duplicate_quality_faults_are_retained_and_rejected.<locals>.<lambda> at 0x00000192D5341620>)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "D:\semg.claude\coinft\tests\test_refit_capture_command.py", line 127, in test_cached_duplicate_quality_faults_are_retained_and_rejected
    self.assertEqual(len(self.requests), 4)
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 2 != 4

======================================================================
FAIL: test_cached_duplicate_quality_faults_are_retained_and_rejected (test_refit_capture_command.RefitCaptureCommandTests.test_cached_duplicate_quality_faults_are_retained_and_rejected) (mutation=<function RefitCaptureCommandTests.test_cached_duplicate_quality_faults_are_retained_and_rejected.<locals>.<lambda> at 0x00000192D53416C0>)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "D:\semg.claude\coinft\tests\test_refit_capture_command.py", line 127, in test_cached_duplicate_quality_faults_are_retained_and_rejected
    self.assertEqual(len(self.requests), 4)
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 2 != 4

======================================================================
FAIL: test_cached_duplicate_quality_faults_are_retained_and_rejected (test_refit_capture_command.RefitCaptureCommandTests.test_cached_duplicate_quality_faults_are_retained_and_rejected) (mutation=<function RefitCaptureCommandTests.test_cached_duplicate_quality_faults_are_retained_and_rejected.<locals>.<lambda> at 0x00000192D5341760>)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "D:\semg.claude\coinft\tests\test_refit_capture_command.py", line 127, in test_cached_duplicate_quality_faults_are_retained_and_rejected
    self.assertEqual(len(self.requests), 4)
    ~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 2 != 4

======================================================================
FAIL: test_cached_duplicates_are_retained_and_forty_distinct_samples_complete (test_refit_capture_command.RefitCaptureCommandTests.test_cached_duplicates_are_retained_and_forty_distinct_samples_complete)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "D:\semg.claude\coinft\tests\test_refit_capture_command.py", line 102, in test_cached_duplicates_are_retained_and_forty_distinct_samples_complete
    self.assertIsNone(self.failure)
    ~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^
AssertionError: SystemExit(1) is not None

======================================================================
FAIL: test_cached_frame_forever_reaches_original_deadline (test_refit_capture_command.RefitCaptureCommandTests.test_cached_frame_forever_reaches_original_deadline)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "D:\semg.claude\coinft\tests\test_refit_capture_command.py", line 148, in test_cached_frame_forever_reaches_original_deadline
    self.assertIn('capture deadline', result['evidence']['error'])
    ~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: 'capture deadline' not found in "ValueError('byte/frame observation not advancing')"

----------------------------------------------------------------------
Ran 11 tests in 11.354s

FAILED (failures=15)

```

## GREEN after source edits

Command: `D:/conda/python.exe -m unittest discover -s tests -p test_capture_valid_span.py`
Exit0:
```text
...................
----------------------------------------------------------------------
Ran 19 tests in 6.152s

OK
```

Command: `D:/conda/python.exe -m unittest discover -s tests -p test_refit_capture_command.py`
Exit0:
```text
...........
----------------------------------------------------------------------
Ran 11 tests in 11.177s

OK
```

Command: `D:/conda/python.exe -m unittest discover -s tests -p test_profile_release_gate.py`
Exit1 (incorrect guessed discovery pattern; no source/test failure):
```text
----------------------------------------------------------------------
Ran 0 tests in 0.000s

NO TESTS RAN
```

Command: `D:/conda/python.exe -m unittest discover -s tests -p '*profile*.py'`
Exit1:
```text
....F....................
======================================================================
FAIL: test_rejects_duplicate_frame_without_skipping_it (test_demo_profile.CaptureTests.test_rejects_duplicate_frame_without_skipping_it)
----------------------------------------------------------------------
Traceback (most recent call last):
  File "D:\semg.claude\coinft\tests\test_demo_profile.py", line 82, in test_rejects_duplicate_frame_without_skipping_it
    with self.assertRaisesRegex(ValueError, "frame not increasing.*previous=8.*current=8"):
         ~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
AssertionError: ValueError not raised

----------------------------------------------------------------------
Ran 25 tests in 0.563s

FAILED (failures=1)
```

Command: `D:/conda/python.exe -m unittest discover -s tests -p test_qualitative_demo_profile.py`
Exit0:
```text
...
----------------------------------------------------------------------
Ran 3 tests in 0.033s

OK
```

## Full suite

The contradictory legacy duplicate-rejection assertion was escalated, then the controller explicitly extended ownership to that one method in the brief. Only its name, frame7 fixture replacement, and previous8/current7 rejection regex changed. All remaining21 demo profile tests and3 qualitative tests were untouched.

Command: `D:/conda/python.exe -m unittest discover -s tests -p '*profile*.py'`
Exit0 after that approved expectation update:
```text
.........................
----------------------------------------------------------------------
Ran 25 tests in 0.550s

OK
```

Command: `D:/conda/python.exe -m unittest discover -s tests`
Exit0, session51053, exactly one full suite process. A JavaScript orchestration SyntaxError occurred before launching this command; it started no shell process. The existing browser tests use their own local HTTP fixture server; no live CoinFT capture endpoint was contacted. Complete output across execution chunks:

```text
....................................................127.0.0.1 - - [28/Sep/2026 20:37:45] "GET / HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:37:45] "GET /style.css HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:37:45] "GET /surface.js HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:37:45] "GET /app.js HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:37:45] code 404, message File not found
127.0.0.1 - - [28/Sep/2026 20:37:45] "GET /shear_profile.json HTTP/1.1" 404 -
127.0.0.1 - - [28/Sep/2026 20:37:45] "GET /shear_demo_profile.json HTTP/1.1" 200 -
.127.0.0.1 - - [28/Sep/2026 20:37:46] "GET / HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:37:46] "GET /style.css HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:37:46] "GET /app.js HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:37:46] "GET /surface.js HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:37:46] code 404, message File not found
127.0.0.1 - - [28/Sep/2026 20:37:46] "GET /shear_profile.json HTTP/1.1" 404 -
127.0.0.1 - - [28/Sep/2026 20:37:46] "GET /shear_demo_profile.json HTTP/1.1" 200 -
.127.0.0.1 - - [28/Sep/2026 20:37:47] "GET / HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:37:47] "GET /style.css HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:37:47] "GET /surface.js HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:37:47] "GET /app.js HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:37:47] code 404, message File not found
127.0.0.1 - - [28/Sep/2026 20:37:47] "GET /shear_profile.json HTTP/1.1" 404 -
.127.0.0.1 - - [28/Sep/2026 20:37:48] "GET / HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:37:48] "GET /style.css HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:37:48] "GET /surface.js HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:37:48] "GET /app.js HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:37:48] code 404, message File not found
127.0.0.1 - - [28/Sep/2026 20:37:48] "GET /shear_profile.json HTTP/1.1" 404 -
127.0.0.1 - - [28/Sep/2026 20:37:48] "POST /api/tare HTTP/1.1" 204 -
.127.0.0.1 - - [28/Sep/2026 20:37:49] "GET / HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:37:49] "GET /app.js HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:37:49] "GET /style.css HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:37:49] "GET /surface.js HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:37:49] code 404, message File not found
127.0.0.1 - - [28/Sep/2026 20:37:49] "GET /shear_profile.json HTTP/1.1" 404 -
127.0.0.1 - - [28/Sep/2026 20:37:49] "GET /shear_demo_profile.json HTTP/1.1" 200 -
.127.0.0.1 - - [28/Sep/2026 20:37:50] "GET / HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:37:50] "GET /style.css HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:37:50] "GET /surface.js HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:37:50] "GET /app.js HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:37:50] code 404, message File not found
127.0.0.1 - - [28/Sep/2026 20:37:50] "GET /shear_profile.json HTTP/1.1" 404 -
127.0.0.1 - - [28/Sep/2026 20:37:50] "GET /shear_demo_profile.json HTTP/1.1" 200 -
.127.0.0.1 - - [28/Sep/2026 20:37:51] "GET / HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:37:51] "GET /style.css HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:37:51] "GET /surface.js HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:37:51] "GET /app.js HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:37:51] code 404, message File not found
127.0.0.1 - - [28/Sep/2026 20:37:51] "GET /shear_profile.json HTTP/1.1" 404 -
127.0.0.1 - - [28/Sep/2026 20:37:51] "GET /shear_demo_profile.json HTTP/1.1" 200 -
.127.0.0.1 - - [28/Sep/2026 20:37:52] "GET / HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:37:52] "GET /style.css HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:37:52] "GET /surface.js HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:37:52] "GET /app.js HTTP/1.1" 200 -
.127.0.0.1 - - [28/Sep/2026 20:37:53] "GET / HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:37:53] "GET /style.css HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:37:53] "GET /surface.js HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:37:53] "GET /app.js HTTP/1.1" 200 -
.127.0.0.1 - - [28/Sep/2026 20:37:54] "GET / HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:37:54] "GET /style.css HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:37:54] "GET /surface.js HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:37:54] "GET /app.js HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:37:54] code 404, message File not found
127.0.0.1 - - [28/Sep/2026 20:37:54] "GET /shear_profile.json HTTP/1.1" 404 -
.127.0.0.1 - - [28/Sep/2026 20:37:56] "GET / HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:37:56] "GET /style.css HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:37:56] "GET /surface.js HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:37:56] "GET /app.js HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:37:56] code 404, message File not found
127.0.0.1 - - [28/Sep/2026 20:37:56] "GET /shear_profile.json HTTP/1.1" 404 -
127.0.0.1 - - [28/Sep/2026 20:37:56] "GET /shear_demo_profile.json HTTP/1.1" 200 -
.127.0.0.1 - - [28/Sep/2026 20:37:57] "GET / HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:37:57] "GET /style.css HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:37:57] "GET /surface.js HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:37:57] "GET /app.js HTTP/1.1" 200 -
.127.0.0.1 - - [28/Sep/2026 20:38:02] "GET / HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:38:02] "GET /style.css HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:38:02] "GET /surface.js HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:38:02] "GET /app.js HTTP/1.1" 200 -
.127.0.0.1 - - [28/Sep/2026 20:38:06] "GET / HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:38:06] "GET /style.css HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:38:06] "GET /surface.js HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:38:06] "GET /app.js HTTP/1.1" 200 -
.127.0.0.1 - - [28/Sep/2026 20:38:08] "GET / HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:38:08] "GET /style.css HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:38:08] "GET /surface.js HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:38:08] "GET /app.js HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:38:09] code 404, message File not found
127.0.0.1 - - [28/Sep/2026 20:38:09] "GET /null HTTP/1.1" 404 -
.127.0.0.1 - - [28/Sep/2026 20:38:10] "GET / HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:38:10] "GET /style.css HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:38:10] "GET /surface.js HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:38:10] "GET /app.js HTTP/1.1" 200 -
.127.0.0.1 - - [28/Sep/2026 20:38:14] "GET / HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:38:14] "GET /style.css HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:38:14] "GET /surface.js HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:38:14] "GET /app.js HTTP/1.1" 200 -
.127.0.0.1 - - [28/Sep/2026 20:38:21] "GET / HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:38:21] "GET /style.css HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:38:21] "GET /surface.js HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:38:21] "GET /app.js HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:38:21] code 404, message File not found
127.0.0.1 - - [28/Sep/2026 20:38:21] "GET /shear_profile.json HTTP/1.1" 404 -
127.0.0.1 - - [28/Sep/2026 20:38:21] "GET /shear_demo_profile.json HTTP/1.1" 200 -
.127.0.0.1 - - [28/Sep/2026 20:38:22] "GET / HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:38:22] "GET /style.css HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:38:22] "GET /surface.js HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:38:22] "GET /app.js HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:38:22] code 404, message File not found
127.0.0.1 - - [28/Sep/2026 20:38:22] "GET /shear_profile.json HTTP/1.1" 404 -
127.0.0.1 - - [28/Sep/2026 20:38:22] "GET /shear_demo_profile.json HTTP/1.1" 200 -
.127.0.0.1 - - [28/Sep/2026 20:38:23] "GET / HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:38:23] "GET /style.css HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:38:23] "GET /surface.js HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:38:23] "GET /app.js HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:38:24] "POST /api/tare HTTP/1.1" 204 -
.127.0.0.1 - - [28/Sep/2026 20:38:25] "GET / HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:38:25] "GET /style.css HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:38:25] "GET /surface.js HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:38:25] "GET /app.js HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:38:25] code 404, message File not found
127.0.0.1 - - [28/Sep/2026 20:38:25] "GET /shear_profile.json HTTP/1.1" 404 -
.127.0.0.1 - - [28/Sep/2026 20:38:29] "GET / HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:38:29] "GET /style.css HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:38:29] "GET /surface.js HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:38:29] "GET /app.js HTTP/1.1" 200 -
.127.0.0.1 - - [28/Sep/2026 20:38:30] "GET / HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:38:30] "GET /style.css HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:38:30] "GET /surface.js HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:38:30] "GET /app.js HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:38:30] code 404, message File not found
127.0.0.1 - - [28/Sep/2026 20:38:30] "GET /shear_profile.json HTTP/1.1" 404 -
.127.0.0.1 - - [28/Sep/2026 20:38:32] "GET / HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:38:32] "GET /style.css HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:38:32] "GET /surface.js HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:38:32] "GET /app.js HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:38:32] code 404, message File not found
127.0.0.1 - - [28/Sep/2026 20:38:32] "GET /shear_profile.json HTTP/1.1" 404 -
.127.0.0.1 - - [28/Sep/2026 20:38:33] "GET / HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:38:33] "GET /style.css HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:38:33] "GET /surface.js HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:38:33] "GET /app.js HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:38:33] code 404, message File not found
127.0.0.1 - - [28/Sep/2026 20:38:33] "GET /shear_profile.json HTTP/1.1" 404 -
.127.0.0.1 - - [28/Sep/2026 20:38:34] "GET / HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:38:34] "GET /style.css HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:38:34] "GET /surface.js HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:38:34] "GET /app.js HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:38:34] code 404, message File not found
127.0.0.1 - - [28/Sep/2026 20:38:34] "GET /shear_profile.json HTTP/1.1" 404 -
.127.0.0.1 - - [28/Sep/2026 20:38:35] "GET / HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:38:35] "GET /style.css HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:38:35] "GET /surface.js HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:38:35] "GET /app.js HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:38:35] code 404, message File not found
127.0.0.1 - - [28/Sep/2026 20:38:35] "GET /shear_profile.json HTTP/1.1" 404 -
127.0.0.1 - - [28/Sep/2026 20:38:36] "POST /api/tare HTTP/1.1" 204 -
127.0.0.1 - - [28/Sep/2026 20:38:36] "GET / HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:38:36] "GET /surface.js HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:38:36] "GET /app.js HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:38:36] "GET /style.css HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:38:37] code 404, message File not found
127.0.0.1 - - [28/Sep/2026 20:38:37] "GET /shear_profile.json HTTP/1.1" 404 -
127.0.0.1 - - [28/Sep/2026 20:38:37] "POST /api/tare HTTP/1.1" 204 -
.127.0.0.1 - - [28/Sep/2026 20:38:38] "GET / HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:38:38] "GET /style.css HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:38:38] "GET /surface.js HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:38:38] "GET /app.js HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:38:38] code 404, message File not found
127.0.0.1 - - [28/Sep/2026 20:38:38] "GET /shear_profile.json HTTP/1.1" 404 -
127.0.0.1 - - [28/Sep/2026 20:38:38] "GET /shear_demo_profile.json HTTP/1.1" 200 -
.127.0.0.1 - - [28/Sep/2026 20:38:39] "GET / HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:38:39] "GET /style.css HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:38:39] "GET /surface.js HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:38:39] "GET /app.js HTTP/1.1" 200 -
127.0.0.1 - - [28/Sep/2026 20:38:39] code 404, message File not found
127.0.0.1 - - [28/Sep/2026 20:38:39] "GET /shear_profile.json HTTP/1.1" 404 -
127.0.0.1 - - [28/Sep/2026 20:38:39] "POST /api/tare HTTP/1.1" 204 -
127.0.0.1 - - [28/Sep/2026 20:38:40] code 404, message File not found
127.0.0.1 - - [28/Sep/2026 20:38:40] "GET /null HTTP/1.1" 404 -
...............................................................................
----------------------------------------------------------------------
Ran 159 tests in 88.524s

OK
CAPTURE_REPLAY {"old": {"zero": 24, "variation": 10.410640929680575}, "current": {"zero": 15, "variation": 6.240847099088214}, "normals": [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]}
```

## SHA256 of changed implementation/tests

- calibration/capture_demo_pose.py: AF9D0836952E954DA0C96FDDD588E917687948610AC4999672E21486601E285A
- .superpowers/sdd/shear-refit-capture-command.py: A52915033D741B916328175706FB60563B96C0C9333C6C8AC6444FFACBBEB622
- tests/test_capture_valid_span.py: AD7D6B3A869F0EAD773E6242180F084487D459865275E4630CE8ABD73A5C5845
- tests/test_refit_capture_command.py: 9A4DE2241861F09DE79F99482E5CE1F4041BB115572A5C9ED17303148C5536F1
- tests/test_demo_profile.py (only approved legacy test method): 416497DE9832BB9DA57A76E4D029C5D127E23834E3EF3377B6B548A93041F294

## Scope self-review and limits

Each implementation change serves duplicate validation/pacing, requested minimum count, or cached diagnostic progress. Existing sample/evidence return fields, observer-first behavior, timeout isolation, owner gates and exclusive writes retained. Test helper changes extend existing fully mocked fixtures; dense0.004 Task1 sampling and25-frame command selection remain. New tests cover duplicates, unsafe duplicates, regression, frozen-frame deadline,40-count completion/failure, invalid argument admission, retained command evidence and diagnostics regression/fresh-frame stagnation.

No backend/serial/firmware/profile implementation/UI/hardware/service changes, Git actions, live capture HTTP or real psutil probes. Existing failed physical evidence remains untouched. No interpolation, fabricated samples, relaxation of5s/40 gates, or timeout extension. Physical capture remains controller-owned after independent review. Prior unrelated browser timeout did not reproduce; no follow-up code changes made. No unresolved implementation concerns found during self-review.
