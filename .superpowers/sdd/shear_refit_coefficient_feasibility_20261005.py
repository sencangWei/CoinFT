"""Offline coefficient-capacity check under fixed sample-wise separation bounds."""
import copy
import hashlib
import json
import math
import statistics
import sys
from pathlib import Path

from scipy.optimize import linprog

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from calibration import shear_refit_replay as refit
from calibration.fit_demo_profile import contrast, normal_score, residual

HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "shear-refit-coefficient-feasibility-20261005.json"
SOURCE_DIR = ROOT / "calibration/shear_refit_20261005_after_button/fit"
NAMES = {"left_before": "left_repeat_after.json", "left": "left_confirmed_repeat.json",
         "press_before": "current_controls_empty.json", "press": "current_controls_press.json",
         "press_after": "current_controls_press_after.json", "right_before": "current_controls_right_before.json",
         "right": "current_controls_right.json", "right_after": "current_controls_right_after.json"}
ORDER = ("left_before", "left", "press_before", "press", "press_after", "right_before", "right", "right_after")
refit.KEYS = ORDER
PROFILE_PATH = ROOT / "demo_web/shear_demo_profile.json"
OWNER = {"pid": 87952, "created": 1791188496.384482}


def median_vector(samples, field):
    return [statistics.median(row[field][i] for row in samples) for i in range(12)]


def main():
    report = {"purpose": "offline feasibility of coefficients in existing qualitative formula, not a fitted acceptance result",
              "command": "D:/conda/python.exe -X utf8 coinft/.superpowers/sdd/shear_refit_coefficient_feasibility_20261005.py",
              "constraints": {"background_abs_max": 0.55, "right_min": 1.2, "left_max": -1.2,
                              "weight_sum": 0, "objective": "minimize L1 norm of eight weights using eight absolute-value auxiliaries"},
              "limitations": ["All eight windows are training data for this feasibility check; a passing replay is in sample and may overfit.",
                              "Recovery counters change from 30/2 to 31/3 at right_after; this is not one uninterrupted sensor stream.",
                              "No independent physical acceptance or deployment."],
              "sources": {}, "status": "started"}
    try:
        originals = {}
        for key in ORDER:
            path = SOURCE_DIR / NAMES[key]
            source_bytes = path.read_bytes()
            original = json.loads(source_bytes)
            originals[key] = original
            offsets = [[s["raw"][i] - s["channels"][i] for i in range(12)] for s in original["samples"]]
            if any(vector != offsets[0] for vector in offsets):
                raise ValueError(f"raw-channel offset changes within {key}")
            if original["owner"] != OWNER:
                raise ValueError(f"owner mismatch: {key}")
            recovery = [o["state"]["recovery"] for o in original.get("observations", []) if "recovery" in o.get("state", {})]
            report["sources"][key] = {"path": str(path.relative_to(ROOT)).replace("\\", "/"),
                "sha256": hashlib.sha256(source_bytes).hexdigest(), "original_pose": original["pose"],
                "derived_evidence": f"feasibility_aligned_{key}.json", "owner": original["owner"],
                "sample_count": len(original["samples"]), "first_host": original["samples"][0]["host"],
                "last_host": original["samples"][-1]["host"], "first_frame": original["samples"][0]["f"],
                "last_frame": original["samples"][-1]["f"], "original_offset": offsets[0],
                "recovery_first": {name: recovery[0][name] for name in ("attempts", "successes")},
                "recovery_last": {name: recovery[-1][name] for name in ("attempts", "successes")}}
        refit.ordered(originals)
        from calibration.build_qualitative_demo_profile import _validate
        reference = report["sources"]["press_before"]["original_offset"]
        windows = {}
        for key in ORDER:
            derived = copy.deepcopy(originals[key])
            derived["pose"] = key
            derived["evidence"] = f"feasibility_aligned_{key}.json"
            for sample in derived["samples"]:
                sample["channels"] = [sample["raw"][i] - reference[i] for i in range(12)]
            windows[key] = derived
            report["sources"][key]["aligned_channels_median"] = median_vector(derived["samples"], "channels")
        _validate(windows)
        baseline = median_vector(windows["press_before"]["samples"], "channels")
        report["feature_basis"] = {"raw_alignment_reference_source": report["sources"]["press_before"]["path"],
                                   "raw_alignment_reference_offset": reference,
                                   "common_replay_baseline": baseline,
                                   "definition": "residual(aligned sample channels - one common press_before median, fixed pressLeak); residual is 8-channel contrast minus pressLeak * normalScore"}
        # The existing fitter computes pressLeak from the press action centered on
        # the average of its two unloaded control medians.
        before = median_vector(windows["press_before"]["samples"], "channels")
        after = median_vector(windows["press_after"]["samples"], "channels")
        press_base = [(a + b) / 2 for a, b in zip(before, after)]
        local_press = [[sample["channels"][i] - press_base[i] for i in range(12)]
                       for sample in windows["press"]["samples"]]
        press_normal = max(statistics.median(normal_score(ch) for ch in local_press), 1)
        leak = [statistics.median(contrast(ch)[i] for ch in local_press) / press_normal for i in range(8)]
        report["feature_basis"]["press_leak"] = leak
        report["feature_basis"]["press_normal_denominator"] = press_normal
        old_bytes = PROFILE_PATH.read_bytes()
        old = json.loads(old_bytes)
        if old["normal"] != {"threshold": 100, "span": 600}:
            raise ValueError("unexpected protected normal configuration")
        report["production_profile"] = {"path": str(PROFILE_PATH.relative_to(ROOT)).replace("\\", "/"),
                                        "sha256": hashlib.sha256(old_bytes).hexdigest(), "normal": old["normal"]}
        features = {key: [residual([s["channels"][i] - baseline[i] for i in range(12)], leak)
                          for s in windows[key]["samples"]] for key in ORDER}
        background = [key for key in ORDER if key not in ("right", "left")]
        inequalities = []
        rhs = []
        for key in background:
            for vector in features[key]:
                inequalities.extend([vector + [0.0] * 8, [-v for v in vector] + [0.0] * 8])
                rhs.extend([0.55, 0.55])
        for vector in features["right"]:
            inequalities.append([-v for v in vector] + [0.0] * 8)
            rhs.append(-1.2)
        for vector in features["left"]:
            inequalities.append(vector + [0.0] * 8)
            rhs.append(-1.2)
        for i in range(8):
            positive = [0.0] * 16
            negative = [0.0] * 16
            positive[i], positive[8+i] = 1.0, -1.0
            negative[i], negative[8+i] = -1.0, -1.0
            inequalities.extend([positive, negative])
            rhs.extend([0.0, 0.0])
        result = linprog([0.0] * 8 + [1.0] * 8, A_ub=inequalities, b_ub=rhs,
                         A_eq=[[1.0] * 8 + [0.0] * 8], b_eq=[0.0],
                         bounds=[(None, None)] * 8 + [(0, None)] * 8, method="highs")
        report["lp"] = {"success": bool(result.success), "status": int(result.status),
                        "message": str(result.message), "objective": float(result.fun) if result.fun is not None else None,
                        "inequality_count": len(rhs), "equality_count": 1,
                        "sample_counts": {key: len(rows) for key, rows in features.items()}}
        if not result.success:
            report["status"] = "infeasible" if result.status == 2 else "optimizer_error"
            report["candidate"] = None
            report["replay"] = None
            report["replay_not_run_reason"] = "No coefficients satisfy the exact LP constraints."
            return
        weights = [float(x) for x in result.x[:8]]
        norm = math.hypot(*weights)
        if norm <= 0:
            raise ValueError("feasible LP returned zero coefficients")
        all_scores = {key: [sum(a*b for a, b in zip(vector, weights)) for vector in rows]
                      for key, rows in features.items()}
        max_background = max(abs(score) for key in background for score in all_scores[key])
        min_right = min(all_scores["right"])
        max_left = max(all_scores["left"])
        if (max_background > 0.55 + 1e-7 or min_right < 1.2 - 1e-7 or
                max_left > -1.2 + 1e-7 or abs(sum(weights)) > 1e-7):
            raise ValueError("LP numerical solution violates exact requested constraints")
        report["lp"].update({"weights_lp_scale": weights, "absolute_auxiliaries": [float(x) for x in result.x[8:]],
                             "weight_l2_norm": norm, "sum_weights": sum(weights),
                             "max_background_abs_score": max_background, "min_right_score": min_right,
                             "max_left_score": max_left, "all_sample_scores_lp_scale": all_scores})
        candidate = copy.deepcopy(old)
        candidate["mode"] = "qualitative"
        candidate["shear"] = {"enabled": True, "weights": [weight / norm for weight in weights],
                              "pressLeak": leak, "threshold": 1.0 / norm, "span": 1.0 / norm}
        candidate["evidence"] = [windows[key]["evidence"] for key in ORDER]
        report["candidate"] = candidate
        replay = refit.replay(candidate, old, windows, baseline)
        report["replay"] = replay
        report["accepted_in_sample"] = refit.passes(replay)
        report["gates"] = {"normal_exactly_unchanged": replay["normalUnchanged"],
                           "steady_state_starts_ms": 600, "idle_press_abs_max": 0.05,
                           "right_active_min": 0.2, "left_active_max": -0.2,
                           "active_fraction_min": 0.8, "right_reverse_min": -0.05,
                           "left_reverse_max": 0.05, "by_window": {}}
        for key, values in replay["poses"].items():
            summary = {"count": len(values), "min": min(values), "median": statistics.median(values), "max": max(values)}
            if key == "right":
                summary.update({"active_count": sum(v >= 0.2 for v in values),
                                "reverse_count": sum(v < -0.05 for v in values)})
            elif key == "left":
                summary.update({"active_count": sum(v <= -0.2 for v in values),
                                "reverse_count": sum(v > 0.05 for v in values)})
            else:
                summary["outside_idle_count"] = sum(abs(v) > 0.05 for v in values)
            report["gates"]["by_window"][key] = summary
        report["status"] = "replayed"
    except Exception as exc:
        report["status"] = "error"
        report["error"] = {"type": type(exc).__name__, "message": str(exc)}
    finally:
        report["source_hashes_verified_after_run"] = all(hashlib.sha256((ROOT / item["path"]).read_bytes()).hexdigest() == item["sha256"] for item in report["sources"].values())
        OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
        print(json.dumps({"status": report["status"], "lp_status": report.get("lp", {}).get("status"),
                          "accepted_in_sample": report.get("accepted_in_sample"), "error": report.get("error"),
                          "report": str(OUTPUT)}, ensure_ascii=True))


if __name__ == "__main__":
    main()
