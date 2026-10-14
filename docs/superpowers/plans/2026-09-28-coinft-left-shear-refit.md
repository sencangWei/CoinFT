# CoinFT Left-Shear Refit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Make +X produce visible left shear, while preserving normal deformation and rejecting unloaded/pure-pressure false shear.

**Architecture:** Correct the supporting HTTP capture timer, then collect eight complete fitting windows and an independent repetition. Reuse the existing qualitative builder and replay the unchanged production surface.js in Chromium. Only install shear coefficients after every fixed acceptance gate passes.

**Tech Stack:** Windows PowerShell; D:\conda\python.exe; unittest; existing Playwright/Chromium; existing local HTTP service. No new dependency or firmware upload.

## Global Constraints

- Approved design: docs/superpowers/specs/2026-09-28-coinft-left-shear-refit-design.md.
- Production changes limited to demo_web/shear_demo_profile.json shear parameters and evidence metadata.
- Preserve version1, qualitative, −X/right and +X/left, normal.threshold=100, normal.span=600.
- Do not edit surface.js, app.js, HTML/CSS, trends, coinft_demo.py, START_DEMO.bat, calibration matrix, IMU, Teensy or CoinFT firmware.
- If profile-only changes cannot pass, stop and report; do not widen the algorithm/rendering scope.
- Fitting requires press_before, press, press_after, right_before, right, right_after, left_before, left; each >=40 increasing distinct frames, actual first/last timestamps >=5 seconds, live, finite twelve-channel values, zero recent invalid/saturated.
- Same assembly and owner/epoch across all fitting windows; host times and frames strictly increase across windows.
- First-request deadline is 6 seconds for a 5-second capture; timeout1.5 seconds; no request starts at/after deadline. Last in-flight request may finish up to7.5 seconds after first request start.
- Only read HTTP from the current sole owner. No second COM6/COM8 client or device commands.
- Prepare and test the capture command before asking for a pose. Wait for explicit pose confirmation. First assistant message after execution: capture finished, release now; analysis follows.
- Fit and independent validation are separate physical loading actions. Independent observations never select weights/threshold. Changing a failed candidate requires fresh independent validation.
- Real surface.js replay: discard first600ms for stable statistics; idle/pure press abs(shearTarget)<=0.05 throughout stable samples; right >=0.20 on >=80%, no <-0.05; left <=-0.20 on >=80%, no >0.05.
- Before/after normalTarget identical per sample. Preserve synthetic release/reversal within600ms tests.
- Independent live windows require sole owner, advancing frames/bytes, aggregate150–250Hz, no new invalid/saturated/parser-discard/resync counts.
- Keep full failure evidence. HTTP observation times are not sensor jitter/latency measurements.
- No Git metadata: no worktree creation, git init, commit, branch or merge. Save reviewed evidence and hashes instead.
- Current24-snapshot and partial8-valid-press data are diagnosis only, never duplicated to manufacture fitting input.
- Browser baseline currently inaccessible: use an explicit recorded unloaded reference for offline replay; final page direction is operator-observed, not independently inspected browser evidence.

## Files and responsibilities

**Approved duplicate-snapshot amendment (2026-09-28):** user explicitly approved retaining healthy cached duplicate observations without counting them as samples. Preserve125ms pacing,6s request admission/1.5s total request timeout,all real-fault checks and40 distinct samples/actual5s requirement. Generic capture callers keep their original30-snapshot policy; add optional minimum_samples for the fitting command to wait for40 within the same existing deadline. Existing repeated-state valid_state predicate remains strict; only capture treats otherwise-healthy exact repeated frame as a cached non-sample. Never skip regression, malformed/nonfinite/invalid state or observer error. Diagnostics may hold for cached duplicate but never regress; fresh frames still require byte/parsed progress. No backend,firmware,serial,profile or UI change. This amendment overrides the original immediate-duplicate rejection in earlier reference code.


- Modify calibration/capture_demo_pose.py: bounded first-valid-sample timing, optional read-only observation callback.
- Modify tests/test_demo_profile.py: update timing-dependent expectations only.
- Create tests/test_capture_valid_span.py: deterministic timing/delay/deadline/callback regression.
- Create calibration/shear_refit_replay.py: ordered fitting-input validation and real-JS replay/gates; no serial/network/write or auto-deployment.
- Create tests/test_shear_refit_replay.py: ordered input rejection, sign gates and normal invariance.
- New evidence files under calibration/shear_refit_20260928/{fit,validation}/ and .superpowers/sdd/.
- Production profile unchanged until Task4.
- Update PROJECT_LOG.md and .superpowers/sdd/progress-shear-left-identification.md at every checkpoint.

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

### Task 2: Ordered input and unchanged-JS replay gate

**Interfaces:** fit_candidate(windows, old)->dict; replay(profile, old, windows, baseline)->dict; passes(report)->bool. windows uses the eight existing qualitative keys, each window carries owner={"pid":int,"created":float} and evidence basename. replay uses a recorded common12-element baseline, never per-action direction-dependent normalization.

- [ ] Create tests/test_shear_refit_replay.py before the implementation:
~~~python
import copy
import json
import unittest
from pathlib import Path
try:
    from calibration import shear_refit_replay as refit
except ImportError:
    refit = None
from test_qualitative_demo_profile import make_windows


def windows():
    result = make_windows()
    # Remove synthetic acquisition offsets: one actual epoch/common baseline.
    for index, window in enumerate(result.values()):
        offset = [100+3*i if index < 6 else 900-2*i for i in range(12)]
        for sample in window["samples"]:
            sample["channels"] = [v-b for v, b in zip(sample["channels"], offset)]
        window["owner"] = {"pid": 7, "created": 123.0}
    return result


class ShearRefitReplayTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(refit, "offline refit behaviors are not implemented")

    def test_preserves_normal_and_replays_actual_surface(self):
        data = windows()
        root = Path(__file__).resolve().parents[1]
        old = json.loads((root / "demo_web/shear_demo_profile.json").read_text(encoding="utf-8"))
        candidate = refit.fit_candidate(data, old)
        self.assertEqual(candidate["normal"], old["normal"])
        result = refit.replay(candidate, old, data, [0]*12)
        self.assertTrue(refit.passes(result), result)
        self.assertTrue(result["normalUnchanged"])

    def test_normal_change_is_detected_and_rejected(self):
        data = windows()
        root = Path(__file__).resolve().parents[1]
        old = json.loads((root / "demo_web/shear_demo_profile.json").read_text(encoding="utf-8"))
        candidate = refit.fit_candidate(data, old)
        changed = copy.deepcopy(candidate)
        changed["normal"]["span"] = 1200
        report = refit.replay(changed, old, data, [0]*12)
        self.assertFalse(report["normalUnchanged"])
        self.assertFalse(refit.passes(report))

    def test_rejects_cross_window_epoch_and_frame_restart(self):
        old = {"normal": {"threshold": 100, "span": 600}}
        for field in ("owner", "frame"):
            data = windows()
            if field == "owner":
                data["left"]["owner"]["created"] += 1
            else:
                data["left"]["samples"][0]["f"] = 1
            with self.assertRaises(ValueError):
                refit.fit_candidate(data, old)

    def test_rejects_false_shear_or_wrong_direction(self):
        good = {"normalUnchanged": True, "poses": {
            "press_before": [0.0], "press": [0.0], "press_after": [0.0],
            "right_before": [0.0], "right": [0.3]*10,
            "right_after": [0.0], "left_before": [0.0], "left": [-0.3]*10}}
        self.assertTrue(refit.passes(good))
        for key, values in (("press", [0.06]), ("left", [0.3]),
                            ("right", [0.3]*7+[0.0]*3)):
            bad = copy.deepcopy(good)
            bad["poses"][key] = values
            self.assertFalse(refit.passes(bad))
        good["normalUnchanged"] = False
        self.assertFalse(refit.passes(good))
~~~

- [ ] RED:
  & 'D:\conda\python.exe' -m unittest discover -s tests -p test_shear_refit_replay.py -v
  Expected assertion FAIL: offline refit behaviors are not implemented. Missing module import is guarded in the test; the test run must not be recorded as a successful behavioral RED merely because of an import/syntax error.

- [ ] Create calibration/shear_refit_replay.py:
~~~python
"""Offline-only shear fitting and unchanged production-JS replay."""
import copy
import math
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright
from calibration.build_qualitative_demo_profile import build_profile, SOURCES

KEYS = tuple(SOURCES)


def ordered(windows):
    previous_host = None
    previous_frame = -1
    owner = None
    for key in KEYS:
        window = windows[key]
        current = window.get("owner")
        if (not isinstance(current, dict) or set(current) != {"pid", "created"}
                or type(current["pid"]) is not int
                or type(current["created"]) not in (int, float)
                or not math.isfinite(current["created"])):
            raise ValueError("missing owner identity")
        if owner is None:
            owner = current
        elif current != owner:
            raise ValueError("owner epoch changed")
        for sample in window["samples"]:
            host = datetime.fromisoformat(sample["host"])
            if ((previous_host is not None and host <= previous_host)
                    or sample["f"] <= previous_frame):
                raise ValueError("cross-window time/frame order changed")
            previous_host, previous_frame = host, sample["f"]


def fit_candidate(windows, old):
    # Existing validator still checks every sample and all eight windows.
    profile = build_profile(windows)
    ordered(windows)
    if old["normal"] != {"threshold": 100, "span": 600}:
        raise ValueError("unexpected protected normal configuration")
    profile["normal"] = copy.deepcopy(old["normal"])
    return profile


def replay(profile, old, windows, baseline):
    # Validate even independent inputs, without fitting from them.
    from calibration.build_qualitative_demo_profile import _validate
    _validate(windows)
    ordered(windows)
    if len(baseline) != 12:
        raise ValueError("baseline needs twelve values")
    source = Path(__file__).resolve().parents[1] / "demo_web/surface.js"
    batches = []
    for key in KEYS:
        samples = windows[key]["samples"]
        first = datetime.fromisoformat(samples[0]["host"])
        batches.append({"key": key, "samples": [
            {"ms": (datetime.fromisoformat(s["host"])-first).total_seconds()*1000,
             "channels": [v-b for v, b in zip(s["channels"], baseline)]}
            for s in samples]})
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            page = browser.new_page(reduced_motion="reduce")
            page.set_content('<canvas id="c" style="width:600px;height:400px"></canvas>')
            page.add_script_tag(path=str(source))
            return page.evaluate("""a => {
                let now=0; performance.now=()=>now;
                const current=createSurface(document.getElementById('c'));
                const previous=createSurface(document.getElementById('c'));
                const poses={}; const samples={}; let normalUnchanged=true;
                for (const batch of a.batches) {
                    current.clear(); previous.clear();
                    const rows=[];
                    for (const sample of batch.samples) {
                        now=sample.ms;
                        current.set(sample.channels,a.profile);
                        previous.set(sample.channels,a.old);
                        normalUnchanged &&= current.target===previous.target;
                        rows.push({ms:now,normal:current.target,
                                   shear:current.shearTarget});
                    }
                    samples[batch.key]=rows;
                    poses[batch.key]=rows.filter(x=>x.ms>=600).map(x=>x.shear);
                }
                return {normalUnchanged,poses,samples};
            }""", {"profile": profile, "old": old, "batches": batches})
        finally:
            browser.close()


def passes(report):
    if not report.get("normalUnchanged") or set(report.get("poses", {})) != set(KEYS):
        return False
    for key, values in report["poses"].items():
        if (not values or any(type(v) not in (int, float)
                              or not math.isfinite(v) for v in values)):
            return False
        if key == "right":
            if any(v < -0.05 for v in values):
                return False
            if sum(v >= 0.20 for v in values)/len(values) < 0.80:
                return False
        elif key == "left":
            if any(v > 0.05 for v in values):
                return False
            if sum(v <= -0.20 for v in values)/len(values) < 0.80:
                return False
        elif any(abs(v) > 0.05 for v in values):
            return False
    return True
~~~

- [ ] GREEN:
  & 'D:\conda\python.exe' -m unittest discover -s tests -p test_shear_refit_replay.py -v
  & 'D:\conda\python.exe' -m unittest discover -s tests -p test_qualitative_demo_profile.py -v
  Expected all pass. Do not adjust gates to improve results.
- [ ] Checkpoint: review profile-only boundary, preserve owner ordering and baseline transparency; write .superpowers/sdd/shear-refit-task2-report.md. No Git commit.

### Task 3: Prepare bounded single-pose command, then collect fitting evidence

**Approved interval amendment (2026-09-28):** user approved changing HTTP observation interval from0.1s to0.125s after the first empty attempt repeated a completed serial batch. Keep >=40 distinct snapshots, actual >=5s span, all quality/epoch gates and total request timeout unchanged. Only command/test cadence changes; no backend, serial settings or firmware edits. Preserve the original failed evidence. Full stdout budget remains conservative for51 states; dry-run must preserve every actual observation.

**Files:** eight new fit evidence JSON files; no production edits.

- [ ] Create evidence directories with apply_patch marker .keep files. Prepare the following Python command before asking for any pose. Set pose to the exact confirmed key and out to its fresh fitting/validation filename; do not run multiple poses automatically.
~~~python
import json
import time
from datetime import datetime
from pathlib import Path
import psutil
from calibration.capture_demo_pose import capture

def owner():
    candidates = []
    for proc in psutil.process_iter(["pid", "create_time", "cmdline"]):
        args = proc.info["cmdline"] or []
        if any(Path(a).name == "coinft_demo.py" for a in args):
            candidates.append(proc.info)
    listeners = [c for c in psutil.net_connections(kind="tcp")
                 if c.status == psutil.CONN_LISTEN and c.laddr.port == 8765]
    if len(candidates) != 1 or len(listeners) != 1:
        raise ValueError("not exactly one HTTP capture owner")
    p = candidates[0]
    if listeners[0].pid != p["pid"]:
        raise ValueError("listener does not belong to capture owner")
    return {"pid": p["pid"], "created": p["create_time"]}

pose = "press_before"
out = Path("calibration/shear_refit_20260928/fit/press_before.json")
if out.exists():
    raise FileExistsError(out)
who = owner()
observations = []
def observe(state):
    observations.append({"host": datetime.now().astimezone().isoformat(),
                         "monotonic": time.monotonic(), "state": state})
    if state.get("port") != "COM6" or state.get("mode") != "live":
        raise ValueError("wrong port/mode")
    if state.get("tare_progress") != 100:
        raise ValueError("tare/baseline epoch not stable")
    if not state.get("diagnostics") or not state.get("recovery"):
        raise ValueError("missing stream quality evidence")
    if len(observations) > 1:
        first, previous = observations[0]["state"], observations[-2]["state"]
        for key in ("invalid_frames", "saturated", "resyncs"):
            if state[key] != first[key]:
                raise ValueError("new cumulative quality fault: "+key)
        for key in ("attempts", "successes"):
            if state["recovery"][key] != first["recovery"][key]:
                raise ValueError("stream recovery changed epoch")
        for key in ("serial_bytes", "parsed_frames"):
            if state["diagnostics"][key] <= previous["diagnostics"][key]:
                raise ValueError("byte/frame observation not advancing")
        if (state["diagnostics"]["parser_discarded_bytes"] !=
                first["diagnostics"]["parser_discarded_bytes"]):
            raise ValueError("parser discarded bytes increased")

try:
    data = capture("http://127.0.0.1:8765", pose,
                   "coinft-current-20260925", 5.0, 0.125, on_state=observe)
    if len(data["samples"]) < 40 or owner() != who:
        raise ValueError("insufficient samples or owner changed")
    a, b = observations[0], observations[-1]
    rate = (b["state"]["frames"]-a["state"]["frames"])/(b["monotonic"]-a["monotonic"])
    if not 150 <= rate <= 250:
        raise ValueError("aggregate frame rate outside150–250Hz")
    data.update(owner=who, evidence=out.name, observations=observations,
                aggregate_rate=rate, capture_ok=True)
    print(json.dumps({"out": str(out), "evidence": data},
                     ensure_ascii=False, allow_nan=False, separators=(",", ":")))
except Exception as exc:
    print(json.dumps({"out": str(out.with_suffix(".failed.json")),
                      "evidence": {"capture_ok": False, "pose": pose,
                                   "owner": who, "error": repr(exc),
                                   "observations": observations}},
                     ensure_ascii=False, separators=(",", ":")))
    raise SystemExit(1)
~~~

This command emits complete compact JSON, not a file write. Use functions.exec store(toolResult) and output only exit/small metadata. Immediately notify the operator of completion/release; only then parse toolResult.output and persist full evidence through apply_patch. Allocate enough exec output budget for51 full states; do not print base data back to the chat. An owner preflight failure before capture is a setup failure; preserve its output too.

- [ ] Dry-run by using mock URL/time/owner inputs, not physical HTTP, to verify failed observations are retained and no HTTP POST/serial commands exist. Reuse Task1 successful/unsafe fixtures; callback rejection must abort immediately. Verify JSON serializes every observation (>=40 successful snapshots) and the selected out path is fresh.
- [ ] Request each physical state separately after prior window is saved; preserve chronological order:

| key | request |
|---|---|
| press_before | empty, hands/weights removed |
| press | center pure pressure, no additional shear |
| press_after | release, empty and settled |
| right_before | empty, unchanged fixture |
| right | upper relative to fixed lower PCB, −X / screen right |
| right_after | release, empty and settled |
| left_before | empty, unchanged fixture |
| left | upper relative to fixed lower PCB, +X / screen left |

On waiting/bad state/epoch change: stop that capture, notify release, retain failed evidence; never fit it. Do not ask harder force just to cross a threshold. Do not tare/reconnect to hide faults. Owner/epoch change invalidates the same-epoch input requirement and needs a separately agreed new acquisition sequence.

- [ ] Load eight successful files and fit/replay using actual code:
~~~python
import json
import statistics
from pathlib import Path
from calibration.shear_refit_replay import KEYS, fit_candidate, replay, passes
root = Path("calibration/shear_refit_20260928/fit")
windows = {k: json.loads((root/(k+".json")).read_text(encoding="utf-8")) for k in KEYS}
old = json.loads(Path("demo_web/shear_demo_profile.json").read_text(encoding="utf-8"))
baseline = [statistics.median(s["channels"][i] for s in windows["press_before"]["samples"])
            for i in range(12)]
candidate = fit_candidate(windows, old)
report = replay(candidate, old, windows, baseline)
print(json.dumps({"candidate": candidate, "baseline": baseline, "report": report,
                  "accepted": passes(report)}, ensure_ascii=False, allow_nan=False))
~~~
Persist full result with apply_patch to .superpowers/sdd/shear-refit-fitting-report-20260928.json; production profile remains unchanged. Build/replay failure is a stop condition, not permission to weaken gates.

- [ ] Review checkpoint: freeze candidate SHA256 and chosen baseline; no validation data has been captured or used to tune. No Git commit.

### Task 4: Independent repetition, candidate-only deployment and acceptance

**Interfaces:** Task2 replay/passes; frozen candidate from Task3. The eight validation windows use new physical loading actions, not renamed/subsampled fit observations.

- [ ] Collect eight validation windows with Task3's complete single-pose command (same order), but out directory calibration/shear_refit_20260928/validation. Request and await each state individually. Each pose must be physically released and re-applied; holding across two labeled windows is not an independent action.
- [ ] Replay without calling fit_candidate on validation:
~~~python
import json
from pathlib import Path
from calibration.shear_refit_replay import KEYS, replay, passes
frozen = json.loads(Path(".superpowers/sdd/shear-refit-fitting-report-20260928.json").read_text(encoding="utf-8"))
root = Path("calibration/shear_refit_20260928/validation")
windows = {k: json.loads((root/(k+".json")).read_text(encoding="utf-8")) for k in KEYS}
old = json.loads(Path("demo_web/shear_demo_profile.json").read_text(encoding="utf-8"))
report = replay(frozen["candidate"], old, windows, frozen["baseline"])
print(json.dumps({"report": report, "accepted": passes(report)},
                 ensure_ascii=False, allow_nan=False))
~~~
Add these checks to the validation command before replay:
~~~python
from datetime import datetime
fit_first = json.loads(Path("calibration/shear_refit_20260928/fit/press_before.json").read_text(encoding="utf-8"))
fit_last = json.loads(Path("calibration/shear_refit_20260928/fit/left.json").read_text(encoding="utf-8"))
assert all(w["owner"] == fit_first["owner"] for w in windows.values())
last = fit_last["samples"][-1]
first = windows["press_before"]["samples"][0]
assert last["f"] < first["f"]
assert datetime.fromisoformat(last["host"]) < datetime.fromisoformat(first["host"])
~~~
If stream was reopened or page reference intentionally changed, do not silently use an obsolete baseline; stop and report.
- [ ] Record independent validation result to .superpowers/sdd/shear-refit-independent-report-20260928.json. Failure leaves old live profile intact. If candidate adjusted, freeze the new candidate and collect new independent validation actions.
- [ ] Before production change: preserve current profile text and SHA256 via apply_patch in .superpowers/sdd/shear-refit-original-profile-20260928.json and manifest. Confirm protected file hashes from stream-recovery-final-manifest.json (all except profile) and current backend hash96EF5BBE88CEB9797686D1E6B1B2473B50360B0A9225E5FAC192CA6DDB913828.
- [ ] Construct deployment content, rather than overwriting normal/source conventions:
~~~python
import copy
import json
from pathlib import Path
old = json.loads(Path("demo_web/shear_demo_profile.json").read_text(encoding="utf-8"))
fit = json.loads(Path(".superpowers/sdd/shear-refit-fitting-report-20260928.json").read_text(encoding="utf-8"))
new = copy.deepcopy(old)
new["shear"] = fit["candidate"]["shear"]
new["evidence"] = fit["candidate"]["evidence"]
assert new["normal"] == old["normal"] == {"threshold":100, "span":600}
assert (new["version"],new["mode"],new["rightLabel"],new["leftLabel"]) == (1,"qualitative","−X","+X")
print(json.dumps(new, ensure_ascii=False, indent=2, allow_nan=False))
~~~
Use this exact output in apply_patch for demo_web/shear_demo_profile.json. No service restart needed; no UI code change.
- [ ] Run complete regressions and protected hashes again:
  & 'D:\conda\python.exe' -m unittest discover -s tests -v
  Expected all pass. The existing old real-data replay test currently contains a profile-dependent exact "24 zeros" historical assertion. If candidate changes that outcome, do not weaken it silently or change protected rendering to satisfy it: report the incompatibility and stop deployment until a narrow evidence-based test-fixture update is separately reviewed. Synthetic release/reversal tests still must pass unchanged.
- [ ] Refresh the page only after explicit empty confirmation, request one original demonstration-zero. Then operator verifies separate center, −X/right, +X/left, release/flat states. Do not claim inspected browser baseline when debugger access is unavailable.
- [ ] Wrong direction/false shear: restore saved original JSON with apply_patch; inspect served profile/hashes, keep service/firmware/trends unchanged. Preserve failed validation/operator feedback.
- [ ] Completion evidence: report file changes, all test results, exact window quality and animation gates, protected-hash comparison, operator direction feedback, remaining unmeasured limitations. Update PROJECT_LOG.md and progress file. "Fixed" requires independent replay and operator-visible direction; preparation alone is not completion.

## Self-review coverage / checkpoint

- Timing/quality/evidence preservation: Task1 plus Task3's owner/diagnostic callback.
- Existing builder validation preserved; current insufficient observations excluded: Task2/Task3.
- Common baseline, independent physical actions, frozen candidate, no validation tuning: Task3/Task4.
- Normal preserved, real JS execution, fixed signed/false-positive gates: Task2/Task4.
- Six-hundred-ms release/reversal and original trends/firmware/recovery: full regression and protected hashes in Task4.
- Deployment/rollback/operator-view limitations: Task4.
- Runtime evidence timestamps remain measured, no copying/upsampling or fabricated epochs.
- Python signatures and dict fields match the inspected current files; no new sensor protocol or dependency.
- Planning only: none of the code blocks above has been installed or executed against live hardware.
