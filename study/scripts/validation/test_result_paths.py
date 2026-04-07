#!/usr/bin/env python3

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT_DIR = Path(__file__).resolve().parents[2]
UTIL_DIR = ROOT_DIR / "scripts" / "util"
sys.path.insert(0, str(UTIL_DIR))


class TestResultPaths(unittest.TestCase):
    def test_default_results_dir_is_study_results(self):
        from result_paths import get_results_dir

        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(get_results_dir(ROOT_DIR), ROOT_DIR / "results")

    def test_exact_only_defaults_to_separate_subdirectory(self):
        from result_paths import get_results_dir

        with patch.dict(os.environ, {"SZZ_EXACT_ONLY": "1"}, clear=True):
            self.assertEqual(get_results_dir(ROOT_DIR), ROOT_DIR / "results" / "exact-only")

    def test_results_dir_env_override_takes_precedence(self):
        from result_paths import get_results_dir

        custom = ROOT_DIR / "results" / "custom-output"
        with patch.dict(
            os.environ,
            {"SZZ_EXACT_ONLY": "1", "RESULTS_DIR": str(custom)},
            clear=True,
        ):
            self.assertEqual(get_results_dir(ROOT_DIR), custom)


class TestPipelineScriptsUseSharedResultsPath(unittest.TestCase):
    def test_primary_pipeline_scripts_use_result_path_utility(self):
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
            self.assertIn("result_path", src, f"{path.name} should use the shared results-path utility")
            self.assertNotIn(
                'parent.parent.parent / "results"',
                src,
                f"{path.name} should not hardcode the top-level results directory",
            )


if __name__ == "__main__":
    unittest.main()
