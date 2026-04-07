#!/usr/bin/env python3

import sys
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
UTIL_DIR = ROOT_DIR / "scripts" / "util"
sys.path.insert(0, str(UTIL_DIR))

from multiple_testing import benjamini_hochberg_qvalues, bonferroni_adjust  # noqa: E402


class TestMultipleTestingMath(unittest.TestCase):
    def test_bonferroni_adjustment_scales_by_family_size(self):
        adjusted = bonferroni_adjust([0.01, 0.03, 0.04, 0.20])
        self.assertEqual(adjusted, [0.04, 0.12, 0.16, 0.8])

    def test_benjamini_hochberg_returns_monotone_q_values(self):
        adjusted = benjamini_hochberg_qvalues([0.01, 0.03, 0.04, 0.20])
        expected = [0.04, 0.05333333333333334, 0.05333333333333334, 0.2]
        for got, want in zip(adjusted, expected):
            self.assertAlmostEqual(got, want)


class TestFullSzzReportIncludesPrimaryFamilyAdjustment(unittest.TestCase):
    def test_full_szz_analysis_reports_adjusted_primary_p_values(self):
        src = (ROOT_DIR / "scripts" / "pipeline" / "full-szz-analysis.py").read_text()
        self.assertIn("PRIMARY-FAMILY MULTIPLE-TESTING ADJUSTMENT", src)
        self.assertIn("Bonferroni-adjusted p", src)
        self.assertIn("BH q-value", src)
        self.assertIn("Exploratory JIT/robustness tests are not part of this family", src)


if __name__ == "__main__":
    unittest.main()
