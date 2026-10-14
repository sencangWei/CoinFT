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

