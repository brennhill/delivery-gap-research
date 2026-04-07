#!/usr/bin/env python3

"""Shared loader for SZZ blame-link datasets and sensitivity filters."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd


def _env_truthy(name: str) -> bool:
    value = os.environ.get(name, "")
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _resolve_szz_path(data_dir: Path, szz_path: str | Path | None) -> Path:
    if szz_path is not None:
        return Path(szz_path)

    env_path = os.environ.get("SZZ_RESULTS_PATH")
    if env_path:
        return Path(env_path)

    return data_dir / "szz-results-merged.csv"


def _load_repo_merge_sha_index(data_dir: Path, repo: str) -> dict[int, str]:
    prs_path = data_dir / f"prs-{repo.replace('/', '-')}.json"
    if not prs_path.exists():
        return {}

    with open(prs_path, "r") as f:
        prs = json.load(f)

    index = {}
    for pr in prs:
        pr_number = pr.get("pr_number")
        merge_sha = pr.get("merge_commit_sha")
        if pr_number is not None and merge_sha:
            index[int(pr_number)] = merge_sha
    return index


def _filter_exact_merge_sha_only(szz: pd.DataFrame, data_dir: Path) -> tuple[pd.DataFrame, dict]:
    repo_cache: dict[str, dict[int, str]] = {}
    exact_mask = []
    exact_rows = 0
    fallback_rows = 0
    unmapped_rows = 0

    for row in szz.itertuples(index=False):
        bug_pr_number = getattr(row, "bug_pr_number", None)
        if pd.isna(bug_pr_number):
            exact_mask.append(False)
            unmapped_rows += 1
            continue

        repo = row.repo
        if repo not in repo_cache:
            repo_cache[repo] = _load_repo_merge_sha_index(data_dir, repo)

        merge_sha = repo_cache[repo].get(int(float(bug_pr_number)))
        is_exact = merge_sha == row.bug_commit_sha
        exact_mask.append(is_exact)
        if is_exact:
            exact_rows += 1
        else:
            fallback_rows += 1

    filtered = szz.loc[exact_mask].copy()
    meta = {
        "source_rows": len(szz),
        "exact_rows": exact_rows,
        "fallback_rows": fallback_rows,
        "unmapped_rows": unmapped_rows,
    }
    return filtered, meta


def load_szz_results(
    data_dir: Path,
    *,
    exact_only: bool | None = None,
    szz_path: str | Path | None = None,
) -> tuple[pd.DataFrame, dict]:
    """Load SZZ blame links, optionally restricting to exact merge-SHA mappings only.

    Environment variables:
      - ``SZZ_EXACT_ONLY=1`` enables exact-only filtering.
      - ``SZZ_RESULTS_PATH=/path/to/file.csv`` overrides the input CSV path.
    """

    data_dir = Path(data_dir)
    szz_path = _resolve_szz_path(data_dir, szz_path)
    exact_only = _env_truthy("SZZ_EXACT_ONLY") if exact_only is None else exact_only

    szz = pd.read_csv(szz_path)
    meta = {
        "mode": "full",
        "path": str(szz_path),
        "source_rows": len(szz),
        "exact_rows": None,
        "fallback_rows": None,
        "unmapped_rows": None,
    }

    if not exact_only:
        return szz, meta

    filtered, counts = _filter_exact_merge_sha_only(szz, data_dir)
    meta.update(counts)
    meta["mode"] = "exact_only"
    return filtered, meta
