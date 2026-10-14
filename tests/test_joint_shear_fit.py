"""Behavioral checks for the offline free-normal-leak profile encoding."""
import importlib.util
import math
from pathlib import Path
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / ".superpowers/sdd/shear_refit_joint_leak_20261005.py"


class JointShearEncodingTests(unittest.TestCase):
    def test_free_beta_matches_existing_profile_score_and_threshold_scale(self):
        self.assertTrue(SCRIPT.exists(), "free-beta profile encoder is missing")
        spec = importlib.util.spec_from_file_location("joint_shear_fit", SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        old = {"version": 1, "mode": "qualitative", "normal": {"threshold": 100, "span": 600},
               "labels": {"right": "right", "left": "left"}, "extra": "preserve",
               "shear": {"enabled": False}}
        weights = [2, -2, 1, -1, 0.5, -0.5, 3, -3]
        norm = math.hypot(*weights)
        for beta in (0.7, -0.7):
            candidate = module.encode_profile(old, weights, beta, threshold=1, span=2)
            self.assertEqual(candidate["normal"], old["normal"])
            self.assertEqual(candidate["labels"], old["labels"])
            self.assertEqual(candidate["extra"], "preserve")
            self.assertAlmostEqual(math.hypot(*candidate["shear"]["weights"]), 1)
            self.assertAlmostEqual(candidate["shear"]["threshold"], 1 / norm)
            self.assertAlmostEqual(candidate["shear"]["span"], 2 / norm)
            for normal in (0, 500):
                ch = [9, 2, -4, 7, 11, -8, 3, 0] + [normal] * 4
                average = sum(ch[:8]) / 8
                expected = (sum(w * (v - average) for w, v in zip(weights, ch[:8])) - beta * normal) / norm
                shear = candidate["shear"]
                actual = sum(w * (v - average - leak * normal)
                             for w, v, leak in zip(shear["weights"], ch[:8], shear["pressLeak"]))
                self.assertAlmostEqual(actual, expected, places=11)
        for weights_bad, beta_bad in (([0] * 8, 1), ([float("nan")] * 8, 1), (weights, float("inf"))):
            with self.assertRaises(ValueError):
                module.encode_profile(old, weights_bad, beta_bad)


if __name__ == "__main__":
    unittest.main()
