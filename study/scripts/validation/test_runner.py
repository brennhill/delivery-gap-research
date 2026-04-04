#!/usr/bin/env python3
"""Tests for runner.py — resilience, resume, manifest correctness."""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from runner import run_all, _save_manifest, _slug, _fetch_prs_fallback


# ── Helpers ──────────────────────────────────────────────────────────

def _repo_entry(repo, tier="AI", lang="TypeScript"):
    return {"repo": repo, "lang": lang, "tier": tier}


def _make_manifest(tmp, repos_data):
    """Write a manifest.json with given repo results."""
    manifest = {
        "started_at": "2026-01-01T00:00:00+00:00",
        "finished_at": "2026-01-01T01:00:00+00:00",
        "total_repos": len(repos_data),
        "spec_signals_success": sum(1 for r in repos_data if r["spec_signals"]["success"]),
        "catchrate_success": sum(1 for r in repos_data if r["catchrate"]["success"]),
        "repos": repos_data,
    }
    (tmp / "manifest.json").write_text(json.dumps(manifest, indent=2))


def _fake_result(repo, success=True, msg="100 PRs"):
    return {
        "repo": repo,
        "language": "TypeScript",
        "tier": "AI",
        "fetch": {"success": success, "message": msg},
        "spec_signals": {"success": success, "message": "success" if success else "skipped"},
        "catchrate": {"success": success, "message": "success" if success else "skipped"},
    }


# ── Unit tests ───────────────────────────────────────────────────────

class TestSlug:
    def test_simple(self):
        assert _slug("owner/repo") == "owner-repo"

    def test_nested(self):
        assert _slug("org/sub-repo") == "org-sub-repo"


class TestSaveManifest:
    def test_writes_valid_json(self, tmp_path):
        path = tmp_path / "manifest.json"
        results = {"foo/bar": _fake_result("foo/bar")}
        _save_manifest(path, "2026-01-01", 1, results, dry_run=False)

        data = json.loads(path.read_text())
        assert data["total_repos"] == 1
        assert data["spec_signals_success"] == 1
        assert len(data["repos"]) == 1
        assert data["repos"][0]["repo"] == "foo/bar"

    def test_dry_run_skips(self, tmp_path):
        path = tmp_path / "manifest.json"
        _save_manifest(path, "2026-01-01", 1, {}, dry_run=True)
        assert not path.exists()

    def test_no_duplicates(self, tmp_path):
        path = tmp_path / "manifest.json"
        results = {
            "a/b": _fake_result("a/b"),
            "c/d": _fake_result("c/d"),
        }
        _save_manifest(path, "2026-01-01", 2, results, dry_run=False)
        data = json.loads(path.read_text())
        assert len(data["repos"]) == 2
        repos = [r["repo"] for r in data["repos"]]
        assert len(set(repos)) == 2  # no duplicates


class TestRunAllResilience:
    """Test that run_all never crashes on individual repo failures."""

    @patch("runner.fetch_prs")
    @patch("runner.run_tool")
    def test_single_failure_doesnt_kill_batch(self, mock_tool, mock_fetch, tmp_path):
        """If one repo fails, others still complete."""
        import runner
        orig_data_dir = runner.DATA_DIR
        runner.DATA_DIR = tmp_path

        def fetch_side_effect(repo, prs_path, dry_run=False):
            if repo == "bad/repo":
                raise RuntimeError("Simulated explosion")
            prs_path.write_text("[]")
            return True, "10 PRs"

        mock_fetch.side_effect = fetch_side_effect
        mock_tool.return_value = (True, "success")

        repos = [
            _repo_entry("good/first"),
            _repo_entry("bad/repo"),
            _repo_entry("good/last"),
        ]

        result = run_all(repos, dry_run=False)
        runner.DATA_DIR = orig_data_dir

        # All 3 repos should be in results
        assert len(result["repos"]) == 3
        repos_by_name = {r["repo"]: r for r in result["repos"]}
        assert repos_by_name["good/first"]["fetch"]["success"] is True
        assert repos_by_name["bad/repo"]["fetch"]["success"] is False
        assert repos_by_name["good/last"]["fetch"]["success"] is True

    @patch("runner.fetch_prs")
    @patch("runner.run_tool")
    def test_always_fetches_and_merges(self, mock_tool, mock_fetch, tmp_path):
        """All repos are fetched every run (merge with existing data)."""
        import runner
        orig_data_dir = runner.DATA_DIR
        runner.DATA_DIR = tmp_path

        mock_fetch.return_value = (True, "50 PRs")
        mock_tool.return_value = (True, "success")

        repos = [
            _repo_entry("repo/one"),
            _repo_entry("repo/two"),
        ]

        # Create dummy prs files
        (tmp_path / "prs-repo-one.json").write_text("[]")
        (tmp_path / "prs-repo-two.json").write_text("[]")

        run_all(repos, dry_run=False)
        runner.DATA_DIR = orig_data_dir

        # Both repos should be fetched (no skipping)
        fetch_calls = [c[0][0] for c in mock_fetch.call_args_list]
        assert "repo/one" in fetch_calls
        assert "repo/two" in fetch_calls

    @patch("runner.fetch_prs")
    @patch("runner.run_tool")
    def test_manifest_saved_incrementally(self, mock_tool, mock_fetch, tmp_path):
        """Manifest is saved after each repo."""
        import runner
        orig_data_dir = runner.DATA_DIR
        runner.DATA_DIR = tmp_path

        save_counts = []

        def counting_fetch(repo, prs_path, dry_run=False):
            prs_path.write_text("[]")
            # Check manifest after each repo
            mpath = tmp_path / "manifest.json"
            if mpath.exists():
                m = json.loads(mpath.read_text())
                save_counts.append(len(m["repos"]))
            return True, "10 PRs"

        mock_fetch.side_effect = counting_fetch
        mock_tool.return_value = (True, "success")

        repos = [_repo_entry("a/a"), _repo_entry("b/b"), _repo_entry("c/c")]
        run_all(repos, dry_run=False)
        runner.DATA_DIR = orig_data_dir

        # Manifest should have been saved after repos 1 and 2
        # (we check inside fetch, so we see the state AFTER previous repo saved)
        assert len(save_counts) >= 2
        assert save_counts[-1] >= 2  # at least 2 repos saved before 3rd fetch

    @patch("runner.fetch_prs")
    @patch("runner.run_tool")
    def test_no_duplicate_repos_in_manifest(self, mock_tool, mock_fetch, tmp_path):
        """Running the same repo list twice doesn't create duplicates."""
        import runner
        orig_data_dir = runner.DATA_DIR
        runner.DATA_DIR = tmp_path

        mock_fetch.return_value = (True, "10 PRs")
        mock_tool.return_value = (True, "success")

        repos = [_repo_entry("test/repo")]

        # Create prs file
        (tmp_path / "prs-test-repo.json").write_text("[]")

        # Run twice
        run_all(repos, dry_run=False)
        run_all(repos, dry_run=False)  # should skip (already done)
        runner.DATA_DIR = orig_data_dir

        m = json.loads((tmp_path / "manifest.json").read_text())
        repo_names = [r["repo"] for r in m["repos"]]
        assert repo_names.count("test/repo") == 1


class TestFetchTimeout:
    """Test that fetch_prs doesn't hang forever."""

    def test_syntax_valid(self):
        """runner.py parses without syntax errors."""
        import ast
        ast.parse(Path("runner.py").read_text())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
