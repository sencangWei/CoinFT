"""Offline, reproducible alignment and replay of the specified eight captures."""
import copy
import hashlib
import json
import statistics
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from calibration import shear_refit_replay as refit
from calibration.fit_demo_profile import signed_score

REPORT = Path(__file__).with_name("shear-refit-reuse-alignment-report-20261005.json")
OLD_DIR = ROOT / "calibration/shear_refit_20260928/fit"
NEW_DIR = ROOT / "calibration/shear_refit_20261005_after_button/fit"
PROFILE = ROOT / "demo_web/shear_demo_profile.json"
SOURCES = {key: (NEW_DIR if key in ("left_before", "left") else OLD_DIR) / ("press_before.json" if key == "left_before" else f"{key}.json") for key in refit.KEYS}
OWNER = {"pid": 87952, "created": 1791188496.384482}


def median_vector(samples, field):
    return [statistics.median(row[field][i] for row in samples) for i in range(12)]


def main():
    report = {"purpose": "offline exploratory reuse fit/replay; no deployment or independent physical acceptance",
              "command": "D:/conda/python.exe coinft/.superpowers/sdd/shear_refit_reuse_alignment_20261005.py",
              "transform": "For every sample set derived channels[i] = original raw[i] - fixed new unloaded-control raw-minus-channels offset[i]. Raw, host, frame, owner and source files remain unchanged.",
              "limitations": ["Captured windows span interrupted/recovered serial stream epochs; monotonic frames, timestamps and unchanged backend owner do not prove one uninterrupted sensor stream.",
                              "These captures are fitting inputs and replayed in sample; no independent physical validation was performed."],
              "excluded_prior_left_before": "calibration/shear_refit_20260928/fit/left_before.json",
              "sources": {}, "status": "started"}
    try:
        originals = {}
        for key, path in SOURCES.items():
            source = path.read_bytes()
            window = json.loads(source)
            originals[key] = window
            offsets = [[s["raw"][i] - s["channels"][i] for i in range(12)] for s in window["samples"]]
            if any(offset != offsets[0] for offset in offsets):
                raise ValueError(f"raw-channel offset changes within {key}")
            if window["owner"] != OWNER:
                raise ValueError(f"owner mismatch: {key}")
            recovery = [obs["state"]["recovery"] for obs in window.get("observations", []) if "recovery" in obs.get("state", {})]
            report["sources"][key] = {"path": str(path.relative_to(ROOT)).replace("\\", "/"),
                "sha256": hashlib.sha256(source).hexdigest(), "original_pose": window["pose"],
                "derived_evidence": f"aligned_{key}.json", "owner": window["owner"],
                "sample_count": len(window["samples"]),
                "first_host": window["samples"][0]["host"], "last_host": window["samples"][-1]["host"],
                "first_frame": window["samples"][0]["f"], "last_frame": window["samples"][-1]["f"],
                "original_offset": offsets[0],
                "recovery_first": recovery[0] if recovery else None,
                "recovery_last": recovery[-1] if recovery else None,
                "original_channels_median": median_vector(window["samples"], "channels"),
                "raw_median": median_vector(window["samples"], "raw")}
        reference = report["sources"]["left_before"]["original_offset"]
        report["reference_offset"] = reference
        report["reference_source"] = report["sources"]["left_before"]["path"]
        windows = {}
        for key, original in originals.items():
            derived = copy.deepcopy(original)
            derived["pose"] = key
            derived["evidence"] = f"aligned_{key}.json"
            for sample in derived["samples"]:
                sample["channels"] = [sample["raw"][i] - reference[i] for i in range(12)]
            windows[key] = derived
            report["sources"][key]["aligned_channels_median"] = median_vector(derived["samples"], "channels")
            report["sources"][key]["duration_seconds"] = (datetime.fromisoformat(derived["samples"][-1]["host"])-datetime.fromisoformat(derived["samples"][0]["host"])).total_seconds()
        baseline = median_vector(windows["press_before"]["samples"], "channels")
        report["common_replay_baseline"] = baseline
        old_bytes = PROFILE.read_bytes()
        old = json.loads(old_bytes)
        report["production_profile"] = {"path": str(PROFILE.relative_to(ROOT)).replace("\\", "/"), "sha256": hashlib.sha256(old_bytes).hexdigest()}
        candidate = refit.fit_candidate(windows, old)
        report["candidate"] = candidate
        report["status"] = "fitted"
        replay = refit.replay(candidate, old, windows, baseline)
        report["replay"] = replay
        report["accepted"] = refit.passes(replay)
        report["gates"] = {"normal_exactly_unchanged": replay["normalUnchanged"], "steady_state_starts_ms": 600,
                           "idle_and_press_abs_max": 0.05, "right_active_threshold": 0.20,
                           "left_active_threshold": -0.20, "active_fraction_min": 0.80,
                           "right_reverse_min": -0.05, "left_reverse_max": 0.05,
                           "by_window": {}}
        for key, values in replay["poses"].items():
            gate = report["gates"]["by_window"].setdefault(key, {})
            gate.update({"count": len(values), "min": min(values), "max": max(values),
                         "median": statistics.median(values)})
            if key == "right":
                gate.update({"active_count": sum(value >= 0.20 for value in values),
                             "active_fraction": sum(value >= 0.20 for value in values) / len(values),
                             "reverse_count": sum(value < -0.05 for value in values)})
            elif key == "left":
                gate.update({"active_count": sum(value <= -0.20 for value in values),
                             "active_fraction": sum(value <= -0.20 for value in values) / len(values),
                             "reverse_count": sum(value > 0.05 for value in values)})
            else:
                gate["outside_idle_count"] = sum(abs(value) > 0.05 for value in values)
        left_rows = replay["samples"]["left"]
        steady_rows = [row for row in left_rows if row["ms"] >= 600]
        midpoint = len(steady_rows) // 2
        report["left_replay_progression"] = {
            "early": {"count": midpoint, "active_count": sum(row["shear"] <= -0.20 for row in steady_rows[:midpoint]),
                      "median_shear": statistics.median(row["shear"] for row in steady_rows[:midpoint])},
            "late": {"count": len(steady_rows) - midpoint, "active_count": sum(row["shear"] <= -0.20 for row in steady_rows[midpoint:]),
                     "median_shear": statistics.median(row["shear"] for row in steady_rows[midpoint:])}}
        left_samples = windows["left"]["samples"]
        first_time = datetime.fromisoformat(left_samples[0]["host"])
        scores = [signed_score([sample["channels"][i] - baseline[i] for i in range(12)],
                               candidate["shear"]["pressLeak"], candidate["shear"]["weights"])
                  for sample in left_samples if (datetime.fromisoformat(sample["host"])-first_time).total_seconds() >= 0.6]
        report["left_signed_score"] = {"basis": "aligned channels minus one common press_before median, same input passed to surface.js",
                                       "threshold": candidate["shear"]["threshold"],
                                       "count": len(scores), "min": min(scores), "median": statistics.median(scores),
                                       "max": max(scores),
                                       "count_at_or_below_negative_threshold": sum(score <= -candidate["shear"]["threshold"] for score in scores),
                                       "early_median": statistics.median(scores[:midpoint]),
                                       "late_median": statistics.median(scores[midpoint:])}
        report["status"] = "replayed"
    except Exception as exc:
        report["status"] = "error"
        report["error"] = {"type": type(exc).__name__, "message": str(exc)}
    REPORT.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    print(json.dumps({"status": report["status"], "accepted": report.get("accepted"), "error": report.get("error"), "report": str(REPORT)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
