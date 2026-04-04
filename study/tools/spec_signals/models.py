"""Shared data types — decouples modules that only need the type, not the logic.

Modules import types from here instead of from the module that computes them.
This breaks the coupling chain that creates the god cluster.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime  # noqa: TC003 — needed at runtime for dataclass fields


@dataclass
class Commit:
    """A git commit with metadata and changed files."""

    sha: str
    message: str  # full message (subject + body)
    author: str
    date: datetime
    files: list[str]


@dataclass
class PullRequest:
    """A GitHub pull request with metadata."""

    number: int
    title: str
    body: str
    author: str
    labels: list[str]
    merged_at: datetime
    files: list[str] = field(default_factory=list)
    created_at: datetime | None = None
    review_count: int = 0
    additions: int = 0
    deletions: int = 0


@dataclass
class SpecClassification:
    """A PR or commit classified as spec'd or unspec'd."""

    pr_number: int | None  # None for commit-based mode
    commit_sha: str | None  # None for PR-based mode
    title: str
    specd: bool
    spec_source: str | None  # ticket ID, URL, template section, or None
    spec_content: str  # the text to score (PR body or commit message)
    merged_at: str  # ISO format

    @property
    def change_id(self) -> str:
        """Stable ID for joining with rework signals."""
        if self.pr_number is not None:
            return str(self.pr_number)
        if self.commit_sha is not None:
            return self.commit_sha
        raise ValueError("SpecClassification has neither pr_number nor commit_sha")

    @property
    def display_id(self) -> str:
        """Human-readable identifier. Uses `is not None` consistently with change_id."""
        if self.pr_number is not None:
            return f"#{self.pr_number}"
        if self.commit_sha is not None:
            return self.commit_sha[:8]
        return "—"
