"""Source adapters for fetching merged changes from various platforms.

Each adapter exports a fetch_changes() function returning list[MergedChange].
"""

import sys
from pathlib import Path


def _github_with_rest_fallback(repo: str, lookback_days: int, limit: int):
    """Fetch PRs with a reliable fallback chain.

    Order:
    1. Pure GraphQL (cursor-paginated, adaptive page sizing) — best for
       large lookback windows. Handles 504s by halving page size.
    2. REST (paginated by most-recently-updated) — slower but very reliable.
    3. gh pr list (no pagination) — last resort, capped at one page.

    Each adapter is tried in order. If one fails or returns 0, the next
    is attempted. This ensures we get the maximum data available.
    """
    # 1. Pure GraphQL — cursor-paginated, handles large windows
    try:
        from . import github_graphql
        changes = github_graphql.fetch_changes(repo, lookback_days, limit=limit)
        if changes:
            return changes
        print(f"  GraphQL returned 0 PRs for {repo}, trying REST...", file=sys.stderr)
    except RuntimeError as exc:
        print(f"  GraphQL failed for {repo}: {str(exc)[:80]}...", file=sys.stderr)

    # 2. REST — paginated, slower but reliable
    try:
        from . import github_rest
        changes = github_rest.fetch_changes(repo, lookback_days, limit=limit)
        if changes:
            return changes
        print(f"  REST returned 0 PRs for {repo}, trying gh pr list...", file=sys.stderr)
    except RuntimeError as exc:
        print(f"  REST failed for {repo}: {str(exc)[:80]}...", file=sys.stderr)

    # 3. gh pr list — last resort, no real pagination
    from . import github
    return github.fetch_changes(repo, lookback_days, limit=limit)


def auto_fetch(
    repo: str,
    lookback_days: int = 90,
    *,
    limit: int = 500,
    source: str | None = None,
):
    """Detect the right adapter based on repo format or explicit source.

    source options: "github" (default for owner/repo), "graphql", "git", "file",
                    "rest_only"

    When source is "github" (or auto-detected as owner/repo), tries GraphQL
    first and automatically falls back to REST on 502/504 gateway errors.
    """
    # Explicit source override
    if source == "graphql":
        from . import github_graphql
        return github_graphql.fetch_changes(repo, lookback_days, limit=limit)
    elif source == "rest_only":
        from . import github_rest
        return github_rest.fetch_changes(repo, lookback_days, limit=limit)
    elif source == "rest" or source == "github":
        return _github_with_rest_fallback(repo, lookback_days, limit)
    elif source == "git":
        from . import git
        return git.fetch_changes(repo, lookback_days, limit=limit)
    elif source == "file":
        from . import file
        return file.fetch_changes(repo)

    # Auto-detect
    if Path(repo).is_file():
        from . import file
        return file.fetch_changes(repo)
    elif Path(repo).is_dir():
        from . import git
        return git.fetch_changes(repo, lookback_days, limit=limit)
    elif "/" in repo:
        return _github_with_rest_fallback(repo, lookback_days, limit)
    else:
        raise ValueError(f"Cannot determine source for: {repo!r}")
