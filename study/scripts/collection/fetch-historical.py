#!/usr/bin/env python3
"""Fetch historical PR data for pre/post AI comparison.

Saves to data-PERIOD/ directories to keep datasets cleanly distinct.

Usage:
    python fetch-historical.py --period 2023-H1    # Jan-Jun 2023 (pre-AI baseline)
    python fetch-historical.py --period 2024-H1    # Jan-Jun 2024 (early AI)
    python fetch-historical.py --period 2025-H2    # Jul-Dec 2025 (current AI era)
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

STUDY_DIR = Path(__file__).resolve().parent

# Repos for pre/post comparison — established projects with visible AI adoption shift
COMPARISON_REPOS = [
    # High AI adoption now, existed in 2023
    {"repo": "antiwork/gumroad",        "note": "went all-in on Devin"},
    {"repo": "novuhq/novu",             "note": "23% AI-tagged now"},
    {"repo": "denoland/deno",           "note": "15% AI-tagged now"},
    {"repo": "biomejs/biome",           "note": "29% AI-tagged now"},
    {"repo": "oven-sh/bun",             "note": "17% AI-tagged now"},
    {"repo": "pnpm/pnpm",              "note": "14% AI-tagged now"},
    {"repo": "PostHog/posthog",         "note": "11% AI-tagged now"},
    # Controls — low AI, high human attention
    {"repo": "grafana/grafana",         "note": "control: 3.5% AI, 34% attention"},
    {"repo": "sveltejs/svelte",         "note": "control: 7% AI, 9.5% attention"},
    {"repo": "astral-sh/ruff",          "note": "control: 0.5% AI, 7% attention"},
    {"repo": "cli/cli",                "note": "control: 1% AI, 8% attention"},
]

PERIODS = {
    "2023-H1": (datetime(2023, 1, 1, tzinfo=timezone.utc), datetime(2023, 7, 1, tzinfo=timezone.utc)),
    "2023-H2": (datetime(2023, 7, 1, tzinfo=timezone.utc), datetime(2024, 1, 1, tzinfo=timezone.utc)),
    "2024-H1": (datetime(2024, 1, 1, tzinfo=timezone.utc), datetime(2024, 7, 1, tzinfo=timezone.utc)),
    "2024-H2": (datetime(2024, 7, 1, tzinfo=timezone.utc), datetime(2025, 1, 1, tzinfo=timezone.utc)),
    "2025-H1": (datetime(2025, 1, 1, tzinfo=timezone.utc), datetime(2025, 7, 1, tzinfo=timezone.utc)),
    "2025-H2": (datetime(2025, 7, 1, tzinfo=timezone.utc), datetime(2026, 1, 1, tzinfo=timezone.utc)),
}


def fetch_repo(repo: str, since: datetime, until: datetime, data_dir: Path) -> int:
    """Fetch PRs for a repo in a fixed time window. Returns PR count."""
    slug = repo.replace("/", "-")
    prs_path = data_dir / f"prs-{slug}.json"

    # Check existing data
    pre_count = 0
    if prs_path.exists():
        try:
            pre_count = len(json.loads(prs_path.read_text()))
            if pre_count > 50:
                print(f"    Already have {pre_count} PRs, skipping fetch", flush=True)
                return pre_count
        except Exception:
            pass

    print(f"    Fetching {since.strftime('%Y-%m-%d')} to {until.strftime('%Y-%m-%d')}...", flush=True)

    try:
        from delivery_gap_signals.sources.github_graphql import fetch_changes
        changes = fetch_changes(
            repo,
            lookback_days=365,  # ignored when since/until provided
            since=since,
            until=until,
            incremental_path=str(prs_path),
        )
        # Incremental saves handle the file, but do a final merge
        data = [c.to_dict() for c in changes]
        if prs_path.exists():
            try:
                existing = {p.get("pr_number"): p for p in json.loads(prs_path.read_text())}
                for d in data:
                    existing[d.get("pr_number")] = d
                data = list(existing.values())
            except Exception:
                pass

        tmp = prs_path.with_suffix('.json.tmp')
        tmp.write_text(json.dumps(data, indent=2, default=str))
        tmp.replace(prs_path)
        print(f"    -> {len(data)} PRs", flush=True)
        return len(data)

    except Exception as e:
        print(f"    -> FAILED: {type(e).__name__}: {e}", flush=True)
        # Check if incremental save got partial data
        if prs_path.exists():
            try:
                partial = json.loads(prs_path.read_text())
                print(f"    -> {len(partial)} PRs saved (partial)", flush=True)
                return len(partial)
            except Exception:
                pass
        return 0


def run_tools(repo: str, data_dir: Path) -> None:
    """Run UPFRONT and CatchRate on fetched data."""
    slug = repo.replace("/", "-")
    prs_path = data_dir / f"prs-{slug}.json"

    if not prs_path.exists():
        return

    for tool, subcmd, out_name in [
        ("upfront", "report", f"upfront-{slug}.json"),
        ("catchrate", "check", f"catchrate-{slug}.json"),
    ]:
        out_path = data_dir / out_name
        if out_path.exists():
            continue
        try:
            result = subprocess.run(
                [tool, subcmd, "--from-prs", str(prs_path), "--json", str(out_path)],
                capture_output=True, text=True, timeout=300,
            )
            if result.returncode == 0:
                print(f"    {tool}: OK", flush=True)
            else:
                print(f"    {tool}: FAILED", flush=True)
        except Exception as e:
            print(f"    {tool}: ERROR {e}", flush=True)


def main():
    parser = argparse.ArgumentParser(description="Fetch historical PR data")
    parser.add_argument("--period", required=True, choices=list(PERIODS.keys()),
                        help="Time period to fetch")
    parser.add_argument("--repo", help="Fetch a single repo instead of all comparison repos")
    parser.add_argument("--fetch-only", action="store_true",
                        help="Skip UPFRONT/CatchRate, just fetch PRs")
    args = parser.parse_args()

    since, until = PERIODS[args.period]
    data_dir = STUDY_DIR / f"data-{args.period}"
    data_dir.mkdir(exist_ok=True)

    print(f"Period: {args.period} ({since.strftime('%Y-%m-%d')} to {until.strftime('%Y-%m-%d')})")
    print(f"Data dir: {data_dir}")
    print()

    if args.repo:
        repos = [{"repo": args.repo, "note": "manual"}]
    else:
        repos = COMPARISON_REPOS

    total_prs = 0
    for i, entry in enumerate(repos, 1):
        repo = entry["repo"]
        print(f"[{i}/{len(repos)}] {repo} ({entry['note']})", flush=True)
        n = fetch_repo(repo, since, until, data_dir)
        total_prs += n

        if not args.fetch_only and n > 0:
            run_tools(repo, data_dir)

        # Auto-commit
        try:
            subprocess.run(
                ["git", "add", str(data_dir)],
                capture_output=True, timeout=10, cwd=str(STUDY_DIR.parent.parent),
            )
            subprocess.run(
                ["git", "commit", "-m", f"data-{args.period}: {repo} ({n} PRs)", "--no-verify"],
                capture_output=True, timeout=10, cwd=str(STUDY_DIR.parent.parent),
            )
            print(f"    [committed]", flush=True)
        except Exception as e:
            print(f"    [commit skipped: {e}]", flush=True)

    print(f"\nDone. {total_prs} total PRs across {len(repos)} repos in {args.period}")
    print(f"Data saved to: {data_dir}")


if __name__ == "__main__":
    main()
