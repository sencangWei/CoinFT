"""Bounded offline center-pull profile fit and unchanged-surface.js replay."""
import argparse
import hashlib
import json
import math
import statistics
from datetime import datetime
from pathlib import Path

import numpy as np
from playwright.sync_api import sync_playwright
from scipy.optimize import linprog


ROOT = Path(__file__).resolve().parents[2]
HERE = ROOT / ".superpowers" / "sdd"
INSTALLED = ROOT / "demo_web" / "shear_demo_profile.json"
ACTUAL_NAMES = [
    "shear-live-page-minus-x-20261005.json",
    "shear-live-page-plus-x-20261005.json",
    "shear-live-page-center-same-baseline-20261005.json",
    "shear-live-page-center-pull-minus-x-20261005.json",
    "shear-live-page-edge-pull-minus-x-20261005.json",
    "shear-live-page-center-pull-foreground-20261005.json",
    "shear-center-pull-full-diagnostic-20261005.json",
    "shear-center-pull-controls-empty-20261005.json",
    "shear-center-pull-controls-press-20261005.json",
]
ACTUAL_KIND = {
    ACTUAL_NAMES[0]: "minus",
    ACTUAL_NAMES[1]: "plus",
    ACTUAL_NAMES[2]: "idle",
    ACTUAL_NAMES[3]: "minus",
    ACTUAL_NAMES[4]: "minus",
    ACTUAL_NAMES[5]: "minus",
    ACTUAL_NAMES[6]: "minus",
    ACTUAL_NAMES[7]: "idle",
    ACTUAL_NAMES[8]: "press",
}


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _relative(channels, baseline):
    return [a - b for a, b in zip(channels, baseline)]


def load_actual():
    datasets = []
    for name in ACTUAL_NAMES:
        path = HERE / name
        data = json.loads(path.read_text(encoding="utf-8"))
        if "observations" in data:
            source = data["observations"]
            first = source[0]["monotonic"]
            rows = [{"ms": (o["monotonic"] - first) * 1000,
                     "channels": _relative(o["page"]["channels"], o["page"]["baseline"])}
                    for o in source]
            baseline = source[0]["page"]["baseline"]
        else:
            source = data["samples"]
            first = source[0]["host"]
            rows = [{"ms": o["host"] - first,
                     "channels": _relative(o["before"]["channels"], o["before"]["baseline"])}
                    for o in source]
            baseline = source[0]["before"]["baseline"]
        datasets.append({"source": name, "kind": ACTUAL_KIND[name], "rows": rows,
                         "baseline": baseline, "sha256": sha256(path),
                         "reference": "captured actual page-relative channels and per-window page baseline"})
    return datasets


def load_fixed_raw():
    validation = json.loads((HERE / "shear-frozen-independent-validation-20261005.json").read_text(encoding="utf-8"))
    baseline = validation["fixed_raw_baseline"]
    datasets = []
    for pose, meta in validation["sources"].items():
        path = ROOT / meta["path"]
        data = json.loads(path.read_text(encoding="utf-8"))
        samples = data["samples"]
        first = datetime.fromisoformat(samples[0]["host"])
        rows = [{"ms": (datetime.fromisoformat(s["host"]) - first).total_seconds() * 1000,
                 "channels": _relative(s["raw"], baseline)} for s in samples]
        kind = "minus" if pose == "right" else "plus" if pose == "left" else "background"
        datasets.append({"source": pose, "kind": kind, "rows": rows, "sha256": sha256(path),
                         "reference": "historical fixed common_raw_baseline",
                         "source_path": meta["path"]})
    return datasets


def replay(datasets, profiles):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page(reduced_motion="reduce")
            page.set_content('<canvas id="c" style="width:600px;height:400px"></canvas>')
            page.add_script_tag(path=str(ROOT / "demo_web" / "surface.js"))
            return page.evaluate("""input => {
              let now=0; performance.now=()=>now;
              return input.datasets.map(d => {
                const results={};
                for (const [name,profile] of Object.entries(input.profiles)) {
                  const surface=createSurface(document.getElementById('c')), rows=[];
                  for (const r of d.rows) {
                    now=r.ms; surface.set(r.channels,profile);
                    rows.push({ms:now,score:shearScore(r.channels,profile),
                               normal:surface.target,shear:surface.shearTarget});
                  }
                  results[name]=rows;
                }
                return {source:d.source,results};
              });
            }""", {"datasets": datasets, "profiles": profiles})
        finally:
            browser.close()


def summarize(datasets, replayed, baseline_name="installed", candidate_name="candidate"):
    output = []
    for data, item in zip(datasets, replayed):
        profiles = {}
        for name, rows in item["results"].items():
            stable = [r for r in rows if r["ms"] >= 600]
            values = [r["shear"] for r in stable]
            profiles[name] = {
                "stable_samples": len(stable),
                "minus_active": sum(v >= 0.2 for v in values),
                "plus_active": sum(v <= -0.2 for v in values),
                "reverse": (sum(v < -0.05 for v in values) if data["kind"] == "minus"
                            else sum(v > 0.05 for v in values) if data["kind"] == "plus"
                            else sum(abs(v) > 0.05 for v in values)),
                "shear_min": min(values), "shear_median": statistics.median(values),
                "shear_max": max(values),
            }
        normal_identical = all(a["normal"] == b["normal"] for a, b in
                               zip(item["results"][baseline_name], item["results"][candidate_name]))
        output.append({k: v for k, v in data.items() if k != "rows"} |
                      {"replay": profiles, "normal_identical": normal_identical})
    return output


def gate(summary, profile_name):
    failures = []
    for row in summary:
        result = row["replay"][profile_name]
        count = result["stable_samples"]
        if row["kind"] == "minus" and (result["minus_active"] < math.ceil(0.8 * count) or result["reverse"]):
            failures.append(row["source"])
        elif row["kind"] == "plus" and (result["plus_active"] < math.ceil(0.8 * count) or result["reverse"]):
            failures.append(row["source"])
        elif row["kind"] in ("idle", "press", "background") and result["reverse"]:
            failures.append(row["source"])
        if not row["normal_identical"]:
            failures.append(row["source"] + ":normal")
    return failures


def _feature(channels):
    shear = np.asarray(channels[:8], dtype=float)
    shear -= shear.mean()
    normal = max(0.0, statistics.median(channels[8:]))
    return np.r_[shear, -normal]


def fit(actual, installed, soft=False):
    stable = [(d, r) for d in actual for r in d["rows"] if r["ms"] >= 600]
    background = [_feature(r["channels"]) for d, r in stable if d["kind"] in ("idle", "press")]
    loaded = [(1 if d["kind"] == "minus" else -1, _feature(r["channels"]), d["source"])
              for d, r in stable if d["kind"] in ("minus", "plus")]
    threshold = installed["shear"]["threshold"]
    old = np.r_[np.asarray(installed["shear"]["weights"]) / threshold,
                sum(w * leak for w, leak in zip(installed["shear"]["weights"],
                                                installed["shear"]["pressLeak"])) / threshold]
    nbase = 9
    ndev = 9
    nslack = len(loaded) if soft else 0
    n = nbase + ndev + nslack
    c = np.r_[np.zeros(nbase), np.ones(ndev), np.full(nslack, 100.0)]
    aub, bub = [], []
    for j in range(nbase):
        row = np.zeros(n); row[j] = 1; row[nbase + j] = -1
        aub.append(row); bub.append(old[j])
        row = np.zeros(n); row[j] = -1; row[nbase + j] = -1
        aub.append(row); bub.append(-old[j])
    for feat in background:
        row = np.zeros(n); row[:nbase] = feat
        aub.append(row); bub.append(0.5)
        aub.append(-row); bub.append(0.5)
    for i, (sign, feat, _) in enumerate(loaded):
        row = np.zeros(n); row[:nbase] = -sign * feat
        if soft:
            row[nbase + ndev + i] = -1
        aub.append(row); bub.append(-1.1)
    aeq = np.zeros((1, n)); aeq[0, :8] = 1
    bounds = [(-0.05, 0.05)] * 8 + [(-0.05, 0.05)] + [(0, None)] * ndev + [(0, None)] * nslack
    result = linprog(c, A_ub=np.asarray(aub), b_ub=np.asarray(bub), A_eq=aeq, b_eq=[0],
                     bounds=bounds, method="highs", options={"time_limit": 10})
    attempt = {"kind": "soft_loaded_lp" if soft else "strict_lp", "time_limit_seconds": 10,
               "success": bool(result.success), "status": int(result.status), "message": result.message,
               "objective": None if result.fun is None else float(result.fun),
               "normalized_threshold": 1, "background_abs_bound": 0.5,
               "signed_loaded_min": 1.1, "coefficient_bounds": [-0.05, 0.05],
               "loaded_slack": bool(soft)}
    if not result.success:
        return None, attempt
    coeff = result.x[:9]
    weights = (coeff[:8] * threshold).tolist()
    pressure_coefficient = coeff[8] * threshold
    old_leak = np.asarray(installed["shear"]["pressLeak"], dtype=float)
    w = np.asarray(weights)
    leak = old_leak + ((pressure_coefficient - float(w @ old_leak)) / float(w @ w)) * w
    candidate = json.loads(json.dumps(installed))
    candidate["shear"]["weights"] = weights
    candidate["shear"]["pressLeak"] = leak.tolist()
    attempt["loaded_slack_sum"] = float(result.x[nbase + ndev:].sum()) if soft else 0.0
    attempt["loaded_slack_by_source"] = {}
    if soft:
        for value, (_, _, source) in zip(result.x[nbase + ndev:], loaded):
            attempt["loaded_slack_by_source"].setdefault(source, []).append(float(value))
        attempt["loaded_slack_by_source"] = {k: {"sum": sum(v), "max": max(v), "count": len(v)}
                                                for k, v in attempt["loaded_slack_by_source"].items()}
    return candidate, attempt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--profile", type=Path, default=INSTALLED,
                        help="explicit candidate path; defaults read-only installed profile")
    parser.add_argument("--fit", action="store_true")
    args = parser.parse_args()
    installed_bytes = INSTALLED.read_bytes()
    installed = json.loads(installed_bytes)
    actual = load_actual()
    attempts = []
    candidate = json.loads(args.profile.read_text(encoding="utf-8"))
    if args.fit:
        candidate, strict = fit(actual, installed, soft=False)
        attempts.append(strict)
        if candidate is None:
            candidate, soft = fit(actual, installed, soft=True)
            attempts.append(soft)
    raw = load_fixed_raw()
    profiles = {"installed": installed, "candidate": candidate or installed}
    actual_summary = summarize(actual, replay(actual, profiles))
    raw_summary = summarize(raw, replay(raw, profiles))
    print(json.dumps({
        "installed_profile_sha256": hashlib.sha256(installed_bytes).hexdigest(),
        "surface_js_sha256": sha256(ROOT / "demo_web" / "surface.js"),
        "profile_path": str(args.profile), "attempts": attempts, "candidate": candidate,
        "actual_page": {"failures": gate(actual_summary, "candidate"), "results": actual_summary},
        "fixed_raw_reference": {"failures": gate(raw_summary, "candidate"), "results": raw_summary},
        "production_unchanged": INSTALLED.read_bytes() == installed_bytes,
    }, ensure_ascii=True, allow_nan=False))


if __name__ == "__main__":
    main()
