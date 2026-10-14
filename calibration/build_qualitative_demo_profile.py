"""Build a qualitative shear demo profile from eight labeled capture windows."""

import argparse
import json
import math
import statistics
from datetime import datetime
from pathlib import Path

try:
    from calibration.fit_demo_profile import contrast, normal_score, percentile, residual, signed_score
except ModuleNotFoundError:  # direct script invocation from the project root
    from fit_demo_profile import contrast, normal_score, percentile, residual, signed_score


SOURCES = {
    "press_before": "calibration/demo_attempt_before_second_usb_reconnect_20260925/demo_train_empty_before_press_20260925.json",
    "press": "calibration/demo_attempt_before_second_usb_reconnect_20260925/demo_train_press_20260925.json",
    "press_after": "calibration/demo_attempt_before_second_usb_reconnect_20260925/demo_train_empty_after_press_20260925.json",
    "right_before": "calibration/demo_attempt_before_second_usb_reconnect_20260925/demo_train_empty_before_right_20260925.json",
    "right": "calibration/demo_attempt_before_second_usb_reconnect_20260925/demo_train_right_20260925.json",
    "right_after": "calibration/demo_attempt_before_second_usb_reconnect_20260925/demo_train_empty_after_right_20260925.json",
    "left_before": "calibration/demo_diagnostic_empty_after_second_usb_20260925.json",
    "left": "calibration/demo_diagnostic_left_demo_force_20260925.json",
}


def _validate(windows):
    if not isinstance(windows, dict) or set(windows) != set(SOURCES):
        raise ValueError("exactly eight qualitative windows are required")
    assemblies = set()
    evidence = []
    for key in SOURCES:
        window = windows[key]
        if not isinstance(window, dict):
            raise ValueError(f"invalid window: {key}")
        assembly = window.get("assemblyId")
        filename = window.get("evidence")
        if not isinstance(assembly, str) or not assembly.strip():
            raise ValueError(f"missing assembly ID: {key}")
        if not isinstance(filename, str) or not filename or Path(filename).name != filename or not filename.endswith(".json"):
            raise ValueError(f"invalid evidence filename: {key}")
        assemblies.add(assembly)
        evidence.append(filename)
        samples = window.get("samples")
        if not isinstance(samples, list) or len(samples) < 40:
            raise ValueError(f"too few samples: {key}")
        first_host = previous_host = None
        previous_frame = -1
        for sample in samples:
            if not isinstance(sample, dict):
                raise ValueError(f"invalid sample: {key}")
            try:
                host = datetime.fromisoformat(sample["host"])
            except (KeyError, TypeError, ValueError):
                raise ValueError(f"invalid timestamp: {key}") from None
            frame = sample.get("f")
            rate = sample.get("rate")
            vectors = (sample.get("channels"), sample.get("raw"))
            if (host.tzinfo is None or (previous_host is not None and host <= previous_host)
                    or type(frame) is not int or frame <= previous_frame
                    or sample.get("status") != "live"
                    or type(rate) not in (int, float) or not math.isfinite(rate) or rate <= 0
                    or type(sample.get("invalid")) is not int or sample["invalid"] != 0
                    or type(sample.get("saturated")) is not int or sample["saturated"] != 0
                    or type(sample.get("resync")) is not int or sample["resync"] < 0
                    or any(not isinstance(vector, list) or len(vector) != 12
                           or any(type(value) not in (int, float) or not math.isfinite(value)
                                  for value in vector) for vector in vectors)):
                raise ValueError(f"invalid live sample: {key}")
            if first_host is None:
                first_host = host
            previous_host = host
            previous_frame = frame
        if (previous_host - first_host).total_seconds() < 5:
            raise ValueError(f"capture duration below 5 seconds: {key}")
    if len(assemblies) != 1 or len(set(evidence)) != len(evidence):
        raise ValueError("mixed assemblies or duplicate evidence")
    return assemblies.pop(), evidence


def _median_channels(samples):
    return [statistics.median(sample["channels"][i] for sample in samples) for i in range(12)]


def build_profile(windows: dict[str, dict]) -> dict:
    assembly, evidence = _validate(windows)
    data = {}
    empty = []
    for action in ("press", "right", "left"):
        before = _median_channels(windows[f"{action}_before"]["samples"])
        after_key = f"{action}_after"
        after = _median_channels(windows[after_key]["samples"]) if after_key in windows else before
        baseline = [(a + b) / 2 for a, b in zip(before, after)]
        for key in (f"{action}_before", action, after_key):
            if key not in windows:
                continue
            data[key] = [[value - base for value, base in zip(sample["channels"], baseline)]
                         for sample in windows[key]["samples"]]
            if key != action:
                empty.extend(data[key])

    press = data["press"]
    right = data["right"]
    left = data["left"]
    press_normal = max(statistics.median(normal_score(ch) for ch in press), 1)
    press_leak = [statistics.median(contrast(ch)[i] for ch in press) / press_normal
                  for i in range(8)]
    difference = [statistics.mean(residual(ch, press_leak)[i] for ch in right)
                  - statistics.mean(residual(ch, press_leak)[i] for ch in left)
                  for i in range(8)]
    magnitude = math.hypot(*difference)
    if magnitude <= 0:
        raise ValueError("no directional contrast")
    weights = [value / magnitude for value in difference]
    score = lambda ch: signed_score(ch, press_leak, weights)
    threshold = max(1.0, 1.05 * percentile([abs(score(ch)) for ch in empty + press], 95))
    right_scores, left_scores = [score(ch) for ch in right], [score(ch) for ch in left]
    if statistics.median(right_scores) <= threshold or statistics.median(left_scores) >= -threshold:
        raise ValueError("qualitative directions do not separate from background")
    span = max(1.0, min(percentile([abs(v) for v in right_scores], 90),
                        percentile([abs(v) for v in left_scores], 90)) - threshold)
    profile = {"version": 1, "mode": "qualitative", "assemblyId": assembly,
               "normal": {"threshold": 100.0, "span": 600.0},
               "shear": {"enabled": True, "weights": weights, "pressLeak": press_leak,
                         "threshold": threshold, "span": span},
               "rightLabel": "−X", "leftLabel": "+X", "evidence": evidence}
    json.dumps(profile, allow_nan=False)
    return profile


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    windows = {}
    for key, relative in SOURCES.items():
        source = root / relative
        window = json.loads(source.read_text(encoding="utf-8"))
        window["evidence"] = source.name
        windows[key] = window
    profile = build_profile(windows)
    with args.out.open("x", encoding="utf-8") as output:
        output.write(json.dumps(profile, ensure_ascii=False, indent=2, allow_nan=False))
    print(json.dumps({"threshold": profile["shear"]["threshold"],
                      "rightMedian": statistics.median(signed_score(ch, profile["shear"]["pressLeak"], profile["shear"]["weights"])
                                                        for ch in _action_increments(windows, "right")),
                      "leftMedian": statistics.median(signed_score(ch, profile["shear"]["pressLeak"], profile["shear"]["weights"])
                                                       for ch in _action_increments(windows, "left")),
                      "evidence": profile["evidence"]}, ensure_ascii=False))


def _action_increments(windows, action):
    before = _median_channels(windows[f"{action}_before"]["samples"])
    after_key = f"{action}_after"
    after = _median_channels(windows[after_key]["samples"]) if after_key in windows else before
    baseline = [(a + b) / 2 for a, b in zip(before, after)]
    return [[value - base for value, base in zip(sample["channels"], baseline)]
            for sample in windows[action]["samples"]]


if __name__ == "__main__":
    main()
