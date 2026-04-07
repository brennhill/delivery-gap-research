#!/usr/bin/env python3

import json
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[2]
UTIL_DIR = ROOT_DIR / "scripts" / "util"
sys.path.insert(0, str(UTIL_DIR))


class TestSzzDataLoader(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.tmpdir.name)

        pd.DataFrame(
            [
                {
                    "repo": "acme/widgets",
                    "fix_pr_number": 10,
                    "fix_merge_sha": "fixsha1",
                    "bug_commit_sha": "exactsha",
                    "file": "src/a.py",
                    "bug_pr_number": 1,
                },
                {
                    "repo": "acme/widgets",
                    "fix_pr_number": 11,
                    "fix_merge_sha": "fixsha2",
                    "bug_commit_sha": "fallbacksha",
                    "file": "src/b.py",
                    "bug_pr_number": 2,
                },
                {
                    "repo": "acme/widgets",
                    "fix_pr_number": 12,
                    "fix_merge_sha": "fixsha3",
                    "bug_commit_sha": "unmappedsha",
                    "file": "src/c.py",
                    "bug_pr_number": None,
                },
            ]
        ).to_csv(self.data_dir / "szz-results-merged.csv", index=False)

        with open(self.data_dir / "prs-acme-widgets.json", "w") as f:
            json.dump(
                [
                    {"pr_number": 1, "merge_commit_sha": "exactsha"},
                    {"pr_number": 2, "merge_commit_sha": "different-merge-sha"},
                ],
                f,
            )

    def tearDown(self):
        self.tmpdir.cleanup()

    def test_exact_only_filters_to_rows_with_matching_bug_commit_and_merge_sha(self):
        from szz_data import load_szz_results

        szz, meta = load_szz_results(self.data_dir, exact_only=True)

        self.assertEqual(meta["mode"], "exact_only")
        self.assertEqual(meta["source_rows"], 3)
        self.assertEqual(meta["exact_rows"], 1)
        self.assertEqual(meta["fallback_rows"], 1)
        self.assertEqual(meta["unmapped_rows"], 1)
        self.assertEqual(len(szz), 1)
        self.assertEqual(szz.iloc[0]["bug_commit_sha"], "exactsha")

    def test_full_mode_returns_all_rows_without_filtering(self):
        from szz_data import load_szz_results

        szz, meta = load_szz_results(self.data_dir, exact_only=False)

        self.assertEqual(meta["mode"], "full")
        self.assertEqual(meta["source_rows"], 3)
        self.assertEqual(len(szz), 3)


class TestPipelineScriptsUseSharedSzzLoader(unittest.TestCase):
    def test_primary_pipeline_scripts_use_shared_loader(self):
        targets = [
            ROOT_DIR / "scripts" / "pipeline" / "full-szz-analysis.py",
            ROOT_DIR / "scripts" / "pipeline" / "primary-with-jit-controls.py",
            ROOT_DIR / "scripts" / "pipeline" / "propensity-score-matching.py",
            ROOT_DIR / "scripts" / "pipeline" / "robustness-subgroups.py",
            ROOT_DIR / "scripts" / "pipeline" / "robustness-highquality.py",
            ROOT_DIR / "scripts" / "pipeline" / "robustness-temporal.py",
            ROOT_DIR / "scripts" / "pipeline" / "robustness-complexity.py",
            ROOT_DIR / "scripts" / "pipeline" / "robustness-issue-linked.py",
        ]

        for path in targets:
            src = path.read_text()
            self.assertIn("load_szz_results", src, f"{path.name} should use the shared SZZ loader")
            self.assertNotIn(
                'pd.read_csv(DATA_DIR / "szz-results-merged.csv")',
                src,
                f"{path.name} should not hardcode the merged SZZ CSV read",
            )


if __name__ == "__main__":
    unittest.main()
