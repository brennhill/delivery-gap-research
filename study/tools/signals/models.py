"""Canonical data models for the delivery-gap ecosystem.

MergedChange is the universal unit that all tools operate on.
Source adapters produce list[MergedChange]. Tools consume it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .signals import extract_ticket_ids


class CIStatus(str, Enum):
    """Aggregate CI result for a change."""
    PASSED = "passed"
    FAILED = "failed"
    NO_CHECKS = "no_checks"


@dataclass(frozen=True)
class Review:
    """A single review on a change."""
    reviewer: str
    state: str          # "approved", "changes_requested", "commented"
    submitted_at: datetime
    is_bot: bool = False
    body: str = ""      # Review comment text (empty if not fetched)


@dataclass(frozen=True)
class Commit:
    """A single commit in a change."""
    message: str
    sha: str = ""
    authored_at: datetime | None = None


@dataclass(frozen=True)
class MergedChange:
    """A single merged change — the universal unit across all tools.

    Produced by source adapters (GitHub, GitLab, git, file).
    Consumed by changeledger, CatchRate, and Upfront.
    """

    # Identity
    id: str                             # Platform-specific: PR number, MR iid, commit SHA
    source: str                         # "github", "gitlab", "git", "file"
    repo: str                           # "owner/repo" or local path

    # Content
    title: str                          # PR title or commit subject
    body: str                           # PR body or commit body
    author: str                         # Username or email

    # Timestamps
    merged_at: datetime
    created_at: datetime | None = None  # When opened (None for git commits)

    # Files
    files: list[str] = field(default_factory=list)
    additions: int = 0
    deletions: int = 0

    # Ticket linkage (auto-extracted from title + body)
    ticket_ids: frozenset[str] = field(default_factory=frozenset)

    # Review data (None when unavailable — e.g., local git)
    reviews: list[Review] | None = None
    ci_status: CIStatus | None = None

    # Commit data
    commits: list[Commit] = field(default_factory=list)
    commit_count: int = 0

    # Engagement metadata
    last_edited_at: datetime | None = None   # PR body was edited after creation
    total_comments_count: int = 0            # PR + review comments

    # Platform-specific identifiers
    merge_commit_sha: str | None = None
    pr_number: int | None = None

    @classmethod
    def build(
        cls,
        *,
        id: str,
        source: str,
        repo: str,
        title: str,
        body: str,
        author: str,
        merged_at: datetime,
        created_at: datetime | None = None,
        files: list[str] | None = None,
        additions: int = 0,
        deletions: int = 0,
        reviews: list[Review] | None = None,
        ci_status: CIStatus | None = None,
        merge_commit_sha: str | None = None,
        pr_number: int | None = None,
        commits: list[Commit] | None = None,
        commit_count: int = 0,
        last_edited_at: datetime | None = None,
        total_comments_count: int = 0,
    ) -> MergedChange:
        """Validated constructor. Auto-extracts ticket IDs from title + body."""
        text = f"{title}\n{body}".strip()
        return cls(
            id=id,
            source=source,
            repo=repo,
            title=title,
            body=body,
            author=author,
            merged_at=merged_at,
            created_at=created_at,
            files=files or [],
            additions=additions,
            deletions=deletions,
            ticket_ids=frozenset(extract_ticket_ids(text)),
            reviews=reviews,
            ci_status=ci_status,
            merge_commit_sha=merge_commit_sha,
            pr_number=pr_number,
            commits=commits or [],
            commit_count=commit_count,
            last_edited_at=last_edited_at,
            total_comments_count=total_comments_count,
        )

    def to_dict(self) -> dict:
        """Serialize to JSON-compatible dict."""
        d = {
            "id": self.id,
            "source": self.source,
            "repo": self.repo,
            "title": self.title,
            "body": self.body,
            "author": self.author,
            "merged_at": self.merged_at.isoformat(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "files": self.files,
            "additions": self.additions,
            "deletions": self.deletions,
            "ticket_ids": sorted(self.ticket_ids),
            "merge_commit_sha": self.merge_commit_sha,
            "pr_number": self.pr_number,
            "ci_status": self.ci_status.value if self.ci_status else None,
            "reviews": [
                {
                    "reviewer": r.reviewer,
                    "state": r.state,
                    "submitted_at": r.submitted_at.isoformat(),
                    "is_bot": r.is_bot,
                    "body": r.body,
                }
                for r in (self.reviews or [])
            ],
            "commits": [
                {
                    "message": c.message,
                    "sha": c.sha,
                    "authored_at": c.authored_at.isoformat() if c.authored_at else None,
                }
                for c in (self.commits or [])
            ],
            "commit_count": self.commit_count,
            "last_edited_at": self.last_edited_at.isoformat() if self.last_edited_at else None,
            "total_comments_count": self.total_comments_count,
        }
        return d
