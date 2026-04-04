"""Compute discard rate from closed-without-merge PRs."""

from __future__ import annotations

from dataclasses import dataclass

from tools.catchrate.bots import is_bot

# ---------------------------------------------------------------------------
# Data containers
# ---------------------------------------------------------------------------


@dataclass
class DiscardResult:
    discard_rate: float
    discarded_prs: int
    total_opened_prs: int
    discarded_pr_numbers: list[int]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compute_discard_rate(
    closed_unmerged_prs: list[dict],
    merged_pr_count: int,
    include_bots: bool = False,
) -> DiscardResult:
    """Compute the discard rate.

    Args:
        closed_unmerged_prs: PRs that were closed without merging.
        merged_pr_count: Total number of merged PRs in the period.
        include_bots: If False, exclude bot-authored/closed PRs from discards.

    Returns:
        DiscardResult with the computed rate.
    """
    discarded: list[int] = []

    for pr in closed_unmerged_prs:
        # Skip if it was reopened and merged (pull_request.merged_at is set)
        pull_request = pr.get("pull_request", {}) or {}
        if pull_request.get("merged_at"):
            continue

        # Skip bots unless included
        user = pr.get("user", {}) or {}
        if not include_bots and is_bot((user.get("login", "") or ""), user.get("type")):
            continue

        number = pr.get("number", 0)
        if number:
            discarded.append(number)

    total_opened = merged_pr_count + len(discarded)

    rate = 0.0 if total_opened == 0 else len(discarded) / total_opened

    return DiscardResult(
        discard_rate=rate,
        discarded_prs=len(discarded),
        total_opened_prs=total_opened,
        discarded_pr_numbers=discarded,
    )
