#!/usr/bin/env python3

import csv
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT_DIR = Path(__file__).resolve().parents[2]
PIPELINE_DIR = ROOT_DIR / "scripts" / "pipeline"


def _load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class TestCatchrateMissingness(unittest.TestCase):
    def test_build_unified_preserves_missing_catchrate_fields(self):
        mod = _load_module("build_unified_csv_test", PIPELINE_DIR / "build-unified-csv.py")

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            prs = [
                {
                    "repo": "owner/repo",
                    "pr_number": 1,
                    "title": "Add feature",
                    "author": "alice",
                    "merged_at": "2026-01-15T12:00:00Z",
                    "additions": 10,
                    "deletions": 2,
                    "files": ["src/app.py"],
                }
            ]
            (tmp_path / "prs-owner-repo.json").write_text(json.dumps(prs))

            with patch.object(mod, "DATA_DIR", tmp_path), patch.object(mod, "_get_tier", return_value="T1"):
                rows = mod.build_rows()

            self.assertEqual(len(rows), 1)
            row = rows[0]
            self.assertEqual(row["classification"], "")
            self.assertEqual(row["ci_status"], "")
            self.assertEqual(row["review_modified"], "")
            self.assertEqual(row["escaped"], "")
            self.assertEqual(row["review_cycles"], "")
            self.assertEqual(row["time_to_merge_hours"], "")
            self.assertEqual(row["lines_changed"], "")
            self.assertEqual(row["size_bucket"], "")

    def test_build_master_preserves_missing_strict_escaped(self):
        mod = _load_module("build_master_csv_test", PIPELINE_DIR / "build-master-csv.py")

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            fieldnames = [
                "repo",
                "pr_number",
                "title",
                "author",
                "merged_at",
                "escaped",
                "q_overall",
            ]
            with open(tmp_path / "unified-prs.csv", "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerow(
                    {
                        "repo": "owner/repo",
                        "pr_number": 1,
                        "title": "Add feature",
                        "author": "alice",
                        "merged_at": "2026-01-15T12:00:00Z",
                        "escaped": "",
                        "q_overall": "",
                    }
                )

            with patch.object(mod, "DATA_DIR", tmp_path):
                mod.main()

            with open(tmp_path / "master-prs.csv", newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))

            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["strict_escaped"], "")


if __name__ == "__main__":
    unittest.main()
