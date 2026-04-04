#!/usr/bin/env python3
"""Tests for fetch completeness/progress tracking."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fetch_progress import (
    clear_active_gap_checkpoint,
    get_active_gap_checkpoint,
    load_progress_state,
    mark_gap_complete,
    plan_gap_fetch,
    save_progress_state,
    update_active_gap_checkpoint,
)


def _write_prs(path: Path, *merged_at_values: datetime) -> None:
    path.write_text(json.dumps([
        {"pr_number": idx, "merged_at": value.isoformat()}
        for idx, value in enumerate(merged_at_values, start=1)
    ], indent=2))


class TestFetchProgress(unittest.TestCase):
    def test_partial_day_gap_requires_fetch_without_checkpoint(self):
        now = datetime(2026, 4, 3, 12, 0, tzinfo=timezone.utc)
        cutoff = now - timedelta(days=365)
        oldest = cutoff + timedelta(hours=6, minutes=30)

        with tempfile.TemporaryDirectory() as tmpdir:
            prs_path = Path(tmpdir) / "prs-owner-repo.json"
            _write_prs(prs_path, oldest)

            plan = plan_gap_fetch(
                repo="owner/repo",
                prs_path=prs_path,
                lookback_days=365,
                now=now,
                progress_state={"repos": {}},
            )

        self.assertIsNotNone(plan)
        self.assertEqual(plan.since_iso, cutoff.isoformat())
        self.assertEqual(plan.until_iso, oldest.isoformat())

    def test_completed_partial_day_gap_is_not_refetched(self):
        now = datetime(2026, 4, 3, 12, 0, tzinfo=timezone.utc)
        cutoff = now - timedelta(days=365)
        oldest = cutoff + timedelta(hours=6, minutes=30)

        with tempfile.TemporaryDirectory() as tmpdir:
            prs_path = Path(tmpdir) / "prs-owner-repo.json"
            _write_prs(prs_path, oldest)

            progress = {"repos": {}}
            mark_gap_complete(
                progress,
                repo="owner/repo",
                requested_since_iso=cutoff.isoformat(),
                requested_until_iso=oldest.isoformat(),
                observed_oldest_iso=oldest.isoformat(),
                completed_at_iso=now.isoformat(),
            )

            plan = plan_gap_fetch(
                repo="owner/repo",
                prs_path=prs_path,
                lookback_days=365,
                now=now,
                progress_state=progress,
            )

        self.assertIsNone(plan)

    def test_stale_checkpoint_does_not_hide_newer_oldest_boundary(self):
        now = datetime(2026, 4, 3, 12, 0, tzinfo=timezone.utc)
        cutoff = now - timedelta(days=365)
        checkpoint_oldest = cutoff + timedelta(hours=1)
        current_oldest = cutoff + timedelta(hours=18)

        with tempfile.TemporaryDirectory() as tmpdir:
            prs_path = Path(tmpdir) / "prs-owner-repo.json"
            _write_prs(prs_path, current_oldest)

            progress = {"repos": {}}
            mark_gap_complete(
                progress,
                repo="owner/repo",
                requested_since_iso=cutoff.isoformat(),
                requested_until_iso=checkpoint_oldest.isoformat(),
                observed_oldest_iso=checkpoint_oldest.isoformat(),
                completed_at_iso=now.isoformat(),
            )

            plan = plan_gap_fetch(
                repo="owner/repo",
                prs_path=prs_path,
                lookback_days=365,
                now=now,
                progress_state=progress,
            )

        self.assertIsNotNone(plan)
        self.assertEqual(plan.until_iso, current_oldest.isoformat())

    def test_progress_state_round_trips_exact_subday_timestamp(self):
        expected_since = "2025-04-03T12:34:56+00:00"
        expected_until = "2025-04-03T18:07:09+00:00"
        expected_completed = "2026-04-03T09:00:00+00:00"

        with tempfile.TemporaryDirectory() as tmpdir:
            progress_path = Path(tmpdir) / "fetch-progress.json"

            progress = {"repos": {}}
            mark_gap_complete(
                progress,
                repo="owner/repo",
                requested_since_iso=expected_since,
                requested_until_iso=expected_until,
                observed_oldest_iso=expected_until,
                completed_at_iso=expected_completed,
            )
            save_progress_state(progress_path, progress)

            loaded = load_progress_state(progress_path)

        self.assertEqual(loaded["repos"]["owner/repo"]["covered_since_iso"], expected_since)
        self.assertEqual(loaded["repos"]["owner/repo"]["covered_until_iso"], expected_until)
        self.assertEqual(loaded["repos"]["owner/repo"]["last_completed_at_iso"], expected_completed)

    def test_active_gap_checkpoint_round_trip(self):
        progress = {"repos": {}}
        update_active_gap_checkpoint(
            progress,
            repo="owner/repo",
            requested_since_iso="2025-04-03T12:00:00+00:00",
            requested_until_iso="2025-04-04T12:00:00+00:00",
            resume_after_cursor="abc123",
            saved_pr_count=17,
            updated_at_iso="2026-04-03T09:00:00+00:00",
        )

        active = get_active_gap_checkpoint(
            progress,
            repo="owner/repo",
            requested_since_iso="2025-04-03T12:00:00+00:00",
            requested_until_iso="2025-04-04T12:00:00+00:00",
        )

        self.assertIsNotNone(active)
        self.assertEqual(active["resume_after_cursor"], "abc123")
        self.assertEqual(active["saved_pr_count"], 17)

    def test_active_gap_checkpoint_ignored_for_different_window(self):
        progress = {"repos": {}}
        update_active_gap_checkpoint(
            progress,
            repo="owner/repo",
            requested_since_iso="2025-04-03T12:00:00+00:00",
            requested_until_iso="2025-04-04T12:00:00+00:00",
            resume_after_cursor="abc123",
            saved_pr_count=17,
            updated_at_iso="2026-04-03T09:00:00+00:00",
        )

        active = get_active_gap_checkpoint(
            progress,
            repo="owner/repo",
            requested_since_iso="2025-04-03T12:00:00+00:00",
            requested_until_iso="2025-04-05T12:00:00+00:00",
        )

        self.assertIsNone(active)

    def test_active_gap_checkpoint_reused_for_later_time_same_day(self):
        progress = {"repos": {}}
        update_active_gap_checkpoint(
            progress,
            repo="owner/repo",
            requested_since_iso="2025-04-03T07:08:31+00:00",
            requested_until_iso="2026-01-15T18:07:00+00:00",
            resume_after_cursor="abc123",
            saved_pr_count=155,
            updated_at_iso="2026-04-03T09:00:00+00:00",
        )

        active = get_active_gap_checkpoint(
            progress,
            repo="owner/repo",
            requested_since_iso="2025-04-03T07:44:24+00:00",
            requested_until_iso="2026-01-15T18:07:00+00:00",
        )

        self.assertIsNotNone(active)
        self.assertEqual(active["resume_after_cursor"], "abc123")

    def test_active_gap_checkpoint_not_reused_across_days(self):
        progress = {"repos": {}}
        update_active_gap_checkpoint(
            progress,
            repo="owner/repo",
            requested_since_iso="2025-04-02T23:59:59+00:00",
            requested_until_iso="2026-01-15T18:07:00+00:00",
            resume_after_cursor="abc123",
            saved_pr_count=155,
            updated_at_iso="2026-04-03T09:00:00+00:00",
        )

        active = get_active_gap_checkpoint(
            progress,
            repo="owner/repo",
            requested_since_iso="2025-04-03T00:00:01+00:00",
            requested_until_iso="2026-01-15T18:07:00+00:00",
        )

        self.assertIsNone(active)

    def test_mark_gap_complete_clears_active_checkpoint(self):
        now = "2026-04-03T09:00:00+00:00"
        since = "2025-04-03T12:00:00+00:00"
        until = "2025-04-04T12:00:00+00:00"

        progress = {"repos": {}}
        update_active_gap_checkpoint(
            progress,
            repo="owner/repo",
            requested_since_iso=since,
            requested_until_iso=until,
            resume_after_cursor="abc123",
            saved_pr_count=17,
            updated_at_iso=now,
        )

        mark_gap_complete(
            progress,
            repo="owner/repo",
            requested_since_iso=since,
            requested_until_iso=until,
            observed_oldest_iso=until,
            completed_at_iso=now,
        )

        self.assertIsNone(
            get_active_gap_checkpoint(
                progress,
                repo="owner/repo",
                requested_since_iso=since,
                requested_until_iso=until,
            )
        )

    def test_clear_active_gap_checkpoint(self):
        progress = {"repos": {}}
        update_active_gap_checkpoint(
            progress,
            repo="owner/repo",
            requested_since_iso="2025-04-03T12:00:00+00:00",
            requested_until_iso="2025-04-04T12:00:00+00:00",
            resume_after_cursor="abc123",
            saved_pr_count=17,
            updated_at_iso="2026-04-03T09:00:00+00:00",
        )

        clear_active_gap_checkpoint(
            progress,
            repo="owner/repo",
            requested_since_iso="2025-04-03T12:00:00+00:00",
            requested_until_iso="2025-04-04T12:00:00+00:00",
        )

        self.assertIsNone(
            get_active_gap_checkpoint(
                progress,
                repo="owner/repo",
                requested_since_iso="2025-04-03T12:00:00+00:00",
                requested_until_iso="2025-04-04T12:00:00+00:00",
            )
        )


if __name__ == "__main__":
    unittest.main()
