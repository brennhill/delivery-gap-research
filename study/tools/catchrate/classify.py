"""Classify each PR: machine_catch, human_save, escape, pending, ungated."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timezone
from typing import NamedTuple

from tools.catchrate.bots import build_llm_reviewer_set, is_bot_author, is_bot_reviewer
from tools.catchrate.dateutil import is_within_window, parse_iso_datetime
from tools.catchrate.log import warn
from tools.catchrate.models import (
    CIStatus,
    Classification,
    ClassificationType,
)
from tools.catchrate.models import (
    PRDataLike as PRData,
)
from tools.catchrate.signals import classify_ci, compute_size_bucket, compute_ttm

# Type alias for LLM reviewer sets (frozenset from build_llm_reviewer_set)
LLMReviewers = set[str] | frozenset[str] | None

# ---------------------------------------------------------------------------
# Shared timeline builder
# ---------------------------------------------------------------------------


class PREvent(NamedTuple):
    """A single event in a PR's timeline."""

    kind: str  # "review" or "commit"
    state: str  # review state ("APPROVED", "CHANGES_REQUESTED") or "" for commits
    timestamp: datetime
    reviewer: str  # reviewer login (lowercase) for reviews, "" for commits


def _build_timeline(pr: PRData, llm_reviewers: LLMReviewers = None) -> list[PREvent]:
    """Build a sorted timeline of review and commit events.

    Filters out: bot reviews, self-reviews, merge commits.
    Uses author date with committer date fallback for commits.
    Returns events sorted chronologically.
    """
    events: list[PREvent] = []

    for review in pr.reviews:
        if is_bot_reviewer(review, llm_reviewers):
            continue
        reviewer_login = (review.get("user", {}) or {}).get("login", "")
        if reviewer_login.lower() == pr.author.lower():
            continue
        submitted = review.get("submitted_at", "")
        ts = parse_iso_datetime(submitted, context=f"PR #{pr.number} review submitted_at")
        if ts:
            state = review.get("state", "")
            events.append(PREvent("review", state, ts, reviewer_login.lower()))

    for commit in pr.commits:
        commit_data = commit.get("commit", {})
        message = commit_data.get("message", "")
        if message.startswith("Merge "):
            continue
        author_info = commit_data.get("author", {}) or {}
        date_str = author_info.get("date", "")
        if not date_str:
            committer_info = commit_data.get("committer", {}) or {}
            date_str = committer_info.get("date", "")
        ts = parse_iso_datetime(date_str, context=f"PR #{pr.number} commit date")
        if ts:
            events.append(PREvent("commit", "", ts, ""))

    events.sort(key=lambda e: e.timestamp)
    return events


# ---------------------------------------------------------------------------
# Review classification
# ---------------------------------------------------------------------------


def _had_human_changes_requested(timeline: list[PREvent]) -> bool:
    """Check if any human reviewer requested changes."""
    return any(e.kind == "review" and e.state == "CHANGES_REQUESTED" for e in timeline)


def _had_comment_based_review(timeline: list[PREvent]) -> bool:
    """Detect human review via COMMENTED reviews followed by new commits.

    Repos using Prow/Bors workflows (e.g. kubernetes) use inline comments
    and label-based approvals (/lgtm, /approve) instead of GitHub's formal
    CHANGES_REQUESTED state.  A human COMMENTED review followed by a new
    commit from the author is functionally equivalent to CHANGES_REQUESTED
    + fix — the reviewer asked for changes via comments and the author
    responded.

    Returns True if any human COMMENTED review is followed chronologically
    by a commit (i.e. the author pushed code in response to the comment).
    """
    for i, event in enumerate(timeline):
        if event.kind == "review" and event.state == "COMMENTED":
            # Check if any commit follows this comment in the timeline
            for later in timeline[i + 1 :]:
                if later.kind == "commit":
                    return True
    return False


def _had_post_approval_commits(timeline: list[PREvent]) -> bool:
    """Check if there were non-merge commits after human approval."""
    last_approval_time = None
    for e in timeline:
        is_approval = e.kind == "review" and e.state == "APPROVED"
        if is_approval and (last_approval_time is None or e.timestamp > last_approval_time):
            last_approval_time = e.timestamp

    if last_approval_time is None:
        return False

    return any(e.kind == "commit" and e.timestamp > last_approval_time for e in timeline)


def _count_review_cycles(timeline: list[PREvent]) -> int:
    """Count human review round-trips.

    A cycle is detected via two patterns:

    1. **Review→commit** (existing): one or more human CHANGES_REQUESTED or
       COMMENTED reviews, followed by the author pushing new commits. Multiple
       reviews before any new commit count as 1 cycle (same feedback round).
       Both CHANGES_REQUESTED and COMMENTED states are counted because repos
       using Prow/Bors workflows (e.g. kubernetes) provide feedback exclusively
       via COMMENTED reviews.

    2. **Comment→approve** (cockroachdb pattern): a reviewer submits COMMENTED,
       then later APPROVED, and there are commits between those two events in
       the timeline.  This catches repos where reviewers rarely use
       CHANGES_REQUESTED — they comment with feedback and approve once it's
       addressed.  Only counted for the SAME reviewer to avoid false positives.

    The two patterns may overlap (a COMMENTED→commit→APPROVED sequence fires
    both), so the final count is the maximum of the two to avoid double-counting.
    """
    # Pattern 1: review → commit round-trips
    commit_cycles = 0
    in_review_round = False
    for e in timeline:
        if (
            e.kind == "review"
            and e.state in ("CHANGES_REQUESTED", "COMMENTED")
            and not in_review_round
        ):
            in_review_round = True
        elif e.kind == "commit" and in_review_round:
            commit_cycles += 1
            in_review_round = False

    # Pattern 2: comment → approve (same reviewer, with commits between)
    # Track pending COMMENTED reviews per reviewer, count a cycle when the
    # same reviewer later submits APPROVED and commits appeared in between.
    approve_cycles = 0
    # Map reviewer -> True if they have a pending COMMENTED with commits after it
    pending_comment: dict[str, bool] = {}  # reviewer -> has_commits_after
    for e in timeline:
        if e.kind == "review" and e.state == "COMMENTED" and e.reviewer:
            if e.reviewer not in pending_comment:
                pending_comment[e.reviewer] = False
        elif e.kind == "commit":
            # Mark all pending commenters as having commits after their comment
            for reviewer in pending_comment:
                pending_comment[reviewer] = True
        elif e.kind == "review" and e.state == "APPROVED" and e.reviewer:
            if pending_comment.get(e.reviewer):
                approve_cycles += 1
            # Reset: this reviewer's comment→approve round is complete
            pending_comment.pop(e.reviewer, None)

    return max(commit_cycles, approve_cycles)


# ---------------------------------------------------------------------------
# Main classification
# ---------------------------------------------------------------------------


def classify_pr(
    pr: PRData,
    window_days: int = 14,
    llm_reviewers: LLMReviewers = None,
    now: datetime | None = None,
) -> Classification:
    """Classify a single PR. Escape detection is done separately in rework module."""
    if now is None:
        now = datetime.now(timezone.utc)

    ci_status = classify_ci(pr)
    bot = is_bot_author(pr)
    commit_shas = [c.get("sha", "") for c in pr.commits if c.get("sha")]
    timeline = _build_timeline(pr, llm_reviewers)
    review_cycles = _count_review_cycles(timeline)
    ttm = compute_ttm(pr)
    lines_changed = pr.additions + pr.deletions
    size_bucket = compute_size_bucket(lines_changed)

    merged_at = pr.merged_at

    def _build(cls_type: ClassificationType, review_mod: bool) -> Classification:
        """Build Classification with shared fields — single definition."""
        return Classification(
            number=pr.number,
            title=pr.title,
            classification=cls_type,
            ci_status=ci_status,
            review_modified=review_mod,
            escaped=False,
            escape_reason="",
            merged_at=merged_at,
            author=pr.author,
            files=pr.files,
            body=pr.body,
            is_bot=bot,
            commits=commit_shas,
            review_cycles=review_cycles,
            time_to_merge_hours=ttm,
            lines_changed=lines_changed,
            size_bucket=size_bucket,
        )

    # Check if PR is still in observation window (pending)
    if not merged_at and pr.merged:
        warn(f"PR #{pr.number}: merged=True but merged_at is None — skipping pending check.")
    if merged_at:
        merge_time = parse_iso_datetime(merged_at, context=f"PR #{pr.number} merged_at")
        if merge_time is not None and is_within_window(merge_time, now, window_days):
            return _build(ClassificationType.PENDING, False)

    # Ungated — no CI checks
    if ci_status == CIStatus.NO_CHECKS:
        return _build(ClassificationType.UNGATED, False)

    # Human save: human requested changes, comment-based review with follow-up commits,
    # or post-approval commits
    review_modified = (
        _had_human_changes_requested(timeline)
        or _had_comment_based_review(timeline)
        or _had_post_approval_commits(timeline)
    )

    cls_type = (
        ClassificationType.HUMAN_SAVE if review_modified else ClassificationType.MACHINE_CATCH
    )
    return _build(cls_type, review_modified)


def classify_all(
    prs: Sequence[PRData],
    window_days: int = 14,
    llm_reviewers: set[str] | None = None,
    include_bots: bool = False,
    include_deps: bool = False,
    now: datetime | None = None,
) -> list[Classification]:
    """Classify all PRs. Bot and dependency PRs excluded unless opted in."""
    from tools.signals import is_dependency_change

    # Pre-compute the combined LLM reviewer set once for the entire run
    combined_llm = build_llm_reviewer_set(llm_reviewers)
    results: list[Classification] = []
    for pr in prs:
        c = classify_pr(pr, window_days=window_days, llm_reviewers=combined_llm, now=now)
        if c.is_bot and not include_bots:
            continue
        if not include_deps and is_dependency_change(pr.title, pr.author, pr.files):
            continue
        results.append(c)
    return results
