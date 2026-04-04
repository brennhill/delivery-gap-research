#!/usr/bin/env python3
"""unittest coverage for runner resume/completion semantics."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fetch_progress import load_fetch_status, write_fetch_status
from runner import fetch_prs, run_all


def _repo_entry(repo, tier="AI", lang="TypeScript"):
    return {"repo": repo, "lang": lang, "tier": tier}


class _InlineProcess:
    """Run the multiprocessing target inline for unit tests."""

    def __init__(self, target=None, args=()):
        self._target = target
        self._args = args
        self._alive = False

    def start(self):
        self._alive = True
        try:
            if self._target is not None:
                self._target(*self._args)
        finally:
            self._alive = False

    def join(self, timeout=None):
        return None

    def is_alive(self):
        return self._alive

    def kill(self):
        self._alive = False


class TestRunnerResume(unittest.TestCase):
    @patch("multiprocessing.Process", _InlineProcess)
    def test_gap_fetch_requires_completion_marker(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            prs_path = Path(tmpdir) / "prs-owner-repo.json"

            def partial_worker(repo, prs_path_str, since_iso=None, until_iso=None):
                Path(prs_path_str).write_text(json.dumps([
                    {"pr_number": 1, "merged_at": "2025-04-10T00:00:00+00:00"},
                ]))

            with patch("runner._fetch_worker", side_effect=partial_worker):
                ok, msg = fetch_prs(
                    "owner/repo",
                    prs_path,
                    dry_run=False,
                    since_iso="2025-04-01T00:00:00+00:00",
                    until_iso="2025-04-15T00:00:00+00:00",
                )

            self.assertFalse(ok)
            self.assertIn("partial gap progress saved", msg)
            self.assertEqual(len(json.loads(prs_path.read_text())), 1)
            self.assertIsNone(load_fetch_status(prs_path))

    @patch("multiprocessing.Process", _InlineProcess)
    def test_gap_fetch_can_complete_with_no_new_prs(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            prs_path = Path(tmpdir) / "prs-owner-repo.json"
            prs_path.write_text(json.dumps([
                {"pr_number": 1, "merged_at": "2025-04-15T00:00:00+00:00"},
            ]))

            def complete_worker(repo, prs_path_str, since_iso=None, until_iso=None):
                write_fetch_status(
                    Path(prs_path_str),
                    repo=repo,
                    requested_since_iso=since_iso,
                    requested_until_iso=until_iso,
                    completed_at_iso="2026-04-03T00:00:00+00:00",
                )

            with patch("runner._fetch_worker", side_effect=complete_worker):
                ok, msg = fetch_prs(
                    "owner/repo",
                    prs_path,
                    dry_run=False,
                    since_iso="2025-04-01T00:00:00+00:00",
                    until_iso="2025-04-15T00:00:00+00:00",
                )

            self.assertTrue(ok)
            self.assertIn("gap complete", msg)

    @patch("runner.fetch_prs")
    @patch("runner.run_tool")
    def test_run_all_scopes_manifest_to_current_batch(self, mock_tool, mock_fetch):
        import runner

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_path = Path(tmpdir)
            orig_data_dir = runner.DATA_DIR
            runner.DATA_DIR = tmp_path

            manifest = {
                "started_at": "2026-01-01T00:00:00+00:00",
                "finished_at": "2026-01-01T01:00:00+00:00",
                "total_repos": 2,
                "catchrate_success": 2,
                "repos": [
                    {"repo": "old/one", "language": "TypeScript", "tier": "AI",
                     "fetch": {"success": True, "message": "ok"},
                     "catchrate": {"success": True, "message": "ok"}},
                    {"repo": "old/two", "language": "TypeScript", "tier": "AI",
                     "fetch": {"success": True, "message": "ok"},
                     "catchrate": {"success": True, "message": "ok"}},
                ],
            }
            (tmp_path / "manifest.json").write_text(json.dumps(manifest, indent=2))

            mock_fetch.return_value = (True, "10 PRs")
            mock_tool.return_value = (True, "success")

            repos = [_repo_entry("new/repo")]
            (tmp_path / "prs-new-repo.json").write_text("[]")

            result = run_all(repos, dry_run=False)
            runner.DATA_DIR = orig_data_dir

            self.assertEqual(len(result["repos"]), 1)
            self.assertEqual(result["repos"][0]["repo"], "new/repo")

            saved = json.loads((tmp_path / "manifest.json").read_text())
            self.assertEqual(saved["total_repos"], 1)
            self.assertEqual(saved["catchrate_success"], 1)
            self.assertEqual([r["repo"] for r in saved["repos"]], ["new/repo"])


if __name__ == "__main__":
    unittest.main()
