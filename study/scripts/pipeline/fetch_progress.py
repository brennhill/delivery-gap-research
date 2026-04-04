#!/usr/bin/env python3
"""Helpers for fetch completeness and partial-gap progress tracking."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path


@dataclass(frozen=True)
class GapPlan:
    """Exact backfill window needed for a repo."""

    since_iso: str
    until_iso: str
    gap_seconds: float
    current_oldest_iso: str


def progress_state_path(data_dir: Path) -> Path:
    return data_dir / "fetch-progress.json"


def fetch_status_path(prs_path: Path) -> Path:
    return prs_path.parent / f".fetch-status-{prs_path.stem}.json"


def load_progress_state(path: Path) -> dict:
    if not path.exists():
        return {"version": 1, "repos": {}}

    try:
        loaded = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError, TypeError):
        return {"version": 1, "repos": {}}

    if not isinstance(loaded, dict):
        return {"version": 1, "repos": {}}

    repos = loaded.get("repos")
    if not isinstance(repos, dict):
        repos = {}

    return {
        "version": loaded.get("version", 1),
        "repos": repos,
    }


def save_progress_state(path: Path, state: dict) -> None:
    normalized = {
        "version": state.get("version", 1),
        "repos": state.get("repos", {}),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(normalized, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(path)


def load_fetch_status(prs_path: Path) -> dict | None:
    path = fetch_status_path(prs_path)
    if not path.exists():
        return None

    try:
        data = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError, TypeError):
        return None

    if not isinstance(data, dict):
        return None
    return data


def clear_fetch_status(prs_path: Path) -> None:
    try:
        fetch_status_path(prs_path).unlink()
    except FileNotFoundError:
        pass


def write_fetch_status(
    prs_path: Path,
    *,
    repo: str,
    requested_since_iso: str | None,
    requested_until_iso: str | None,
    completed_at_iso: str | None = None,
) -> None:
    payload = {
        "repo": repo,
        "requested_since_iso": requested_since_iso,
        "requested_until_iso": requested_until_iso,
        "completed_at_iso": completed_at_iso or datetime.now(timezone.utc).isoformat(),
        "completed": True,
    }
    path = fetch_status_path(prs_path)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(path)


def oldest_pr_iso(prs_path: Path) -> str | None:
    oldest = oldest_pr_datetime(prs_path)
    return oldest.isoformat() if oldest else None


def oldest_pr_datetime(prs_path: Path) -> datetime | None:
    try:
        prs = json.loads(prs_path.read_text())
    except (FileNotFoundError, json.JSONDecodeError, OSError, TypeError):
        return None

    if not isinstance(prs, list):
        return None

    oldest: datetime | None = None
    for pr in prs:
        if not isinstance(pr, dict):
            continue
        raw = pr.get("merged_at") or pr.get("created_at")
        if not raw or not isinstance(raw, str):
            continue
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            continue
        if oldest is None or dt < oldest:
            oldest = dt
    return oldest


def plan_gap_fetch(
    *,
    repo: str,
    prs_path: Path,
    lookback_days: int,
    now: datetime | None = None,
    progress_state: dict | None = None,
) -> GapPlan | None:
    oldest = oldest_pr_datetime(prs_path)
    if oldest is None:
        return None

    now = now or datetime.now(timezone.utc)
    cutoff = now - timedelta(days=lookback_days)
    if oldest <= cutoff:
        return None

    progress = ((progress_state or {}).get("repos") or {}).get(repo) or {}
    covered_since = _parse_iso(progress.get("covered_since_iso"))
    covered_until = _parse_iso(progress.get("covered_until_iso"))

    if (
        covered_since is not None
        and covered_until is not None
        and covered_since <= cutoff
        and oldest <= covered_until
    ):
        return None

    return GapPlan(
        since_iso=cutoff.isoformat(),
        until_iso=oldest.isoformat(),
        gap_seconds=(oldest - cutoff).total_seconds(),
        current_oldest_iso=oldest.isoformat(),
    )


def mark_gap_complete(
    state: dict,
    *,
    repo: str,
    requested_since_iso: str,
    requested_until_iso: str,
    observed_oldest_iso: str | None,
    completed_at_iso: str,
) -> None:
    repos = state.setdefault("repos", {})
    entry = repos.setdefault(repo, {})

    requested_since = _parse_iso(requested_since_iso)
    requested_until = _parse_iso(requested_until_iso)
    observed_oldest = _parse_iso(observed_oldest_iso)
    existing_since = _parse_iso(entry.get("covered_since_iso"))
    existing_until = _parse_iso(entry.get("covered_until_iso"))

    since_candidates = [dt for dt in (existing_since, requested_since) if dt is not None]
    until_candidates = [
        dt
        for dt in (existing_until, requested_until, observed_oldest)
        if dt is not None
    ]

    if not since_candidates or not until_candidates:
        return

    entry.update({
        "covered_since_iso": min(since_candidates).isoformat(),
        "covered_until_iso": max(until_candidates).isoformat(),
        "last_requested_since_iso": requested_since_iso,
        "last_requested_until_iso": requested_until_iso,
        "last_observed_oldest_iso": observed_oldest_iso,
        "last_completed_at_iso": completed_at_iso,
    })
    entry.pop("active_gap", None)
    state["version"] = state.get("version", 1)


def get_active_gap_checkpoint(
    state: dict,
    *,
    repo: str,
    requested_since_iso: str,
    requested_until_iso: str,
) -> dict | None:
    progress = ((state or {}).get("repos") or {}).get(repo) or {}
    active = progress.get("active_gap")
    if not isinstance(active, dict):
        return None
    active_since = _parse_iso(active.get("requested_since_iso"))
    requested_since = _parse_iso(requested_since_iso)
    active_until = active.get("requested_until_iso")
    if active_until != requested_until_iso:
        return None
    if active_since is None or requested_since is None:
        return None
    if active_since.date() != requested_since.date():
        return None
    if active_since > requested_since:
        return None
    return active


def update_active_gap_checkpoint(
    state: dict,
    *,
    repo: str,
    requested_since_iso: str,
    requested_until_iso: str,
    resume_after_cursor: str | None,
    saved_pr_count: int,
    updated_at_iso: str,
) -> None:
    repos = state.setdefault("repos", {})
    entry = repos.setdefault(repo, {})
    entry["active_gap"] = {
        "requested_since_iso": requested_since_iso,
        "requested_until_iso": requested_until_iso,
        "resume_after_cursor": resume_after_cursor,
        "saved_pr_count": saved_pr_count,
        "updated_at_iso": updated_at_iso,
    }
    state["version"] = state.get("version", 1)


def clear_active_gap_checkpoint(
    state: dict,
    *,
    repo: str,
    requested_since_iso: str | None = None,
    requested_until_iso: str | None = None,
) -> None:
    progress = ((state or {}).get("repos") or {}).get(repo)
    if not isinstance(progress, dict):
        return
    active = progress.get("active_gap")
    if not isinstance(active, dict):
        return
    if requested_since_iso is not None and active.get("requested_since_iso") != requested_since_iso:
        return
    if requested_until_iso is not None and active.get("requested_until_iso") != requested_until_iso:
        return
    progress.pop("active_gap", None)


def _parse_iso(value: str | None) -> datetime | None:
    if not value or not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
