"""Run the existing offline alignment/replay helper on corrected current controls."""
import hashlib
import json
import math
import runpy
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
helper = runpy.run_path(str(HERE / "shear_refit_reuse_alignment_20261005.py"))
root = helper["ROOT"]
refit = helper["refit"]
refit.KEYS = ("left_before", "left", "press_before", "press", "press_after",
              "right_before", "right", "right_after")
source_dir = root / "calibration/shear_refit_20261005_after_button/fit"
names = {"left_before": "left_repeat_after.json", "left": "left_confirmed_repeat.json",
         "press_before": "current_controls_empty.json", "press": "current_controls_press.json",
         "press_after": "current_controls_press_after.json",
         "right_before": "current_controls_right_before.json", "right": "current_controls_right.json",
         "right_after": "current_controls_right_after.json"}
helper["SOURCES"].clear()
helper["SOURCES"].update({key: source_dir / names[key] for key in refit.KEYS})
ordered_windows = {key: json.loads(path.read_text(encoding="utf-8")) for key, path in helper["SOURCES"].items()}
refit.ordered(ordered_windows)
output = HERE / "shear-refit-current-controls-report-20261005.json"
helper["main"].__globals__["REPORT"] = output
helper["main"]()
prior_output = output
report = json.loads(prior_output.read_text(encoding="utf-8"))
if len(report["sources"]) == 8 and "common_replay_baseline" in report:
    prior_reference = report["reference_offset"]
    current_reference = report["sources"]["press_before"]["original_offset"]
    delta = [prior_reference[i] - current_reference[i] for i in range(12)]
    for source in report["sources"].values():
        source["aligned_channels_median"] = [source["aligned_channels_median"][i] + delta[i] for i in range(12)]
    report["common_replay_baseline"] = [report["common_replay_baseline"][i] + delta[i] for i in range(12)]
    report["reference_offset"] = current_reference
    report["reference_source"] = report["sources"]["press_before"]["path"]
    report["reference_equivalence"] = "Fit subtracts a local unloaded median per action; replay subtracts the same common press_before median. Changing the fixed raw-alignment reference adds one constant vector to all channels and to the replay baseline, so candidate and per-sample replay are identical. Reported aligned medians and baseline use current_controls_empty as reference."
    recoveries = {key: {"first": {k: entry["recovery_first"][k] for k in ("attempts", "successes")},
                         "last": {k: entry["recovery_last"][k] for k in ("attempts", "successes")}}
                  for key, entry in report["sources"].items()}
    report["recovery_counters"] = recoveries
    report["stable_recovery_within_windows"] = all(item["first"] == item["last"] for item in recoveries.values())
    report["homogeneous_recovery_across_windows"] = len({tuple(item["first"].values()) for item in recoveries.values()}) == 1
    report["same_stream_provenance_gate"] = report["stable_recovery_within_windows"] and report["homogeneous_recovery_across_windows"]
    report["fit_replay_gate"] = report.get("accepted", False) if report["status"] == "replayed" else None
if report["status"] == "error" and report.get("error", {}).get("message") == "qualitative directions do not separate from background":
    from calibration.fit_demo_profile import contrast, normal_score, percentile, residual, signed_score
    ref = report["reference_offset"]
    data = {}
    empty = []
    raw = {key: json.loads(path.read_text(encoding="utf-8"))["samples"] for key, path in helper["SOURCES"].items()}
    for action in ("press", "right", "left"):
        before = [statistics.median(sample["raw"][i] - ref[i] for sample in raw[f"{action}_before"]) for i in range(12)]
        after_key = f"{action}_after"
        after = ([statistics.median(sample["raw"][i] - ref[i] for sample in raw[after_key]) for i in range(12)]
                 if after_key in raw else before)
        local_baseline = [(before[i] + after[i]) / 2 for i in range(12)]
        for key in (f"{action}_before", action, after_key):
            if key not in raw:
                continue
            data[key] = [[sample["raw"][i] - ref[i] - local_baseline[i] for i in range(12)] for sample in raw[key]]
            if key != action:
                empty.extend(data[key])
    press_normal = max(statistics.median(normal_score(ch) for ch in data["press"]), 1)
    leak = [statistics.median(contrast(ch)[i] for ch in data["press"]) / press_normal for i in range(8)]
    difference = [statistics.mean(residual(ch, leak)[i] for ch in data["right"]) -
                  statistics.mean(residual(ch, leak)[i] for ch in data["left"]) for i in range(8)]
    magnitude = math.hypot(*difference)
    weights = [value / magnitude for value in difference]
    score = lambda ch: signed_score(ch, leak, weights)
    threshold = max(1.0, 1.05 * percentile([abs(score(ch)) for ch in empty + data["press"]], 95))
    scores = {key: [score(ch) for ch in data[key]] for key in ("press", "right", "left")}
    report["fit_failure_diagnostics"] = {"rule": "right median must exceed +threshold and left median must be below -threshold",
        "threshold": threshold, "background_abs_p95_before_multiplier": percentile([abs(score(ch)) for ch in empty + data["press"]], 95),
        "direction_magnitude": magnitude,
        "scores": {key: {"count": len(values), "min": min(values), "median": statistics.median(values),
                          "max": max(values), "fraction_past_signed_threshold":
                          sum((v > threshold if key == "right" else v < -threshold) for v in values) / len(values)
                          if key != "press" else None} for key, values in scores.items()},
        "all_sample_scores": {key: [score(ch) for ch in data[key]] for key in refit.KEYS},
        "press_leak": leak, "weights": weights}
report["purpose"] = "Offline exploratory fit of corrected current control and confirmed +X windows; no independent physical validation or deployment."
report["command"] = "D:/conda/python.exe -X utf8 coinft/.superpowers/sdd/shear_refit_current_controls_20261005.py"
report["logical_label_order"] = ["press_before", "press", "press_after", "right_before", "right", "right_after", "left_before", "left"]
report["actual_acquisition_order"] = list(refit.KEYS)
report["strict_host_frame_order_validated"] = True
report["ordering_note"] = "The user acquired confirmed left and its empty control before the current press/right controls. Validation uses strict actual host/frame order; stored values were not changed."
report["excluded_operator_typo"] = "calibration/shear_refit_20261005_after_button/fit/left_repeat.json (operator confirmed actually empty)"
report["transform"] = "All derived channels are original raw minus one fixed current_controls_empty raw-channel offset; timestamps, frames, raw data, owner and source files are untouched."
report["production_file_changes"] = False
report["source_hashes_verified_after_run"] = all(hashlib.sha256((root / entry["path"]).read_bytes()).hexdigest() == entry["sha256"] for entry in report["sources"].values())
output.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
print(json.dumps({"status": report["status"], "fit_replay_gate": report.get("fit_replay_gate"),
                  "same_stream_provenance_gate": report.get("same_stream_provenance_gate"),
                  "error": report.get("error"), "report": str(output)}, ensure_ascii=True))
