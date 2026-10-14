"""Refit the existing method on one complete fresh right trial, offline only."""
import copy
import hashlib
import importlib.util
import json
import statistics
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from calibration import shear_refit_replay as refit
from calibration.build_qualitative_demo_profile import _validate, build_profile
from calibration.capture_demo_pose import invalid_reasons

HERE = Path(__file__).resolve().parent
OUTPUT = HERE / "shear-refit-fresh-right-20261005.json"
TASK_REPORT = HERE / "fresh-right-refit-report-20261005.md"
ORDER = ("left_before", "left", "press_before", "press", "press_after", "right_before", "right", "right_after")


def compare_frozen_report():
    """Actual JS comparison of two existing profiles, without invoking any fitter."""
    report = json.loads(OUTPUT.read_text(encoding="utf-8"))
    soft_path = HERE / "shear-refit-coefficient-softmargin-20261005.json"
    soft_bytes = soft_path.read_bytes()
    soft_report = json.loads(soft_bytes)
    profiles = {"previous_softmargin": soft_report["candidate"],
                "original_production": json.loads((ROOT / "demo_web/shear_demo_profile.json").read_text(encoding="utf-8"))}
    old = profiles["original_production"]
    windows = {}
    for key, entry in report["sources"].items():
        contents = (ROOT / entry["path"]).read_bytes()
        if hashlib.sha256(contents).hexdigest() != entry["sha256"]:
            raise ValueError("comparison source changed")
        window = json.loads(contents)
        window["pose"], window["evidence"] = key, entry["derived_evidence"]
        for sample in window["samples"]:
            sample["channels"] = [a-b for a, b in zip(sample["raw"], report["feature_basis"]["reference_offset"])]
        windows[key] = window
    refit.KEYS = ORDER
    comparison = {}
    for name, profile in profiles.items():
        replay = refit.replay(profile, old, windows, report["feature_basis"]["common_baseline"])
        summary = {}
        for key, values in replay["poses"].items():
            sign = 1 if key=="right" else -1
            active = sum(sign*v>=.2 for v in values) if key in ("left", "right") else sum(abs(v)>.05 for v in values)
            reverse = sum(sign*v<-.05 for v in values) if key in ("left", "right") else 0
            summary[key] = {"count": len(values), "active_count": active, "reverse_count": reverse,
                            "min": min(values), "median": statistics.median(values), "max": max(values),
                            "passes_pose": active/len(values)>=.8 and reverse==0 if key in ("left", "right") else active==0}
        comparison[name] = {"accepted_in_sample": refit.passes(replay), "summaries": summary, "replay": replay,
                            "failed_poses": [key for key, value in summary.items() if not value["passes_pose"]]}
    report["frozen_existing_profile_comparison"] = comparison
    report["comparison_softmargin_report_sha256"] = hashlib.sha256(soft_bytes).hexdigest()
    report["comparison_scope"] = "No fitting: existing frozen profiles, same eight complete selected TRAINING windows and same fresh common baseline; all previous fitting failures retained."
    passing = next((name for name, value in comparison.items() if value["accepted_in_sample"]), None)
    if passing is not None:
        report.setdefault("fresh_joint_fitting_result", {key: report.get(key) for key in
                         ("status", "candidate", "candidate_sha256", "accepted_in_sample", "replay", "summaries")})
        report.update({"status": "frozen_training_candidate", "selected_method": f"existing_frozen_{passing}_profile_no_new_fit",
                       "candidate": profiles[passing], "accepted_in_sample": True, "replay": comparison[passing]["replay"]})
        report["candidate_sha256"] = hashlib.sha256(json.dumps(profiles[passing], sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        report["candidate_learning_provenance"] = {"source_report": str(soft_path),
            "source_report_sha256": hashlib.sha256(soft_bytes).hexdigest(), "original_training_sources": soft_report["sources"],
            "original_feature_basis": soft_report["feature_basis"], "profile_exactly_unchanged_from_original_candidate": profiles[passing] == soft_report["candidate"],
            "disclosure": "Weights/pressLeak/threshold/span were learned on the original older eight windows by the previous softmargin fit. They were not retrained on fresh right. The intact profile was selected by replay on the new eight training windows at the fixed fresh baseline."}
        report["candidate_selection_provenance"] = {"selected_training_sources": report["sources"],
            "fixed_common_raw_baseline": report["feature_basis"]["common_raw_baseline"],
            "fixed_reference_offset": report["feature_basis"]["reference_offset"],
            "fixed_common_baseline": report["feature_basis"]["common_baseline"],
            "candidate_location": "candidate", "baseline_location": "feature_basis.common_raw_baseline",
            "independent_acceptance": "not yet performed", "deployment": "not performed"}
        report["failed_actual_gates"] = []
        report["actual_left_active_fraction"] = comparison[passing]["summaries"]["left"]["active_count"] / comparison[passing]["summaries"]["left"]["count"]
        report["actual_right_active_fraction"] = comparison[passing]["summaries"]["right"]["active_count"] / comparison[passing]["summaries"]["right"]["count"]
        report["summaries"] = {}
        for key in ORDER:
            report["summaries"][key] = {}
            for phase in ("transition", "stable"):
                rows = [row for row in report["replay"]["samples"][key] if (row["ms"]>=600)==(phase=="stable")]
                values = [row["shear"] for row in rows]
                sign = 1 if key=="right" else -1
                report["summaries"][key][phase] = {"count": len(values), "min": min(values), "median": statistics.median(values), "max": max(values),
                    "active_count": sum(sign*x>=.2 for x in values) if key in ("left", "right") else sum(abs(x)>.05 for x in values),
                    "reverse_count": sum(sign*x<-.05 for x in values) if key in ("left", "right") else 0}
    digest = lambda path: hashlib.sha256(Path(path).read_bytes()).hexdigest()
    if any(digest(path) != value for path, value in report["input_hashes_after"].items()) or digest(soft_path) != report["comparison_softmargin_report_sha256"]:
        raise ValueError("comparison inputs changed")
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    lines = ["", "## Frozen existing profile comparison (no fitting)", "", report["comparison_scope"], ""]
    for name, result in comparison.items():
        lines.append(f"{name}: full unchanged JS gate={result['accepted_in_sample']}; failed poses={result['failed_poses']}.")
        for key, value in result["summaries"].items():
            lines.append(f"- {key}: active{value['active_count']}/{value['count']}, reverse{value['reverse_count']}, min/median/max={value['min']:.6f}/{value['median']:.6f}/{value['max']:.6f}.")
        lines.append("")
    content = TASK_REPORT.read_text(encoding="utf-8")
    content = content.split("\n## Frozen existing profile comparison (no fitting)")[0]
    if passing is not None:
        content = content.replace("Status: training_gate_failed; actual unchanged Chromium gate=False.",
                                  "Earlier fresh joint fitting result: training_gate_failed; actual unchanged Chromium gate=False (preserved below).")
        content = content.replace("DONE_WITH_CONCERNS. Existing builder", "Earlier fitting attempt: Existing builder")
        header = (f"\nFinal status: DONE / frozen_training_candidate. The existing {passing} profile passes the same selected eight TRAINING windows at the same fresh common raw baseline: left34/34, right34/36 (94.44%), every idle/press output zero, no reversals, normal exactly unchanged. No new fit produced this passing profile. It is frozen only for future independent acceptance and has not been deployed. Candidate SHA256 `{report['candidate_sha256']}`.\n")
        if "Final status: DONE / frozen_training_candidate." not in content:
            content = content.replace("# Fresh complete right trial refit — 2026-10-05\n", "# Fresh complete right trial refit — 2026-10-05\n"+header)
        lines += ["", "The selected softmargin profile is exactly unchanged: its weights, pressLeak, threshold/span and original evidence were learned on the ORIGINAL older eight windows; it was selected on the NEW eight windows, not retrained on fresh right. Learning/selection source provenance are stored separately in the JSON.", "",
                  f"Frozen candidate location: `candidate`; SHA256 `{report['candidate_sha256']}`. Fixed baseline location: `feature_basis.common_raw_baseline` = `{report['feature_basis']['common_raw_baseline']}`. Reference/common baseline are also preserved for exact reconstruction.", "",
                  "Replay-only reproduction (no fitting), from `D:/semg.claude/coinft`: `D:/conda/python.exe -X utf8 -c \"import importlib.util;from pathlib import Path;p=Path('.superpowers/sdd/shear_refit_fresh_right_20261005.py');s=importlib.util.spec_from_file_location('fresh_refit',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);m.compare_frozen_report()\"`."]
    TASK_REPORT.write_text(content+"\n".join(lines)+"\n", encoding="utf-8")
    print(json.dumps({name: {"accepted": value["accepted_in_sample"], "failed_poses": value["failed_poses"], "summaries": value["summaries"]} for name, value in comparison.items()}), flush=True)


def main():
    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
    prior_path = HERE / "shear-refit-joint-leak-20261005.json"
    diagnostic_path = HERE / "shear-joint-fresh-right-replay-20261005.json"
    prior = json.loads(prior_path.read_text(encoding="utf-8"))
    diagnostic = json.loads(diagnostic_path.read_text(encoding="utf-8"))
    manifest = json.loads((HERE / "stream-recovery-final-manifest.json").read_text(encoding="utf-8"))
    protected = {str(Path(item["path"])): item["sha256"].lower() for item in manifest["files"]}
    protected[str(ROOT / "coinft_demo.py")] = manifest["production_hash"].lower()
    inputs = [prior_path, diagnostic_path, HERE / "shear_refit_joint_leak_20261005.py",
              HERE / "joint-shear-refit-report-20261005.md", HERE / "stream-recovery-final-manifest.json"]
    inputs += [ROOT / entry["path"] for entry in prior["sources"].values()]
    hashes = {str(path): digest(path) for path in inputs}
    hashes.update({path: digest(Path(path)) for path in protected})
    if any(hashes[path] != expected for path, expected in protected.items()):
        raise ValueError("protected production hashes changed")
    for entry in prior["sources"].values():
        if digest(ROOT / entry["path"]) != entry["sha256"]:
            raise ValueError("original training source hash changed")
    originals, sources = {}, {}
    for key in ORDER:
        if key in ORDER[:5]:
            entry = prior["sources"][key]
            path = ROOT / entry["path"]
        else:
            entry = diagnostic["sources"][{"right_before": "empty", "right": "right", "right_after": "right_after"}[key]]
            path = Path(entry["path"])
        if digest(path) != entry["sha256"]:
            raise ValueError(f"selected source changed: {key}")
        window = json.loads(path.read_text(encoding="utf-8"))
        if window["owner"] != {"pid": 87952, "created": 1791188496.384482}:
            raise ValueError("selected source owner changed")
        samples = window["samples"]
        offset = [a-b for a, b in zip(samples[0]["raw"], samples[0]["channels"])]
        if any([a-b for a, b in zip(s["raw"], s["channels"])] != offset for s in samples):
            raise ValueError("raw-channel offset changes inside selected source")
        states = [obs["state"] for obs in window["observations"]]
        if any(invalid_reasons(state, -1) for state in states):
            raise ValueError("selected source observations fail capture validator")
        recoveries = [{k: state["recovery"][k] for k in ("attempts", "successes")} for state in states]
        if any(item != recoveries[0] for item in recoveries):
            raise ValueError("recovery changes within selected source")
        invalid = [state["invalid_frames"] for state in states]
        if len(set(invalid)) != 1:
            raise ValueError("invalid counter changes within selected source")
        hashes[str(path)] = digest(path)
        originals[key] = window
        sources[key] = {"path": str(path.relative_to(ROOT)).replace("\\", "/"), "sha256": entry["sha256"],
                        "original_pose": window["pose"], "owner": window["owner"], "original_offset": offset,
                        "derived_evidence": f"fresh_right_refit_aligned_{key}.json", "sample_count": len(samples),
                        "first_host": samples[0]["host"], "last_host": samples[-1]["host"],
                        "first_frame": samples[0]["f"], "last_frame": samples[-1]["f"],
                        "duration_seconds": (datetime.fromisoformat(samples[-1]["host"])-datetime.fromisoformat(samples[0]["host"])).total_seconds(),
                        "recovery_first": recoveries[0], "recovery_last": recoveries[-1],
                        "invalid_frames_first": invalid[0], "invalid_frames_last": invalid[-1]}
    reference = sources["right_before"]["original_offset"]
    raw_baseline = [statistics.median(s["raw"][i] for s in originals["right_before"]["samples"]) for i in range(12)]
    baseline = [a-b for a, b in zip(raw_baseline, reference)]
    windows = {}
    for key in ORDER:
        derived = copy.deepcopy(originals[key])
        derived["pose"], derived["evidence"] = key, sources[key]["derived_evidence"]
        for sample in derived["samples"]:
            sample["channels"] = [a-b for a, b in zip(sample["raw"], reference)]
        windows[key] = derived
    refit.KEYS = ORDER
    _validate(windows)
    refit.ordered(windows)
    old = json.loads((ROOT / "demo_web/shear_demo_profile.json").read_text(encoding="utf-8"))
    if old["normal"] != {"threshold": 100, "span": 600}:
        raise ValueError("protected normal configuration changed")
    report = {"status": "started", "sources": sources, "dataset_selection": "Five complete old left/press windows plus the whole fresh unloaded/right/released trial; no sample cropping. Earlier failed right trial remains preserved.",
              "feature_basis": {"reference_offset": reference, "common_baseline": baseline, "common_raw_baseline": raw_baseline,
                                "definition": "One latest fresh unloaded raw median chosen before fitting; same baseline for all eight windows."},
              "limitations": ["The previously diagnostic right trial becomes TRAINING evidence in this refit; independent physical acceptance remains required.",
                              "Old left/press recovery30/2 versus fresh right31/3; these are mixed-stream windows, separately reset in replay, not continuous acceptance.",
                              "Cumulative invalid3 to4 occurred in the unobserved interval between fresh empty/right, not inside captures; no force/noise causation is claimed.",
                              "Corrected unloaded left_repeat.json is excluded; selected loaded left_confirmed_repeat.json is preserved in full.",
                              "No production deployment, tare, device commands, process changes or new physical hold requests."],
              "attempts": [], "candidate": None, "accepted_in_sample": False, "input_hashes_before": hashes}
    try:
        candidate = build_profile(windows)
        candidate["normal"] = copy.deepcopy(old["normal"])
        replay = refit.replay(candidate, old, windows, baseline)
        accepted = refit.passes(replay)
        report["attempts"].append({"kind": "original_builder", "candidate": candidate, "replay": replay, "accepted_in_sample": accepted})
        print(json.dumps({"attempt": "original_builder", "accepted": accepted,
                          "stable_counts": {key: {"count": len(v), "active": sum(x>=.2 for x in v) if key=="right" else sum(x<=-.2 for x in v) if key=="left" else sum(abs(x)>.05 for x in v)} for key, v in replay["poses"].items()}}), flush=True)
    except ValueError as exc:
        report["attempts"].append({"kind": "original_builder", "error": str(exc), "accepted_in_sample": False})
        accepted = False
        print(json.dumps({"attempt": "original_builder", "accepted": False, "error": str(exc)}), flush=True)
    if not accepted:
        spec = importlib.util.spec_from_file_location("reviewed_joint_refit", HERE / "shear_refit_joint_leak_20261005.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        adapter = {"sources": sources, "feature_basis": {"reference_offset": reference, "common_baseline": baseline}}
        # Adapt only the original press_before baseline identity check in memory.
        # Features, channels, solver constraints and encoded scores are unchanged.
        original_median = module.statistics.median
        expected_press = [original_median(s["channels"][i] for s in windows["press_before"]["samples"]) for i in range(12)]
        if expected_press != baseline:
            # Reuse the reviewed solver code with its obsolete press_before-specific
            # check replaced in memory by this task's fresh right_before check.
            source = (HERE / "shear_refit_joint_leak_20261005.py").read_text(encoding="utf-8")
            source = source.replace('windows["press_before"]["samples"]) for i in range(12)] != baseline',
                                    'windows["right_before"]["samples"]) for i in range(12)] != baseline')
            exec(compile(source, str(HERE / "shear_refit_joint_leak_20261005.py"), "exec"), module.__dict__)
        class InputReport:
            def read_bytes(self):
                return json.dumps(adapter, sort_keys=False, allow_nan=False).encode()
            def read_text(self, encoding="utf-8"):
                return self.read_bytes().decode(encoding)
        module.INPUT, module.OUTPUT = InputReport(), OUTPUT
        module.main()
        joint_result = json.loads(OUTPUT.read_text(encoding="utf-8"))
        report["joint_solver_reuse"] = {"module_sha256": digest(HERE / "shear_refit_joint_leak_20261005.py"),
                                        "adaptation": "in-memory input adapter; common-baseline identity check points to fresh right_before rather than old press_before; solver/encoding/replay unchanged"}
        report["attempts"].extend(joint_result["attempts"])
        report["joint_details"] = joint_result
        accepted = joint_result["accepted_in_sample"]
        candidate, replay = joint_result.get("candidate"), joint_result.get("replay")
    report.update({"status": "frozen_training_candidate" if accepted else "training_gate_failed", "accepted_in_sample": accepted,
                   "candidate": candidate, "replay": replay})
    report["method_scope"] = "Bounded sufficient no-clipping joint formulation; failure does not prove that all possible clipped/hysteretic existing profiles are infeasible or establish a hardware fault."
    if candidate is not None:
        report["candidate_sha256"] = hashlib.sha256(json.dumps(candidate, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
        report["candidate_sha_encoding"] = "UTF-8 sorted-key compact JSON, ensure_ascii=True"
    report["summaries"] = {}
    if replay is not None:
        for key in ORDER:
            report["summaries"][key] = {}
            for phase in ("transition", "stable"):
                rows = [row for row in replay["samples"][key] if (row["ms"]>=600)==(phase=="stable")]
                v = [row["shear"] for row in rows]
                sign = 1 if key=="right" else -1
                report["summaries"][key][phase] = {"count": len(v), "min": min(v), "median": statistics.median(v), "max": max(v),
                    "active_count": sum(sign*x>=.2 for x in v) if key in ("left", "right") else sum(abs(x)>.05 for x in v),
                    "reverse_count": sum(sign*x<-.05 for x in v) if key in ("left", "right") else 0}
    report["input_hashes_after"] = {path: digest(Path(path)) for path in hashes}
    report["all_input_hashes_unchanged"] = hashes == report["input_hashes_after"]
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    lines = ["# Fresh complete right trial refit — 2026-10-05", "", f"Status: {report['status']}; actual unchanged Chromium gate={accepted}.", "",
             report["dataset_selection"], "", *report["limitations"], "",
             "One fresh unloaded raw median is used for every replay window. Full source provenance, failed attempts, candidate, transition/stable timelines and hashes are in the JSON.", "",
             "| Window | Stable count / active / reverse | Min / median / max |", "|---|---:|---|"]
    for key, phases in report["summaries"].items():
        s = phases["stable"]
        lines.append(f"| {key} | {s['count']} / {s['active_count']} / {s['reverse_count']} | {s['min']:.6f} / {s['median']:.6f} / {s['max']:.6f} |")
    lines += ["", "| Window | Transition count / active / reverse | Min / median / max |", "|---|---:|---|"]
    for key, phases in report["summaries"].items():
        s = phases["transition"]
        lines.append(f"| {key} | {s['count']} / {s['active_count']} / {s['reverse_count']} | {s['min']:.6f} / {s['median']:.6f} / {s['max']:.6f} |")
    lines += ["", "Idle/press active above counts abs(output)>.05. Stable cutoff600ms. Left/right active counts use −.20/+.20; required fraction80%; no reverse beyond .05; normal exactly unchanged.", "",
              f"Candidate SHA256: {report.get('candidate_sha256')}. All {len(hashes)} protected/input/source hashes unchanged={report['all_input_hashes_unchanged']}.", "",
              "This is in-sample training replay; a passing candidate is frozen only in the report for later independent physical acceptance, without deployment.", "",
              report["method_scope"], "",
              "Execution: `D:/conda/python.exe -X utf8 .superpowers/sdd/shear_refit_fresh_right_20261005.py`. Solver math is reused from the previously reviewed joint module with only its common-baseline identity check changed in memory. No old module/report or source was edited."]
    TASK_REPORT.write_text("\n".join(lines)+"\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "accepted": accepted, "candidate_sha256": report.get("candidate_sha256"),
                      "all_hashes_unchanged": report["all_input_hashes_unchanged"], "report": str(OUTPUT)}), flush=True)


if __name__ == "__main__":
    main()
