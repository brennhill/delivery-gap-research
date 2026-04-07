#!/usr/bin/env python3

"""Shared output-path resolution for baseline and exact-only analyses."""

from __future__ import annotations

import os
from pathlib import Path


def _env_truthy(name: str) -> bool:
    value = os.environ.get(name, "")
    return value.strip().lower() in {"1", "true", "yes", "on"}


def get_results_dir(project_root: Path) -> Path:
    """Return the active results directory, creating it if needed."""

    project_root = Path(project_root)
    env_dir = os.environ.get("RESULTS_DIR")

    if env_dir:
        results_dir = Path(env_dir)
    elif _env_truthy("SZZ_EXACT_ONLY"):
        results_dir = project_root / "results" / "exact-only"
    else:
        results_dir = project_root / "results"

    results_dir.mkdir(parents=True, exist_ok=True)
    return results_dir


def result_path(project_root: Path, filename: str) -> Path:
    """Resolve a filename under the active results directory."""

    return get_results_dir(project_root) / filename
