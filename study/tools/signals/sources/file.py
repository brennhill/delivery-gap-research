"""File source adapter — reads cached MergedChange data from JSON."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from tools.signals.models import CIStatus, MergedChange, Review
from tools.signals.signals import extract_ticket_ids


def fetch_changes(path: str, **kwargs) -> list[MergedChange]:
    """Read cached MergedChange data from JSON file (--from-prs).

    Accepts the JSON produced by MergedChange.to_dict() or by the
    GitHub adapter's raw output.
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"Expected JSON array in {path}, got {type(data).__name__}")

    changes: list[MergedChange] = []
    for item in data:
        reviews = None
        if item.get("reviews") is not None:
            reviews = [
                Review(
                    reviewer=r.get("reviewer", ""),
                    state=r.get("state", "commented"),
                    submitted_at=datetime.fromisoformat(r["submitted_at"]),
                    is_bot=r.get("is_bot", False),
                )
                for r in item["reviews"]
                if r.get("submitted_at")
            ]

        ci_status = None
        if item.get("ci_status"):
            ci_status = CIStatus(item["ci_status"])

        merged_at = item.get("merged_at") or item.get("mergedAt", "")
        created_at = item.get("created_at") or item.get("createdAt")

        changes.append(MergedChange(
            id=str(item.get("id", item.get("number", ""))),
            source=item.get("source", "file"),
            repo=item.get("repo", ""),
            title=item.get("title", ""),
            body=item.get("body", "") or "",
            author=item.get("author", ""),
            merged_at=datetime.fromisoformat(merged_at.replace("Z", "+00:00")) if isinstance(merged_at, str) else merged_at,
            created_at=datetime.fromisoformat(created_at.replace("Z", "+00:00")) if isinstance(created_at, str) and created_at else None,
            files=item.get("files", []),
            additions=item.get("additions", 0) or 0,
            deletions=item.get("deletions", 0) or 0,
            ticket_ids=frozenset(item["ticket_ids"]) if "ticket_ids" in item else frozenset(extract_ticket_ids(f"{item.get('title', '')}\n{item.get('body', '')}")),
            reviews=reviews,
            ci_status=ci_status,
            merge_commit_sha=item.get("merge_commit_sha"),
            pr_number=item.get("pr_number"),
        ))

    return changes
