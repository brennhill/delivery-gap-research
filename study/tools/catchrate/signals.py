"""CI status detection and PR metrics for CATCHRATE.

Extracted from classify.py to separate signal detection from classification
orchestration. Each function is a pure computation over PR data.
"""

from __future__ import annotations

from tools.catchrate.dateutil import parse_iso_datetime
from tools.catchrate.log import warn
from tools.catchrate.models import CIStatus
from tools.catchrate.models import PRDataLike as PRData


def classify_ci(pr: PRData) -> CIStatus:
    """Classify the CI status of a PR.

    Returns one of: clean_pass, caught_and_fixed, no_checks, failed.
    """
    check_runs = pr.check_runs
    if not check_runs:
        return CIStatus.NO_CHECKS

    conclusions = [cr.get("conclusion") for cr in check_runs if cr.get("conclusion")]

    if not conclusions:
        return CIStatus.NO_CHECKS

    all_passed = all(c in ("success", "neutral", "skipped") for c in conclusions)
    fail_conclusions = ("failure", "cancelled")
    any_failed = any(c in fail_conclusions for c in conclusions)

    if all_passed:
        return CIStatus.CLEAN_PASS
    elif any_failed:
        any_passed = any(c in ("success", "neutral", "skipped") for c in conclusions)
        if any_passed:
            return CIStatus.CAUGHT_AND_FIXED
        return CIStatus.FAILED
    else:
        return CIStatus.FAILED


def compute_ttm(pr: PRData) -> float | None:
    """Compute time-to-merge in hours (merged_at - created_at)."""
    if not pr.merged_at or not pr.created_at:
        return None
    merged = parse_iso_datetime(pr.merged_at, context=f"PR #{pr.number} merged_at")
    created = parse_iso_datetime(pr.created_at, context=f"PR #{pr.number} created_at")
    if merged is None or created is None:
        return None
    delta = merged - created
    hours = delta.total_seconds() / 3600.0
    if hours < 0:
        warn(f"PR #{pr.number}: negative TTM (merged_at before created_at).")
        return None
    return hours


def compute_size_bucket(lines_changed: int) -> str:
    """Bucket PR by lines changed: small (<100), medium (100-499), large (>=500)."""
    if lines_changed >= 500:
        return "large"
    if lines_changed >= 100:
        return "medium"
    return "small"
