#!/usr/bin/env python3
"""Tests for page-level gap fetch resume checkpoints."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fetch_progress import (
    get_active_gap_checkpoint,
    load_fetch_status,
    load_progress_state,
    progress_state_path,
)
import runner


class _DummyChange:
    def __init__(self, number: int, merged_at: str) -> None:
        self.number = number
        self.merged_at = merged_at

    def to_dict(self) -> dict:
        return {
            "pr_number": self.number,
            "merged_at": self.merged_at,
        }


class TestGapResume(unittest.TestCase):
    def test_merge_head_commit_rollup_moves_status_to_last_commit(self):
        pr_node = {
            "commits": {
                "nodes": [
                    {"commit": {"message": "first"}},
                    {"commit": {"message": "last"}},
                ]
            },
            "headCommit": {
                "nodes": [
                    {
                        "commit": {
                            "statusCheckRollup": {
                                "contexts": {"nodes": [{"state": "SUCCESS"}]}
                            }
                        }
                    }
                ]
            },
        }

        merged = runner._merge_head_commit_rollup(pr_node)

        self.assertNotIn("headCommit", merged)
        self.assertNotIn("statusCheckRollup", merged["commits"]["nodes"][0]["commit"])
        self.assertEqual(
            merged["commits"]["nodes"][-1]["commit"]["statusCheckRollup"]["contexts"]["nodes"][0]["state"],
            "SUCCESS",
        )

    def test_gap_fetch_backs_off_to_page_size_two(self):
        from delivery_gap_signals.sources import github_graphql

        since_iso = "2025-04-01T00:00:00+00:00"
        until_iso = "2025-04-15T00:00:00+00:00"

        page = {
            "data": {
                "repository": {
                    "pullRequests": {
                        "nodes": [{"number": 201, "mergedAt": "2025-04-10T00:00:00Z"}],
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                    }
                }
            }
        }

        seen_sizes = []

        def run_graphql(query, variables):
            seen_sizes.append(variables["pageSize"])
            if variables["pageSize"] > 2:
                raise RuntimeError("GraphQL query failed: gh: HTTP 504")
            return page

        def parse_pr(pr, repo, lookback_days, since=None, until=None):
            return _DummyChange(pr["number"], pr["mergedAt"].replace("Z", "+00:00"))

        with tempfile.TemporaryDirectory() as tmpdir:
            prs_path = Path(tmpdir) / "prs-owner-repo.json"

            with patch.object(github_graphql, "_skip_to_window_fast", return_value=None), \
                 patch.object(github_graphql, "_parse_pr_node", side_effect=parse_pr), \
                 patch.object(github_graphql, "_run_graphql", side_effect=run_graphql):
                runner._fetch_gap_with_resume("owner/repo", str(prs_path), since_iso, until_iso)

            saved = json.loads(prs_path.read_text())
            self.assertEqual([pr["pr_number"] for pr in saved], [201])
            self.assertEqual(seen_sizes, [15, 7, 3, 2])

    def test_gap_fetch_resumes_from_saved_cursor(self):
        from delivery_gap_signals.sources import github_graphql

        since_iso = "2025-04-01T00:00:00+00:00"
        until_iso = "2025-04-15T00:00:00+00:00"

        page1 = {
            "data": {
                "repository": {
                    "pullRequests": {
                        "nodes": [{"number": 101, "mergedAt": "2025-04-10T00:00:00Z"}],
                        "pageInfo": {"hasNextPage": True, "endCursor": "cursor-1"},
                    }
                }
            }
        }
        page2 = {
            "data": {
                "repository": {
                    "pullRequests": {
                        "nodes": [{"number": 102, "mergedAt": "2025-04-08T00:00:00Z"}],
                        "pageInfo": {"hasNextPage": False, "endCursor": None},
                    }
                }
            }
        }

        def parse_pr(pr, repo, lookback_days, since=None, until=None):
            return _DummyChange(pr["number"], pr["mergedAt"].replace("Z", "+00:00"))

        with tempfile.TemporaryDirectory() as tmpdir:
            prs_path = Path(tmpdir) / "prs-owner-repo.json"

            with patch.object(github_graphql, "_skip_to_window_fast", return_value="skip-cursor"), \
                 patch.object(github_graphql, "_parse_pr_node", side_effect=parse_pr), \
                 patch.object(github_graphql, "_run_graphql", side_effect=[page1, RuntimeError("boom")]):
                with self.assertRaises(RuntimeError):
                    runner._fetch_gap_with_resume("owner/repo", str(prs_path), since_iso, until_iso)

            first_pass = json.loads(prs_path.read_text())
            self.assertEqual(len(first_pass), 1)
            self.assertEqual(first_pass[0]["pr_number"], 101)
            self.assertIsNone(load_fetch_status(prs_path))

            progress = load_progress_state(progress_state_path(prs_path.parent))
            active = get_active_gap_checkpoint(
                progress,
                repo="owner/repo",
                requested_since_iso=since_iso,
                requested_until_iso=until_iso,
            )
            self.assertIsNotNone(active)
            self.assertEqual(active["resume_after_cursor"], "cursor-1")
            self.assertEqual(active["saved_pr_count"], 1)

            seen_after_values = []

            def run_graphql_resume(query, variables):
                seen_after_values.append(variables.get("after"))
                return page2

            with patch.object(github_graphql, "_skip_to_window_fast", side_effect=AssertionError("should not skip again")), \
                 patch.object(github_graphql, "_parse_pr_node", side_effect=parse_pr), \
                 patch.object(github_graphql, "_run_graphql", side_effect=run_graphql_resume):
                runner._fetch_gap_with_resume("owner/repo", str(prs_path), since_iso, until_iso)

            second_pass = json.loads(prs_path.read_text())
            self.assertEqual({pr["pr_number"] for pr in second_pass}, {101, 102})
            self.assertEqual(seen_after_values, ["cursor-1"])

            status = load_fetch_status(prs_path)
            self.assertIsNotNone(status)
            self.assertTrue(status["completed"])

            progress = load_progress_state(progress_state_path(prs_path.parent))
            active = get_active_gap_checkpoint(
                progress,
                repo="owner/repo",
                requested_since_iso=since_iso,
                requested_until_iso=until_iso,
            )
            self.assertIsNotNone(active)
            self.assertIsNone(active["resume_after_cursor"])
            self.assertEqual(active["saved_pr_count"], 2)


if __name__ == "__main__":
    unittest.main()
