### Task 1: First-valid-sample capture timer

**Approved review amendment (2026-09-28):** user chose true aggregate timeout. The original urllib block below is the initial implementation reference, not an accepted final total-duration implementation. A request must bound the complete open/read/JSON operation by total1.5 seconds from its start, not just socket inactivity; timeout aborts the entire capture and makes no later request. Late results must never be validated/appended or delivered to on_state. Observer remains local synchronous bookkeeping. First-request admission deadline6s/request-phase7.5s remains unchanged. Add RED/GREEN coverage of slow/trickling whole response, late result isolation and separately advanced wall/monotonic clocks. Fix implementation in Task1-owned files, re-run focused/full tests, and obtain independent re-review before Task2. All profile/UI/firmware/service protections remain unchanged.

**Interfaces:** preserve capture(url, pose, assembly_id, seconds, interval)->dict; add optional on_state(state)->None callback. Callback observes every received state before validation, so caller can preserve a bad final observation. Existing sample keys and CLI exclusive-write behavior remain unchanged.

- [ ] Add tests/test_capture_valid_span.py:

~~~python
import io
import json
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from calibration.capture_demo_pose import capture


class CaptureValidSpanTests(unittest.TestCase):
    def run_capture(self, delay=0.0, interval=0.125, observer=None,
                    repeated_delay=0.0):
        tick = [0.0]
        requested = []
        self.requested, self.tick = requested, tick
        stamp = datetime(2026, 9, 28, tzinfo=timezone.utc)

        class ClockDate:
            @classmethod
            def now(cls):
                return stamp + timedelta(seconds=tick[0])

        def receive(url, timeout):
            requested.append(tick[0])
            frame = len(requested)
            tick[0] += delay if frame == 1 else repeated_delay
            return io.BytesIO(json.dumps({
                "status": "live", "frames": frame, "rate": 200.0,
                "invalid_recent": 0, "saturated_recent": 0, "resyncs": 0,
                "channels": [0.0]*12, "raw": [24000]*12,
            }).encode())

        def sleep(seconds):
            tick[0] += seconds

        with patch("calibration.capture_demo_pose.time.monotonic",
                   side_effect=lambda: tick[0]), \
             patch("calibration.capture_demo_pose.time.sleep", side_effect=sleep), \
             patch("calibration.capture_demo_pose.datetime", ClockDate), \
             patch("calibration.capture_demo_pose.urllib.request.urlopen",
                   side_effect=receive):
            options = {} if observer is None else {"on_state": observer}
            return capture("http://example.test", "press", "assembly-A",
                           5.0, interval, **options), requested

    def test_success_spans_five_seconds_between_valid_samples(self):
        result, requested = self.run_capture()
        samples = result["samples"]
        span = (datetime.fromisoformat(samples[-1]["host"]) -
                datetime.fromisoformat(samples[0]["host"])).total_seconds()
        self.assertGreaterEqual(span, 5.0)
        self.assertEqual(len(samples), 41)
        self.assertTrue(all(t < 6 for t in requested))

    def test_initial_http_delay_is_not_counted_as_sample_span(self):
        result, requested = self.run_capture(delay=0.8, interval=0.125)
        samples = result["samples"]
        span = (datetime.fromisoformat(samples[-1]["host"]) -
                datetime.fromisoformat(samples[0]["host"])).total_seconds()
        self.assertGreaterEqual(span, 5.0)
        self.assertGreaterEqual(len(samples), 40)
        self.assertTrue(all(t < 6 for t in requested))

    def test_slow_capture_fails_without_extending_request_deadline(self):
        with self.assertRaisesRegex(ValueError, "too few distinct snapshots"):
            self.run_capture(delay=1.49, repeated_delay=1.49, interval=0.01)
        self.assertTrue(all(t < 6 for t in self.requested))
        self.assertLessEqual(self.tick[0], 7.5)

    def test_sparse_capture_fails_at_deadline(self):
        with self.assertRaisesRegex(ValueError, "capture deadline"):
            self.run_capture(interval=10.0)
        self.assertEqual(self.requested, [0.0])
        self.assertEqual(self.tick[0], 6.0)

    def test_optional_observer_receives_all_distinct_observations(self):
        seen = []
        result, requested = self.run_capture(observer=seen.append)
        self.assertEqual([s["frames"] for s in seen],
                         [s["f"] for s in result["samples"]])
        self.assertEqual(len(seen), len(requested))
~~~

Both successful timing tests collect41 observations spanning5 seconds. The initially delayed case's latest request starts5.8<6; repeated slow requests are bounded separately.

- [ ] Run RED before changing implementation:
  & 'D:\conda\python.exe' -m unittest discover -s tests -p test_capture_valid_span.py -v
  Expected: the first test fails span4.875<5; callback test currently errors for unsupported on_state. Save exact output; timing test failure is the bug reproduction.

- [ ] Minimal implementation: replace capture's signature/timing loop, retaining current state-validation and sample construction. Add optional callback and stop only when valid sample span is enough. The complete replacement capture function is:
~~~python
def capture(url: str, pose: str, assembly_id: str, seconds: float,
            interval: float, on_state=None) -> dict:
    if not all(math.isfinite(value) and value > 0
               for value in (seconds, interval)):
        raise ValueError("seconds and interval must be finite and positive")
    samples = []
    previous_frame = -1
    first_valid = None
    deadline = time.monotonic() + seconds + 1.0
    complete = False
    while time.monotonic() < deadline:
        started = time.monotonic()
        with urllib.request.urlopen(f"{url.rstrip('/')}/api/state",
                                    timeout=1.5) as response:
            state = json.load(response)
        if on_state is not None:
            on_state(state)
        if not valid_state(state, previous_frame):
            raise ValueError(
                f"unsafe state during {pose}: "
                f"{'; '.join(invalid_reasons(state, previous_frame))}")
        received = time.monotonic()
        if first_valid is None:
            first_valid = received
        previous_frame = state["frames"]
        samples.append({
            "host": datetime.now().astimezone().isoformat(),
            "f": previous_frame, "channels": state["channels"],
            "raw": state["raw"], "status": state["status"],
            "rate": state["rate"], "invalid": state["invalid_recent"],
            "saturated": state["saturated_recent"], "resync": state["resyncs"],
        })
        host_span = (datetime.fromisoformat(samples[-1]["host"]) -
                     datetime.fromisoformat(samples[0]["host"])).total_seconds()
        if received - first_valid >= seconds and host_span >= seconds:
            complete = True
            break
        time.sleep(min(max(0, interval - (time.monotonic() - started)),
                       max(0, deadline - time.monotonic())))
    if not complete:
        raise ValueError("capture deadline reached before valid sample span")
    if len(samples) < 30:
        raise ValueError(f"too few distinct snapshots: {len(samples)} < 30")
    return {"pose": pose, "assemblyId": assembly_id, "source": url,
            "sample_kind": "http_snapshot", "samples": samples}
~~~

- [ ] Timing-dependent old tests: expected frame range becomes list(range(1,42)); existing minimum-count test must supply enough HTTP responses but still <30 samples, using interval0.2 and seconds3.625. Replace only its call with:
~~~python
self.run_capture([state(i) for i in range(1, 30)],
                 seconds=3.625, interval=0.2)
~~~

- [ ] The existing CaptureTests.run_capture must also provide host timestamps from its deterministic clock, otherwise real wall time and fake monotonic time disagree. Replace that helper with:
~~~python
def run_capture(self, states, seconds=5, interval=0.125):
    clock = FakeClock()
    urls = []
    responses = iter(states)
    start = datetime(2026, 9, 28, tzinfo=timezone.utc)

    class ClockDate:
        @classmethod
        def now(cls):
            return start + timedelta(seconds=clock.now)

    def urlopen(url, timeout):
        urls.append((url, timeout))
        return io.BytesIO(json.dumps(next(responses)).encode("utf-8"))

    with patch("calibration.capture_demo_pose.urllib.request.urlopen",
               side_effect=urlopen), \
         patch("calibration.capture_demo_pose.time.monotonic",
               side_effect=clock.monotonic), \
         patch("calibration.capture_demo_pose.time.sleep",
               side_effect=clock.sleep), \
         patch("calibration.capture_demo_pose.datetime", ClockDate):
        result = capture("http://example.test", "train_press",
                         "assembly-A", seconds, interval)
    return result, urls
~~~

- [ ] GREEN: run both test files with discover, then complete suite:
  & 'D:\conda\python.exe' -m unittest discover -s tests -p test_capture_valid_span.py -v
  & 'D:\conda\python.exe' -m unittest discover -s tests -p test_demo_profile.py -v
  & 'D:\conda\python.exe' -m unittest discover -s tests -v
  Expected all pass; preserve bad-state rejection/exclusive-write tests. No live capture yet.
- [ ] Checkpoint: save RED/GREEN output and changed-file hashes to .superpowers/sdd/shear-refit-task1-report.md. No Git commit.

