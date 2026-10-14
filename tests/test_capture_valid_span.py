import io
import json
import threading
import time
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from calibration.capture_demo_pose import capture


class CaptureValidSpanTests(unittest.TestCase):
    def run_capture(self, delay=0.0, interval=0.125, observer=None,
                    repeated_delay=0.0, bad_frame=None, host_rate=1.0,
                    duplicates=(), unsafe=None, minimum_samples=None):
        tick = [0.0]
        requested = []
        self.requested, self.tick = requested, tick
        stamp = datetime(2026, 9, 28, tzinfo=timezone.utc)

        class ClockDate:
            @classmethod
            def now(cls):
                return stamp + timedelta(seconds=tick[0] * host_rate)

            @staticmethod
            def fromisoformat(value):
                return datetime.fromisoformat(value)

        def receive(url, timeout):
            requested.append(tick[0])
            frame = len(requested)
            tick[0] += delay if frame == 1 else repeated_delay
            state = {
                "status": "live", "frames": bad_frame if bad_frame is not None else
                frame - sum(index <= frame for index in duplicates),
                "rate": 200.0, "invalid_recent": 0, "saturated_recent": 0,
                "resyncs": 0, "channels": [0.0]*12, "raw": [24000]*12,
            }
            if unsafe is not None and frame == 4:
                unsafe(state)
            return io.BytesIO(json.dumps(state).encode())

        def sleep(seconds):
            tick[0] += seconds

        with patch("calibration.capture_demo_pose.time.monotonic",
                   side_effect=lambda: tick[0]), \
             patch("calibration.capture_demo_pose.time.sleep", side_effect=sleep), \
             patch("calibration.capture_demo_pose.datetime", ClockDate), \
             patch("calibration.capture_demo_pose.urllib.request.urlopen",
                   side_effect=receive):
            options = {} if observer is None else {"on_state": observer}
            if minimum_samples is not None:
                options["minimum_samples"] = minimum_samples
            return capture("http://example.test", "press", "assembly-A",
                           5.0, interval, **options), requested

    def test_healthy_duplicates_are_observed_but_not_samples(self):
        seen = []
        result, requested = self.run_capture(observer=seen.append, duplicates=(2, 3, 4))
        self.assertEqual(len(seen), len(requested))
        self.assertEqual([state['frames'] for state in seen[:4]], [1, 1, 1, 1])
        self.assertEqual(len(result['samples']), len(seen) - 3)
        self.assertEqual([sample['f'] for sample in result['samples']], list(range(1, 39)))

    def test_invalid_duplicate_and_regression_abort_after_observation(self):
        mutations = [lambda s: s.update(status='waiting'),
                     lambda s: s.update(invalid_recent=1),
                     lambda s: s.update(saturated_recent=1),
                     lambda s: s.update(rate=float('nan')),
                     lambda s: s.update(raw=[]),
                     lambda s: s.update(channels=[float('inf')] * 12),
                     lambda s: s.update(frames=0)]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                seen = []
                with self.assertRaisesRegex(ValueError, 'unsafe state'):
                    self.run_capture(observer=seen.append, duplicates=(2, 3, 4), unsafe=mutation)
                self.assertEqual(len(seen), 4)
                self.assertEqual(len(self.requested), 4)

    def test_unchanged_frame_times_out_with_normal_pacing(self):
        seen = []
        with self.assertRaisesRegex(ValueError, 'capture deadline'):
            self.run_capture(observer=seen.append, bad_frame=1)
        self.assertEqual(len(seen), 48)
        self.assertEqual(self.requested, [index * 0.125 for index in range(48)])
        self.assertEqual(self.tick[0], 6.0)

    def test_minimum_forty_waits_past_five_seconds_for_distinct_samples(self):
        seen = []
        result, requested = self.run_capture(observer=seen.append, duplicates=(2, 3, 4, 5),
                                             minimum_samples=40)
        self.assertEqual(len(result['samples']), 40)
        self.assertEqual(len(seen), 44)
        self.assertEqual(requested[-1], 5.375)
        self.assertEqual(len({sample['host'] for sample in result['samples']}), 40)
        self.assertEqual(len({sample['f'] for sample in result['samples']}), 40)

    def test_minimum_forty_cannot_be_replaced_by_thirty_or_duplicates(self):
        for options in ({'interval': 0.175}, {'duplicates': tuple(range(2, 12))}):
            with self.subTest(options=options):
                with self.assertRaisesRegex(ValueError, 'capture deadline'):
                    self.run_capture(minimum_samples=40, **options)
                self.assertTrue(all(t < 6 for t in self.requested))
                self.assertEqual(self.tick[0], 6.0)

    def test_bad_minimum_rejects_before_http(self):
        for minimum in (True, False, 29, 0, -1, 40.0, '40'):
            with self.subTest(minimum=minimum), \
                 patch('calibration.capture_demo_pose.urllib.request.urlopen') as request:
                with self.assertRaisesRegex(ValueError, 'minimum_samples'):
                    capture('http://example.test', 'press', 'assembly-A', 5.0, 0.125,
                            minimum_samples=minimum)
                request.assert_not_called()

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

    def test_observer_receives_unsafe_state_before_validation(self):
        seen = []
        with self.assertRaisesRegex(ValueError, "frame not increasing"):
            self.run_capture(observer=seen.append, bad_frame=-1)
        self.assertEqual([state["frames"] for state in seen], [-1])

    def test_observer_exception_stops_capture_immediately(self):
        def fail(state):
            raise RuntimeError("observer failed")

        with self.assertRaisesRegex(RuntimeError, "observer failed"):
            self.run_capture(observer=fail)
        self.assertEqual(len(self.requested), 1)

    def test_host_span_cannot_replace_monotonic_span(self):
        result, requested = self.run_capture(host_rate=2.0)
        self.assertEqual(len(result["samples"]), 41)
        self.assertGreaterEqual(requested[-1] - requested[0], 5.0)

    def test_monotonic_span_cannot_replace_host_span(self):
        with self.assertRaisesRegex(ValueError, "capture deadline"):
            self.run_capture(host_rate=0.5)
        self.assertTrue(all(t < 6 for t in self.requested))
        self.assertEqual(self.tick[0], 6.0)

    def test_trickled_body_times_out_without_late_observation(self):
        finished = threading.Event()
        seen = []
        worker_daemon = []
        payload = json.dumps({"status": "live", "frames": 1,
                              "rate": 200.0, "invalid_recent": 0,
                              "saturated_recent": 0, "resyncs": 0,
                              "channels": [0.0]*12, "raw": [24000]*12}).encode()

        class TrickleResponse(io.BytesIO):
            def read(self, *args):
                worker_daemon.append(threading.current_thread().daemon)
                # Each chunk arrives well within the 1.5s inactivity timeout,
                # but the complete body takes 2s. No network is used.
                for _ in range(20):
                    time.sleep(0.1)
                return super().read(*args)

            def close(self):
                super().close()
                finished.set()

        response = TrickleResponse(payload)
        with patch("calibration.capture_demo_pose.urllib.request.urlopen",
                   side_effect=[response, TimeoutError("second request")]) as request, \
             patch("calibration.capture_demo_pose.valid_state") as validate:
            started = time.monotonic()
            with self.assertRaises(TimeoutError):
                capture("http://example.test", "press", "assembly-A",
                        5.0, 0.125, on_state=seen.append)
            elapsed = time.monotonic() - started
            # Allow 0.3s for OS scheduling; this is not a real-time guarantee.
            self.assertLess(elapsed, 1.8)
            self.assertEqual(request.call_count, 1)
            self.assertEqual(seen, [])
            validate.assert_not_called()
            self.assertTrue(finished.wait(2.0))
            self.assertEqual(seen, [])
            validate.assert_not_called()
            self.assertEqual(worker_daemon, [True])

    def test_open_and_json_are_inside_total_timeout(self):
        for stage in ("open", "json"):
            with self.subTest(stage=stage):
                finished = threading.Event()
                seen = []

                def slow():
                    time.sleep(2.0)

                class CompletedResponse(io.BytesIO):
                    def close(self):
                        super().close()
                        finished.set()

                def receive(url, timeout):
                    if stage == "open":
                        slow()
                    return CompletedResponse(b"{}")

                def decode(response):
                    if stage == "json":
                        slow()
                    return {}

                with patch("calibration.capture_demo_pose.urllib.request.urlopen",
                           side_effect=receive) as request, \
                     patch("calibration.capture_demo_pose.json.load",
                           side_effect=decode), \
                     patch("calibration.capture_demo_pose.valid_state") as validate:
                    started = time.monotonic()
                    with self.assertRaisesRegex(TimeoutError, "total 1.5"):
                        capture("http://example.test", "press", "assembly-A",
                                5.0, 0.125, on_state=seen.append)
                    self.assertLess(time.monotonic() - started, 1.8)
                    self.assertEqual(request.call_count, 1)
                    self.assertTrue(finished.wait(2.0))
                    self.assertEqual(seen, [])
                    validate.assert_not_called()

    def test_already_queued_late_result_is_rejected(self):
        seen = []
        with self.assertRaisesRegex(TimeoutError, "total 1.5"):
            self.run_capture(delay=1.5, observer=seen.append)
        self.assertEqual(len(self.requested), 1)
        self.assertEqual(seen, [])

    def test_request_is_not_admitted_when_start_reaches_deadline(self):
        with patch("calibration.capture_demo_pose.time.monotonic",
                   side_effect=[0.0, 5.999, 6.0, 6.0, 6.0, 6.0]), \
             patch("calibration.capture_demo_pose.urllib.request.urlopen",
                   side_effect=TimeoutError("request admitted")) as request:
            try:
                capture("http://example.test", "press", "assembly-A", 5.0, 0.125)
            except (ValueError, TimeoutError):
                pass
            request.assert_not_called()
