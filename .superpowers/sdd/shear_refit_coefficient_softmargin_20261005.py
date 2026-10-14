"""One bounded offline soft-margin coefficient attempt with unchanged replay gates."""
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
from calibration.build_qualitative_demo_profile import _validate
from calibration.fit_demo_profile import residual

HERE = Path(__file__).resolve().parent
INPUT_REPORT = HERE / "shear-refit-coefficient-feasibility-20261005.json"
OUTPUT = HERE / "shear-refit-coefficient-softmargin-20261005.json"
PROFILE = ROOT / "demo_web/shear_demo_profile.json"
ORDER = ("left_before", "left", "press_before", "press", "press_after", "right_before", "right", "right_after")
refit.KEYS = ORDER
OWNER = {"pid": 87952, "created": 1791188496.384482}


def main():
    prior_bytes = INPUT_REPORT.read_bytes()
    prior = json.loads(prior_bytes)
    report = {"purpose": "single offline soft-margin coefficient attempt, in-sample only; no deployment",
              "command": "D:/conda/python.exe -X utf8 coinft/.superpowers/sdd/shear_refit_coefficient_softmargin_20261005.py",
              "prior_feasibility_report_sha256": hashlib.sha256(prior_bytes).hexdigest(),
              "constraints": {"idle_press_abs_max_lp_scale": 0.55,
                              "all_loaded_wrong_direction_floor_lp_scale": -0.55,
                              "right_target_lp_scale": 1.2, "left_target_lp_scale": -1.2,
                              "weight_sum": 0, "objective": "sum of loaded-point hinge slacks + 0.0001 * L1(weights)",
                              "time_limit_seconds": 10.0},
              "limitations": ["All optimization and replay windows are the same training set; a passing replay is in sample and may overfit.",
                              "Recovery counters change from 30/2 to 31/3 at right_after; windows are not one uninterrupted sensor stream.",
                              "No independent physical acceptance or deployment."],
              "sources": {}, "status": "started"}
    try:
        if prior["status"] != "infeasible" or tuple(prior["sources"]) != ORDER:
            raise ValueError("unexpected prior report or source order")
        reference = prior["feature_basis"]["raw_alignment_reference_offset"]
        baseline = prior["feature_basis"]["common_replay_baseline"]
        leak = prior["feature_basis"]["press_leak"]
        windows = {}
        for key in ORDER:
            entry = prior["sources"][key]
            path = ROOT / entry["path"]
            contents = path.read_bytes()
            if hashlib.sha256(contents).hexdigest() != entry["sha256"]:
                raise ValueError(f"source SHA changed: {key}")
            original = json.loads(contents)
            if original["owner"] != OWNER:
                raise ValueError(f"owner changed: {key}")
            offsets = [[s["raw"][i] - s["channels"][i] for i in range(12)] for s in original["samples"]]
            if any(offset != offsets[0] for offset in offsets) or offsets[0] != entry["original_offset"]:
                raise ValueError(f"raw-channel offset changed: {key}")
            derived = copy.deepcopy(original)
            derived["pose"] = key
            derived["evidence"] = f"softmargin_aligned_{key}.json"
            for sample in derived["samples"]:
                sample["channels"] = [sample["raw"][i] - reference[i] for i in range(12)]
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
        current_baseline = [statistics.median(s["channels"][i] for s in windows["press_before"]["samples"]) for i in range(12)]
        if current_baseline != baseline:
            raise ValueError("common baseline changed")
        report["feature_basis"] = {"definition": "residual(raw-aligned channels minus one common press_before median, fixed existing-builder pressLeak)",
                                   "reference_source": prior["feature_basis"]["raw_alignment_reference_source"],
                                   "reference_offset": reference, "common_baseline": baseline,
                                   "press_leak": leak}
        features = {key: [residual([s["channels"][i] - baseline[i] for i in range(12)], leak)
                          for s in windows[key]["samples"]] for key in ORDER}
        loaded = [(key, i, vector) for key in ("right", "left")
                  for i, vector in enumerate(features[key])]
        nslack = len(loaded)
        nvar = 16 + nslack
        A, b = [], []
        def row(vector, slack_index=None, slack_value=0):
            result = list(vector) + [0.0] * (nvar - 8)
            if slack_index is not None:
                result[16 + slack_index] = slack_value
            return result
        for key in ORDER:
            if key in ("right", "left"):
                continue
            for vector in features[key]:
                A.extend((row(vector), row([-v for v in vector])))
                b.extend((0.55, 0.55))
        for j, (key, _, vector) in enumerate(loaded):
            if key == "right":
                A.extend((row([-v for v in vector]), row([-v for v in vector], j, -1)))
            else:
                A.extend((row(vector), row(vector, j, -1)))
            b.extend((0.55, -1.2))
        for i in range(8):
            pos, neg = [0.0] * nvar, [0.0] * nvar
            pos[i], pos[8+i] = 1, -1
            neg[i], neg[8+i] = -1, -1
            A.extend((pos, neg))
            b.extend((0.0, 0.0))
        result = linprog([0.0]*8 + [0.0001]*8 + [1.0]*nslack,
                         A_ub=A, b_ub=b, A_eq=[[1.0]*8 + [0.0]*(nvar-8)], b_eq=[0.0],
                         bounds=[(None, None)]*8 + [(0, None)]*(8+nslack),
                         method="highs", options={"time_limit": 10.0})
        report["lp"] = {"success": bool(result.success), "status": int(result.status),
                        "message": str(result.message), "objective": float(result.fun) if result.fun is not None else None,
                        "inequality_count": len(b), "loaded_slack_count": nslack,
                        "sample_counts": {key: len(rows) for key, rows in features.items()}}
        if not result.success:
            report["status"] = "infeasible" if result.status == 2 else "optimizer_error"
            report["candidate"] = None
            report["replay"] = None
            return
        weights = [float(value) for value in result.x[:8]]
        auxiliaries = [float(value) for value in result.x[8:16]]
        slacks = [float(value) for value in result.x[16:]]
        norm = math.hypot(*weights)
        if norm <= 0:
            raise ValueError("zero coefficient vector")
        scores = {key: [sum(a*b for a, b in zip(vector, weights)) for vector in rows]
                  for key, rows in features.items()}
        background_max = max(abs(value) for key in ORDER if key not in ("left", "right") for value in scores[key])
        right_min = min(scores["right"])
        left_max = max(scores["left"])
        if background_max > 0.55+1e-7 or right_min < -0.55-1e-7 or left_max > 0.55+1e-7 or abs(sum(weights)) > 1e-7:
            raise ValueError("LP numerical result violates hard bounds")
        report["lp"].update({"weights_lp_scale": weights, "absolute_auxiliaries": auxiliaries,
                             "slacks": [{"key": key, "sample_index": i, "value": slacks[j]}
                                        for j, (key, i, _) in enumerate(loaded)],
                             "total_hinge_slack": sum(slacks), "l1_weight_norm": sum(abs(v) for v in weights),
                             "l2_weight_norm": norm, "sum_weights": sum(weights),
                             "max_background_abs_score": background_max, "min_right_score": right_min,
                             "max_left_score": left_max, "score_fractions": {
                                 "right_at_least_1p2": sum(v >= 1.2-1e-8 for v in scores["right"])/len(scores["right"]),
                                 "left_at_most_minus_1p2": sum(v <= -1.2+1e-8 for v in scores["left"])/len(scores["left"])},
                             "all_sample_scores_lp_scale": scores})
        old_bytes = PROFILE.read_bytes()
        old = json.loads(old_bytes)
        if old["normal"] != {"threshold": 100, "span": 600}:
            raise ValueError("unexpected protected normal configuration")
        candidate = copy.deepcopy(old)
        candidate["mode"] = "qualitative"
        candidate["normal"] = copy.deepcopy(old["normal"])
        candidate["shear"] = {"enabled": True, "weights": [v/norm for v in weights],
                              "pressLeak": leak, "threshold": 1/norm, "span": 1/norm}
        candidate["evidence"] = [windows[key]["evidence"] for key in ORDER]
        report["production_profile"] = {"path": str(PROFILE.relative_to(ROOT)).replace("\\", "/"),
                                        "sha256": hashlib.sha256(old_bytes).hexdigest()}
        report["candidate"] = candidate
        report["coefficient_scale"] = {"unit_l2_norm": norm, "weights_divisor": norm,
                                       "threshold": 1/norm, "span": 1/norm}
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
        right_gate = report["gates"]["by_window"]["right"]
        left_gate = report["gates"]["by_window"]["left"]
        right_gate["active_fraction"] = right_gate["active_count"] / right_gate["count"]
        left_gate["active_fraction"] = left_gate["active_count"] / left_gate["count"]
        report["gates"]["failed"] = (
            ([] if replay["normalUnchanged"] else ["normal_exactly_unchanged"]) +
            [f"{key}_outside_idle" for key in ORDER if key not in ("left", "right")
             and report["gates"]["by_window"][key]["outside_idle_count"]] +
            ([] if right_gate["active_fraction"] >= 0.8 else ["right_active_fraction"]) +
            ([] if left_gate["active_fraction"] >= 0.8 else ["left_active_fraction"]) +
            ([] if right_gate["reverse_count"] == 0 else ["right_reverse"]) +
            ([] if left_gate["reverse_count"] == 0 else ["left_reverse"]))
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
