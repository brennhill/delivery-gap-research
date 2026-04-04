"""Rework signal detection — reverts and bug-fix follow-ups.

Compares rework rates for spec'd vs unspec'd changes.
Works with GitHub PRs (--repo) or local git commits (--git-dir).
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import TYPE_CHECKING

from tools.signals import is_fix_message, is_revert_message, extract_revert_pr_numbers

if TYPE_CHECKING:
    from tools.spec_signals.models import Commit, PullRequest, SpecClassification

# Bug-fix classification — require strong signals to avoid false positives
# Base prefix detection delegated to delivery_gap_signals.is_fix_message()
FIX_LABELS = {"bug", "fix", "hotfix", "bugfix"}

TRIVIAL_FIX_RE = re.compile(
    r"(?:^fix(?:\(.*?\))?:\s*|\bfix\s+)(?:typo|lint|format|formatting|whitespace|indent|style|import|spacing)\b",
    re.IGNORECASE,
)
# If the trivial word is followed by substantive context, it's a real bug (not trivial)
_TRIVIAL_OVERRIDE_RE = re.compile(
    r"(?:typo|import)\s+(?:in\s+)?(?:config|key|env|secret|credential|password|setting|variable|constant|flag)\b",
    re.IGNORECASE,
)
# Strong signals that are unambiguous bug-fix indicators even without a fix: prefix
FIX_KEYWORDS_STRONG_RE = re.compile(
    r"\b(?:broken|regression|crash|null\s*pointer)\b",
    re.IGNORECASE,
)

SHA_HEX_RE = re.compile(r"^[0-9a-f]+$", re.IGNORECASE)


@dataclass
class ReworkItem:
    """Typed schema for rework detection input. Replaces untyped dict."""

    id: str
    message: str
    date: datetime
    files: list[str]
    labels: list[str] | None
    revert_target: str | None


@dataclass
class PRMetadata:
    """Typed schema for friction/complexity input. Replaces untyped dict."""

    number: int
    specd: bool
    review_count: int
    created_at: datetime
    merged_at: datetime
    lines: int
    reworked: bool


@dataclass
class ReworkSignal:
    type: str  # "revert" or "bug-fix"
    source_id: str  # PR number (as str) or commit SHA
    target_id: str  # PR number (as str) or commit SHA
    classification: str  # "heuristic" or "llm"
    overlapping_files: list[str]


@dataclass
class FrictionMetrics:
    specd_median_review_cycles: float | None
    unspecd_median_review_cycles: float | None
    specd_median_hours_to_merge: float | None
    unspecd_median_hours_to_merge: float | None


@dataclass
class EffectivenessResult:
    specd_rework_rate: float
    unspecd_rework_rate: float
    delta: float
    specd_sample_size: int
    unspecd_sample_size: int
    specd_rework_count: int
    unspecd_rework_count: int
    significance: str  # "significant", "limited", "insufficient"
    signals: list[ReworkSignal] = field(default_factory=list)


# --- Shared classification helpers ---


def _is_bugfix_message(message: str, labels: list[str] | None = None) -> bool:
    """Classify a commit/PR message as a bug fix.

    Checks title first, then first paragraph of body for fix signals.
    Weak keywords (bug/error/exception) only match with a fix: prefix or label.
    """
    lines = message.split("\n")
    first_line = lines[0].lower().strip()

    # Check for conventional commit fix: prefix (shared package)
    if is_fix_message(first_line):
        if TRIVIAL_FIX_RE.search(first_line):
            # Override: if followed by substantive context (config key, env var), it's a real bug
            return bool(_TRIVIAL_OVERRIDE_RE.search(first_line))
        return True

    # Label-based detection
    if labels and {lbl.lower() for lbl in labels} & FIX_LABELS:
        return True

    # Strong keywords (unambiguous even without fix: prefix)
    if FIX_KEYWORDS_STRONG_RE.search(first_line):
        return True

    # Check body first paragraph for fix signals (E5: not just first line)
    body_first_para = ""
    in_body = False
    for line in lines[1:]:
        if not in_body and line.strip():
            in_body = True
        if in_body:
            if not line.strip():
                break
            body_first_para += " " + line.strip()

    if body_first_para:
        body_lower = body_first_para.lower()
        # Fix keywords in body count as fix context
        if any(body_lower.startswith(p) or f" {p}" in body_lower for p in ("fix", "fixes", "bugfix", "hotfix")):
            return True
        if FIX_KEYWORDS_STRONG_RE.search(body_lower):
            return True

    return False


def _resolve_revert_target(revert_target: str | None, items_by_id: dict[str, ReworkItem]) -> str | None:
    """Resolve a revert target, handling abbreviated SHAs with prefix matching."""
    if not revert_target:
        return None
    # Exact match first
    if revert_target in items_by_id:
        return revert_target
    # Prefix match for abbreviated SHAs (7+ hex chars)
    if len(revert_target) >= 7 and SHA_HEX_RE.match(revert_target):
        matches = [k for k in items_by_id if k.startswith(revert_target)]
        if len(matches) == 1:
            return matches[0]
    return None


def _detect_rework_generic(
    items: list[ReworkItem],
    rework_window_days: int = 14,
) -> list[ReworkSignal]:
    """Generic rework detection for both PRs and commits."""
    signals = []
    items_by_id: dict[str, ReworkItem] = {item.id: item for item in items}

    file_sets: dict[str, frozenset[str]] = {item.id: frozenset(item.files) for item in items}

    file_to_items: dict[str, list[tuple[str, datetime]]] = defaultdict(list)
    for item in items:
        for f in item.files:
            file_to_items[f].append((item.id, item.date))

    # Exclude high-frequency files (>30% of items) — they create spurious attributions
    n_items = len(items)
    high_freq_threshold = max(3, int(n_items * 0.3))
    high_freq_files = {f for f, entries in file_to_items.items() if len(entries) > high_freq_threshold}

    sorted_items = sorted(items, key=lambda i: i.date)

    for item in sorted_items:
        item_id = item.id

        # Check for reverts (with prefix matching for abbreviated SHAs)
        resolved_target = _resolve_revert_target(item.revert_target, items_by_id)
        if resolved_target and resolved_target != item_id:
            overlap = sorted(file_sets[item_id] & file_sets.get(resolved_target, frozenset()))
            signals.append(
                ReworkSignal(
                    type="revert",
                    source_id=item_id,
                    target_id=resolved_target,
                    classification="heuristic",
                    overlapping_files=overlap,
                )
            )
            continue

        # Check for bug-fix follow-ups
        if not _is_bugfix_message(item.message, item.labels):
            continue

        candidate_scores: dict[str, int] = defaultdict(int)
        window_cutoff = item.date - timedelta(days=rework_window_days)

        for f in item.files:
            if f in high_freq_files:
                continue  # skip noisy files (lockfiles, configs)
            for cand_id, cand_date in file_to_items.get(f, []):
                if cand_id == item_id:
                    continue
                if cand_date >= item.date:
                    continue
                if cand_date < window_cutoff:
                    continue
                candidate_scores[cand_id] += 1

        if not candidate_scores:
            continue

        # Numeric sort for PR numbers ("9" < "100" in string sort but 9 < 100 numerically)
        best_id = max(
            candidate_scores,
            key=lambda cid, _scores=candidate_scores, _items=items_by_id: (  # type: ignore[misc]
                _scores[cid],
                _items[cid].date,
                int(cid) if cid.isdigit() else 0,
                cid,
            ),
        )
        overlap = sorted((file_sets[item_id] & file_sets.get(best_id, frozenset())) - high_freq_files)
        if overlap:
            signals.append(
                ReworkSignal(
                    type="bug-fix",
                    source_id=item_id,
                    target_id=best_id,
                    classification="heuristic",
                    overlapping_files=overlap,
                )
            )

    return signals


# --- GitHub PR mode ---


def detect_rework_prs(
    prs: list[PullRequest],
    rework_window_days: int = 14,
) -> list[ReworkSignal]:
    """Detect rework signals from GitHub PR data."""
    items: list[ReworkItem] = []
    for pr in prs:
        if pr.merged_at is None:
            continue
        # Check if this is a revert (shared package for pattern matching)
        revert_target = None
        title = pr.title or ""
        if is_revert_message(title):
            # Only use explicit "Reverts #N" pattern — do NOT grab arbitrary #N from body
            body = pr.body or ""
            pr_nums = extract_revert_pr_numbers(body)
            if pr_nums:
                revert_target = str(min(pr_nums))
            else:
                # Check title for Revert #N pattern only
                title_pr_nums = extract_revert_pr_numbers(title)
                if title_pr_nums:
                    revert_target = str(min(title_pr_nums))

        items.append(
            ReworkItem(
                id=str(pr.number),
                message=f"{pr.title}\n{pr.body or ''}",
                date=pr.merged_at,
                files=pr.files,
                labels=pr.labels,
                revert_target=revert_target,
            )
        )

    return _detect_rework_generic(items, rework_window_days)


# --- Git commit mode ---


def detect_rework_commits(
    commits: list[Commit],
    rework_window_days: int = 14,
) -> list[ReworkSignal]:
    """Detect rework signals from git commit data."""
    from tools.signals import is_revert_message, extract_fixes_sha

    def is_revert_commit(commit: Commit) -> str | None:
        if not is_revert_message(commit.message):
            return None
        sha = extract_fixes_sha(commit.message)
        if sha:
            return sha
        for line in commit.message.splitlines():
            stripped = line.strip().lower()
            if stripped.startswith("this reverts commit "):
                sha = stripped.removeprefix("this reverts commit ").rstrip(".").strip()
                if len(sha) >= 7:
                    return sha
        return None

    items: list[ReworkItem] = []
    for commit in commits:
        if commit.date is None:
            continue
        revert_target = is_revert_commit(commit)

        items.append(
            ReworkItem(
                id=commit.sha,
                message=commit.message,
                date=commit.date,
                files=commit.files,
                labels=None,
                revert_target=revert_target,
            )
        )

    return _detect_rework_generic(items, rework_window_days)


# --- Pre-merge friction metrics (GitHub-only) ---


def _median(values: list[float]) -> float | None:
    """Compute median. Returns None for empty list."""
    if not values:
        return None
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    if n % 2 == 1:
        return sorted_vals[n // 2]
    return (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2


def compute_friction(prs: list[PRMetadata]) -> FrictionMetrics:
    """Compute pre-merge friction: review cycles and time-to-merge."""
    specd_reviews: list[float] = []
    unspecd_reviews: list[float] = []
    specd_hours: list[float] = []
    unspecd_hours: list[float] = []

    for pr in prs:
        hours = max(0, (pr.merged_at - pr.created_at).total_seconds() / 3600)
        if pr.specd:
            specd_reviews.append(float(pr.review_count))
            specd_hours.append(hours)
        else:
            unspecd_reviews.append(float(pr.review_count))
            unspecd_hours.append(hours)

    return FrictionMetrics(
        specd_median_review_cycles=_median(specd_reviews),
        unspecd_median_review_cycles=_median(unspecd_reviews),
        specd_median_hours_to_merge=_median(specd_hours),
        unspecd_median_hours_to_merge=_median(unspecd_hours),
    )


# --- Complexity bucketing ---


@dataclass
class ComplexityBucket:
    """Typed result for a single complexity bucket."""

    specd_rework_rate: float
    unspecd_rework_rate: float
    specd_count: int
    unspecd_count: int
    friction: FrictionMetrics


COMPLEXITY_BUCKETS = {
    "small": (0, 100),
    "medium": (100, 500),
    "large": (500, float("inf")),
}
MIN_BUCKET_SIZE = 5


def compute_complexity_buckets(prs: list[PRMetadata]) -> dict[str, ComplexityBucket]:
    """Bucket PRs by lines changed and compute per-bucket rework/friction.

    Buckets with < MIN_BUCKET_SIZE in either group are omitted.
    """
    results: dict[str, ComplexityBucket] = {}

    for bucket_name, (lo, hi) in COMPLEXITY_BUCKETS.items():
        in_bucket = [pr for pr in prs if lo <= pr.lines < hi]
        specd = [pr for pr in in_bucket if pr.specd]
        unspecd = [pr for pr in in_bucket if not pr.specd]

        if len(specd) < MIN_BUCKET_SIZE or len(unspecd) < MIN_BUCKET_SIZE:
            continue

        specd_rework = sum(1 for pr in specd if pr.reworked)
        unspecd_rework = sum(1 for pr in unspecd if pr.reworked)

        results[bucket_name] = ComplexityBucket(
            specd_rework_rate=round(specd_rework / len(specd), 4),
            unspecd_rework_rate=round(unspecd_rework / len(unspecd), 4),
            specd_count=len(specd),
            unspecd_count=len(unspecd),
            friction=compute_friction(in_bucket),
        )

    return results


# --- Compute effectiveness (works for both modes) ---


def compute_effectiveness(
    classifications: list[SpecClassification],
    signals: list[ReworkSignal],
) -> EffectivenessResult:
    """Compute effectiveness by comparing rework rates.

    Uses SpecClassification.change_id as the join key (PR number or commit SHA).
    """
    specd_ids: set[str] = set()
    unspecd_ids: set[str] = set()

    for c in classifications:
        if c.specd:
            specd_ids.add(c.change_id)
        else:
            unspecd_ids.add(c.change_id)

    # Count unique targets to prevent double-counting (two bug-fixes targeting the same PR = 1 rework)
    specd_rework_targets: set[str] = set()
    unspecd_rework_targets: set[str] = set()

    for signal in signals:
        target = signal.target_id
        if target in specd_ids:
            specd_rework_targets.add(target)
        elif target in unspecd_ids:
            unspecd_rework_targets.add(target)

    specd_rework = len(specd_rework_targets)
    unspecd_rework = len(unspecd_rework_targets)

    specd_count = len(specd_ids)
    unspecd_count = len(unspecd_ids)

    specd_rate = specd_rework / specd_count if specd_count > 0 else 0.0
    unspecd_rate = unspecd_rework / unspecd_count if unspecd_count > 0 else 0.0
    delta = specd_rate - unspecd_rate

    min_group = min(specd_count, unspecd_count) if specd_count and unspecd_count else 0
    if min_group >= 30:
        significance = "significant"
    elif min_group >= 10:
        significance = "limited"
    else:
        significance = "insufficient"

    return EffectivenessResult(
        specd_rework_rate=round(specd_rate, 4),
        unspecd_rework_rate=round(unspecd_rate, 4),
        delta=round(delta, 4),
        specd_sample_size=specd_count,
        unspecd_sample_size=unspecd_count,
        specd_rework_count=specd_rework,
        unspecd_rework_count=unspecd_rework,
        significance=significance,
        signals=signals,
    )
