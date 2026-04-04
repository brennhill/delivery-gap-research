"""Fetch PR data from GitHub API via gh CLI subprocess calls."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from tools.catchrate.log import warn as _warn
from tools.catchrate.models import CheckRunDict, CommitDict, ReviewDict

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_RETRY_DELAY = 2  # seconds between retries on 5xx
_MAX_PER_PAGE = 100
_MAX_WORKERS = 8


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class GHError(Exception):
    """Raised for any gh-related error that should stop the run."""

    def __init__(self, tag: str, message: str) -> None:
        self.tag = tag
        self.message = message
        super().__init__(message)

    def __str__(self) -> str:
        return f"[{self.tag}] {self.message}"


class RateLimitError(GHError):
    """Raised when rate limit is hit — may carry partial results."""

    def __init__(
        self,
        message: str,
        reset_time: str = "",
        fetched: int = 0,
        total: int = 0,
        partial_results: list | None = None,
    ) -> None:
        super().__init__("rate-limited", message)
        self.reset_time = reset_time
        self.fetched = fetched
        self.total = total
        self.partial_results = partial_results if partial_results is not None else []


# ---------------------------------------------------------------------------
# Data containers
# ---------------------------------------------------------------------------


@dataclass
class PRData:
    number: int
    title: str
    body: str
    state: str  # "closed" for merged PRs fetched this way
    merged: bool
    merged_at: str | None
    created_at: str
    closed_at: str | None
    author: str
    author_type: str  # "User", "Bot", etc.
    is_draft: bool
    reviews: list[ReviewDict] = field(default_factory=list)
    check_runs: list[CheckRunDict] = field(default_factory=list)
    commits: list[CommitDict] = field(default_factory=list)
    files: list[str] = field(default_factory=list)
    head_sha: str = ""
    additions: int = 0
    deletions: int = 0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _check_gh_installed() -> None:
    if shutil.which("gh") is None:
        raise GHError(
            "gh-missing",
            "GitHub CLI (gh) is not installed or not found on $PATH.\n"
            "Install it: https://cli.github.com/\n"
            "Verify with: gh --version",
        )


def _run_gh(args: list[str]) -> subprocess.CompletedProcess:
    """Run a gh command and return the CompletedProcess."""
    cmd = ["gh", *args]
    try:
        result = subprocess.run(  # noqa: S603
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except FileNotFoundError as err:
        raise GHError(
            "gh-missing",
            "GitHub CLI (gh) is not installed or not found on $PATH.\n"
            "Install it: https://cli.github.com/\n"
            "Verify with: gh --version",
        ) from err
    except subprocess.TimeoutExpired as err:
        raise GHError(
            "network-error",
            f"GitHub API request timed out after 60s\n"
            f"URL: {' '.join(args)}\n"
            "Check your network connection and try again.",
        ) from err
    return result


_SENSITIVE_KEYWORDS = re.compile(
    r"token|authorization|bearer|credential|ghp_|gho_|ghs_|github_pat_",
    re.IGNORECASE,
)


def _sanitize_stderr(stderr: str) -> str:
    """Filter out lines that may contain token fragments or credentials."""
    return "\n".join(line for line in stderr.splitlines() if not _SENSITIVE_KEYWORDS.search(line))


def _classify_gh_error(stderr: str, method: str, endpoint: str, repo: str | None = None) -> GHError:
    """Classify a gh CLI error by parsing stderr. Returns the appropriate exception."""
    if "auth" in stderr.lower() or "not logged" in stderr.lower():
        return GHError(
            "gh-auth",
            "GitHub CLI is not authenticated. No valid token found.\n"
            "Run: gh auth login\n"
            "Then retry: catchrate check --repo owner/repo",
        )
    if "403" in stderr or "HTTP 403" in stderr:
        if "rate limit" in stderr.lower():
            reset_time = _extract_reset_time(stderr)
            return RateLimitError(
                f"GitHub API rate limit exceeded. Resets at {reset_time}.",
                reset_time=reset_time,
            )
        return GHError(
            "gh-permissions",
            f"GitHub token lacks required permissions. "
            f"Got HTTP 403 on: {method} {endpoint}\n"
            "Required scopes: repo (read access to PRs, reviews, "
            "check runs, and commits)\n"
            "Check your scopes: gh auth status\n"
            "Re-authenticate with: gh auth login --scopes repo",
        )
    if "404" in stderr or "Not Found" in stderr:
        repo_name = repo or _extract_repo_from_endpoint(endpoint)
        return GHError(
            "repo-not-found",
            f'Repository "{repo_name}" not found or not accessible '
            "with current credentials.\n"
            f"Verify the repo exists and your gh token has access: "
            f"gh repo view {repo_name}",
        )
    if re.search(r"\b5\d{2}\b", stderr):
        status_match = re.search(r"\b5\d{2}\b", stderr)
        status_code = status_match.group(0) if status_match else "5xx"
        return GHError(
            "github-server-error",
            f"GitHub API returned {status_code} on: {method} {endpoint}\n"
            "GitHub may be experiencing issues. "
            "Check https://www.githubstatus.com/ and try again later.",
        )
    return GHError(
        "network-error",
        f"GitHub API request failed: {stderr}\n"
        f"URL: {endpoint}\n"
        "Check your network connection and try again.",
    )


def _gh_api(
    endpoint: str,
    method: str = "GET",
    repo: str | None = None,
    paginate: bool = False,
) -> Any:
    """Call gh api and return parsed JSON."""
    args = ["api", endpoint, "--method", method]
    if paginate:
        args.append("--paginate")

    result = _run_gh(args)

    if result.returncode != 0:
        stderr = _sanitize_stderr(result.stderr.strip())
        err = _classify_gh_error(stderr, method, endpoint, repo)

        # 5xx: retry once before raising
        if err.tag == "github-server-error":
            time.sleep(_RETRY_DELAY)
            retry = _run_gh(args)
            if retry.returncode != 0:
                raise _classify_gh_error(
                    _sanitize_stderr(retry.stderr.strip()),
                    method,
                    endpoint,
                    repo,
                )
            result = retry
        else:
            raise err

    stdout = result.stdout.strip()
    if not stdout:
        return [] if paginate else {}

    # gh --paginate may emit multiple JSON arrays concatenated — merge them
    if paginate:
        return _parse_paginated_json(stdout)

    try:
        return json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise GHError(
            "network-error",
            f"GitHub API returned invalid JSON: {exc}\nURL: {endpoint}",
        ) from exc


def _parse_paginated_json(raw: str) -> list:
    """Parse potentially concatenated JSON arrays from gh --paginate."""
    # gh --paginate can output: [{...}]\n[{...}]\n...
    # or just [{...}]
    results: list = []
    decoder = json.JSONDecoder()
    pos = 0
    raw = raw.strip()
    while pos < len(raw):
        # skip whitespace
        while pos < len(raw) and raw[pos] in " \t\n\r":
            pos += 1
        if pos >= len(raw):
            break
        try:
            obj, end = decoder.raw_decode(raw, pos)
            if isinstance(obj, list):
                results.extend(obj)
            else:
                results.append(obj)
            pos = end
        except json.JSONDecodeError:
            if pos < len(raw):
                _warn("Partial JSON response from GitHub API — some data may be missing.")
            break
    return results


def _extract_reset_time(stderr: str) -> str:
    """Try to extract rate limit reset time from error text."""
    # Look for epoch timestamp
    match = re.search(r"reset[^\d]*(\d{10,})", stderr, re.IGNORECASE)
    if match:
        try:
            ts = int(match.group(1))
            dt = datetime.fromtimestamp(ts, tz=timezone.utc)
            return dt.strftime("%Y-%m-%d %H:%M:%S UTC")
        except (ValueError, OSError):
            pass
    return "unknown"


def _extract_repo_from_endpoint(endpoint: str) -> str:
    match = re.search(r"/repos/([^/]+/[^/]+)", endpoint)
    return match.group(1) if match else "unknown"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def verify_gh() -> None:
    """Check that gh is installed and authenticated."""
    _check_gh_installed()
    # Quick auth check
    result = _run_gh(["auth", "status"])
    if result.returncode != 0:
        raise GHError(
            "gh-auth",
            "GitHub CLI is not authenticated. No valid token found.\n"
            "Run: gh auth login\n"
            "Then retry: catchrate check --repo owner/repo",
        )


def verify_repo(repo: str) -> None:
    """Verify the repository is accessible."""
    _gh_api(f"/repos/{repo}")


def fetch_merged_prs(repo: str, since: str) -> list[dict]:
    """Fetch merged PRs since the given ISO date.

    Uses ``gh pr list`` with cursor-based pagination by narrowing the
    search window on each batch.  This avoids the 1 000-result cap of
    the ``/search/issues`` endpoint.
    """
    return _gh_pr_list_paginate(
        repo,
        state="merged",
        date_qualifier="merged",
        since=since,
    )


def fetch_closed_unmerged_prs(repo: str, since: str) -> list[dict]:
    """Fetch PRs closed without merging since the given ISO date.

    Uses ``gh pr list`` with cursor-based pagination, same approach as
    :func:`fetch_merged_prs`.  Results are shaped to match the dict
    format that :func:`catchrate.discard.compute_discard_rate` expects
    (``number``, ``user``, ``pull_request``).
    """
    return _gh_pr_list_paginate(
        repo,
        state="closed",
        date_qualifier="closed",
        since=since,
        unmerged_only=True,
    )


_MAX_PAGES = 50  # safety valve: 100 * 50 = 5 000 PRs max


def _gh_pr_list_paginate(
    repo: str,
    *,
    state: str,
    date_qualifier: str,
    since: str,
    unmerged_only: bool = False,
) -> list[dict]:
    """Page through ``gh pr list`` by narrowing the date window.

    Returns dicts whose shape matches what the rest of catchrate expects:
      - merged PRs: ``{"number": int, ...}``
      - closed-unmerged PRs: ``{"number": int, "user": {...}, "pull_request": {...}}``
    """
    # date_str is YYYY-MM-DD (or full ISO) used in the search qualifier
    date_str = since[:10]  # normalise to YYYY-MM-DD

    # Fields we ask gh to return — kept minimal for speed
    fields = "number,author,mergedAt,closedAt,isDraft"

    all_items: list[dict] = []
    seen_numbers: set[int] = set()

    for _page in range(_MAX_PAGES):
        search_q = f"{date_qualifier}:>={date_str}"
        if unmerged_only:
            # gh pr list --state closed already filters to closed PRs;
            # add NOT merged qualifier so we only get unmerged ones.
            search_q += " -is:merged"

        result = _run_gh(
            [
                "pr",
                "list",
                "--repo",
                repo,
                "--state",
                state,
                "--search",
                search_q,
                "--limit",
                str(_MAX_PER_PAGE),
                "--json",
                fields,
            ]
        )

        if result.returncode != 0:
            stderr = _sanitize_stderr(result.stderr.strip())
            raise _classify_gh_error(stderr, "GET", f"pr list --repo {repo}", repo)

        stdout = result.stdout.strip()
        if not stdout:
            break

        try:
            batch: list[dict] = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise GHError(
                "network-error",
                f"gh pr list returned invalid JSON: {exc}",
            ) from exc

        if not batch:
            break

        # Deduplicate (date-window overlap can return the same PR twice)
        new_items = [it for it in batch if it.get("number") not in seen_numbers]
        seen_numbers.update(it["number"] for it in batch)

        # Normalise each item into the shape the rest of catchrate expects
        for item in new_items:
            all_items.append(_normalise_pr_list_item(item))

        if len(batch) < _MAX_PER_PAGE:
            break  # last page

        # Narrow the window: find the oldest date in this batch and restart
        date_key = "mergedAt" if date_qualifier == "merged" else "closedAt"
        dates = [it.get(date_key, "") for it in batch if it.get(date_key)]
        if not dates:
            break
        oldest = min(dates)
        date_str = oldest[:10]  # YYYY-MM-DD

    return all_items


def _normalise_pr_list_item(item: dict) -> dict:
    """Convert a ``gh pr list --json`` item into the dict shape callers expect.

    ``fetch_merged_prs`` callers only read ``number``.
    ``compute_discard_rate`` reads ``number``, ``user.login``, ``user.type``,
    and ``pull_request.merged_at``.
    """
    author = item.get("author", {}) or {}
    login = author.get("login", "") if isinstance(author, dict) else str(author)

    return {
        "number": item.get("number", 0),
        # Compat with compute_discard_rate
        "user": {
            "login": login,
            "type": "User",  # gh pr list does not expose user type
        },
        "pull_request": {
            "merged_at": item.get("mergedAt"),
        },
    }


def fetch_pr_details(
    repo: str, pr_numbers: list[int], verbose: bool = False, on_progress: Any = None
) -> list[PRData]:
    """Fetch full details for a list of PR numbers in parallel."""
    results: list[PRData] = []
    results_lock = threading.Lock()
    errors: list[str] = []

    def _fetch_one(pr_num: int) -> PRData | None:
        try:
            return _fetch_single_pr(repo, pr_num, verbose=verbose)
        except RateLimitError:
            raise
        except GHError as exc:
            with results_lock:
                errors.append(str(exc))
            _warn(f"Skipping PR #{pr_num}: unexpected API response — {exc.message}")
            return None
        except Exception as exc:
            with results_lock:
                errors.append(str(exc))
            _warn(f"Skipping PR #{pr_num}: unexpected API response — {exc}")
            return None

    fetched_count = 0
    processed_count = 0
    total = len(pr_numbers)

    with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as executor:
        future_to_num = {executor.submit(_fetch_one, num): num for num in pr_numbers}
        for future in as_completed(future_to_num):
            try:
                pr_data = future.result()
                with results_lock:
                    if pr_data is not None:
                        results.append(pr_data)
                        fetched_count += 1
                    processed_count += 1
                if on_progress:
                    on_progress(processed_count, total)
            except RateLimitError as exc:
                with results_lock:
                    exc.fetched = fetched_count
                    exc.total = total
                    exc.partial_results = list(results)
                # Cancel remaining futures
                for f in future_to_num:
                    f.cancel()
                # Return partial results via exception
                raise

    if errors:
        _warn(
            f"{len(errors)} PR(s) skipped due to unexpected API responses. "
            "Run with --verbose for details."
        )

    return results


_GRAPHQL_QUERY = """
query($owner: String!, $repo: String!, $number: Int!) {
  repository(owner: $owner, name: $repo) {
    pullRequest(number: $number) {
      title body state merged mergedAt createdAt closedAt isDraft
      additions deletions
      author { login ...on User { __typename } ...on Bot { __typename } }
      headRefOid
      reviews(first: 100) {
        nodes {
          state submittedAt
          author { login ...on User { __typename } ...on Bot { __typename } }
        }
        pageInfo { hasNextPage }
      }
      commits(first: 100) {
        nodes { commit { oid message authoredDate committedDate } }
        pageInfo { hasNextPage }
      }
      files(first: 100) {
        nodes { path }
        pageInfo { hasNextPage }
      }
      latestReviews(first: 100) {
        nodes { state }
      }
    }
  }
}
"""


def _fetch_single_pr(repo: str, pr_num: int, verbose: bool = False) -> PRData:
    """Fetch all data for a single PR.

    Uses GraphQL (1 query) + REST (1 check-runs call) = 2 calls per PR.
    Falls back to full REST (5 calls) if GraphQL fails.
    """
    owner, name = repo.split("/", 1)

    try:
        return _fetch_single_pr_graphql(owner, name, pr_num)
    except (GHError, KeyError, TypeError, json.JSONDecodeError):
        # Fall back to REST if GraphQL fails
        if verbose:
            _warn(f"GraphQL failed for PR #{pr_num}, falling back to REST")
        return _fetch_single_pr_rest(repo, pr_num)


def _fetch_single_pr_graphql(owner: str, name: str, pr_num: int) -> PRData:
    """Fetch PR data via a single GraphQL query."""
    variables = json.dumps({"owner": owner, "repo": name, "number": pr_num})
    result = _run_gh(
        [
            "api",
            "graphql",
            "-f",
            f"query={_GRAPHQL_QUERY}",
            "-f",
            f"variables={variables}",
        ]
    )

    if result.returncode != 0:
        stderr = _sanitize_stderr(result.stderr.strip())
        raise GHError("network-error", f"GraphQL query failed for PR #{pr_num}: {stderr}")

    data = json.loads(result.stdout)

    # Check for GraphQL errors — partial responses should fall back to REST
    if "errors" in data:
        error_msgs = [e.get("message", "") for e in data["errors"] if isinstance(e, dict)]
        raise GHError(
            "network-error",
            f"GraphQL returned errors for PR #{pr_num}: {'; '.join(error_msgs)}",
        )
    if data.get("data") is None:
        raise GHError("network-error", f"GraphQL returned null data for PR #{pr_num}")

    pr = data["data"]["repository"]["pullRequest"]
    if pr is None:
        raise GHError("network-error", f"PR #{pr_num} not found via GraphQL")

    # Parse author
    author_node = pr.get("author") or {}
    author_login = author_node.get("login", "")
    author_type = author_node.get("__typename", "User")

    # Parse reviews into REST-compatible format
    reviews = []
    for node in (pr.get("reviews", {}) or {}).get("nodes", []):
        if node is None:
            continue
        author = node.get("author") or {}
        reviews.append(
            {
                "state": node.get("state", ""),
                "submitted_at": node.get("submittedAt", ""),
                "user": {
                    "login": author.get("login", ""),
                    "type": author.get("__typename", "User"),
                },
            }
        )

    # Parse commits into REST-compatible format
    commits = []
    for node in (pr.get("commits", {}) or {}).get("nodes", []):
        if node is None:
            continue
        commit = node.get("commit", {})
        commits.append(
            {
                "sha": commit.get("oid", ""),
                "commit": {
                    "message": commit.get("message", ""),
                    "author": {"date": commit.get("authoredDate", "")},
                    "committer": {"date": commit.get("committedDate", "")},
                },
            }
        )

    # Parse files
    file_names = []
    for node in (pr.get("files", {}) or {}).get("nodes", []):
        if node is not None and node.get("path"):
            file_names.append(node["path"])

    # If any connection was truncated at 100 items, fall back to REST
    # for those connections to avoid silent data loss.
    repo_slug = f"{owner}/{name}"
    for conn_name in ("reviews", "commits", "files"):
        conn = pr.get(conn_name, {}) or {}
        page_info = conn.get("pageInfo", {}) or {}
        if page_info.get("hasNextPage"):
            if conn_name == "reviews":
                rest_reviews = _gh_api(f"/repos/{repo_slug}/pulls/{pr_num}/reviews", paginate=True)
                if isinstance(rest_reviews, list):
                    reviews = rest_reviews
            elif conn_name == "commits":
                rest_commits = _gh_api(f"/repos/{repo_slug}/pulls/{pr_num}/commits", paginate=True)
                if isinstance(rest_commits, list):
                    commits = rest_commits
            elif conn_name == "files":
                rest_files = _gh_api(f"/repos/{repo_slug}/pulls/{pr_num}/files", paginate=True)
                if isinstance(rest_files, list):
                    file_names = [f.get("filename", "") for f in rest_files if isinstance(f, dict)]

    # Check runs are not available via PR GraphQL — use empty list.
    # The REST check-runs endpoint is the only way to get these.
    # For now, fall back to a separate REST call for check runs only.
    head_sha = pr.get("headRefOid", "")
    check_runs_data: list[dict] = []
    if head_sha:
        try:
            cr_resp = _gh_api(f"/repos/{owner}/{name}/commits/{head_sha}/check-runs")
            if isinstance(cr_resp, dict):
                check_runs_data = cr_resp.get("check_runs", [])
        except GHError:
            pass  # Check runs unavailable — classify as no_checks

    merged_at = pr.get("mergedAt")

    return PRData(
        number=pr_num,
        title=pr.get("title", ""),
        body=pr.get("body", "") or "",
        state=pr.get("state", "").lower(),
        merged=pr.get("merged", False) or (merged_at is not None),
        merged_at=merged_at,
        created_at=pr.get("createdAt", ""),
        closed_at=pr.get("closedAt"),
        author=author_login,
        author_type=author_type,
        is_draft=pr.get("isDraft", False),
        reviews=reviews,  # type: ignore[arg-type]  # GraphQL dicts
        check_runs=check_runs_data,  # type: ignore[arg-type]
        commits=commits,  # type: ignore[arg-type]
        files=file_names,
        head_sha=head_sha,
        additions=pr.get("additions", 0) or 0,
        deletions=pr.get("deletions", 0) or 0,
    )


def _fetch_single_pr_rest(repo: str, pr_num: int) -> PRData:
    """Fetch all data for a single PR using REST API (fallback)."""
    pr = _gh_api(f"/repos/{repo}/pulls/{pr_num}")
    head_sha = pr.get("head", {}).get("sha", "")

    reviews = _gh_api(f"/repos/{repo}/pulls/{pr_num}/reviews", paginate=True)
    if not isinstance(reviews, list):
        reviews = []

    check_runs_data: list[dict] = []
    if head_sha:
        cr_resp = _gh_api(f"/repos/{repo}/commits/{head_sha}/check-runs")
        if isinstance(cr_resp, dict):
            check_runs_data = cr_resp.get("check_runs", [])

    commits = _gh_api(f"/repos/{repo}/pulls/{pr_num}/commits", paginate=True)
    if not isinstance(commits, list):
        commits = []

    files_resp = _gh_api(f"/repos/{repo}/pulls/{pr_num}/files", paginate=True)
    if not isinstance(files_resp, list):
        files_resp = []
    file_names = [f.get("filename", "") for f in files_resp if isinstance(f, dict)]

    user = pr.get("user", {}) or {}
    merged_at = pr.get("merged_at")

    return PRData(
        number=pr_num,
        title=pr.get("title", ""),
        body=pr.get("body", "") or "",
        state=pr.get("state", ""),
        merged=pr.get("merged", False) or (merged_at is not None),
        merged_at=merged_at,
        created_at=pr.get("created_at", ""),
        closed_at=pr.get("closed_at"),
        author=user.get("login", ""),
        author_type=user.get("type", "User"),
        is_draft=pr.get("draft", False),
        reviews=reviews,  # type: ignore[arg-type]  # REST raw dicts
        check_runs=check_runs_data,  # type: ignore[arg-type]
        commits=commits,  # type: ignore[arg-type]
        files=file_names,
        head_sha=head_sha,
        additions=pr.get("additions", 0) or 0,
        deletions=pr.get("deletions", 0) or 0,
    )
