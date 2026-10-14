# Task 1 report: first-valid-sample capture timer

## Change

`capture()` now requires both monotonic time and serialized host timestamps to span the requested duration between valid observations. Its request deadline is `seconds + 1.0`, requests retain the 1.5-second timeout, and the loop does not begin requests at or after the deadline. It accepts an optional `on_state(state)` observer and calls it after receipt but before state validation. Existing evidence fields, the 30-snapshot minimum, and exclusive output creation remain unchanged.

## RED evidence

Command:

```powershell
& 'D:\conda\python.exe' -m unittest discover -s tests -p test_capture_valid_span.py -v
```

Before implementation, it failed with the expected timing reproduction:

```text
FAIL: test_success_spans_five_seconds_between_valid_samples
AssertionError: 4.875 not greater than or equal to 5.0

FAIL: test_initial_http_delay_is_not_counted_as_sample_span
AssertionError: 4.125 not greater than or equal to 5.0
```

The sparse timing case also reported `too few distinct snapshots: 1 < 30` rather than reaching its deadline, and the observer cases reported `TypeError: capture() got an unexpected keyword argument 'on_state'`. The command summary was `Ran 7 tests ... FAILED (failures=3, errors=3)`.

## GREEN evidence

```text
& 'D:\conda\python.exe' -m unittest discover -s tests -p test_capture_valid_span.py -v
Ran 7 tests ... OK

& 'D:\conda\python.exe' -m unittest discover -s tests -p test_demo_profile.py -v
Ran 22 tests ... OK

& 'D:\conda\python.exe' -m unittest discover -s tests -q
Ran 131 tests in 69.253s
OK
Exit code: 0
```

The new tests check five-second host and monotonic spans, initial response delay, deadline bounds for sparse and slow captures, observer order for unsafe state, and immediate propagation of observer exceptions. Existing sample schema, quality rejection, and CLI exclusive-write coverage passed.

## Files and SHA-256

- `calibration/capture_demo_pose.py` — `B67F8E050F4FC955176DDF25A1A3D9F561E5F2A3185B9EED4829F5A975C2CE45`
- `tests/test_capture_valid_span.py` — `BFB88F82005080139808804CDEBB06614EA6FA3EA8B87DB4A2ED475FB21D9490`
- `tests/test_demo_profile.py` — `5A838E8C5AD68E2BC10DC072F85BD4F50AD1D9B39F82B4729FFC07C582321CEE`

## Self-review

Only the assigned capture implementation, timing tests, capture test helper, and this report were changed. No live HTTP, serial, hardware, or service restart was used. No additional concerns found.

## Approved aggregate-timeout review fix (2026-09-28)

The approved amendment supersedes the original inactivity-timeout assumption above. The complete HTTP open/read/JSON operation now runs in an isolated daemon worker. Capture waits on a private one-result queue only for the remainder of 1.5 seconds from request start, then checks monotonic time again before returning any result. A timeout raises immediately and aborts capture; no observer, validation, sample append, or subsequent request runs for the timed-out result. The worker only owns its response and private result queue. Observer and evidence bookkeeping remain on the caller thread. Request start is rechecked against the admission deadline; the worker also checks the admission and aggregate deadlines before opening HTTP. Original five-argument calls, sample schema, quality rejection, minimum count, and CLI exclusive writes are preserved.

### Additional RED evidence

Command (cwd `D:\semg.claude\coinft`):

```powershell
& 'D:\conda\python.exe' -m unittest discover -s tests -p test_capture_valid_span.py -v
```

Before the fix, the fake response delivered 20 chunks at 0.1-second intervals (each below the socket inactivity timeout), taking approximately 2 seconds overall. The failure was an assertion, not an import/setup error:

```text
FAIL: test_trickled_body_times_out_without_late_observation
AssertionError: 2.0129764000012074 not less than 1.8
Ran 10 tests in 2.035s
FAILED (failures=1)
Exit code: 1
```

A separate deadline-edge regression was run before adding the request-start recheck:

```powershell
& 'D:\conda\python.exe' -m unittest discover -s tests -p test_capture_valid_span.py -k admitted -v
```

```text
FAIL: test_request_is_not_admitted_when_start_reaches_deadline
AssertionError: Expected 'urlopen' to not have been called. Called 1 times.
Calls: [call('http://example.test/api/state', timeout=1.5)].
Ran 1 test in 0.014s
FAILED (failures=1)
Exit code: 1
```

### Final GREEN evidence

```text
& 'D:\conda\python.exe' -m unittest discover -s tests -p test_capture_valid_span.py -v
Ran 13 tests in 6.078s
OK
Exit code: 0

& 'D:\conda\python.exe' -m unittest discover -s tests -p test_demo_profile.py -v
Ran 22 tests in 0.502s
OK
Exit code: 0

& 'D:\conda\python.exe' -m unittest discover -s tests -q
Ran 137 tests in 75.481s
OK
Exit code: 0
```

The full suite was run once after the final implementation stabilized. Its existing local HTTP/browser fixtures emitted expected 200/204/404 logs; no manual live HTTP, serial/device/service/profile/UI/firmware operation was performed. New capture tests use fake responses only. Regression checks cover body trickling, slow open and JSON phases, exact-boundary late queued results, one-request abort, late observer/validation isolation, daemon worker status, and independent host-clock rates (2x and 0.5x) so neither clock span can substitute for the other.

### Final SHA-256

- `calibration/capture_demo_pose.py`: `BDDAFA90547D978E6B8ACA6BB827EBCB791DE44CFBDE09AE2900474BD8F16ADC`
- `tests/test_capture_valid_span.py`: `38AF6AE647D6115843DC59FE3E663A4DC3DF6A3D8FB253C391BB8D3128020E64`
- `tests/test_demo_profile.py`: `5A838E8C5AD68E2BC10DC072F85BD4F50AD1D9B39F82B4729FFC07C582321CEE` (unchanged by this review fix)

### Design rationale and remaining limits

Stdlib urllib socket timeouts bound inactivity, so the private daemon worker is required to bound caller waiting across opening, reading, parsing, and response closure. Python cannot safely forcibly terminate an HTTP thread: after capture times out, a trickling worker may finish later (or remain blocked), but cannot deliver callbacks or mutate capture evidence and cannot keep the process alive. Capture issues no later request after timeout. These are software deadline checks subject to OS scheduling, not hard real-time guarantees; tests allow 0.3 seconds of scheduling margin around 1.5 seconds while distinguishing the 2-second failing body. Synchronous observer code is assumed finite local bookkeeping as approved; arbitrary caller callbacks are not claimed forcibly bounded. Independent re-review remains the controller's next checkpoint. No unrelated follow-up code changes were made.
