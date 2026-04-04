"""Convert delivery_gap_signals.MergedChange to CatchRate's PRData."""

from __future__ import annotations

from typing import TYPE_CHECKING

from tools.catchrate.github import PRData

if TYPE_CHECKING:
    from tools.signals.models import CIStatus as DGSCIStatus
    from tools.signals.models import MergedChange


def _ci_status_to_check_runs(ci_status: DGSCIStatus | None) -> list[dict]:
    """Map a DGS CIStatus enum to synthetic check_runs dicts.

    CatchRate's classify_ci reads check_runs[].conclusion to determine
    CIStatus. We produce minimal check_run dicts that round-trip
    correctly through classify_ci.
    """
    if ci_status is None:
        return []

    conclusion_map = {
        "passed": "success",
        "failed": "failure",
        "no_checks": None,
    }
    conclusion = conclusion_map.get(ci_status.value)
    if conclusion is None:
        return []  # no_checks → empty list → CIStatus.NO_CHECKS

    return [{"name": "ci", "conclusion": conclusion}]


def _reviews_to_dicts(change: MergedChange) -> list[dict]:
    """Convert DGS Review objects to CatchRate's ReviewDict shape."""
    if change.reviews is None:
        return []

    result = []
    for r in change.reviews:
        result.append(
            {
                "state": r.state.upper(),  # DGS uses lowercase; CatchRate expects uppercase
                "submitted_at": r.submitted_at.isoformat(),
                "user": {
                    "login": r.reviewer,
                    "type": "Bot" if r.is_bot else "User",
                },
            }
        )
    return result


def merged_change_to_prdata(change: MergedChange) -> PRData:
    """Convert a single MergedChange to a CatchRate PRData instance."""
    # Build commits list: include merge_commit_sha so revert detection works
    commits: list[dict] = []
    if change.merge_commit_sha:
        commits.append(
            {
                "sha": change.merge_commit_sha,
                "commit": {
                    "message": "",
                    "author": {"date": change.merged_at.isoformat()},
                    "committer": {"date": change.merged_at.isoformat()},
                },
            }
        )

    return PRData(
        number=change.pr_number
        if change.pr_number
        else (int(change.id) if change.id.isdigit() else 0),
        title=change.title,
        body=change.body,
        state="closed",
        merged=True,
        merged_at=change.merged_at.isoformat(),
        created_at=change.created_at.isoformat()
        if change.created_at
        else change.merged_at.isoformat(),
        closed_at=change.merged_at.isoformat(),
        author=change.author,
        author_type="User",
        is_draft=False,
        reviews=_reviews_to_dicts(change),  # type: ignore[arg-type]
        check_runs=_ci_status_to_check_runs(change.ci_status),  # type: ignore[arg-type]
        commits=commits,  # type: ignore[arg-type]
        files=change.files,
        head_sha=change.merge_commit_sha or "",
        additions=change.additions,
        deletions=change.deletions,
    )


def merged_changes_to_prdata(changes: list[MergedChange]) -> list[PRData]:
    """Convert a list of MergedChange to CatchRate PRData list."""
    return [merged_change_to_prdata(c) for c in changes]
