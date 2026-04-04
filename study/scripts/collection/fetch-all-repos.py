#!/usr/bin/env python3
"""Fetch PR data for all study repos from a single canonical manifest.

This replaces the split between runner.py (43 repos) and fetch-new-repos.py
(76 repos) with one script that reads from data/repo-manifest.json.

Usage:
    python fetch-all-repos.py                       # fetch all repos
    python fetch-all-repos.py --repo rails/rails    # fetch one
    python fetch-all-repos.py --dry-run              # show what would run
    python fetch-all-repos.py --tier new-strong       # only one tier
    python fetch-all-repos.py --refetch              # re-fetch existing repos
    python fetch-all-repos.py --incomplete           # only repos missing lookback coverage
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

STUDY_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(STUDY_DIR))

from fetch_progress import load_progress_state, plan_gap_fetch, progress_state_path
from runner import run_all, DATA_DIR

MANIFEST_FILE = DATA_DIR / "repo-manifest.json"


def load_manifest() -> list[dict]:
    """Load the canonical repo manifest."""
    if not MANIFEST_FILE.exists():
        print(f"ERROR: {MANIFEST_FILE} not found.")
        print("Run build-master-csv.py first, or create the manifest manually.")
        sys.exit(1)
    with open(MANIFEST_FILE) as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser(
        description="Fetch PR data for all study repos (reads from data/repo-manifest.json)"
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--repo", help="Fetch a single repo (e.g., 'apache/kafka')")
    parser.add_argument("--tier", help="Only fetch repos with this tier label")
    parser.add_argument("--refetch", action="store_true",
                        help="Re-fetch repos that already have data (extends lookback window)")
    parser.add_argument("--incomplete", action="store_true",
                        help="Only fetch repos whose data doesn't cover the full lookback window")
    parser.add_argument("--lookback-days", type=int, default=365,
                        help="Lookback window in days (default: 365)")
    args = parser.parse_args()

    manifest = load_manifest()
    print(f"Manifest: {len(manifest)} repos")

    # Filter
    if args.repo:
        matching = [e for e in manifest if e["repo"] == args.repo]
        if matching:
            repos = matching
        else:
            print(f"Repo {args.repo} not in manifest. Running anyway.")
            repos = [{"repo": args.repo, "tier": "unknown"}]
    elif args.tier:
        repos = [r for r in manifest if r.get("tier") == args.tier]
        print(f"Tier '{args.tier}': {len(repos)} repos")
    elif args.incomplete:
        now = datetime.now(timezone.utc)
        progress = load_progress_state(progress_state_path(DATA_DIR))
        incomplete = []
        for r in manifest:
            slug = r["repo"].replace("/", "-")
            fp = DATA_DIR / f"prs-{slug}.json"
            if not fp.exists():
                # No data at all — full fetch needed
                print(f"  {r['repo']}: no PR data file yet — full fetch needed")
                incomplete.append(r)
                continue
            with open(fp) as f:
                prs = json.load(f)
            if not prs:
                print(f"  {r['repo']}: PR data file is empty — full fetch needed")
                incomplete.append(r)
                continue
            if not any(
                isinstance(p, dict) and (p.get("merged_at") or p.get("created_at"))
                for p in prs
            ):
                print(f"  {r['repo']}: PR data has no usable timestamps — full fetch needed")
                incomplete.append(r)
                continue
            plan = plan_gap_fetch(
                repo=r["repo"],
                prs_path=fp,
                lookback_days=args.lookback_days,
                now=now,
                progress_state=progress,
            )
            if plan is None:
                continue
            days_back = (now - datetime.fromisoformat(plan.until_iso)).total_seconds() / 86400
            gap_days = plan.gap_seconds / 86400
            if gap_days <= 0:
                continue
            r["_since_iso"] = plan.since_iso
            r["_until_iso"] = plan.until_iso
            r["_gap_days"] = gap_days
            print(
                f"  {r['repo']}: have {days_back:.2f}d, need {args.lookback_days}d "
                f"— will fetch {gap_days:.2f}d gap"
            )
            incomplete.append(r)
        # Sort by gap size: smallest gaps first so repos complete quickly
        # incomplete.sort(key=lambda r: r.get("_gap_days", args.lookback_days))
        repos = incomplete
        print(f"Incomplete repos (don't cover full {args.lookback_days}d window): {len(repos)}/{len(manifest)}")
    else:
        repos = manifest

    # Convert to runner.py format (preserve _since_iso/_until_iso for gap fetching)
    to_run = [{"repo": r["repo"], "lang": r.get("lang", "unknown"),
               "tier": r.get("tier", "unknown"),
               **({k: r[k] for k in ("_since_iso", "_until_iso") if k in r})}
              for r in repos]

    # Skip repos we already have data for (unless --refetch or --incomplete)
    if args.refetch or args.incomplete:
        to_fetch = to_run
        if args.refetch:
            print("--refetch: will extend all repos to full lookback window")
    else:
        already = set()
        for fp in DATA_DIR.glob("prs-*.json"):
            slug = fp.stem.replace("prs-", "")
            already.add(slug)

        to_fetch = []
        skipped = []
        for r in to_run:
            slug = r["repo"].replace("/", "-")
            if slug in already:
                skipped.append(r["repo"])
            else:
                to_fetch.append(r)

        if skipped:
            print(f"Skipping {len(skipped)} repos with existing data")
            print(f"  (use --refetch to extend, or --incomplete for partial lookback coverage)")

    if not to_fetch:
        print("All repos already fetched!")
        return

    print(f"\nFetching {len(to_fetch)} repos")
    run_all(to_fetch, dry_run=args.dry_run, fetch_only=True)


if __name__ == "__main__":
    main()
