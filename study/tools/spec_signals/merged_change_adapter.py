"""Adapter: convert delivery_gap_signals.MergedChange → upfront.PullRequest.

Used when --from-prs provides pre-fetched data instead of live GitHub API calls.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from tools.spec_signals.models import PullRequest

if TYPE_CHECKING:
    from tools.signals.models import MergedChange


def merged_change_to_pr(change: MergedChange) -> PullRequest:
    """Convert a single MergedChange to Upfront's PullRequest model."""
    return PullRequest(
        number=change.pr_number if change.pr_number is not None else int(change.id) if change.id.isdigit() else 0,
        title=change.title,
        body=change.body,
        author=change.author,
        labels=[],
        merged_at=change.merged_at,
        files=list(change.files),
        created_at=change.created_at,
        review_count=len(change.reviews) if change.reviews else 0,
        additions=change.additions,
        deletions=change.deletions,
    )


def convert_merged_changes(changes: list[MergedChange]) -> list[PullRequest]:
    """Convert a list of MergedChange objects to Upfront PullRequest objects."""
    return [merged_change_to_pr(c) for c in changes]
