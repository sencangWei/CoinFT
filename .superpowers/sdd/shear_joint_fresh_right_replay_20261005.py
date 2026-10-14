"""Read-only replay of two fresh diagnostic captures; no coefficients are fitted."""
import hashlib
import json
import math
import statistics
import sys
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from calibration.capture_demo_pose import invalid_reasons
from calibration.fit_demo_profile import contrast, normal_score

HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "shear-joint-fresh-right-replay-20261005.json"


def main():
    sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
    previous_report = json.loads(OUTPUT.read_text(encoding="utf-8")) if OUTPUT.exists() else None
    previous_two_window = None
    if previous_report is not None:
        previous_two_window = previous_report.get("previous_two_window_report")
        if set(previous_report["sources"]) == {"empty", "right"}:
            previous_two_window = {"sha256": sha(OUTPUT), "sources": previous_report["sources"],
                                   "baselines_raw": previous_report["baselines_raw"], "summaries": previous_report["summaries"],
                                   "disclosure": "Original two-window provenance/summaries retained here while adding operator-confirmed released AFTER. Both baselines and frozen coefficients remain unchanged."}
    joint_path = HERE / "shear-refit-joint-leak-20261005.json"
    soft_path = HERE / "shear-refit-coefficient-softmargin-20261005.json"
    joint = json.loads(joint_path.read_text(encoding="utf-8"))
    soft = json.loads(soft_path.read_text(encoding="utf-8"))
    candidate_sha = hashlib.sha256(json.dumps(joint["candidate"], sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    if candidate_sha != joint["candidate_sha256"]:
        raise ValueError("frozen joint candidate SHA changed")
    for entry in joint["sources"].values():
        if sha(ROOT / entry["path"]) != entry["sha256"]:
            raise ValueError("original training source SHA changed")
    manifest = json.loads((HERE / "stream-recovery-final-manifest.json").read_text(encoding="utf-8"))
    protected = {str(Path(x["path"])): x["sha256"].lower() for x in manifest["files"]}
    protected[str(ROOT / "coinft_demo.py")] = manifest["production_hash"].lower()
    inputs = [joint_path, soft_path, HERE / "joint-shear-refit-report-20261005.md",
              HERE / "stream-recovery-final-manifest.json", ROOT / "calibration/capture_demo_pose.py"]
    inputs += [ROOT / entry["path"] for entry in joint["sources"].values()]
    before = {str(path): sha(path) for path in inputs}
    before.update({path: sha(Path(path)) for path in protected})
    if any(before[path] != expected for path, expected in protected.items()):
        raise ValueError("protected hash changed")
    profiles = {"frozen_failed_joint": joint["candidate"],
                "original_production": json.loads((ROOT / "demo_web/shear_demo_profile.json").read_text(encoding="utf-8")),
                "previous_softmargin": soft["candidate"]}
    if sha(ROOT / "demo_web/shear_demo_profile.json") != joint["protection_hashes_before"][str(ROOT / "demo_web/shear_demo_profile.json")]:
        raise ValueError("original production profile changed")
    windows, sources = {}, {}
    previous_frame, previous_host = -1, None
    for key in ("empty", "right", "right_after"):
        path = ROOT / f"calibration/shear_joint_diagnostic_20261005/{key}.json"
        before[str(path)] = sha(path)
        window = json.loads(path.read_text(encoding="utf-8"))
        if window["owner"] != {"pid": 87952, "created": 1791188496.384482} or not window["capture_ok"]:
            raise ValueError("capture owner/result changed")
        samples = window["samples"]
        offset = [a-b for a, b in zip(samples[0]["raw"], samples[0]["channels"])]
        for sample in samples:
            state = {"status": sample["status"], "frames": sample["f"], "rate": sample["rate"],
                     "invalid_recent": sample["invalid"], "saturated_recent": sample["saturated"],
                     "resyncs": sample["resync"], "channels": sample["channels"], "raw": sample["raw"]}
            reasons = invalid_reasons(state, previous_frame)
            host = datetime.fromisoformat(sample["host"])
            if reasons or host.tzinfo is None or (previous_host is not None and host <= previous_host):
                raise ValueError(f"invalid frame/host/state: {key}: {reasons}")
            if [a-b for a, b in zip(sample["raw"], sample["channels"])] != offset:
                raise ValueError(f"offset changes inside {key}")
            previous_frame, previous_host = sample["f"], host
        duration = (datetime.fromisoformat(samples[-1]["host"]) - datetime.fromisoformat(samples[0]["host"])).total_seconds()
        if len(samples) < 40 or duration < 5:
            raise ValueError("insufficient capture window")
        states = [o["state"] for o in window["observations"]]
        if any(invalid_reasons(s, -1) for s in states):
            raise ValueError("invalid observation state")
        if any(s["recovery"]["attempts"] != 31 or s["recovery"]["successes"] != 3 for s in states):
            raise ValueError("recovery changes inside capture")
        invalid = [s["invalid_frames"] for s in states]
        if len(set(invalid)) != 1:
            raise ValueError("invalid frame counter increments inside capture")
        previous_observation_host, previous_observation_frame = None, -1
        for observation in window["observations"]:
            host = datetime.fromisoformat(observation["host"])
            if (host.tzinfo is None or (previous_observation_host is not None and host <= previous_observation_host)
                    or observation["state"]["frames"] < previous_observation_frame):
                raise ValueError("observation time/frame order changes")
            previous_observation_host, previous_observation_frame = host, observation["state"]["frames"]
        sources[key] = {"path": str(path), "sha256": before[str(path)], "owner": window["owner"],
                        "sample_count": len(samples), "duration_seconds": duration, "raw_channel_offset": offset,
                        "first_frame": samples[0]["f"], "last_frame": samples[-1]["f"],
                        "first_host": samples[0]["host"], "last_host": samples[-1]["host"],
                        "invalid_frames_first": invalid[0], "invalid_frames_last": invalid[-1],
                        "recovery": {"attempts": 31, "successes": 3}, "validator": "capture_demo_pose.invalid_reasons per sample and observation, explicit owner/offset/host/order/duration checks"}
        windows[key] = window
    baselines = {"original_joint_raw_baseline": [a+b for a, b in zip(joint["feature_basis"]["reference_offset"], joint["feature_basis"]["common_baseline"])],
                 "fresh_empty_raw_median_diagnostic": [statistics.median(s["raw"][i] for s in windows["empty"]["samples"]) for i in range(12)]}
    batches = []
    for scenario, baseline in baselines.items():
        for key, window in windows.items():
            first = datetime.fromisoformat(window["samples"][0]["host"])
            batches.append({"scenario": scenario, "key": key,
                            "samples": [{"ms": (datetime.fromisoformat(s["host"])-first).total_seconds()*1000,
                                         "f": s["f"], "host": s["host"], "raw": s["raw"],
                                         "channels": [v-b for v, b in zip(s["raw"], baseline)]} for s in window["samples"]]})
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        try:
            page = browser.new_page(reduced_motion="reduce")
            page.set_content('<canvas id="c" style="width:600px;height:400px"></canvas>')
            page.add_script_tag(path=str(ROOT / "demo_web/surface.js"))
            replay = page.evaluate("""a => {
                let now=0; performance.now=()=>now;
                const output={};
                for (const batch of a.batches) {
                    output[batch.scenario] ||= {};
                    const result={}; const normals={};
                    for (const [name,profile] of Object.entries(a.profiles)) {
                        const surface=createSurface(document.getElementById('c'));
                        surface.clear(); const rows=[];
                        for(const sample of batch.samples) {
                            now=sample.ms; surface.set(sample.channels,profile);
                            rows.push({...sample,rawscore:shearScore(sample.channels,profile),
                                       normalScore:normalScore(sample.channels),normal:surface.target,shear:surface.shearTarget});
                        }
                        result[name]=rows; normals[name]=rows.map(x=>x.normal);
                    }
                    const expected=normals.original_production;
                    output[batch.scenario][batch.key]={profiles:result,
                      normalEquality:Object.values(normals).every(rows=>rows.every((x,i)=>x===expected[i]))};
                }
                return output;
            }""", {"batches": batches, "profiles": profiles})
        finally:
            browser.close()
    summaries = {}
    for scenario, poses in replay.items():
        summaries[scenario] = {}
        for key, pose in poses.items():
            summaries[scenario][key] = {}
            for name, timeline in pose["profiles"].items():
                summary = {}
                for phase in ("transition", "stable"):
                    rows = [r for r in timeline if (r["ms"] >= 600) == (phase == "stable")]
                    values = [r["shear"] for r in rows]
                    summary[phase] = {"count": len(values), "min": min(values), "median": statistics.median(values), "max": max(values),
                                      "positive_at_least_p2": sum(v>=.2 for v in values), "negative_at_most_m2": sum(v<=-.2 for v in values),
                                      "wrong_sign_below_m05": sum(v<-.05 for v in values), "empty_false_abs_above_p05": sum(abs(v)>.05 for v in values) if key!="right" else None,
                                      "right_active_fraction": sum(v>=.2 for v in values)/len(values) if key=="right" else None,
                                      "right_80pct_gate": sum(v>=.2 for v in values)/len(values)>=.8 and not any(v<-.05 for v in values) if key=="right" else None,
                                      "normal_zero_count": sum(r["normal"]==0 for r in rows)}
                summaries[scenario][key][name] = summary
    comparison = {}
    old_right = json.loads((ROOT / joint["sources"]["right"]["path"]).read_text(encoding="utf-8"))
    old_baseline = baselines["original_joint_raw_baseline"]
    old_ch = [[v-b for v, b in zip(s["raw"], old_baseline)] for s in old_right["samples"]]
    old_features = {"channel_feature_min_median_max": [[min(ch[i] for ch in old_ch), statistics.median(ch[i] for ch in old_ch), max(ch[i] for ch in old_ch)] for i in range(12)],
                    "contrast_feature_min_median_max": [[min(contrast(ch)[i] for ch in old_ch), statistics.median(contrast(ch)[i] for ch in old_ch), max(contrast(ch)[i] for ch in old_ch)] for i in range(8)],
                    "normalScore_min_median_max": [min(normal_score(ch) for ch in old_ch), statistics.median(normal_score(ch) for ch in old_ch), max(normal_score(ch) for ch in old_ch)]}
    for scenario in baselines:
        rows = replay[scenario]["right"]["profiles"]["frozen_failed_joint"]
        comparison[scenario] = {"fresh_right_normal_min_median_max": [min(r["normal"] for r in rows), statistics.median(r["normal"] for r in rows), max(r["normal"] for r in rows)],
                               "fresh_right_normalScore_min_median_max": [min(r["normalScore"] for r in rows), statistics.median(r["normalScore"] for r in rows), max(r["normalScore"] for r in rows)],
                               "fresh_right_miss_ms": [r["ms"] for r in rows if r["ms"]>=600 and r["shear"]<.2],
                               "fresh_right_rawscore_min_median_max": [min(r["rawscore"] for r in rows), statistics.median(r["rawscore"] for r in rows), max(r["rawscore"] for r in rows)],
                               "channel_feature_min_median_max": [[min(r["channels"][i] for r in rows),statistics.median(r["channels"][i] for r in rows),max(r["channels"][i] for r in rows)] for i in range(12)],
                               "contrast_feature_min_median_max": [[min(contrast(r["channels"])[i] for r in rows),statistics.median(contrast(r["channels"])[i] for r in rows),max(contrast(r["channels"])[i] for r in rows)] for i in range(8)]}
    if previous_two_window is not None and (previous_two_window["baselines_raw"] != baselines or
            any(previous_two_window["sources"][key]["sha256"] != sources[key]["sha256"] for key in ("empty", "right"))):
        raise ValueError("original two-window source/baseline provenance changed")
    report = {"status": "diagnostic_replayed_no_fit", "sources": sources, "baselines_raw": baselines,
              "previous_two_window_report": previous_two_window,
              "frozen_candidate_sha256": joint["candidate_sha256"], "profiles": profiles,
              "limitations": ["No fitting, deployment, new captures or device commands; only existing surface.js replay.",
                              "The empty/right/released right_after captures are separate HTTP-snapshot windows, reset per window; no continuous transition evidence. AFTER is not used to change either baseline or coefficients.",
                              "Cumulative invalid_frames increases 3 to 4 in the UNOBSERVED interval between windows; neither capture contains an increment. No force/noise causation is established.",
                              "Fresh-empty raw median is a separate no-load initialization diagnostic; it is not the frozen fitting baseline or an accepted replacement profile.",
                              "Three right/empty/released-after diagnostic windows cannot satisfy the full eight-window or independent model acceptance specification."],
              "normal_equality_all": all(pose["normalEquality"] for poses in replay.values() for pose in poses.values()),
              "original_vs_fresh_raw_baseline_delta": [b-a for a, b in zip(baselines["original_joint_raw_baseline"], baselines["fresh_empty_raw_median_diagnostic"])],
              "original_channel_offsets_differ_between_fresh_windows": sources["empty"]["raw_channel_offset"] != sources["right"]["raw_channel_offset"],
              "summaries": summaries, "comparison": comparison,
              "old_right_failure_segments": joint["right_failure_segments"],
              "old_right_raw_feature_summary": {"source": joint["sources"]["right"]["path"], "raw_scores": joint["all_raw_scores"]["right"],
                                                 "raw_score_units": "unnormalized fitted score, threshold=1",
                                                 "encoded_profile_raw_scores": [v/joint["coefficient_scale"]["l2_norm"] for v in joint["all_raw_scores"]["right"]],
                                                 "actual_timeline": joint["replay"]["samples"]["right"], "features": old_features},
              "replay": replay, "input_hashes_before": before,
              "input_hashes_after": {path: sha(Path(path)) for path in before}}
    report["all_input_hashes_unchanged"] = before == report["input_hashes_after"]
    report["interpretation"] = ["Frozen joint candidate improves from old training right24/37 to fresh right33/36 using its original fixed RAW baseline, with fresh empty36/36 zero; this is a limited fresh diagnostic result, not full model acceptance.",
                                "Fresh-empty initialization shifts that same frozen candidate to25/36; baseline choice materially affects right activation. Original production reaches36/36 in both baseline scenarios, so this diagnostic does not favor deploying the joint candidate.",
                                "Fresh right normal output remains1 throughout42 samples in both scenarios; old right normal fell to0 for three early samples. Fresh right remains positive throughout, while old right contains a contiguous early shear dropout.",
                                "Fresh original raw-channel offsets differ between empty/right but are constant within each. Both scenarios use one common RAW baseline for the pair, so changing stored channel zero offsets cannot manufacture replay alignment.",
                                "Fresh right raw normalScore spans989.5–1091 at the original baseline, versus old27.5–1271.5; full per-channel/contrast ranges and actual timelines are reported. No cause is assigned to the heterogeneous old hold."]
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    print(json.dumps({"status": report["status"], "normal_equality": report["normal_equality_all"],
                      "stable_right_counts": {scenario: {name: values["stable"]["positive_at_least_p2"]
                          for name, values in poses["right"].items()} for scenario, poses in summaries.items()},
                      "after_false_counts": {scenario: {name: values["stable"]["empty_false_abs_above_p05"]
                          for name, values in poses["right_after"].items()} for scenario, poses in summaries.items()},
                      "all_hashes_unchanged": report["all_input_hashes_unchanged"], "report": str(OUTPUT)}, ensure_ascii=True))


if __name__ == "__main__":
    main()
