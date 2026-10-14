# New-file review package (no Git repository)

Brief: joint-shear-refit-brief-20261005.md
Report: joint-shear-refit-report-20261005.md

--- /dev/null
+++ .superpowers/sdd/shear_refit_joint_leak_20261005.py
@@ newly added full file @@
+"""Two bounded offline attempts within the existing qualitative profile formula."""
+import copy
+import hashlib
+import json
+import math
+import statistics
+import sys
+import time
+from datetime import datetime
+from pathlib import Path
+
+import numpy as np
+from scipy.optimize import Bounds, LinearConstraint, linprog, milp
+
+ROOT = Path(__file__).resolve().parents[2]
+sys.path.insert(0, str(ROOT))
+from calibration import shear_refit_replay as refit
+from calibration.build_qualitative_demo_profile import _validate
+from calibration.fit_demo_profile import contrast, normal_score
+
+HERE = Path(__file__).resolve().parent
+INPUT = HERE / "shear-refit-coefficient-softmargin-20261005.json"
+OUTPUT = HERE / "shear-refit-joint-leak-20261005.json"
+ORDER = ("left_before", "left", "press_before", "press", "press_after", "right_before", "right", "right_after")
+PROFILE = ROOT / "demo_web/shear_demo_profile.json"
+
+
+def encode_profile(old, weights, beta, threshold=1, span=1):
+    weights = np.asarray(weights, dtype=float)
+    norm = float(np.linalg.norm(weights))
+    if (weights.shape != (8,) or not np.all(np.isfinite(weights)) or
+            not math.isfinite(beta) or not math.isfinite(norm) or norm <= 0 or
+            not math.isfinite(threshold) or not math.isfinite(span) or min(threshold, span) <= 0):
+        raise ValueError("invalid joint coefficient/profile scale")
+    candidate = copy.deepcopy(old)
+    candidate["shear"] = {"enabled": True, "weights": (weights / norm).tolist(),
+                          "pressLeak": (beta * weights / norm**2).tolist(),
+                          "threshold": threshold / norm, "span": span / norm}
+    return candidate
+
+
+def main():
+    refit.KEYS = ORDER
+    manifest_path = HERE / "stream-recovery-final-manifest.json"
+    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
+    protected = {str(Path(item["path"])): item["sha256"].lower() for item in manifest["files"]}
+    protected[str(ROOT / "coinft_demo.py")] = manifest["production_hash"].lower()
+    digest = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
+    before = {name: digest(Path(name)) for name in protected}
+    if before != protected:
+        raise ValueError("protected manifest hash changed before fit")
+    report = {"status": "started", "purpose": "bounded free-beta joint fit in unchanged profile formula; training only, no deployment",
+              "input_report_sha256": digest(INPUT), "protection_manifest_sha256": digest(manifest_path),
+              "protection_hashes_before": before,
+              "limitations": ["All eight solver/replay windows are TRAINING evidence, not independent acceptance.",
+                              "Windows are separately reset replays, not a continuous stream; right_after recovery 31/3 versus earlier 30/2.",
+                              "Corrected left_repeat.json is unloaded and excluded; no other sample exclusions.",
+                              "A failed sufficient no-clipping formulation is not proof of universal infeasibility or hardware fault."],
+              "sources": {}, "attempts": [], "candidate": None, "accepted_in_sample": False}
+    try:
+        prior = json.loads(INPUT.read_text(encoding="utf-8"))
+        if tuple(prior["sources"]) != ORDER:
+            raise ValueError("source order changed")
+        reference = prior["feature_basis"]["reference_offset"]
+        baseline = prior["feature_basis"]["common_baseline"]
+        old = json.loads(PROFILE.read_text(encoding="utf-8"))
+        if old["normal"] != {"threshold": 100, "span": 600} or old["mode"] != "qualitative":
+            raise ValueError("protected normal/mode changed")
+        windows, features, filtered, milliseconds = {}, {}, {}, {}
+        for key in ORDER:
+            entry = prior["sources"][key]
+            path = ROOT / entry["path"]
+            if digest(path) != entry["sha256"]:
+                raise ValueError(f"source hash changed: {key}")
+            original = json.loads(path.read_text(encoding="utf-8"))
+            if original["owner"] != entry["owner"]:
+                raise ValueError(f"source owner changed: {key}")
+            if any([s["raw"][i] - s["channels"][i] for i in range(12)] != entry["original_offset"]
+                   for s in original["samples"]):
+                raise ValueError(f"original offsets changed: {key}")
+            derived = copy.deepcopy(original)
+            derived["pose"], derived["evidence"] = key, f"joint_leak_aligned_{key}.json"
+            for sample in derived["samples"]:
+                sample["channels"] = [v - r for v, r in zip(sample["raw"], reference)]
+            if any((a["raw"], a["f"], a["host"]) != (b["raw"], b["f"], b["host"])
+                   for a, b in zip(original["samples"], derived["samples"])):
+                raise ValueError("raw/frame/time changed")
+            windows[key] = derived
+            report["sources"][key] = copy.deepcopy(entry)
+            report["sources"][key]["derived_evidence"] = derived["evidence"]
+            ch = [[v - b for v, b in zip(s["channels"], baseline)] for s in derived["samples"]]
+            # Coefficient vector is [w_1...w_8, -beta]. There is no intercept.
+            features[key] = np.asarray([contrast(c) + [normal_score(c)] for c in ch])
+            first = datetime.fromisoformat(derived["samples"][0]["host"])
+            milliseconds[key] = [(datetime.fromisoformat(s["host"]) - first).total_seconds() * 1000
+                                 for s in derived["samples"]]
+            ema = features[key][0].copy()
+            rows = [ema.copy()]
+            for i in range(1, len(ch)):
+                alpha = 1 - math.exp(-(milliseconds[key][i] - milliseconds[key][i-1]) / 180)
+                ema = ema + (features[key][i] - ema) * alpha
+                rows.append(ema.copy())
+            filtered[key] = np.asarray(rows)
+        _validate(windows)
+        refit.ordered(windows)
+        if [statistics.median(s["channels"][i] for s in windows["press_before"]["samples"]) for i in range(12)] != baseline:
+            raise ValueError("fixed common baseline changed")
+        scales = np.maximum(np.max(np.abs(np.vstack(list(features.values()))), axis=0), 1)
+        F = {key: rows / scales for key, rows in features.items()}
+        E = {key: rows / scales for key, rows in filtered.items()}
+        report["feature_basis"] = {"reference_offset": reference, "common_baseline": baseline,
+                                   "definition": "contrast(first8), normalScore(CH9-12); score=w.contrast-beta*normal; no intercept",
+                                   "coefficient_scales": scales.tolist(), "weight_sum": 0}
+
+        # Strict raw feasibility is a diagnostic, not the actual acceptance rule.
+        A, upper = [], []
+        for key in ORDER:
+            sign = 1 if key == "right" else -1
+            for vector in F[key]:
+                if key in ("left", "right"):
+                    A.append(np.r_[-sign * vector, np.zeros(9)])
+                    upper.append(-1.1)
+                else:
+                    A.extend((np.r_[vector, np.zeros(9)], np.r_[-vector, np.zeros(9)]))
+                    upper.extend((0.5, 0.5))
+        for i in range(9):
+            v, a = np.eye(9)[i], -np.eye(9)[i]
+            A.extend((np.r_[v, a], np.r_[-v, a]))
+            upper.extend((0, 0))
+        equality = np.r_[1 / scales[:8], 0, np.zeros(9)]
+        started = time.perf_counter()
+        strict = linprog(np.r_[np.zeros(9), np.ones(9)], A_ub=A, b_ub=upper,
+                         A_eq=[equality], b_eq=[0], bounds=[(None, None)]*9 + [(0, None)]*9,
+                         method="highs", options={"time_limit": 10.0})
+        report["attempts"].append({"kind": "strict_raw_lp", "time_limit_seconds": 10,
+                                   "runtime_seconds": time.perf_counter() - started, "status": int(strict.status),
+                                   "success": bool(strict.success), "message": str(strict.message),
+                                   "objective": "minimize L1 of scaled joint coefficients", "threshold": 1, "span": 1,
+                                   "background_abs_bound": 0.5, "right_min": 1.1, "left_max": -1.1})
+        chosen, span, selected_attempt = strict.x, 1, "strict_raw_lp"
+        if not strict.success:
+            # One MILP, retaining a best balanced coverage diagnostic if the 80% target is unreachable.
+            selected = [(key, i) for key in ("left", "right") for i, ms in enumerate(milliseconds[key]) if ms >= 600]
+            targets = {key: math.ceil(0.8 * sum(k == key for k, _ in selected)) for key in ("left", "right")}
+            nvar = 20 + len(selected)  # 9 coefficients, 9 L1 auxiliaries, span, coverage rho, binaries.
+            A, lower, upper = [], [], []
+            def constrain(vector, low=-np.inf, high=np.inf, extra=None):
+                row = np.zeros(nvar)
+                row[:9] = vector
+                for index, value in (extra or {}).items():
+                    row[index] = value
+                A.append(row)
+                lower.append(low)
+                upper.append(high)
+            for key in ORDER:
+                sign = 1 if key == "right" else -1
+                for vector in F[key]:
+                    if key in ("left", "right"):
+                        constrain(vector, high=0.6, extra={18: -0.85})
+                        constrain(-vector, high=0.6, extra={18: -0.85})
+                        constrain(sign * vector, low=-0.5)
+                    else:
+                        constrain(vector, -0.5, 0.5)
+            for i in range(9):
+                constrain(np.eye(9)[i], high=0, extra={9+i: -1})
+                constrain(-np.eye(9)[i], high=0, extra={9+i: -1})
+            constrain(np.r_[1 / scales[:8], 0], 0, 0)
+            for j, (key, i) in enumerate(selected):
+                sign = 1 if key == "right" else -1
+                # Filtered raw is bounded below by -.5; M=1.55 is therefore sufficient.
+                constrain(sign * E[key][i], low=1.05-1.55, extra={20+j: -1.55})
+            for key in ("left", "right"):
+                constrain(np.zeros(9), low=0,
+                          extra={19: -targets[key], **{20+j: 1 for j, (k, _) in enumerate(selected) if k == key}})
+            objective = np.r_[np.zeros(9), np.full(9, 1e-7), 1e-8, -1, np.zeros(len(selected))]
+            started = time.perf_counter()
+            temporal = milp(objective, integrality=np.r_[np.zeros(20), np.ones(len(selected))],
+                            bounds=Bounds(np.r_[np.full(9, -np.inf), np.zeros(9), 0.5, 0, np.zeros(len(selected))],
+                                          np.r_[np.full(18, np.inf), 2.5, 1, np.ones(len(selected))]),
+                            constraints=LinearConstraint(np.asarray(A), lower, upper),
+                            options={"time_limit": 30.0, "mip_rel_gap": 0})
+            attempt = {"kind": "temporal_cardinality_milp", "time_limit_seconds": 30,
+                       "runtime_seconds": time.perf_counter() - started, "status": int(temporal.status),
+                       "success": bool(temporal.success), "message": str(temporal.message),
+                       "objective": "maximize balanced coverage rho up to ceil(80% stable count) per direction; tiny 1e-7 scaled-L1 and 1e-8 span penalties",
+                       "stable_targets": targets, "threshold": 1, "span_bounds": [0.5, 2.5],
+                       "selected_signed_ema_min": 1.05, "big_m": 1.55, "background_raw_abs_max": 0.5,
+                       "loaded_signed_raw_min": -0.5,
+                       "no_clipping_bound": "abs(raw_score)<=.6+.85*span",
+                       "semantics": "exact host dt/EMA180ms, first sample direct, reset each window; selected EMA>=1.05 activates and output>=.2 for entire span range",
+                       "mip_gap": float(temporal.mip_gap) if getattr(temporal, "mip_gap", None) is not None else None}
+            report["attempts"].append(attempt)
+            chosen = temporal.x
+            selected_attempt = "temporal_cardinality_milp"
+            if chosen is not None:
+                span = float(chosen[18])
+                attempt.update({"span": span, "balanced_target_coverage": float(chosen[19]),
+                                "selected_counts": {key: int(sum(chosen[20+j] > 0.5 for j, (k, _) in enumerate(selected) if k == key))
+                                                    for key in ("left", "right")}})
+                constraint_values = np.asarray(A) @ chosen
+                violation = float(max(np.max(np.asarray(lower) - constraint_values), np.max(constraint_values - np.asarray(upper)), 0))
+                attempt["max_constraint_violation"] = violation
+                if violation > 1e-6:
+                    raise ValueError("MILP incumbent violates numerical constraints")
+        if chosen is None:
+            report["status"] = "no_solver_incumbent"
+            return
+        if not np.all(np.isfinite(chosen)):
+            raise ValueError("nonfinite solver output")
+        coefficients = chosen[:9] / scales
+        weights, beta = coefficients[:8], -float(coefficients[8])
+        if abs(sum(weights)) > 1e-7:
+            raise ValueError("weight sum constraint violated")
+        candidate = encode_profile(old, weights, beta, span=span)
+        norm = float(np.linalg.norm(weights))
+        scores = {key: (rows @ coefficients).tolist() for key, rows in features.items()}
+        max_error = 0
+        for key in ORDER:
+            for sample, score in zip(windows[key]["samples"], scores[key]):
+                ch = [v - b for v, b in zip(sample["channels"], baseline)]
+                encoded = sum(w * (v - leak * normal_score(ch))
+                              for w, v, leak in zip(candidate["shear"]["weights"], contrast(ch), candidate["shear"]["pressLeak"]))
+                max_error = max(max_error, abs(encoded - score / norm))
+        if max_error > 1e-9:
+            raise ValueError("encoded profile scores disagree")
+        report.update({"candidate": candidate, "candidate_sha256": hashlib.sha256(json.dumps(candidate, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest(),
+                       "candidate_sha_encoding": "UTF-8 JSON sorted keys, compact separators, ensure_ascii=True",
+                       "selected_attempt": selected_attempt,
+                       "coefficient_scale": {"weights": weights.tolist(), "beta": beta, "l2_norm": norm,
+                                             "threshold": 1, "span": span, "encoded_score_max_error": max_error},
+                       "all_raw_scores": scores,
+                       "all_unclipped_ema_scores": {key: (rows @ coefficients).tolist() for key, rows in filtered.items()}})
+        replay = refit.replay(candidate, old, windows, baseline)
+        report["replay"] = replay
+        report["accepted_in_sample"] = refit.passes(replay)
+        report["gates"] = {"stable_cutoff_ms": 600, "idle_press_abs_max": 0.05,
+                           "right_min": 0.2, "left_max": -0.2, "active_fraction_min": 0.8,
+                           "wrong_direction_abs_limit": 0.05, "normal_exactly_unchanged": replay["normalUnchanged"]}
+        report["status"] = "frozen_training_candidate" if report["accepted_in_sample"] else "training_gate_failed"
+        report["summaries"] = {}
+        for key in ORDER:
+            report["summaries"][key] = {}
+            for phase in ("transition", "stable"):
+                rows = [row for row in replay["samples"][key] if (row["ms"] < 600) == (phase == "transition")]
+                values = [row["shear"] for row in rows]
+                sign = 1 if key == "right" else -1
+                report["summaries"][key][phase] = {"count": len(values), "min": min(values),
+                    "median": statistics.median(values), "max": max(values),
+                    "active_count": sum(sign * v >= 0.2 for v in values) if key in ("left", "right") else sum(abs(v) > 0.05 for v in values),
+                    "reverse_count": sum(sign * v < -0.05 for v in values) if key in ("left", "right") else 0,
+                    "outside_idle_count": sum(abs(v) > 0.05 for v in values) if key not in ("left", "right") else None}
+        report["right_failure_segments"] = []
+        segment = []
+        for i, row in enumerate(replay["samples"]["right"]):
+            failed = row["ms"] >= 600 and row["shear"] < 0.2
+            if failed:
+                segment.append({"sample_index": i, "ms": row["ms"], "host": windows["right"]["samples"][i]["host"],
+                                "frame": windows["right"]["samples"][i]["f"], "raw_score": scores["right"][i],
+                                "ema_score": report["all_unclipped_ema_scores"]["right"][i],
+                                "normal_output": row["normal"], "output": row["shear"]})
+            if segment and (not failed or i == len(replay["samples"]["right"])-1):
+                report["right_failure_segments"].append(segment)
+                segment = []
+    except Exception as exc:
+        report["status"] = "error"
+        report["error"] = {"type": type(exc).__name__, "message": str(exc)}
+    finally:
+        report["protection_hashes_after"] = {name: digest(Path(name)) for name in protected}
+        report["protection_unchanged"] = before == report["protection_hashes_after"]
+        report["source_hashes_verified_after_run"] = all(digest(ROOT / entry["path"]) == entry["sha256"] for entry in report["sources"].values())
+        OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
+        print(json.dumps({"status": report["status"], "accepted_in_sample": report["accepted_in_sample"],
+                          "attempts": report["attempts"], "error": report.get("error"), "report": str(OUTPUT)}, ensure_ascii=True))
+
+
+if __name__ == "__main__":
+    main()
+

--- /dev/null
+++ tests/test_joint_shear_fit.py
@@ newly added full file @@
+"""Behavioral checks for the offline free-normal-leak profile encoding."""
+import importlib.util
+import math
+from pathlib import Path
+import unittest
+
+
+SCRIPT = Path(__file__).resolve().parents[1] / ".superpowers/sdd/shear_refit_joint_leak_20261005.py"
+
+
+class JointShearEncodingTests(unittest.TestCase):
+    def test_free_beta_matches_existing_profile_score_and_threshold_scale(self):
+        self.assertTrue(SCRIPT.exists(), "free-beta profile encoder is missing")
+        spec = importlib.util.spec_from_file_location("joint_shear_fit", SCRIPT)
+        module = importlib.util.module_from_spec(spec)
+        spec.loader.exec_module(module)
+        old = {"version": 1, "mode": "qualitative", "normal": {"threshold": 100, "span": 600},
+               "labels": {"right": "right", "left": "left"}, "extra": "preserve",
+               "shear": {"enabled": False}}
+        weights = [2, -2, 1, -1, 0.5, -0.5, 3, -3]
+        norm = math.hypot(*weights)
+        for beta in (0.7, -0.7):
+            candidate = module.encode_profile(old, weights, beta, threshold=1, span=2)
+            self.assertEqual(candidate["normal"], old["normal"])
+            self.assertEqual(candidate["labels"], old["labels"])
+            self.assertEqual(candidate["extra"], "preserve")
+            self.assertAlmostEqual(math.hypot(*candidate["shear"]["weights"]), 1)
+            self.assertAlmostEqual(candidate["shear"]["threshold"], 1 / norm)
+            self.assertAlmostEqual(candidate["shear"]["span"], 2 / norm)
+            for normal in (0, 500):
+                ch = [9, 2, -4, 7, 11, -8, 3, 0] + [normal] * 4
+                average = sum(ch[:8]) / 8
+                expected = (sum(w * (v - average) for w, v in zip(weights, ch[:8])) - beta * normal) / norm
+                shear = candidate["shear"]
+                actual = sum(w * (v - average - leak * normal)
+                             for w, v, leak in zip(shear["weights"], ch[:8], shear["pressLeak"]))
+                self.assertAlmostEqual(actual, expected, places=11)
+        for weights_bad, beta_bad in (([0] * 8, 1), ([float("nan")] * 8, 1), (weights, float("inf"))):
+            with self.assertRaises(ValueError):
+                module.encode_profile(old, weights_bad, beta_bad)
+
+
+if __name__ == "__main__":
+    unittest.main()
+


