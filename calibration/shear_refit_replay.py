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
