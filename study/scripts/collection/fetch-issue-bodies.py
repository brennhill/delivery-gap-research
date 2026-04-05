#!/usr/bin/env python3
"""Fetch GitHub issue bodies for spec'd PRs that reference issues.

For each spec'd PR whose spec_source is a GitHub issue (#NNN or URL),
fetches the issue body via the GitHub API and saves it alongside the
PR data. This gives us the actual specification content rather than
just the PR description.

Resume-safe: saves per-repo, skips already-fetched issues.

Requires: gh CLI authenticated (gh auth status).

Usage:
    python3 scripts/collection/fetch-issue-bodies.py                # all repos
    python3 scripts/collection/fetch-issue-bodies.py --repo cli-cli # one repo
    python3 scripts/collection/fetch-issue-bodies.py --dry-run      # count only
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
RATE_LIMIT_SLEEP = 0.1  # seconds between API calls


def _parse_issue_ref(spec_source: str, repo: str) -> tuple[str, int] | None:
    """Parse a spec_source into (owner/repo, issue_number).

    Handles:
      - #123
      - https://github.com/owner/repo/issues/123
      - https://github.com/owner/repo/issues/123)  (trailing paren)
    """
    if not spec_source:
        return None

    # Skip #000 (placeholder)
    if spec_source == "#000" or spec_source == "#0":
        return None

    # GitHub URL
    m = re.match(r"https?://github\.com/([^/]+/[^/]+)/issues/(\d+)", spec_source)
    if m:
        return m.group(1), int(m.group(2))

    # Bare #NNN — issue is in the same repo
    m = re.match(r"#(\d+)$", spec_source)
    if m:
        issue_num = int(m.group(1))
        if issue_num > 0:
            return repo, issue_num

    return None


class RateLimitError(Exception):
    pass


def _fetch_issue(owner_repo: str, issue_number: int) -> dict | None:
    """Fetch a single issue via gh CLI.

    Returns {title, body, labels, state} on success, None if 404,
    raises RateLimitError on 403/429.
    """
    try:
        result = subprocess.run(
            ["gh", "api", f"repos/{owner_repo}/issues/{issue_number}",
             "--jq", '{title: .title, body: .body, state: .state, labels: [.labels[].name], html_url: .html_url}'],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            stderr = result.stderr.lower()
            if "403" in stderr or "429" in stderr or "rate limit" in stderr or "secondary rate" in stderr:
                raise RateLimitError(result.stderr.strip()[:200])
            if "404" in stderr:
                return None  # genuinely doesn't exist
            print(f"      API error {owner_repo}#{issue_number}: {result.stderr[:200]}", flush=True)
            return None
        return json.loads(result.stdout)
    except RateLimitError:
        raise
    except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception) as e:
        print(f"      Error fetching {owner_repo}#{issue_number}: {e}", flush=True)
        return None


def fetch_repo_issues(repo_slug: str, dry_run: bool = False) -> dict:
    """Fetch all referenced issue bodies for a repo.

    Returns dict mapping issue_key -> {title, body, ...}.
    Saves to data/issue-bodies-{slug}.json.
    """
    ss_path = DATA_DIR / f"spec-signals-{repo_slug}.json"
    if not ss_path.exists():
        return {}

    with open(ss_path) as f:
        ss_data = json.load(f)

    repo = ss_data.get("repo", repo_slug.replace("-", "/", 1))

    # Collect all issue references
    issue_refs: dict[str, list[int]] = {}  # (owner/repo, issue_num) -> list of PR numbers
    for pr in ss_data["coverage"]["prs"]:
        if not pr.get("specd"):
            continue
        parsed = _parse_issue_ref(pr.get("spec_source", ""), repo)
        if parsed:
            owner_repo, issue_num = parsed
            key = f"{owner_repo}#{issue_num}"
            if key not in issue_refs:
                issue_refs[key] = []
            issue_refs[key].append(pr["number"])

    if not issue_refs:
        print(f"  No GitHub issue references found", flush=True)
        return {}

    # Deduplicate — many PRs can reference the same issue
    unique_issues = set()
    for key in issue_refs:
        parts = key.rsplit("#", 1)
        unique_issues.add((parts[0], int(parts[1])))

    print(f"  {len(issue_refs)} issue refs from {sum(len(v) for v in issue_refs.values())} PRs "
          f"({len(unique_issues)} unique issues)", flush=True)

    if dry_run:
        return {}

    # Resume: load existing
    out_path = DATA_DIR / f"issue-bodies-{repo_slug}.json"
    existing: dict[str, dict] = {}
    if out_path.exists():
        try:
            loaded = json.loads(out_path.read_text())
            # Only keep successful fetches — retry not-found and errors
            existing = {k: v for k, v in loaded.items() if not v.get("_not_found")}
            dropped = len(loaded) - len(existing)
            print(f"  Resuming: {len(existing)} already fetched" +
                  (f", {dropped} not-found will be retried" if dropped else ""), flush=True)
        except Exception as e:
            print(f"  Warning: could not load existing: {e}", flush=True)

    fetched_count = 0
    skipped_count = 0
    failed_count = 0

    for owner_repo, issue_num in sorted(unique_issues):
        key = f"{owner_repo}#{issue_num}"
        if key in existing:
            skipped_count += 1
            continue

        try:
            issue = _fetch_issue(owner_repo, issue_num)
        except RateLimitError as e:
            # Save progress, wait, then retry with backoff
            _save_atomic(out_path, existing)
            for wait in [60, 120, 300]:
                print(f"    RATE LIMITED — saved progress, waiting {wait}s... ({e})", flush=True)
                time.sleep(wait)
                try:
                    issue = _fetch_issue(owner_repo, issue_num)
                    break  # success
                except RateLimitError:
                    continue
            else:
                print(f"    Rate limit not cleared after 3 retries — stopping repo", flush=True)
                break

        if issue:
            existing[key] = issue
            fetched_count += 1
            body_len = len(issue.get("body") or "")
            print(f"    {key}: {body_len} chars", flush=True)
        else:
            existing[key] = {"_not_found": True}
            failed_count += 1

        # Save every 50
        if (fetched_count + failed_count) % 50 == 0:
            _save_atomic(out_path, existing)

        time.sleep(RATE_LIMIT_SLEEP)

    # Final save
    _save_atomic(out_path, existing)

    print(f"  Done: {fetched_count} fetched, {skipped_count} cached, {failed_count} not found",
          flush=True)
    return existing


def _save_atomic(path: Path, data: dict) -> None:
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    os.replace(str(tmp), str(path))


def main():
    parser = argparse.ArgumentParser(
        description="Fetch GitHub issue bodies for spec'd PRs. "
                    "Resume-safe: re-run to continue. "
                    "Delete issue-bodies-*.json to re-fetch."
    )
    parser.add_argument("--repo", help="Fetch for a single repo slug")
    parser.add_argument("--dry-run", action="store_true", help="Count only")
    args = parser.parse_args()

    # Verify gh is authenticated
    if not args.dry_run:
        result = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True)
        if result.returncode != 0:
            print("Error: gh CLI not authenticated. Run: gh auth login", file=sys.stderr)
            sys.exit(1)

    if args.repo:
        slugs = [args.repo]
    else:
        slugs = sorted(
            p.stem.replace("spec-signals-", "")
            for p in DATA_DIR.glob("spec-signals-*.json")
        )

    total_fetched = 0
    total_issues = 0

    for i, slug in enumerate(slugs):
        print(f"\n[{i+1}/{len(slugs)}] {slug}:", flush=True)
        result = fetch_repo_issues(slug, dry_run=args.dry_run)
        valid = sum(1 for v in result.values() if not v.get("_not_found"))
        total_fetched += valid
        total_issues += len(result)

    print(f"\nDone. {total_fetched} issue bodies fetched ({total_issues} total refs).",
          flush=True)


if __name__ == "__main__":
    main()
