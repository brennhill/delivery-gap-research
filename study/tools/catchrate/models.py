"""Data types and enums for CATCHRATE."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Protocol, TypedDict, runtime_checkable

if TYPE_CHECKING:
    from tools.catchrate.aggregate import Effectiveness, Rates
    from tools.catchrate.discard import DiscardResult

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ClassificationType(str, Enum):
    MACHINE_CATCH = "machine_catch"
    HUMAN_SAVE = "human_save"
    ESCAPE = "escape"
    PENDING = "pending"
    UNGATED = "ungated"


class CIStatus(str, Enum):
    CLEAN_PASS = "clean_pass"  # noqa: S105  # nosec B105
    CAUGHT_AND_FIXED = "caught_and_fixed"
    NO_CHECKS = "no_checks"
    FAILED = "failed"


# ---------------------------------------------------------------------------
# GitHub API response shapes (for type checking)
# ---------------------------------------------------------------------------


class UserDict(TypedDict, total=False):
    login: str
    type: str  # "User" or "Bot"
    __typename: str  # GraphQL typename


class ReviewDict(TypedDict, total=False):
    state: str  # "APPROVED", "CHANGES_REQUESTED", etc.
    submitted_at: str
    user: UserDict


class CommitInfoDict(TypedDict, total=False):
    date: str


class CommitDataDict(TypedDict, total=False):
    message: str
    author: CommitInfoDict
    committer: CommitInfoDict


class CommitDict(TypedDict, total=False):
    sha: str
    commit: CommitDataDict


class CheckRunDict(TypedDict, total=False):
    name: str
    conclusion: str


# ---------------------------------------------------------------------------
# PR data protocol — the contract that classification depends on
# ---------------------------------------------------------------------------


@runtime_checkable
class PRDataLike(Protocol):
    """Minimum interface for PR data consumed by classification.

    Any data source (GitHub, GitLab, local git) can satisfy this
    protocol without importing or subclassing PRData.
    """

    number: int
    title: str
    body: str
    merged: bool
    merged_at: str | None
    created_at: str
    author: str
    author_type: str
    is_draft: bool
    reviews: list[ReviewDict]
    check_runs: list[CheckRunDict]
    commits: list[CommitDict]
    files: list[str]
    additions: int
    deletions: int


# ---------------------------------------------------------------------------
# Classification result
# ---------------------------------------------------------------------------


class EscapeConfidence(str, Enum):
    """Confidence tier for rework/escape detection.

    Tier 1 (CONFIRMED): Reverts — unambiguous, 100% precision.
    Tier 2 (HIGH): Explicit PR reference in fix title/body.
    Tier 3 (MEDIUM): Same author + same component + close in time.
    Tier 4 (LOW): File overlap only — ~37% precision, flag for review.
    """

    CONFIRMED = "confirmed"  # Revert — 100% precision
    HIGH = "high"  # Explicit PR reference
    MEDIUM = "medium"  # Same author + component + timing
    LOW = "low"  # File overlap only


@dataclass
class Classification:
    number: int
    title: str
    classification: ClassificationType
    ci_status: CIStatus
    review_modified: bool
    escaped: bool
    escape_reason: str  # e.g. "reverted by #142", "fix: #136 (file overlap)"
    escape_confidence: EscapeConfidence | None = None  # None if not escaped
    merged_at: str | None = None
    author: str = ""
    files: list[str] = field(default_factory=list)
    body: str = ""
    is_bot: bool = False
    commits: list[str] = field(default_factory=list)
    review_cycles: int = 0
    time_to_merge_hours: float | None = None
    lines_changed: int = 0
    size_bucket: str = "small"


# ---------------------------------------------------------------------------
# Analysis configuration and result container
# ---------------------------------------------------------------------------


@dataclass
class AnalysisConfig:
    """Configuration for the analysis pipeline. Threaded through all phases."""

    window_days: int = 14
    llm_reviewers: set[str] | None = None
    include_bots: bool = False
    include_deps: bool = False
    ignore_files: list[str] | None = None
    ticket_pattern: str | None = None
    verbose: bool = False
    no_discard: bool = False


@dataclass
class CatchrateResult:
    """Bundles the full output context — used directly by all renderers."""

    repo: str
    lookback_days: int
    window_days: int
    rates: Rates
    classifications: list[Classification]
    effectiveness: Effectiveness
    discard: DiscardResult | None = None
    trend: dict[str, Any] | None = None
    partial: bool = False
    no_discard: bool = False
