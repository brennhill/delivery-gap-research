#!/usr/bin/env python3
"""Run CATCHRATE against public GitHub repos.

Usage:
    python runner.py                  # run all 30 repos
    python runner.py --dry-run        # print commands without executing
    python runner.py --repo cli/cli   # run a single repo (for testing)
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from fetch_progress import (
    get_active_gap_checkpoint,
    clear_fetch_status,
    load_fetch_status,
    load_progress_state,
    mark_gap_complete,
    oldest_pr_iso,
    progress_state_path,
    save_progress_state,
    update_active_gap_checkpoint,
    write_fetch_status,
)

STUDY_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = STUDY_DIR / "data"
GAP_FETCH_INITIAL_PAGE_SIZE = 15
GAP_FETCH_MIN_PAGE_SIZE = 2
GAP_FETCH_QUERY = """
query($owner: String!, $repo: String!, $after: String, $pageSize: Int!) {
  repository(owner: $owner, name: $repo) {
    pullRequests(
      states: MERGED,
      orderBy: {field: UPDATED_AT, direction: DESC},
      first: $pageSize,
      after: $after
    ) {
      pageInfo {
        hasNextPage
        endCursor
      }
      nodes {
        number
        title
        body
        mergedAt
        createdAt
        lastEditedAt
        totalCommentsCount
        additions
        deletions
        author { login }
        mergeCommit { oid }
        files(first: 100) {
          nodes { path }
        }
        reviews(first: 50) {
          nodes {
            author { login }
            state
            submittedAt
            body
          }
        }
        commits(first: 100) {
          totalCount
          nodes {
            commit {
              message
            }
          }
        }
        headCommit: commits(last: 1) {
          nodes {
            commit {
              statusCheckRollup {
                contexts(first: 50) {
                  nodes {
                    ... on CheckRun {
                      conclusion
                    }
                    ... on StatusContext {
                      state
                    }
                  }
                }
              }
            }
          }
        }
      }
    }
  }
}
"""

# ── The 30 repos ─────────────────────────────────────────────────────────

REPOS: list[dict[str, str]] = [
    # Tier AI first — these are what we need most data on
    {"repo": "promptfoo/promptfoo",         "lang": "TypeScript",       "tier": "AI"},
    {"repo": "mendableai/firecrawl",        "lang": "TypeScript",       "tier": "AI"},
    {"repo": "calcom/cal.com",              "lang": "TypeScript",       "tier": "AI"},
    {"repo": "mlflow/mlflow",               "lang": "Python",           "tier": "AI"},
    {"repo": "liam-hq/liam",                "lang": "TypeScript",       "tier": "AI"},
    {"repo": "novuhq/novu",                 "lang": "TypeScript",       "tier": "AI"},
    {"repo": "antiwork/gumroad",            "lang": "Ruby",             "tier": "AI"},
    {"repo": "dotnet/aspire",               "lang": "C#",               "tier": "AI"},
    {"repo": "continuedev/continue",        "lang": "TypeScript",       "tier": "AI"},
    {"repo": "lobehub/lobe-chat",           "lang": "TypeScript",       "tier": "AI"},
    {"repo": "anthropics/anthropic-cookbook","lang": "Python",           "tier": "AI"},
    {"repo": "PostHog/posthog",             "lang": "TypeScript",       "tier": "AI"},
    {"repo": "clerkinc/javascript",         "lang": "TypeScript",       "tier": "AI"},
    {"repo": "n8n-io/n8n",                  "lang": "TypeScript",       "tier": "AI"},
    # Tier A: Near-100% issue linking
    {"repo": "kubernetes/kubernetes",       "lang": "Go",               "tier": "A"},
    {"repo": "cockroachdb/cockroach",       "lang": "Go",               "tier": "A"},
    {"repo": "microsoft/vscode",            "lang": "TypeScript",       "tier": "A"},
    {"repo": "pingcap/tidb",               "lang": "Go",               "tier": "A"},
    {"repo": "apache/arrow",               "lang": "Multi",            "tier": "A"},
    {"repo": "apache/kafka",               "lang": "Java/Scala",       "tier": "A"},
    {"repo": "biomejs/biome",              "lang": "Rust",             "tier": "A"},
    {"repo": "sveltejs/svelte",            "lang": "TypeScript",       "tier": "A"},
    # Tier B: 60-90% issue linking
    {"repo": "rust-lang/rust",             "lang": "Rust",             "tier": "B"},
    {"repo": "python/cpython",             "lang": "C/Python",         "tier": "B"},
    {"repo": "grafana/grafana",            "lang": "Go/TypeScript",    "tier": "B"},
    {"repo": "prometheus/prometheus",      "lang": "Go",               "tier": "B"},
    {"repo": "django/django",              "lang": "Python",           "tier": "B"},
    {"repo": "envoyproxy/envoy",           "lang": "C++",              "tier": "B"},
    {"repo": "cli/cli",                    "lang": "Go",               "tier": "B"},
    {"repo": "astral-sh/ruff",             "lang": "Rust",             "tier": "B"},
    {"repo": "denoland/deno",              "lang": "Rust/TypeScript",  "tier": "B"},
    {"repo": "oven-sh/bun",               "lang": "Zig/TypeScript",   "tier": "B"},
    {"repo": "temporalio/temporal",        "lang": "Go",               "tier": "B"},
    {"repo": "pnpm/pnpm",                 "lang": "TypeScript",       "tier": "B"},
    # Tier C: 30-50% issue linking
    {"repo": "vercel/next.js",             "lang": "TypeScript",       "tier": "C"},
    {"repo": "huggingface/transformers",   "lang": "Python",           "tier": "C"},
    {"repo": "langchain-ai/langchain",     "lang": "Python",           "tier": "C"},
    {"repo": "supabase/supabase",          "lang": "TypeScript",       "tier": "C"},
    {"repo": "elastic/elasticsearch",      "lang": "Java",             "tier": "C"},
    {"repo": "facebook/react",             "lang": "JavaScript",       "tier": "C"},
    # Tier D: Low linking
    {"repo": "astral-sh/uv",              "lang": "Rust",             "tier": "D"},
    {"repo": "tailwindlabs/tailwindcss",   "lang": "Rust/TypeScript",  "tier": "D"},
    {"repo": "traefik/traefik",            "lang": "Go",               "tier": "D"},
    {"repo": "nats-io/nats-server",        "lang": "Go",               "tier": "D"},
]


def _slug(repo: str) -> str:
    """Convert owner/repo to owner-repo for filenames."""
    return repo.replace("/", "-")


def _merge_with_existing(new_data: list[dict], prs_path: Path) -> list[dict]:
    """Merge newly fetched PRs with existing data. Never lose PRs.

    Deduplicates by pr_number, preferring new data (may have more fields
    from a better adapter).
    """
    if not prs_path.exists():
        return new_data

    try:
        with open(prs_path) as f:
            existing = json.load(f)
    except Exception:
        return new_data

    # Index by pr_number — new data wins on collision
    by_number = {}
    for pr in existing:
        by_number[pr.get("pr_number")] = pr
    for pr in new_data:
        by_number[pr.get("pr_number")] = pr

    merged = list(by_number.values())
    if len(merged) > len(new_data):
        added = len(merged) - len(new_data)
        print(f"  -> kept {added} existing PRs not in new fetch", flush=True)
    return merged


def _count_prs_on_disk(prs_path: Path) -> int:
    try:
        data = json.loads(prs_path.read_text())
    except Exception:
        return 0
    return len(data) if isinstance(data, list) else 0


def _merge_head_commit_rollup(pr_node: dict) -> dict:
    """Attach head-commit status rollup onto the last commit node for parser compatibility."""
    commits = (((pr_node.get("commits") or {}).get("nodes")) or [])
    head_nodes = (((pr_node.get("headCommit") or {}).get("nodes")) or [])
    if commits and head_nodes:
        head_commit = (head_nodes[-1].get("commit") or {})
        head_rollup = head_commit.get("statusCheckRollup")
        if head_rollup is not None:
            commit_obj = commits[-1].setdefault("commit", {})
            commit_obj["statusCheckRollup"] = head_rollup
    pr_node.pop("headCommit", None)
    return pr_node


def _fetch_gap_with_resume(repo: str, prs_path_str: str, since_iso: str, until_iso: str) -> None:
    """Fetch a fixed gap window with page-level cursor checkpoints."""
    from delivery_gap_signals.sources import github_graphql

    prs_path = Path(prs_path_str)
    progress_path = progress_state_path(prs_path.parent)
    progress_state = load_progress_state(progress_path)
    checkpoint = get_active_gap_checkpoint(
        progress_state,
        repo=repo,
        requested_since_iso=since_iso,
        requested_until_iso=until_iso,
    )

    owner, name = repo.split("/", 1)
    since_dt = datetime.fromisoformat(since_iso)
    until_dt = datetime.fromisoformat(until_iso)

    if checkpoint is not None:
        cursor = checkpoint.get("resume_after_cursor")
        saved_pr_count = checkpoint.get("saved_pr_count", 0)
        if cursor is None:
            print(f"  [child] gap pages already saved ({saved_pr_count} PRs), finalizing", flush=True)
            write_fetch_status(
                prs_path,
                repo=repo,
                requested_since_iso=since_iso,
                requested_until_iso=until_iso,
            )
            return
        print(
            f"  [child] resuming gap from saved cursor ({saved_pr_count} PRs already on disk)",
            flush=True,
        )
    else:
        cursor = github_graphql._skip_to_window_fast(owner, name, until_dt)
        if cursor is github_graphql._EXHAUSTED:
            write_fetch_status(
                prs_path,
                repo=repo,
                requested_since_iso=since_iso,
                requested_until_iso=until_iso,
            )
            return

    current_page_size = GAP_FETCH_INITIAL_PAGE_SIZE
    consecutive_successes = 0

    while True:
        variables = {
            "owner": owner,
            "repo": name,
            "after": cursor,
            "pageSize": current_page_size,
        }

        try:
            data = github_graphql._run_graphql(GAP_FETCH_QUERY, variables)
        except RuntimeError as exc:
            print(
                f"    [gap {since_iso[:10]}..{until_iso[:10]}] page size={current_page_size} FAILED",
                flush=True,
            )
            if github_graphql._is_gateway_error(str(exc)) and current_page_size > GAP_FETCH_MIN_PAGE_SIZE:
                current_page_size = max(GAP_FETCH_MIN_PAGE_SIZE, current_page_size // 2)
                consecutive_successes = 0
                print(f"    backing down to size={current_page_size}", flush=True)
                continue
            raise

        prs_data = data.get("data", {}).get("repository", {}).get("pullRequests", {})
        nodes = prs_data.get("nodes", [])
        page_info = prs_data.get("pageInfo", {})

        page_changes = []
        any_before_since = False
        for pr in nodes:
            pr = _merge_head_commit_rollup(pr)
            merged_at = pr.get("mergedAt")
            if merged_at:
                merged_dt = datetime.fromisoformat(merged_at.replace("Z", "+00:00"))
                if merged_dt < since_dt:
                    any_before_since = True

            change = github_graphql._parse_pr_node(
                pr,
                repo,
                365,
                since=since_dt,
                until=until_dt,
            )
            if change is not None:
                page_changes.append(change)

        pre_save_count = _count_prs_on_disk(prs_path)
        if page_changes:
            github_graphql._save_incremental(prs_path_str, page_changes)

        cursor = page_info.get("endCursor")
        post_save_count = _count_prs_on_disk(prs_path)
        unique_added = max(0, post_save_count - pre_save_count)
        progress_state = load_progress_state(progress_path)
        update_active_gap_checkpoint(
            progress_state,
            repo=repo,
            requested_since_iso=since_iso,
            requested_until_iso=until_iso,
            resume_after_cursor=cursor,
            saved_pr_count=_count_prs_on_disk(prs_path),
            updated_at_iso=datetime.now(timezone.utc).isoformat(),
        )
        save_progress_state(progress_path, progress_state)
        overlap_note = " overlap-only" if unique_added == 0 and nodes else ""
        print(
            f"    [gap {since_iso[:10]}..{until_iso[:10]}] saved page: "
            f"{len(nodes)} nodes, +{unique_added} unique, {post_save_count} total{overlap_note}",
            flush=True,
        )

        if any_before_since:
            break
        if not page_info.get("hasNextPage"):
            break
        if not cursor:
            break

        consecutive_successes += 1
        if consecutive_successes >= 3 and current_page_size < GAP_FETCH_INITIAL_PAGE_SIZE:
            current_page_size = min(GAP_FETCH_INITIAL_PAGE_SIZE, current_page_size * 2)
            consecutive_successes = 0

    write_fetch_status(
        prs_path,
        repo=repo,
        requested_since_iso=since_iso,
        requested_until_iso=until_iso,
    )


def _fetch_worker(repo: str, prs_path_str: str,
                   since_iso: str | None = None, until_iso: str | None = None) -> None:
    """Run auto_fetch in a child process so we can kill it on timeout.

    Passes incremental_path to the GraphQL adapter so each page is saved
    to disk immediately. If killed mid-fetch, whatever pages completed
    are preserved on disk.

    When since_iso/until_iso are provided, fetches only that window
    (used by --incomplete to fill gaps instead of re-fetching everything).

    Module-level function so multiprocessing can pickle it.
    """
    try:
        if since_iso and until_iso:
            print(f"  [child] filling gap: {since_iso[:10]} to {until_iso[:10]}", flush=True)
            _fetch_gap_with_resume(repo, prs_path_str, since_iso, until_iso)
            return

        from delivery_gap_signals.sources import github_graphql
        github_graphql.fetch_changes(repo, lookback_days=365, incremental_path=prs_path_str)
    except Exception as e:
        # Even on error, partial data may have been saved to disk
        print(f"  [child] fetch error: {e}", flush=True)


def fetch_prs(repo: str, prs_path: Path, dry_run: bool = False,
              since_iso: str | None = None, until_iso: str | None = None) -> tuple[bool, str]:
    """Fetch PRs once via shared library. Returns (success, message).

    Tries auto_fetch in a child process with 5-min timeout.
    Falls back to gh pr list without search filter on failure.

    When since_iso/until_iso are provided, fetches only that window
    (used by --incomplete to fill gaps).
    """
    if dry_run:
        window = f" ({since_iso[:10]} to {until_iso[:10]})" if since_iso else ""
        msg = f"[dry-run] fetch_changes({repo}){window} -> {prs_path}"
        print(msg)
        return True, msg

    clear_fetch_status(prs_path)

    # Record PR count before fetch
    pre_count = 0
    if prs_path.exists():
        try:
            pre_count = len(json.loads(prs_path.read_text()))
            print(f"  Resuming from {pre_count} PRs on disk", flush=True)
        except Exception:
            pass
    else:
        print(f"  No existing data — starting fresh", flush=True)

    window_desc = f" (gap: {since_iso[:10]} to {until_iso[:10]})" if since_iso else " (365 days)"
    print(f"  Fetching PRs{window_desc}...", flush=True)
    try:
        import multiprocessing as _mp

        proc = _mp.Process(target=_fetch_worker, args=(repo, str(prs_path), since_iso, until_iso))
        proc.start()
        # 2 hour timeout: the GraphQL adapter retries rate limits indefinitely
        # (15 min waits), so we need a long timeout. Most repos finish in
        # minutes, but rate-limited repos may need multiple retry cycles.
        proc.join(timeout=7200)

        if proc.is_alive():
            print(f"  -> child still alive after 2 hours, killing", flush=True)
            proc.kill()
            proc.join(5)

        # Don't trust the queue — trust what's on disk.
        # _fetch_worker saves incrementally via incremental_path,
        # so even a killed/errored process leaves partial data.
        post_count = 0
        if prs_path.exists():
            try:
                post_count = len(json.loads(prs_path.read_text()))
            except Exception:
                pass

        if since_iso and until_iso:
            status = load_fetch_status(prs_path)
            if status and status.get("completed"):
                if post_count > pre_count:
                    gained = post_count - pre_count
                    print(f"  -> gap complete: {post_count} PRs on disk (+{gained} new)", flush=True)
                    return True, f"{post_count} PRs (gap complete, +{gained} new)"
                if post_count > 0:
                    print(f"  -> gap complete: {post_count} PRs on disk", flush=True)
                    return True, f"{post_count} PRs (gap complete)"
                print(f"  -> gap complete: no PRs on disk", flush=True)
                return True, "gap complete (0 PRs)"

            checkpoint_msg = "partial gap progress saved"
            if post_count > pre_count:
                gained = post_count - pre_count
                print(f"  -> {checkpoint_msg}: {post_count} PRs on disk (+{gained} new)", flush=True)
                return False, f"{checkpoint_msg} ({post_count} PRs on disk, +{gained} new)"
            if post_count > 0:
                print(f"  -> {checkpoint_msg}: {post_count} PRs on disk", flush=True)
                return False, f"{checkpoint_msg} ({post_count} PRs on disk)"
            print(f"  -> gap made no durable progress, trying fallback...", flush=True)
            return _fetch_prs_fallback(repo, prs_path)

        if post_count > pre_count:
            gained = post_count - pre_count
            print(f"  -> {post_count} PRs on disk (+{gained} new)", flush=True)
            return True, f"{post_count} PRs"
        elif post_count > 0:
            print(f"  -> {post_count} PRs on disk (no new)", flush=True)
            return True, f"{post_count} PRs (unchanged)"
        else:
            print(f"  -> 0 PRs, trying fallback...", flush=True)
            return _fetch_prs_fallback(repo, prs_path)

    except Exception as e:
        print(f"  -> fetch error: {e}, trying fallback...", flush=True)
        return _fetch_prs_fallback(repo, prs_path)


def _fetch_prs_fallback(repo: str, prs_path: Path) -> tuple[bool, str]:
    """Fallback fetcher: paginate gh pr list without --search filter.

    Fetches up to 1000 PRs, filters by date client-side.
    """
    from datetime import timedelta
    since = (datetime.now(timezone.utc) - timedelta(days=365)).isoformat()

    fields = (
        "number,title,body,author,mergedAt,createdAt,additions,deletions,"
        "files,reviews,mergeCommit"
    )
    all_prs = []
    # gh pr list without --search returns most-recent-first
    for batch_num in range(5):  # single-batch; see trailing break comment
        cmd = [
            "gh", "pr", "list", "--repo", repo,
            "--state", "merged", "--limit", "100",
            "--json", fields,
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        except subprocess.TimeoutExpired:
            break
        if result.returncode != 0:
            print(f"  -> fallback failed: {result.stderr[:100]}")
            return False, f"fallback failed: {result.stderr[:100]}"

        batch = json.loads(result.stdout)
        if not batch:
            break

        # Filter by merge date
        for pr in batch:
            merged_at = pr.get("mergedAt", "")
            if merged_at and merged_at >= since:
                if pr["number"] not in {p["number"] for p in all_prs}:
                    all_prs.append(pr)

        # If oldest in batch is before our window, we're done
        oldest = min((p.get("mergedAt", "") for p in batch), default="")
        if oldest and oldest < since:
            break
        # gh pr list doesn't support cursor-based pagination, so only a single
        # batch is retrievable. The enclosing for-loop is intentionally
        # single-iteration; it exists only for structural consistency with
        # paginated fetch patterns.
        break

    if not all_prs:
        print(f"  -> fallback also returned 0 PRs")
        return False, "0 PRs from both methods"

    # Convert to MergedChange format
    from delivery_gap_signals.sources.github import _parse_reviews, _parse_ci_status
    from delivery_gap_signals.models import MergedChange

    changes = []
    for pr in all_prs:
        merged_at = pr.get("mergedAt", "")
        if not merged_at:
            continue
        author = ""
        if isinstance(pr.get("author"), dict):
            author = pr["author"].get("login", "")
        files = [f.get("path", "") for f in pr.get("files", []) if f.get("path")]
        sha = (pr.get("mergeCommit") or {}).get("oid", "")
        created_at = None
        if pr.get("createdAt"):
            created_at = datetime.fromisoformat(pr["createdAt"].replace("Z", "+00:00"))

        changes.append(MergedChange.build(
            id=str(pr["number"]),
            source="github",
            repo=repo,
            title=pr.get("title", ""),
            body=pr.get("body", "") or "",
            author=author,
            merged_at=datetime.fromisoformat(merged_at.replace("Z", "+00:00")),
            created_at=created_at,
            files=files,
            additions=pr.get("additions", 0) or 0,
            deletions=pr.get("deletions", 0) or 0,
            reviews=_parse_reviews(pr),
            ci_status=_parse_ci_status(pr),
            merge_commit_sha=sha or None,
            pr_number=pr["number"],
        ))

    data = [c.to_dict() for c in changes]
    data = _merge_with_existing(data, prs_path)
    tmp = prs_path.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(data, indent=2, default=str))
    tmp.replace(prs_path)
    print(f"  -> {len(data)} PRs (fallback, merged with existing)")
    return True, f"{len(data)} PRs (fallback)"


def _run_scorers(slug: str, dry_run: bool = False) -> None:
    """Run combined LLM scorer (quality + formality in one call per PR).

    Has built-in resume (skip already-scored PRs, retry errors).
    Failures are caught and logged — they don't block the pipeline.
    """
    if dry_run:
        print(f"  [dry-run] would score specs and formality for {slug}")
        return

    try:
        from score_all import score_repo
        score_repo(slug)
    except Exception as e:
        print(f"  Scoring failed: {e}", flush=True)


def run_tool(
    tool: str,
    subcmd: str,
    prs_path: Path,
    json_path: Path,
    dry_run: bool = False,
) -> tuple[bool, str]:
    """Run a single tool with --from-prs. Returns (success, message)."""
    cmd = [tool, subcmd, "--from-prs", str(prs_path), "--json", str(json_path)]

    if dry_run:
        msg = f"[dry-run] {' '.join(cmd)}"
        print(msg)
        return True, msg

    print(f"  Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=600,  # 10 minutes per tool per repo
        )
        if result.returncode == 0:
            print(f"  -> OK")
            return True, "success"
        else:
            stderr = result.stderr.strip()[:200] if result.stderr else "(no stderr)"
            print(f"  -> FAILED (exit {result.returncode}): {stderr}")
            return False, f"exit {result.returncode}: {stderr}"
    except subprocess.TimeoutExpired:
        print(f"  -> TIMEOUT (600s)")
        return False, "timeout after 600s"
    except FileNotFoundError:
        print(f"  -> TOOL NOT FOUND: {tool}")
        return False, f"tool not found: {tool}"
    except Exception as e:
        print(f"  -> ERROR: {e}")
        return False, str(e)


def run_all(repos: list[dict[str, str]], dry_run: bool = False,
            fetch_only: bool = False, score_only: bool = False) -> dict:
    """Fetch PRs, run tools, and score — or subsets via flags.

    --fetch-only: fetch + CatchRate, skip scoring (fast)
    --score-only: skip fetching, just score existing data
    Resilient: every repo is wrapped in try/except. No single repo failure
    kills the batch. Results are saved incrementally after each repo.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    started_at = datetime.now(timezone.utc).isoformat()
    manifest_path = DATA_DIR / "manifest.json"
    progress_path = progress_state_path(DATA_DIR)
    progress_state = load_progress_state(progress_path) if not dry_run else {"version": 1, "repos": {}}
    target_repos = {entry["repo"] for entry in repos}

    # Load existing results to support resume — keyed by repo to avoid duplicates
    results_by_repo: dict[str, dict] = {}
    if not dry_run and manifest_path.exists():
        try:
            existing = json.loads(manifest_path.read_text())
            for r in existing.get("repos", []):
                if r.get("repo") in target_repos:
                    results_by_repo[r["repo"]] = r
        except Exception:
            pass

    total = len(repos)

    for i, entry in enumerate(repos, 1):
        repo = entry["repo"]
        slug = _slug(repo)

        prs_path = DATA_DIR / f"prs-{slug}.json"

        print(f"\n[{i}/{total}] {repo} ({entry['lang']}, tier {entry['tier']})", flush=True)
        catchrate_path = DATA_DIR / f"catchrate-{slug}.json"

        try:
            # Score-only mode: skip fetching and tools
            if score_only:
                if not prs_path.exists():
                    print(f"  No data on disk, skipping", flush=True)
                    continue
                _run_scorers(slug, dry_run=dry_run)
                _save_manifest(manifest_path, started_at, total, results_by_repo, dry_run)
                if not dry_run:
                    _auto_commit(repo, slug)
                    _print_progress(i, total)
                continue

            # Fetch once (with optional per-repo gap window)
            since_iso = entry.get("_since_iso")
            until_iso = entry.get("_until_iso")
            fetch_ok, fetch_msg = fetch_prs(repo, prs_path, dry_run=dry_run,
                                            since_iso=since_iso, until_iso=until_iso)
            if not fetch_ok:
                if since_iso and until_iso:
                    clear_fetch_status(prs_path)
                results_by_repo[repo] = {
                    "repo": repo,
                    "language": entry["lang"],
                    "tier": entry["tier"],
                    "fetch": {"success": False, "message": fetch_msg},
                    "catchrate": {"success": False, "message": "skipped (fetch failed)"},
                }
                _save_manifest(manifest_path, started_at, total, results_by_repo, dry_run)
                continue

            if not dry_run and since_iso and until_iso:
                status = load_fetch_status(prs_path)
                if status and status.get("completed"):
                    mark_gap_complete(
                        progress_state,
                        repo=repo,
                        requested_since_iso=since_iso,
                        requested_until_iso=until_iso,
                        observed_oldest_iso=oldest_pr_iso(prs_path),
                        completed_at_iso=status.get("completed_at_iso") or datetime.now(timezone.utc).isoformat(),
                    )
                    save_progress_state(progress_path, progress_state)
                clear_fetch_status(prs_path)

            # Run workflow analysis
            try:
                from delivery_gap_signals.sources.file import fetch_changes as load_prs
                from delivery_gap_signals.analysis import analyze_workflow, print_workflow_report
                loaded = load_prs(str(prs_path))
                profile = analyze_workflow(loaded)
                workflow_path = DATA_DIR / f"workflow-{slug}.json"
                workflow_path.write_text(json.dumps(profile.to_dict(), indent=2, default=str))
                print(f"  Workflow: {profile.current.workflow_type} ({profile.current.mechanisms.sample_size} PRs)")
                if profile.transitions:
                    for t in profile.transitions:
                        print(f"  ⚠ Transition: {t.description}")
            except Exception as e:
                print(f"  Workflow analysis failed: {e}")

            # Run catchrate from cached PRs
            catchrate_ok, catchrate_msg = run_tool(
                "catchrate", "check", prs_path, catchrate_path, dry_run=dry_run
            )

            # Score specs and formality (unless --fetch-only)
            if not fetch_only:
                _run_scorers(slug, dry_run=dry_run)

            results_by_repo[repo] = {
                "repo": repo,
                "language": entry["lang"],
                "tier": entry["tier"],
                "fetch": {"success": True, "message": fetch_msg},
                "catchrate": {"success": catchrate_ok, "message": catchrate_msg, "file": str(catchrate_path)},
            }

        except Exception as e:
            print(f"  -> UNEXPECTED ERROR (repo skipped): {e}", flush=True)
            results_by_repo[repo] = {
                "repo": repo,
                "language": entry["lang"],
                "tier": entry["tier"],
                "fetch": {"success": False, "message": f"unexpected: {e}"},
                "catchrate": {"success": False, "message": "skipped"},
            }

        # Save after every repo — never lose progress
        _save_manifest(manifest_path, started_at, total, results_by_repo, dry_run)

        # Auto-commit and show progress
        if not dry_run:
            _auto_commit(repo, slug)
            _print_progress(i, total)

    # Final summary
    all_results = list(results_by_repo.values())
    catchrate_ok = sum(1 for r in all_results if r["catchrate"]["success"])
    print(f"\nDone. CATCHRATE: {catchrate_ok}/{total} succeeded.")

    return {"repos": all_results}


def _auto_commit(repo: str, slug: str) -> None:
    """Git add and commit data files for this repo. Never fails the pipeline."""
    try:
        data_files = [
            f"data/prs-{slug}.json",
            f"data/catchrate-{slug}.json",
            f"data/workflow-{slug}.json",
            f"data/spec-quality-{slug}.json",
            f"data/engagement-{slug}.json",
            f"data/manifest.json",
        ]
        existing = [f for f in data_files if (STUDY_DIR / f).exists()]
        progress_file = "data/fetch-progress.json"
        if (STUDY_DIR / progress_file).exists():
            existing.append(progress_file)
        if not existing:
            return
        subprocess.run(
            ["git", "add"] + existing,
            cwd=str(STUDY_DIR), capture_output=True, timeout=10,
        )
        subprocess.run(
            ["git", "commit", "-m", f"data: {repo}", "--no-verify"],
            cwd=str(STUDY_DIR.parent.parent),  # repo root
            capture_output=True, timeout=10,
        )
        print(f"  [committed]", flush=True)
    except Exception as e:
        print(f"  [commit skipped: {e}]", flush=True)


def _print_progress(i: int, total: int) -> None:
    """Print summary of data on disk."""
    total_prs = 0
    repos_done = 0
    for f in DATA_DIR.glob("prs-*.json"):
        try:
            with open(f) as fh:
                n = len(json.load(fh))
            total_prs += n
            repos_done += 1
        except Exception:
            pass
    print(f"\n  === Progress: {i}/{total} repos processed, "
          f"{repos_done} with data, {total_prs} total PRs on disk ===\n", flush=True)


def _save_manifest(
    path: Path, started_at: str, total: int,
    results_by_repo: dict[str, dict], dry_run: bool,
) -> None:
    """Save manifest incrementally. Keyed by repo to avoid duplicates."""
    if dry_run:
        return
    all_results = list(results_by_repo.values())
    manifest = {
        "started_at": started_at,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "total_repos": total,
        "catchrate_success": sum(1 for r in all_results if r["catchrate"]["success"]),
        "repos": all_results,
    }
    tmp = path.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    tmp.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run CATCHRATE against public GitHub repos"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print commands without executing",
    )
    parser.add_argument(
        "--repo",
        help="Run a single repo (e.g., cli/cli) instead of all",
    )
    parser.add_argument(
        "--fetch-only",
        action="store_true",
        help="Fetch + CatchRate only, skip LLM scoring",
    )
    parser.add_argument(
        "--score-only",
        action="store_true",
        help="Score existing data only, skip fetching",
    )
    args = parser.parse_args()

    if args.repo:
        # Find repo in list or allow arbitrary
        matching = [e for e in REPOS if e["repo"] == args.repo]
        if matching:
            repos = matching
        else:
            print(f"Repo {args.repo} not in study list. Running it anyway.")
            repos = [{"repo": args.repo, "lang": "unknown", "tier": "?"}]
    else:
        repos = REPOS

    run_all(repos, dry_run=args.dry_run,
            fetch_only=args.fetch_only, score_only=args.score_only)


if __name__ == "__main__":
    main()
