import json
import importlib.util
import math
import unittest
from pathlib import Path


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CANDIDATE = HERE / "center-pull-refit-20261006-candidate.json"
SPEC = importlib.util.spec_from_file_location(
    "center_pull_refit_20261006", HERE / "center-pull-refit-20261006.py"
)
refit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(refit)


class CenterPullRegression(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.installed = json.loads(refit.INSTALLED.read_text(encoding="utf-8"))
        cls.candidate = json.loads(CANDIDATE.read_text(encoding="utf-8"))
        cls.actual = refit.load_actual()
        cls.raw = refit.load_fixed_raw()
        profiles = {"installed": cls.installed, "candidate": cls.candidate}
        cls.actual_summary = refit.summarize(cls.actual, refit.replay(cls.actual, profiles))
        cls.raw_summary = refit.summarize(cls.raw, refit.replay(cls.raw, profiles))

    def test_full_center_minus_x_is_stably_right_without_normal_change(self):
        result = next(
            row for row in self.actual_summary
            if row["source"] == "shear-center-pull-full-diagnostic-20261005.json"
        )
        current = result["replay"]["candidate"]
        self.assertGreaterEqual(current["minus_active"] / current["stable_samples"], 0.8)
        self.assertEqual(current["reverse"], 0)
        self.assertTrue(result["normal_identical"])

    def test_all_actual_page_and_historical_fixed_raw_gates(self):
        self.assertEqual(refit.gate(self.actual_summary, "candidate"), [])
        self.assertEqual(refit.gate(self.raw_summary, "candidate"), [])

    def test_candidate_preserves_profile_contract(self):
        self.assertEqual(self.candidate["version"], self.installed["version"])
        self.assertEqual(self.candidate["mode"], self.installed["mode"])
        self.assertEqual(self.candidate["assemblyId"], self.installed["assemblyId"])
        self.assertEqual(self.candidate["normal"], self.installed["normal"])
        self.assertEqual(self.candidate["rightLabel"], self.installed["rightLabel"])
        self.assertEqual(self.candidate["leftLabel"], self.installed["leftLabel"])
        self.assertEqual(self.candidate["shear"]["threshold"], self.installed["shear"]["threshold"])
        self.assertEqual(self.candidate["shear"]["span"], self.installed["shear"]["span"])
        self.assertTrue(math.isclose(sum(self.candidate["shear"]["weights"]), 0, abs_tol=1e-12))


if __name__ == "__main__":
    unittest.main()
