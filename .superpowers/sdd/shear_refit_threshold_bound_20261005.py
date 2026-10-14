"""One offline background-bound threshold derivation and unchanged JS replay."""
import copy
import hashlib
import json
import math
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from calibration import shear_refit_replay as refit
from calibration.build_qualitative_demo_profile import _validate
from calibration.fit_demo_profile import residual

HERE = Path(__file__).resolve().parent
INPUT = HERE / "shear-refit-coefficient-softmargin-20261005.json"
OUTPUT = HERE / "shear-refit-threshold-bound-20261005.json"
ORDER = ("left_before", "left", "press_before", "press", "press_after", "right_before", "right", "right_after")
refit.KEYS = ORDER
PROFILE = ROOT / "demo_web/shear_demo_profile.json"


def main():
    prior_bytes = INPUT.read_bytes()
    prior = json.loads(prior_bytes)
    report = {"purpose": "one offline, background-derived threshold check using fixed soft-margin coefficients; in-sample only",
              "command": "D:/conda/python.exe -X utf8 coinft/.superpowers/sdd/shear_refit_threshold_bound_20261005.py",
              "prior_softmargin_report_sha256": hashlib.sha256(prior_bytes).hexdigest(),
              "source_files_changed": False, "production_files_changed": False,
              "limitations": ["The same captured windows supplied coefficients, background bound, and replay; this is not independent physical acceptance.",
                              "Recovery counters change from 30/2 to 31/3 at right_after; windows are not one uninterrupted sensor stream.",
                              "No deployment."],
              "sources": {}, "status": "started"}
    try:
        if prior["status"] != "replayed" or tuple(prior["sources"]) != ORDER:
            raise ValueError("unexpected prior report or source order")
        ref = prior["feature_basis"]["reference_offset"]
        baseline = prior["feature_basis"]["common_baseline"]
        leak = prior["feature_basis"]["press_leak"]
        weights_lp = prior["lp"]["weights_lp_scale"]
        norm = prior["lp"]["l2_weight_norm"]
        span_lp = 1.0
        safety_margin = 0.005
        if not math.isclose(math.hypot(*weights_lp), norm, rel_tol=1e-12) or norm <= 0:
            raise ValueError("prior coefficient norm mismatch")
        windows = {}
        for key in ORDER:
            entry = prior["sources"][key]
            path = ROOT / entry["path"]
            contents = path.read_bytes()
            if hashlib.sha256(contents).hexdigest() != entry["sha256"]:
                raise ValueError(f"source SHA changed: {key}")
            original = json.loads(contents)
            if original["owner"] != entry["owner"] or original["pose"] != entry["original_pose"]:
                raise ValueError(f"source provenance changed: {key}")
            offsets = [[s["raw"][i] - s["channels"][i] for i in range(12)] for s in original["samples"]]
            if any(offset != offsets[0] for offset in offsets) or offsets[0] != entry["original_offset"]:
                raise ValueError(f"raw-channel offset changed: {key}")
            derived = copy.deepcopy(original)
            derived["pose"] = key
            derived["evidence"] = f"threshold_bound_aligned_{key}.json"
            for sample in derived["samples"]:
                sample["channels"] = [sample["raw"][i] - ref[i] for i in range(12)]
            windows[key] = derived
            report["sources"][key] = {"path": entry["path"], "sha256": entry["sha256"],
                "original_pose": original["pose"], "derived_evidence": derived["evidence"],
                "owner": original["owner"], "sample_count": len(original["samples"]),
                "first_host": original["samples"][0]["host"], "last_host": original["samples"][-1]["host"],
                "first_frame": original["samples"][0]["f"], "last_frame": original["samples"][-1]["f"],
                "original_offset": offsets[0], "recovery_first": entry["recovery_first"],
                "recovery_last": entry["recovery_last"]}
        refit.ordered(windows)
        _validate(windows)
        actual_baseline = [statistics.median(s["channels"][i] for s in windows["press_before"]["samples"]) for i in range(12)]
        if actual_baseline != baseline:
            raise ValueError("common baseline changed")
        scores = {}
        for key in ORDER:
            scores[key] = [sum(a*b for a, b in zip(
                residual([s["channels"][i] - baseline[i] for i in range(12)], leak), weights_lp))
                for s in windows[key]["samples"]]
        background_keys = tuple(key for key in ORDER if key not in ("left", "right"))
        B = max(abs(value) for key in background_keys for value in scores[key])
        if not math.isclose(B, prior["lp"]["max_background_abs_score"], rel_tol=1e-12, abs_tol=1e-12):
            raise ValueError("background bound changed")
        # In qualitativeShear, active magnitude uses a 0.6*t continuation
        # and a 0.85*span denominator. The 0.05 idle tolerance gives this
        # one lower bound; add a fixed numerical safety margin.
        t = (B - 0.05 * 0.85 * span_lp) / 0.6 + safety_margin
        report["threshold_rule"] = {"background_worst_abs_lp_scale": B, "idle_tolerance": 0.05,
            "continuation_factor": 0.6, "display_span_factor": 0.85,
            "span_lp_scale": span_lp, "safety_margin_lp_scale": safety_margin,
            "formula": "t = (B - 0.05 * 0.85 * span) / 0.6 + 0.005",
            "derived_threshold_lp_scale": t, "strictly_exceeds_background": t > B,
            "background_keys": background_keys}
        if not t > B:
            report["status"] = "bound_not_usable"
            report["replay"] = None
            return
        old_bytes = PROFILE.read_bytes()
        old = json.loads(old_bytes)
        if old["normal"] != {"threshold": 100, "span": 600}:
            raise ValueError("unexpected protected normal configuration")
        candidate = copy.deepcopy(prior["candidate"])
        if candidate["shear"]["pressLeak"] != leak or not all(
                math.isclose(candidate["shear"]["weights"][i], weights_lp[i]/norm, rel_tol=1e-12)
                for i in range(8)):
            raise ValueError("soft-margin coefficients changed")
        candidate["shear"]["threshold"] = t / norm
        candidate["shear"]["span"] = span_lp / norm
        candidate["evidence"] = [windows[key]["evidence"] for key in ORDER]
        report["feature_basis"] = {"reference_source": prior["feature_basis"]["reference_source"],
            "reference_offset": ref, "common_baseline": baseline, "press_leak": leak,
            "all_sample_scores_lp_scale": scores}
        report["production_profile"] = {"path": str(PROFILE.relative_to(ROOT)).replace("\\", "/"),
            "sha256": hashlib.sha256(old_bytes).hexdigest(), "normal": old["normal"]}
        report["candidate"] = candidate
        report["coefficient_scale"] = {"l2_norm": norm, "weights_divisor": norm,
            "threshold": t/norm, "span": span_lp/norm,
            "weights_fixed_from_prior": True, "press_leak_fixed_from_prior": True}
        replay = refit.replay(candidate, old, windows, baseline)
        report["replay"] = replay
        report["accepted_in_sample"] = refit.passes(replay)
        report["gates"] = {"normal_exactly_unchanged": replay["normalUnchanged"],
            "steady_state_starts_ms": 600, "idle_press_abs_max": 0.05,
            "right_active_min": 0.2, "left_active_max": -0.2,
            "active_fraction_min": 0.8, "right_reverse_min": -0.05,
            "left_reverse_max": 0.05, "by_window": {}, "failed": []}
        for key, values in replay["poses"].items():
            summary = {"count": len(values), "min": min(values),
                       "median": statistics.median(values), "max": max(values)}
            if key == "right":
                summary["active_count"] = sum(v >= 0.2 for v in values)
                summary["active_fraction"] = summary["active_count"] / len(values)
                summary["reverse_count"] = sum(v < -0.05 for v in values)
                if summary["active_fraction"] < 0.8:
                    report["gates"]["failed"].append("right_active_fraction")
                if summary["reverse_count"]:
                    report["gates"]["failed"].append("right_reverse")
            elif key == "left":
                summary["active_count"] = sum(v <= -0.2 for v in values)
                summary["active_fraction"] = summary["active_count"] / len(values)
                summary["reverse_count"] = sum(v > 0.05 for v in values)
                if summary["active_fraction"] < 0.8:
                    report["gates"]["failed"].append("left_active_fraction")
                if summary["reverse_count"]:
                    report["gates"]["failed"].append("left_reverse")
            else:
                summary["outside_idle_count"] = sum(abs(v) > 0.05 for v in values)
                if summary["outside_idle_count"]:
                    report["gates"]["failed"].append(f"{key}_outside_idle")
            report["gates"]["by_window"][key] = summary
        if not replay["normalUnchanged"]:
            report["gates"]["failed"].append("normal_changed")
        report["status"] = "replayed"
    except Exception as exc:
        report["status"] = "error"
        report["error"] = {"type": type(exc).__name__, "message": str(exc)}
    finally:
        report["source_hashes_verified_after_run"] = all(hashlib.sha256((ROOT / entry["path"]).read_bytes()).hexdigest() == entry["sha256"] for entry in report["sources"].values())
        OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
        print(json.dumps({"status": report["status"], "accepted_in_sample": report.get("accepted_in_sample"),
                          "failed_gates": report.get("gates", {}).get("failed"),
                          "error": report.get("error"), "report": str(OUTPUT)}, ensure_ascii=True))


if __name__ == "__main__":
    main()
