#!/usr/bin/env python3

import unittest
from pathlib import Path

import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[2]


class TestSpecTreatmentDefinition(unittest.TestCase):
    def test_specd_and_q_overall_presence_are_not_equivalent(self):
        df = pd.read_csv(ROOT_DIR / "data" / "master-prs.csv", low_memory=False)

        specd = df["specd"].map(
            {
                True: True,
                False: False,
                "True": True,
                "False": False,
                "true": True,
                "false": False,
                1: True,
                0: False,
                "1": True,
                "0": False,
            }
        )
        scored = pd.to_numeric(df["q_overall"], errors="coerce").notna()

        self.assertEqual(((specd == False) & scored).sum(), 1656)
        self.assertEqual(((specd == True) & ~scored).sum(), 104)

    def test_analysis_scripts_do_not_define_treatment_from_q_overall_presence(self):
        bad_snippets = {
            ROOT_DIR / "scripts" / "analysis" / "spec-vs-nospec-analysis.py":
                'df["has_spec"] = df["q_overall"].notna().astype(int)',
            ROOT_DIR / "scripts" / "analysis" / "full-spec-analysis.py":
                'r["_has_spec"] = 1 if to_float(r["q_overall"]) is not None else 0',
        }

        for path, snippet in bad_snippets.items():
            src = path.read_text()
            self.assertNotIn(snippet, src, f"{path.name} still defines treatment from q_overall presence")
            self.assertIn("specd", src, f"{path.name} should use specd for the treatment definition")


if __name__ == "__main__":
    unittest.main()
