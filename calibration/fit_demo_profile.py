"""Fit a local demo profile from one labeled train/holdout capture set."""

import argparse
import json
import math
import statistics
from datetime import datetime
from pathlib import Path


ACTIONS = ("press", "right", "left")
ROUNDS = ("train", "holdout")
POSES = tuple(f"{round_name}_{pose}" for round_name in ROUNDS
              for action in ACTIONS
              for pose in (f"empty_before_{action}", action, f"empty_after_{action}"))


def percentile(values, percentage):
    ordered = sorted(values)
    position = (len(ordered) - 1) * percentage / 100
    lower = int(position)
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[min(lower + 1, len(ordered) - 1)] * fraction


def normal_score(ch):
    return max(0.0, statistics.median(ch[8:12]))


def contrast(ch):
    average = statistics.mean(ch[:8])
    return [value - average for value in ch[:8]]


def residual(ch, press_leak):
    normal = normal_score(ch)
    return [value - leak * normal for value, leak in zip(contrast(ch), press_leak)]


def signed_score(ch, press_leak, weights):
    return sum(a * b for a, b in zip(residual(ch, press_leak), weights))


def _validate(windows, right_label, left_label):
    if set(windows) != set(POSES):
        raise ValueError("exactly the 18 required train/holdout poses are required")
    if not all(isinstance(label, str) and label.strip() for label in (right_label, left_label)) or right_label == left_label:
        raise ValueError("distinct nonempty right/left labels are required")
    assemblies = set()
    evidence = []
    last_host = None
    last_frame = None
    for pose in POSES:
        window = windows[pose]
        if not isinstance(window, dict) or window.get("pose") != pose:
            raise ValueError(f"incorrect pose: {pose}")
        assembly = window.get("assemblyId")
        if not isinstance(assembly, str) or not assembly.strip():
            raise ValueError(f"missing assembly ID: {pose}")
        assemblies.add(assembly)
        filename = window.get("evidence")
        if filename is not None and (not isinstance(filename, str) or Path(filename).name != filename
                                     or not filename.startswith(f"demo_{pose}_") or not filename.endswith(".json")):
            raise ValueError(f"invalid evidence filename: {pose}")
        if filename is not None:
            evidence.append(filename)
        samples = window.get("samples")
        if not isinstance(samples, list) or len(samples) < 30:
            raise ValueError(f"too few samples: {pose}")
        previous = -1
        previous_host = None
        first_host = None
        for sample in samples:
            if not isinstance(sample, dict):
                raise ValueError(f"invalid sample: {pose}")
            try:
                host = datetime.fromisoformat(sample["host"])
            except (KeyError, TypeError, ValueError):
                raise ValueError(f"invalid timestamp: {pose}") from None
            if host.tzinfo is None or (previous_host is not None and host <= previous_host):
                raise ValueError(f"non-increasing timestamp: {pose}")
            if previous_host is None and last_host is not None and host <= last_host:
                raise ValueError(f"capture windows overlap or are not chronological: {pose}")
            if first_host is None:
                first_host = host
            previous_host = host
            frame = sample.get("f")
            if previous == -1 and last_frame is not None and (type(frame) is not int or frame <= last_frame):
                raise ValueError(f"capture frames overlap or are not chronological: {pose}")
            rate = sample.get("rate")
            vectors = (sample.get("channels"), sample.get("raw"))
            if (type(frame) is not int or frame <= previous or sample.get("status") != "live"
                    or type(rate) not in (int, float) or not math.isfinite(rate) or rate <= 0
                    or type(sample.get("invalid")) is not int or sample["invalid"] != 0
                    or type(sample.get("saturated")) is not int or sample["saturated"] != 0
                    or type(sample.get("resync")) is not int or sample["resync"] < 0
                    or any(not isinstance(vector, list) or len(vector) != 12
                           or any(type(value) not in (int, float) or not math.isfinite(value)
                                  for value in vector) for vector in vectors)):
                raise ValueError(f"invalid live sample: {pose}")
            previous = frame
        if (previous_host - first_host).total_seconds() < 4.0:
            raise ValueError(f"capture duration below 4 seconds: {pose}")
        last_host = previous_host
        last_frame = previous
    if len(assemblies) != 1 or len(set(evidence)) != len(evidence) or len(evidence) not in (0, len(POSES)):
        raise ValueError("mixed assemblies or incomplete evidence names")
    return assemblies.pop(), evidence


def _background(data, round_name):
    return [ch for action in ACTIONS for side in ("before", "after")
            for ch in data[f"{round_name}_empty_{side}_{action}"]]


def _fraction(values, predicate):
    return sum(predicate(value) for value in values) / len(values)


def fit_profile(windows: dict[str, dict], right_label: str, left_label: str) -> tuple[dict, dict]:
    assembly, evidence = _validate(windows, right_label, left_label)
    data = {pose: [sample["channels"] for sample in windows[pose]["samples"]] for pose in POSES}
    train_empty = _background(data, "train")
    train_press = data["train_press"]
    empty_p95 = percentile([normal_score(ch) for ch in train_empty], 95)
    press_p10 = percentile([normal_score(ch) for ch in train_press], 10)
    normal_separated = empty_p95 < press_p10
    normal_threshold = (empty_p95 + press_p10) / 2 if normal_separated else 100.0
    normal_span = max(1.0, percentile([normal_score(ch) for ch in train_press], 90) - normal_threshold)
    press_normal = max(statistics.median(normal_score(ch) for ch in train_press), 1)
    press_leak = [statistics.median(contrast(ch)[i] for ch in train_press) / press_normal for i in range(8)]
    right_residual = [residual(ch, press_leak) for ch in data["train_right"]]
    left_residual = [residual(ch, press_leak) for ch in data["train_left"]]
    difference = [statistics.mean(row[i] for row in right_residual)
                  - statistics.mean(row[i] for row in left_residual) for i in range(8)]
    magnitude = math.hypot(*difference)
    weights = [value / magnitude for value in difference] if magnitude > 0 else [0.0] * 8
    score = lambda ch: signed_score(ch, press_leak, weights)
    train_bg = train_empty + train_press
    bg_p95 = percentile([abs(score(ch)) for ch in train_bg], 95)
    right_scores = [score(ch) for ch in data["train_right"]]
    left_scores = [score(ch) for ch in data["train_left"]]
    right_p10 = percentile([abs(value) for value in right_scores], 10)
    left_p10 = percentile([abs(value) for value in left_scores], 10)
    signs_valid = statistics.median(right_scores) > 0 and statistics.median(left_scores) < 0
    shear_separated = magnitude > 0 and signs_valid and bg_p95 < right_p10 and bg_p95 < left_p10
    shear_threshold = (bg_p95 + min(right_p10, left_p10)) / 2 if shear_separated else 1.0
    shear_span = max(1.0, min(percentile([abs(value) for value in right_scores], 90),
                              percentile([abs(value) for value in left_scores], 90)) - shear_threshold)

    holdout_press_normal = _fraction(data["holdout_press"], lambda ch: normal_score(ch) > normal_threshold)
    holdout_right = _fraction(data["holdout_right"], lambda ch: score(ch) > shear_threshold)
    holdout_left = _fraction(data["holdout_left"], lambda ch: score(ch) < -shear_threshold)
    release_threshold = 0.7 * shear_threshold
    empty_names = [f"holdout_empty_{side}_{action}" for action in ACTIONS for side in ("before", "after")]
    holdout_empty_by_window = {
        name: _fraction(data[name], lambda ch: abs(score(ch)) > shear_threshold)
        for name in empty_names}
    holdout_empty_release_by_window = {
        name: _fraction(data[name], lambda ch: abs(score(ch)) > release_threshold)
        for name in empty_names}
    holdout_empty_spurious = _fraction(_background(data, "holdout"), lambda ch: abs(score(ch)) > shear_threshold)
    holdout_empty_release_spurious = _fraction(_background(data, "holdout"), lambda ch: abs(score(ch)) > release_threshold)
    holdout_press_spurious = _fraction(data["holdout_press"], lambda ch: abs(score(ch)) > shear_threshold)
    holdout_press_release_spurious = _fraction(data["holdout_press"], lambda ch: abs(score(ch)) > release_threshold)
    reasons = []
    if not normal_separated:
        reasons.append("train normal background/press not separated")
    if not shear_separated:
        reasons.append("train signed shear or background/actions not separated")
    for name, value in (("holdout_press_normal", holdout_press_normal),
                        ("holdout_right", holdout_right), ("holdout_left", holdout_left)):
        if value < 0.8:
            reasons.append(f"{name} below 0.8")
    for name, value in (("holdout_empty_spurious", holdout_empty_spurious),
                        ("holdout_press_spurious", holdout_press_spurious),
                        ("holdout_press_release_spurious", holdout_press_release_spurious)):
        if value >= 0.2:
            reasons.append(f"{name} at least 0.2")
    for name in empty_names:
        if holdout_empty_by_window[name] >= 0.2:
            reasons.append(f"{name} activation spurious at least 0.2")
        if holdout_empty_release_by_window[name] >= 0.2:
            reasons.append(f"{name} release spurious at least 0.2")
    enabled = not reasons
    profile = {"version": 1, "assemblyId": assembly,
               "normal": {"threshold": normal_threshold, "span": normal_span},
               "shear": {"enabled": enabled, "weights": weights if enabled else [0.0] * 8,
                         "pressLeak": press_leak if enabled else [0.0] * 8,
                         "threshold": shear_threshold, "span": shear_span},
               "rightLabel": right_label, "leftLabel": left_label, "evidence": evidence}
    report = {"passed": enabled, "reasons": reasons, "assemblyId": assembly, "evidence": evidence,
              "train": {"normalEmptyP95": empty_p95, "normalPressP10": press_p10,
                        "normalThreshold": normal_threshold, "shearBackgroundP95": bg_p95,
                        "rightAbsP10": right_p10, "leftAbsP10": left_p10,
                        "shearThreshold": shear_threshold, "releaseThreshold": release_threshold,
                        "signsValid": signs_valid,
                        "separated": shear_separated},
              "holdout": {"pressNormal": holdout_press_normal, "right": holdout_right,
                          "left": holdout_left, "emptySpurious": holdout_empty_spurious,
                          "emptySpuriousByWindow": holdout_empty_by_window,
                          "emptyReleaseSpurious": holdout_empty_release_spurious,
                          "emptyReleaseSpuriousByWindow": holdout_empty_release_by_window,
                          "pressSpurious": holdout_press_spurious,
                          "pressReleaseSpurious": holdout_press_release_spurious}}
    json.dumps((profile, report), allow_nan=False)
    return profile, report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-dir", required=True, type=Path)
    parser.add_argument("--date", required=True, help="one capture date suffix, e.g. 20260925")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--right-label", required=True)
    parser.add_argument("--left-label", required=True)
    args = parser.parse_args(argv)
    if not args.date.isdigit() or len(args.date) != 8:
        parser.error("--date must be YYYYMMDD")
    if args.output == args.report or args.output.exists() or args.report.exists():
        raise FileExistsError("output/report already exists")
    windows = {}
    for pose in POSES:
        filename = f"demo_{pose}_{args.date}.json"
        window = json.loads((args.input_dir / filename).read_text(encoding="utf-8"))
        window["evidence"] = filename
        windows[pose] = window
    profile, report = fit_profile(windows, args.right_label, args.left_label)
    profile_text = json.dumps(profile, ensure_ascii=False, indent=2, allow_nan=False)
    report_text = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)
    with args.report.open("x", encoding="utf-8") as output:
        output.write(report_text)
    with args.output.open("x", encoding="utf-8") as output:
        output.write(profile_text)
    print(json.dumps({"passed": report["passed"], "reasons": report["reasons"],
                      "holdout": report["holdout"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
