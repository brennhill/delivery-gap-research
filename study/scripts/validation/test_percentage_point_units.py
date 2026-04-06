#!/usr/bin/env python3

import sys
import unittest
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
UTIL_DIR = ROOT_DIR / "scripts" / "util"
sys.path.insert(0, str(UTIL_DIR))

from effect_units import format_percentage_point_delta  # noqa: E402


class TestPercentagePointUnits(unittest.TestCase):
    def test_formatter_scales_raw_probability_deltas_to_percentage_points(self):
        self.assertEqual(format_percentage_point_delta(0.014), "+1.40 pp")
        self.assertEqual(format_percentage_point_delta(-0.0235), "-2.35 pp")
        self.assertEqual(format_percentage_point_delta(0.0), "+0.00 pp")

    def test_pipeline_scripts_do_not_print_raw_decimals_as_pp(self):
        targets = [
            ROOT_DIR / "scripts" / "pipeline" / "full-szz-analysis.py",
            ROOT_DIR / "scripts" / "pipeline" / "propensity-score-matching.py",
        ]

        bad_snippets = [
            '{coef:+.4f} pp',
            '{diff:+.4f} pp',
            '{result[\'diff\']:+.4f} pp',
            '{result[\'raw_diff\']:+.4f} pp',
        ]

        for path in targets:
            src = path.read_text()
            for snippet in bad_snippets:
                self.assertNotIn(snippet, src, f"{path.name} still prints raw decimals as percentage points")
            self.assertIn("format_percentage_point_delta", src, f"{path.name} should use the shared pp formatter")

    def test_full_szz_controlled_logit_reports_coef_and_or(self):
        src = (ROOT_DIR / "scripts" / "pipeline" / "full-szz-analysis.py").read_text()
        self.assertIn("Controlled (logistic regression + repo FE): log-odds coefficients", src)
        self.assertIn("OR=", src)
        self.assertIn("np.exp(coef)", src)


if __name__ == "__main__":
    unittest.main()
