#!/usr/bin/env python3
"""Re-fetch repos with missing data fields (commits, comments, review bodies).

These repos were originally fetched with the older adapter that didn't capture
total_comments_count, commits, last_edited_at, or review body text.

Usage:
    python refetch-incomplete.py          # re-fetch all 15 repos
    python refetch-incomplete.py --repo grafana/grafana  # re-fetch one

The script uses the updated GraphQL adapter and merges new data with existing,
preserving any PRs already fetched correctly (new data wins on conflicts).
"""

import json
import sys
import time
from pathlib import Path
from multiprocessing import Process

DATA_DIR = Path(__file__).resolve().parent / "data"

# Repos needing full re-fetch (100% or near-100% missing commits)
FULL_REFETCH = [
    "calcom/cal.com",        # 99% missing
    "elastic/elasticsearch",  # 100% missing
    "grafana/grafana",        # 100% missing
    "python/cpython",         # 95% missing
    "supabase/supabase",      # 93% missing
    "oven-sh/bun",            # 90% missing
    "antiwork/gumroad",       # 74% missing
    "clerkinc/javascript",    # 64% missing
    "kubernetes/kubernetes",  # 57% missing
]

# Repos needing partial re-fetch (some PRs have data, others don't)
PARTIAL_REFETCH = [
    "PostHog/posthog",        # 55% missing
    "dotnet/aspire",          # 55% missing
    "vercel/next.js",         # 51% missing
    "promptfoo/promptfoo",    # 45% missing
    "denoland/deno",          # 40% missing
    "n8n-io/n8n",             # 38% missing
    "astral-sh/ruff",         # 11% missing
    "prometheus/prometheus",  # 11% missing
    "continuedev/continue",   # 8% missing
    "temporalio/temporal",    # 6% missing
    "cockroachdb/cockroach",  # 3% missing
]

ALL_REPOS = FULL_REFETCH + PARTIAL_REFETCH


def fetch_repo(repo: str) -> None:
    """Fetch PRs for a single repo using the delivery-gap-signals adapter."""
    from delivery_gap_signals.sources import auto_fetch

    slug = repo.replace("/", "-")
    prs_path = DATA_DIR / f"prs-{slug}.json"

    # Load existing data
    existing = {}
    if prs_path.exists():
        try:
            with open(prs_path) as f:
                for p in json.load(f):
                    existing[p["pr_number"]] = p
        except Exception:
            pass

    print(f"  {repo}: {len(existing)} existing PRs on disk", flush=True)

    # Fetch fresh data via GraphQL (has commits, comments, review bodies)
    # Retry up to 3 times on rate limit errors (adapter waits 15 min internally)
    from dataclasses import asdict
    new_prs = []
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            raw = auto_fetch(repo, lookback_days=180, limit=500, source="graphql")
            new_prs = [asdict(pr) for pr in raw]
            print(f"  {repo}: fetched {len(new_prs)} PRs from API", flush=True)
            break
        except Exception as e:
            err_str = str(e).lower()
            is_rate_limit = "rate limit" in err_str or "403" in err_str or "502" in err_str or "504" in err_str
            if is_rate_limit and attempt < max_retries:
                import time as _time
                wait = 60 * 16  # 16 min — just over GitHub's 15 min reset
                print(f"  {repo}: rate limited (attempt {attempt}/{max_retries}), waiting {wait}s...", flush=True)
                _time.sleep(wait)
            else:
                print(f"  {repo}: FETCH ERROR (attempt {attempt}) - {e}", flush=True)
                if attempt == max_retries:
                    return

    # Merge: new data wins on conflicts, keep existing PRs not in new fetch
    for p in new_prs:
        existing[p["pr_number"]] = p

    merged = sorted(existing.values(), key=lambda p: p["pr_number"], reverse=True)

    # Validate: check that new data has the fields we need
    if new_prs:
        sample = new_prs[0]
        has_commits = "commits" in sample or "commit_count" in sample
        has_comments = "total_comments_count" in sample
        has_review_body = any(
            len((rev.get("body", "") or "")) > 0
            for rev in (sample.get("reviews") or [])
        )
        print(f"  {repo}: fields check — commits={has_commits} comments={has_comments} review_body={has_review_body}", flush=True)

    # Atomic write (handle datetime objects)
    def default_serializer(obj):
        if hasattr(obj, 'isoformat'):
            return obj.isoformat()
        if isinstance(obj, (set, frozenset)):
            return list(obj)
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    tmp = prs_path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(merged, indent=2, default=default_serializer), encoding="utf-8")
    tmp.replace(prs_path)
    print(f"  {repo}: wrote {len(merged)} PRs to {prs_path.name}", flush=True)


def _fetch_worker(repo: str) -> None:
    """Module-level worker for multiprocessing."""
    try:
        fetch_repo(repo)
    except Exception as e:
        print(f"  {repo}: WORKER ERROR - {e}", flush=True)


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", help="Fetch a single repo")
    args = parser.parse_args()

    repos = [args.repo] if args.repo else ALL_REPOS

    for i, repo in enumerate(repos):
        print(f"\n[{i+1}/{len(repos)}] {repo}:", flush=True)

        proc = Process(target=_fetch_worker, args=(repo,))
        proc.start()
        proc.join(timeout=3600)  # 60 min max per repo (includes up to 3 rate limit waits)

        if proc.is_alive():
            print(f"  {repo}: TIMEOUT after 1200s, killing", flush=True)
            proc.terminate()
            proc.join(5)

        # Verify data after fetch
        slug = repo.replace("/", "-")
        prs_path = DATA_DIR / f"prs-{slug}.json"
        if prs_path.exists():
            with open(prs_path) as f:
                prs = json.load(f)
            has_comments = sum(1 for p in prs if p.get("total_comments_count") is not None)
            has_commits = sum(1 for p in prs if p.get("commits"))
            print(f"  {repo}: VERIFIED — {len(prs)} PRs, {has_comments} with comments, {has_commits} with commits", flush=True)

        time.sleep(1)

    print("\nDone. Run build-unified-csv.py → compute-features.py → build-master-csv.py to rebuild.")


if __name__ == "__main__":
    main()
