#!/usr/bin/env python3

import sys
import unittest
from pathlib import Path

import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[2]
UTIL_DIR = ROOT_DIR / "scripts" / "util"
sys.path.insert(0, str(UTIL_DIR))

from quality_tiers import (  # noqa: E402
    BOTTOM_75,
    TOP_10,
    TOP_25_ONLY,
    LOCKED_TOP_DECILE_CUTOFF,
    LOCKED_TOP_QUARTILE_CUTOFF,
    quality_tier,
)


class TestQualityTierThresholds(unittest.TestCase):
    def test_locked_cutoffs_match_current_master_csv_quantiles(self):
        q = pd.to_numeric(
            pd.read_csv(ROOT_DIR / "data" / "master-prs.csv", low_memory=False)["q_overall"],
            errors="coerce",
        ).dropna()

        self.assertEqual(LOCKED_TOP_QUARTILE_CUTOFF, q.quantile(0.75))
        self.assertEqual(LOCKED_TOP_DECILE_CUTOFF, q.quantile(0.90))

    def test_quality_tier_uses_locked_quantile_bands(self):
        self.assertEqual(quality_tier(57), BOTTOM_75)
        self.assertEqual(quality_tier(58), TOP_25_ONLY)
        self.assertEqual(quality_tier(65), TOP_25_ONLY)
        self.assertEqual(quality_tier(66), TOP_10)


class TestScriptsUseLockedThresholds(unittest.TestCase):
    def test_scripts_no_longer_hardcode_legacy_bins(self):
        targets = [
            ROOT_DIR / "scripts" / "analysis" / "full-spec-analysis.py",
            ROOT_DIR / "scripts" / "analysis" / "join-spec-quality.py",
            ROOT_DIR / "scripts" / "analysis" / "spec-quality-no-promptfoo.py",
            ROOT_DIR / "scripts" / "analysis" / "szz-jit-analysis.py",
            ROOT_DIR / "scripts" / "pipeline" / "robustness-highquality.py",
            ROOT_DIR / "scripts" / "pipeline" / "robustness-temporal.py",
        ]

        legacy_snippets = ["<= 2.0", "<= 3.5", "if q < 40", "if val < 40", "if q < 70", "if val < 70"]

        for path in targets:
            src = path.read_text()
            for snippet in legacy_snippets:
                self.assertNotIn(snippet, src, f"{path.name} still contains legacy tier snippet {snippet!r}")

    def test_robustness_scripts_use_locked_cutoff_constants(self):
        for path in [
            ROOT_DIR / "scripts" / "pipeline" / "robustness-highquality.py",
            ROOT_DIR / "scripts" / "pipeline" / "robustness-temporal.py",
        ]:
            src = path.read_text()
            self.assertIn("LOCKED_TOP_QUARTILE_CUTOFF", src, f"{path.name} should use the locked p75 cutoff")
            self.assertIn("LOCKED_TOP_DECILE_CUTOFF", src, f"{path.name} should use the locked p90 cutoff")


if __name__ == "__main__":
    unittest.main()
