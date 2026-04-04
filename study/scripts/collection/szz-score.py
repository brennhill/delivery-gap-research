#!/usr/bin/env python3
"""
SZZ Analysis: Trace bug-introducing commits across 43 repositories.

Uses the SZZ algorithm (Sliwerski, Zimmermann, Zeller 2005) via PyDriller
to identify which PRs introduced bugs that were later fixed.

This is the gold-standard method in empirical software engineering for
linking fixes to their root causes. It replaces heuristic follow-up
PR matching with actual git blame tracing.

The algorithm:
    1. Identify "fix" PRs by title keywords
    2. For each fix, find the merge commit in the local clone
    3. Diff the merge commit to see which lines were changed
    4. Run git blame on the PARENT version of those lines
    5. The blamed commit is the candidate "bug-introducing" commit
    6. Map bug-introducing commits back to PRs via merge_commit_sha
    7. Score each PR: was it ever identified as bug-introducing?

Prerequisites:
    pip install pydriller pandas scipy

    Repos must be cloned locally. The script will clone them if not present.

In addition to SZZ, computes all 14 Kamei et al. (2013) JIT defect
prediction features for every PR. These features measure diffusion,
size, purpose, history, and developer experience -- the standard
feature set for predicting whether a commit will introduce a defect.

Usage:
    python3 szz-score.py --repos-dir /path/to/cloned/repos
    python3 szz-score.py --repos-dir /path/to/cloned/repos --clone
    python3 szz-score.py --repos-dir /path/to/cloned/repos --repo apache/kafka  # single repo
    python3 szz-score.py --repos-dir /path/to/cloned/repos --jit-only           # JIT features only
    python3 szz-score.py --repos-dir /path/to/cloned/repos --skip-jit           # SZZ only, no JIT

Runtime estimate:
    Cloning 43 repos: 30-90 minutes depending on network (some repos are huge).
    SZZ analysis: 1-6 hours total. Large repos (kubernetes, cockroachdb, rust-lang)
    can take 30-60 minutes each due to extensive git blame operations.
    The script checkpoints after each repo, so you can Ctrl-C and resume.

Data sources:
    - master-prs.csv: 23,967 PRs across 43 repos, 93 columns
      Key columns used: repo, pr_number, title, merged_at, reworked, escaped,
                         classification, tier, q_overall
    - prs-*.json: Per-repo PR data with richer fields
      Key fields used: merge_commit_sha, title, pr_number, files, commits
      NOTE: commits[].sha is EMPTY in our data. We rely on merge_commit_sha only.

master-prs.csv columns (93 total):
    repo, tier, pr_number, title, author, merged_at, additions, deletions,
    lines_changed, size_bucket, files_count, specd, spec_source, classification,
    ci_status, review_modified, escaped, review_cycles, time_to_merge_hours,
    approval_mechanism, workflow_type, reworked, rework_type, q_overall,
    q_outcome_clarity, q_error_states, q_scope_boundaries, q_acceptance_criteria,
    q_data_contracts, q_dependency_context, q_behavioral_specificity, q_change_type,
    q_spec_length_signal, strict_escaped, f_is_bot_author, f_ai_tagged, f_typos,
    f_casual, f_questions, ... (feature columns), ai_probability,
    s_length, s_structure, s_specificity, s_error_awareness, s_scope,
    s_acceptance, s_questions, s_references, s_overall

prs-*.json structure (per PR):
    id, source, repo, title, body, author, merged_at, created_at, files,
    additions, deletions, ticket_ids, merge_commit_sha, pr_number, ci_status,
    reviews, commits, commit_count, last_edited_at, total_comments_count

    commits[]: {message, sha (EMPTY STRING), authored_at (null)}
    files[]: list of filename strings (no patch data)
"""

import argparse
import csv
import json
import logging
import math
import os
import re
import subprocess
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Lazy imports: we check for pydriller and pandas at runtime so the user
# gets a clear error message instead of a traceback.
# ---------------------------------------------------------------------------
try:
    import pandas as pd
except ImportError:
    print("ERROR: pandas is required. Install with: pip install pandas")
    sys.exit(1)

try:
    from pydriller import Git
except ImportError:
    print("ERROR: pydriller is required. Install with: pip install pydriller")
    sys.exit(1)

try:
    from scipy import stats as scipy_stats
except ImportError:
    print("WARNING: scipy not found. Correlation analysis (Part 7) will be skipped.")
    print("Install with: pip install scipy")
    scipy_stats = None


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Path to study data, relative to this script's location.
SCRIPT_DIR = Path(__file__).resolve().parent
DATA_DIR = SCRIPT_DIR.parent.parent / "data"
MASTER_CSV = DATA_DIR / "master-prs.csv"

# Output files. All written to the data directory alongside master-prs.csv.
# These are defaults; --batch-id overrides them with batch-specific filenames.
CHECKPOINT_FILE = DATA_DIR / "szz-checkpoint.json"
OUTPUT_CSV = DATA_DIR / "szz-results.csv"
OUTPUT_SUMMARY = DATA_DIR / "szz-summary.txt"

# JIT defect prediction features output (Kamei et al. 2016).
JIT_OUTPUT_CSV = DATA_DIR / "jit-features-full.csv"


def apply_batch_id(batch_id: str) -> None:
    """Override output file paths with batch-specific names for safe parallel execution."""
    global CHECKPOINT_FILE, OUTPUT_CSV, OUTPUT_SUMMARY, JIT_OUTPUT_CSV
    CHECKPOINT_FILE = DATA_DIR / f"szz-checkpoint-{batch_id}.json"
    OUTPUT_CSV = DATA_DIR / f"szz-results-{batch_id}.csv"
    OUTPUT_SUMMARY = DATA_DIR / f"szz-summary-{batch_id}.txt"
    JIT_OUTPUT_CSV = DATA_DIR / f"jit-features-{batch_id}.csv"

# How many seconds to wait between GitHub clones to avoid rate limiting.
# GitHub doesn't rate-limit clones aggressively, but politeness helps.
CLONE_DELAY_SECONDS = 2

# SZZ filter: ignore bug-introducing candidates older than this many days
# before the fix commit. A commit from 3 years ago that happens to touch
# the same line is unlikely to be the "bug" that was fixed.
# 365 days is a common threshold in SZZ literature (Kim et al. 2006).
MAX_BUG_INTRO_AGE_DAYS = 365

# Fix-detection keywords. These are matched case-insensitively against
# PR titles only. We use conservative keywords to avoid false positives.
# "fix" alone is broad but standard in SZZ literature.
# We do NOT include "refactor" or "update" -- those are not fixes.
FIX_KEYWORDS = [
    r"\bfix\b",       # "fix" only (not "prefix") -- \b handles word boundary
    r"\bfixes\b",     # explicit plural
    r"\bfixed\b",     # past tense
    r"\bbugfix\b",    # compound
    r"\bhotfix\b",    # urgent fix
    r"\brevert\b",    # reverts are often fixing a broken change
    r"\bregression\b",# fixing a regression
    r"\bbug\b",       # "bug" in title often means it's a fix
]

# Compiled regex: match any of the keywords (case-insensitive).
FIX_PATTERN = re.compile("|".join(FIX_KEYWORDS), re.IGNORECASE)

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("szz")


# ===========================================================================
# PART 1: Load data and identify repositories
# ===========================================================================

def load_master_csv() -> pd.DataFrame:
    """
    Load master-prs.csv into a DataFrame.

    We need: repo, pr_number, title, merged_at, and the quality/outcome columns
    for the final correlation analysis.

    Returns a DataFrame with 23,967 rows (one per merged PR).
    """
    log.info(f"Loading {MASTER_CSV}")
    df = pd.read_csv(MASTER_CSV)
    log.info(f"  Loaded {len(df)} PRs across {df['repo'].nunique()} repos")
    return df


def load_pr_json(repo_slug: str) -> list[dict]:
    """
    Load the per-repo PR JSON file for richer data (merge_commit_sha).

    The JSON filename uses dashes instead of slashes:
        apache/kafka -> prs-apache-kafka.json

    Returns a list of PR dicts.
    """
    # Convert "apache/kafka" to "apache-kafka"
    safe_name = repo_slug.replace("/", "-")
    json_path = DATA_DIR / f"prs-{safe_name}.json"

    if not json_path.exists():
        log.warning(f"  No JSON file found at {json_path}")
        return []

    with open(json_path, "r") as f:
        prs = json.load(f)

    log.info(f"  Loaded {len(prs)} PRs from {json_path.name}")
    return prs


def get_repo_list(df: pd.DataFrame) -> list[str]:
    """
    Extract the unique list of repo slugs (e.g., "apache/kafka") from the
    master CSV. Returns them sorted for deterministic ordering.
    """
    repos = sorted(df["repo"].unique().tolist())
    log.info(f"Found {len(repos)} repositories")
    return repos


# ===========================================================================
# PART 2: Clone repositories
# ===========================================================================

def clone_repo(repo_slug: str, repos_dir: Path) -> Path:
    """
    Clone a single repository from GitHub if it doesn't exist locally.

    We need FULL clones (not shallow) because git blame needs the complete
    commit history to trace lines back to their introduction.

    Args:
        repo_slug: e.g., "apache/kafka"
        repos_dir: parent directory for all clones

    Returns:
        Path to the cloned repo directory
    """
    # Convert "apache/kafka" to a local directory path.
    # We use the slug directly to keep the org/repo structure.
    repo_dir = repos_dir / repo_slug

    if repo_dir.exists() and (repo_dir / ".git").exists():
        log.info(f"  Repo already cloned: {repo_dir}")
        return repo_dir

    # Create parent directory (e.g., repos_dir/apache/)
    repo_dir.parent.mkdir(parents=True, exist_ok=True)

    clone_url = f"https://github.com/{repo_slug}.git"
    log.info(f"  Cloning {clone_url} -> {repo_dir}")
    log.info(f"  (This may take a while for large repos)")

    try:
        # We use --single-branch to save space (we only need the default branch).
        # If shallow_since is set, use --shallow-since to limit history depth.
        # SZZ needs blame history, but 2 years is enough for our PR window.
        clone_cmd = ["git", "clone", "--single-branch"]
        shallow_since = os.environ.get("SZZ_SHALLOW_SINCE")
        if shallow_since:
            clone_cmd.extend(["--shallow-since", shallow_since])
        clone_cmd.extend([clone_url, str(repo_dir)])
        subprocess.run(
            clone_cmd,
            check=True,
            capture_output=True,
            text=True,
            # Some repos are huge. Give up after 30 minutes.
            timeout=1800,
        )
        log.info(f"  Clone complete: {repo_dir}")
    except subprocess.TimeoutExpired:
        log.error(f"  Clone timed out after 30 minutes: {repo_slug}")
        # Clean up partial clone so the next run can retry.
        if repo_dir.exists():
            subprocess.run(["rm", "-rf", str(repo_dir)], check=False)
        raise
    except subprocess.CalledProcessError as e:
        log.error(f"  Clone failed: {e.stderr}")
        raise

    return repo_dir


def clone_all_repos(repos: list[str], repos_dir: Path) -> dict[str, Path]:
    """
    Clone all repositories, with progress reporting and rate limiting.

    Returns a dict mapping repo_slug -> local path.
    """
    repo_paths = {}
    for i, repo_slug in enumerate(repos, 1):
        log.info(f"[{i}/{len(repos)}] Checking {repo_slug}")
        try:
            repo_paths[repo_slug] = clone_repo(repo_slug, repos_dir)
        except Exception as e:
            log.error(f"  FAILED to clone {repo_slug}: {e}")
            log.error(f"  Skipping this repo. Re-run to retry.")
            continue

        # Small delay between clones to be polite to GitHub.
        if i < len(repos):
            time.sleep(CLONE_DELAY_SECONDS)

    log.info(f"Cloned/verified {len(repo_paths)}/{len(repos)} repos")
    return repo_paths


# ===========================================================================
# PART 3: Identify fix PRs
# ===========================================================================

def is_fix_pr(title: str) -> bool:
    """
    Determine if a PR is a "fix" based on its title.

    We match against PR TITLE ONLY. The SZZ literature (Sliwerski 2005,
    Kim 2006) matches against commit messages, which are short and focused.
    PR bodies are long and often mention "fix" casually ("this refactors
    the handler to fix a flaky test"), which inflates the fix PR count.
    Title-only matching is more conservative and more accurate.

    Criteria:
    - Title contains a fix-related keyword (word-boundary matched)

    We intentionally DO NOT match:
    - PR bodies -- too noisy, high false positive rate
    - "refactor" -- restructuring, not fixing
    - "update" -- too broad, catches dependency bumps
    - "improve" -- enhancements, not fixes
    - Issue references (#1234) alone -- could be features, not just bugs
    """
    return bool(FIX_PATTERN.search(title or ""))


def find_fix_prs(repo_slug: str, pr_json: list[dict]) -> list[dict]:
    """
    From the JSON PR data for one repo, find all PRs that look like fixes.

    We need the JSON data (not just master-prs.csv) because:
    1. The JSON has `merge_commit_sha` -- needed for SZZ tracing

    Returns a list of dicts with: pr_number, merge_commit_sha, title
    """
    fix_prs = []

    for pr in pr_json:
        title = pr.get("title", "")
        merge_sha = pr.get("merge_commit_sha", "")

        # Skip PRs without a merge commit SHA -- we can't trace them.
        if not merge_sha:
            continue

        if is_fix_pr(title):
            fix_prs.append({
                "pr_number": pr["pr_number"],
                "merge_commit_sha": merge_sha,
                "title": title,
            })

    log.info(f"  Found {len(fix_prs)} fix PRs out of {len(pr_json)} total")
    return fix_prs


# ===========================================================================
# PART 4: Run SZZ for each fix PR
# ===========================================================================

def run_szz_for_fix(
    repo_dir: Path,
    merge_commit_sha: str,
    pr_number: int,
) -> list[dict]:
    """
    Run the SZZ algorithm for a single fix commit.

    The core idea:
        1. Look at the fix commit's diff (which lines were changed).
        2. For each DELETED or MODIFIED line, run git blame on the parent
           version to find which commit last introduced that line.
        3. That commit is the candidate "bug-introducing" commit.

    We use PyDriller's Git.get_commits_last_modified_lines() which implements
    this logic. Under the hood, it:
        - Gets the diff of the given commit
        - For each modified file, for each deleted/changed line:
          - Runs `git blame` on the file at the PARENT commit
          - Records which commit last touched that line
        - Returns a dict: {filepath: set of commit hashes}

    AG-SZZ improvements we apply (Kim et al. 2006, Davies et al. 2014):
        1. Skip whitespace-only changes (PyDriller uses `git blame -w`)
        2. Skip commits older than MAX_BUG_INTRO_AGE_DAYS
        3. Filter out the fix commit blaming itself (can happen with merge commits)

    What we partially filter:
        - Comment-only changes: PyDriller's _useless_line filters some
          common comment prefixes (//, #, /*, triple-quotes) but misses
          other languages (XML, SQL, etc.) and mid-line comments. The RA-SZZ
          variant (Neto et al. 2018) handles this properly but requires
          language-specific parsing. We accept the noise and note it as
          a limitation.

    Args:
        repo_dir: Path to the cloned repository
        merge_commit_sha: The merge commit SHA of the fix PR
        pr_number: For logging purposes

    Returns:
        List of dicts, each with:
            - bug_commit_sha: the blamed commit SHA
            - file: the file where the blame was found
    """
    candidates = []

    try:
        # Initialize PyDriller's Git wrapper for this repo.
        git = Git(str(repo_dir))

        # PyDriller's key SZZ method. It:
        #   1. Checks out the diff of merge_commit_sha
        #   2. For each modified file, identifies deleted/changed lines
        #   3. Runs git blame on the parent to find who last touched those lines
        #   4. Returns {filepath: {set of commit SHAs that last touched those lines}}
        #
        # This IS the SZZ algorithm -- the rest is filtering and mapping.
        buggy_commits = git.get_commits_last_modified_lines(
            git.get_commit(merge_commit_sha)
        )
        # buggy_commits looks like:
        # {
        #     "src/main.py": {"abc123", "def456"},
        #     "src/utils.py": {"abc123", "ghi789"},
        # }

        # Get the fix commit's date for the age filter.
        fix_commit = git.get_commit(merge_commit_sha)
        fix_date = fix_commit.committer_date

        for filepath, commit_shas in buggy_commits.items():
            for sha in commit_shas:
                # FILTER 1: Don't blame the fix commit on itself.
                # This can happen with merge commits where one parent is the fix.
                if sha == merge_commit_sha:
                    continue

                # FILTER 2: Age filter.
                # If the blamed commit is older than MAX_BUG_INTRO_AGE_DAYS,
                # it's unlikely to be the actual bug-introducing commit.
                # More likely, the fix is touching a line that has been stable
                # for years and was merely reformatted or extended.
                try:
                    blamed_commit = git.get_commit(sha)
                    blamed_date = blamed_commit.committer_date
                    age = fix_date - blamed_date
                    if age > timedelta(days=MAX_BUG_INTRO_AGE_DAYS):
                        continue
                except Exception as e:
                    # If we can't look up the commit (e.g., it was in a
                    # squashed/rebased branch), skip it.
                    log.debug(f"    Could not look up blamed commit {sha[:8]}: {e}")
                    continue

                candidates.append({
                    "bug_commit_sha": sha,
                    "file": filepath,
                })

    except Exception as e:
        # PyDriller can fail on some commits (e.g., octopus merges, binary
        # files, repos with unusual history). Log and continue.
        log.warning(f"  SZZ failed for PR #{pr_number} ({merge_commit_sha[:8]}): {e}")

    return candidates


def run_szz_for_repo(
    repo_slug: str,
    repo_dir: Path,
    fix_prs: list[dict],
) -> list[dict]:
    """
    Run SZZ on all fix PRs in a single repository.

    Returns a list of dicts with keys: repo, fix_pr_number, fix_merge_sha,
    bug_commit_sha, file. Each entry means: "fix PR #X traced back to
    commit Y via file Z."
    """
    results = []
    total = len(fix_prs)

    for i, fix_pr in enumerate(fix_prs, 1):
        if i % 50 == 0 or i == 1:
            log.info(f"    SZZ tracing: {i}/{total} fix PRs processed")

        candidates = run_szz_for_fix(
            repo_dir,
            fix_pr["merge_commit_sha"],
            fix_pr["pr_number"],
        )

        for c in candidates:
            results.append({
                "repo": repo_slug,
                "fix_pr_number": fix_pr["pr_number"],
                "fix_merge_sha": fix_pr["merge_commit_sha"],
                "bug_commit_sha": c["bug_commit_sha"],
                "file": c["file"],
            })

    log.info(f"  SZZ complete: {len(results)} bug-introducing links from {total} fix PRs")
    return results


# ===========================================================================
# PART 5: Map bug-introducing commits to PRs
# ===========================================================================

def build_merge_sha_to_pr_index(pr_json: list[dict]) -> dict[str, int]:
    """
    Build a lookup: merge_commit_sha -> pr_number.

    This lets us map a bug-introducing commit back to the PR that introduced it.

    IMPORTANT LIMITATION: This only maps MERGE COMMITS to PRs. If a PR was
    squash-merged, the merge_commit_sha IS the squashed commit. But if a PR
    was merge-committed (creating a merge node), the individual commits within
    the PR won't be in this index.

    In practice, most of our repos use squash-merge, so merge_commit_sha
    corresponds 1:1 with the PR's code changes. For repos using merge commits,
    we may miss some mappings (the bug-introducing commit might be an individual
    commit within a PR, not the merge commit itself).

    We could also build an index from individual commit SHAs, but our JSON
    data has EMPTY commit SHAs (sha: ""). So merge_commit_sha is all we have.

    Fallback: For commits that don't match any merge SHA, we try `git log`
    to find the PR via commit message (see map_commit_to_pr_via_git below).
    """
    index = {}
    for pr in pr_json:
        sha = pr.get("merge_commit_sha", "")
        if sha:
            index[sha] = pr["pr_number"]
    return index


def map_commit_to_pr_via_git(
    repo_dir: Path,
    commit_sha: str,
) -> int | None:
    """
    Fallback: try to find which PR a commit belongs to by searching the git log.

    Strategy:
        1. Check if the commit message mentions a PR number (#1234)
        2. Use `git log --ancestry-path` to find the merge commit that
           includes this commit (works for non-squash merges)

    This is expensive, so we only use it as a fallback when the SHA index
    lookup fails.

    Returns the PR number if found, None otherwise.
    """
    try:
        # Strategy 1: Check commit message for PR reference.
        # We look for GitHub-style merge patterns that unambiguously reference
        # a PR number (not just any #1234 which could be an issue reference).
        result = subprocess.run(
            ["git", "-C", str(repo_dir), "log", "-1", "--format=%s%n%b", commit_sha],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            msg = result.stdout
            # Match unambiguous PR references only:
            #   "Merge pull request #1234"  (GitHub merge commit format)
            #   "(#1234)"                   (squash-merge title suffix)
            # Do NOT match bare "#1234" -- could be an issue reference.
            pr_match = re.search(r"Merge pull request #(\d+)", msg)
            if not pr_match:
                pr_match = re.search(r"\(#(\d+)\)", msg)
            if pr_match:
                return int(pr_match.group(1))

        # Strategy 2: Find the merge commit containing this commit.
        # We use --reverse to get the OLDEST merge commit in the ancestry
        # path -- i.e., the merge that originally brought this commit into
        # the default branch. Without --reverse, git log shows newest-first
        # and -1 would return the wrong merge commit.
        # NOTE: This can be slow on large repos. We set a 30-second timeout.
        result = subprocess.run(
            [
                "git", "-C", str(repo_dir),
                "log", "--merges", "--ancestry-path", "--oneline",
                "--reverse",
                f"{commit_sha}..HEAD",
                "-1",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            merge_msg = result.stdout.strip()
            # GitHub merge commits: "Merge pull request #1234 from ..."
            pr_match = re.search(r"Merge pull request #(\d+)", merge_msg)
            if not pr_match:
                pr_match = re.search(r"\(#(\d+)\)", merge_msg)
            if pr_match:
                return int(pr_match.group(1))

    except Exception as e:
        log.debug(f"  Fallback lookup failed for {commit_sha[:8]}: {e}")

    return None


def map_bugs_to_prs(
    repo_slug: str,
    repo_dir: Path,
    szz_results: list[dict],
    pr_json: list[dict],
) -> list[dict]:
    """
    For each bug-introducing commit, try to find the PR that introduced it.

    Uses two strategies:
        1. Direct SHA lookup against merge_commit_sha index (fast)
        2. Git log search for PR references (slow fallback)

    Adds 'bug_pr_number' to each result dict.
    Results where we can't find a PR get bug_pr_number = None.
    """
    sha_index = build_merge_sha_to_pr_index(pr_json)

    # Track unique commits we need to look up (avoid redundant git operations).
    unique_shas = set(r["bug_commit_sha"] for r in szz_results)
    sha_to_pr = {}

    # First pass: direct SHA lookup (fast).
    for sha in unique_shas:
        if sha in sha_index:
            sha_to_pr[sha] = sha_index[sha]

    # Count how many we resolved vs need fallback.
    resolved = len(sha_to_pr)
    unresolved = len(unique_shas) - resolved
    log.info(f"  SHA index resolved {resolved}/{len(unique_shas)} bug-introducing commits")

    # Second pass: git log fallback for unresolved SHAs.
    # This is slow, so we only do it for unresolved commits.
    if unresolved > 0:
        log.info(f"  Attempting git-log fallback for {unresolved} unresolved commits...")
        fallback_count = 0
        for sha in unique_shas:
            if sha not in sha_to_pr:
                pr_num = map_commit_to_pr_via_git(repo_dir, sha)
                if pr_num is not None:
                    sha_to_pr[sha] = pr_num
                    fallback_count += 1
        log.info(f"  Git-log fallback resolved {fallback_count} additional commits")

    # Annotate results with PR numbers.
    for result in szz_results:
        result["bug_pr_number"] = sha_to_pr.get(result["bug_commit_sha"])

    # Report unmapped commits.
    unmapped = sum(1 for r in szz_results if r["bug_pr_number"] is None)
    if unmapped > 0:
        log.info(f"  {unmapped} bug-introducing links could not be mapped to a PR")
        log.info(f"  (These are likely direct pushes to main, not PRs)")

    return szz_results


# ===========================================================================
# PART 6: Checkpointing (resume after crash)
# ===========================================================================

def load_checkpoint() -> dict:
    """
    Load checkpoint data. The checkpoint records which repos have been
    fully processed, so we can skip them on restart.

    Checkpoint format:
    {
        "completed_repos": ["apache/kafka", "cli/cli", ...],
        "all_results": [
            {"repo": "...", "fix_pr_number": ..., "bug_commit_sha": "...",
             "bug_pr_number": ..., "file": "..."},
            ...
        ]
    }
    """
    if CHECKPOINT_FILE.exists():
        with open(CHECKPOINT_FILE, "r") as f:
            data = json.load(f)
            log.info(f"Loaded checkpoint: {len(data.get('completed_repos', []))} SZZ repos done, "
                     f"{len(data.get('jit_completed_repos', []))} JIT repos done")
            # Ensure JIT fields exist (backward compat with old checkpoints).
            if "jit_completed_repos" not in data:
                data["jit_completed_repos"] = []
            if "all_jit_results" not in data:
                data["all_jit_results"] = []
            if "repo_hashes" not in data:
                data["repo_hashes"] = {}
            return data
    return {"completed_repos": [], "all_results": [],
            "jit_completed_repos": [], "all_jit_results": [],
            "repo_hashes": {}}


def get_repo_head_hash(repo_dir: Path) -> str:
    """Get the HEAD commit hash of a cloned repo for reproducibility."""
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_dir), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True, timeout=10,
        )
        return result.stdout.strip()
    except Exception:
        return "unknown"


def save_checkpoint(checkpoint: dict) -> None:
    """Save checkpoint data to disk atomically. Called after each repo completes."""
    tmp = CHECKPOINT_FILE.with_suffix(".json.tmp")
    with open(tmp, "w") as f:
        json.dump(checkpoint, f, indent=2)
    tmp.rename(CHECKPOINT_FILE)


# ===========================================================================
# PART 7: Score PRs and output results
# ===========================================================================

def score_prs(
    master_df: pd.DataFrame,
    all_results: list[dict],
) -> pd.DataFrame:
    """
    Add SZZ columns to the master PR DataFrame.

    New columns:
        szz_bug_introducing (bool): True if this PR was identified as
            bug-introducing by at least one fix PR's SZZ trace.
        szz_fix_count (int): How many distinct fix PRs traced back to this PR.
            A PR with fix_count=5 introduced bugs that required 5 separate
            fixes -- that's a problematic PR.

    How we match: We use (repo, bug_pr_number) from the SZZ results to
    look up the corresponding row in master_df by (repo, pr_number).
    """
    # Count distinct fix PRs per bug PR, not raw file-level links.
    # One fix PR might blame the same bug PR through multiple files --
    # we want to know how many DISTINCT fixes traced back to each PR.
    bug_fix_prs = defaultdict(set)
    for result in all_results:
        if result.get("bug_pr_number") is not None:
            key = (result["repo"], result["bug_pr_number"])
            bug_fix_prs[key].add(result["fix_pr_number"])

    # Add columns to the DataFrame.
    master_df = master_df.copy()
    master_df["szz_bug_introducing"] = master_df.apply(
        lambda row: (row["repo"], row["pr_number"]) in bug_fix_prs,
        axis=1,
    )
    master_df["szz_fix_count"] = master_df.apply(
        lambda row: len(bug_fix_prs.get((row["repo"], row["pr_number"]), set())),
        axis=1,
    )

    return master_df


def print_summary(df: pd.DataFrame, all_results: list[dict]) -> str:
    """
    Print and return summary statistics.
    """
    lines = []

    def p(msg=""):
        lines.append(msg)
        print(msg)

    total = len(df)
    bug_intro = df["szz_bug_introducing"].sum()
    pct = 100 * bug_intro / total if total else 0

    p("=" * 70)
    p("SZZ ANALYSIS SUMMARY")
    p("=" * 70)
    p()
    p(f"Total PRs analyzed: {total:,}")
    p(f"PRs identified as bug-introducing: {bug_intro:,} ({pct:.1f}%)")
    p(f"Total SZZ links (fix -> bug): {len(all_results):,}")
    p()

    # By repo
    p("Bug-introducing rate by repo:")
    p("-" * 50)
    repo_stats = df.groupby("repo").agg(
        total_prs=("pr_number", "count"),
        bug_prs=("szz_bug_introducing", "sum"),
    )
    repo_stats["rate"] = (100 * repo_stats["bug_prs"] / repo_stats["total_prs"]).round(1)
    repo_stats = repo_stats.sort_values("rate", ascending=False)
    for repo, row in repo_stats.iterrows():
        p(f"  {repo:40s} {row['bug_prs']:4.0f}/{row['total_prs']:5.0f} ({row['rate']:.1f}%)")
    p()

    # By classification (Human vs Augmented)
    if "classification" in df.columns:
        p("Bug-introducing rate by AI classification:")
        p("-" * 50)
        for cls in sorted(df["classification"].dropna().unique()):
            subset = df[df["classification"] == cls]
            n = len(subset)
            bugs = subset["szz_bug_introducing"].sum()
            rate = 100 * bugs / n if n else 0
            p(f"  {cls:20s} {bugs:5.0f}/{n:6,} ({rate:.1f}%)")
        p()

    # By tier
    if "tier" in df.columns:
        p("Bug-introducing rate by tier:")
        p("-" * 50)
        for tier in sorted(df["tier"].dropna().unique()):
            subset = df[df["tier"] == tier]
            n = len(subset)
            bugs = subset["szz_bug_introducing"].sum()
            rate = 100 * bugs / n if n else 0
            p(f"  {tier:20s} {bugs:5.0f}/{n:6,} ({rate:.1f}%)")
        p()

    # Top "most fixed" PRs (PRs that introduced the most bugs)
    worst = df[df["szz_fix_count"] > 0].nlargest(10, "szz_fix_count")
    if len(worst) > 0:
        p("Top 10 most bug-introducing PRs (by number of subsequent fixes):")
        p("-" * 70)
        for _, row in worst.iterrows():
            title = (row["title"][:50] + "...") if len(str(row["title"])) > 50 else row["title"]
            p(f"  {row['repo']:30s} #{row['pr_number']:<6} fixes={row['szz_fix_count']:2.0f}  {title}")
        p()

    return "\n".join(lines)


# ===========================================================================
# PART 8: Correlation with spec quality
# ===========================================================================

def analyze_correlations(df: pd.DataFrame) -> str:
    """
    Among scored PRs, compare bug-introducing rates by quality tier.

    Key question: Do PRs with better specs introduce fewer bugs?

    We use Fisher's exact test (2x2 contingency table) because:
    - Binary outcome (bug-introducing yes/no)
    - Categorical predictor (spec quality tier)
    - Some cells may have small counts
    - Fisher's is exact, not approximate like chi-squared

    We also check by classification (Human vs Augmented) to see if
    the AI effect interacts with bug introduction.
    """
    if scipy_stats is None:
        return "SKIPPED: scipy not installed\n"

    lines = []

    def p(msg=""):
        lines.append(msg)
        print(msg)

    p("=" * 70)
    p("CORRELATION ANALYSIS: Spec Quality vs Bug Introduction")
    p("=" * 70)
    p()

    # q_overall is the spec quality score (0-100).
    # Bucket into tiers for the contingency table.
    if "q_overall" not in df.columns:
        p("SKIPPED: q_overall column not found")
        return "\n".join(lines)

    # Only analyze PRs that have a quality score (i.e., spec'd PRs).
    scored = df[df["q_overall"].notna()].copy()
    p(f"PRs with spec quality scores: {len(scored):,}")

    if len(scored) < 20:
        p("Too few scored PRs for meaningful analysis")
        return "\n".join(lines)

    # Bucket quality scores into thirds.
    # Use qcut without labels first, then map -- because duplicates="drop"
    # can produce fewer than 3 bins (e.g., LLM scorer with 99% HIGH scores),
    # which crashes if we pass a 3-element labels list.
    try:
        tier_bins = pd.qcut(scored["q_overall"], q=3, duplicates="drop")
        n_bins = tier_bins.cat.categories.size
        if n_bins == 3:
            label_map = {cat: label for cat, label in zip(tier_bins.cat.categories, ["low", "medium", "high"])}
        elif n_bins == 2:
            label_map = {cat: label for cat, label in zip(tier_bins.cat.categories, ["low", "high"])}
            p("  WARNING: Only 2 quality tiers (score variance too low for 3 bins)")
        else:
            p(f"  WARNING: Only {n_bins} quality tier(s) — scores have near-zero variance")
            p("  Skipping tier analysis")
            return "\n".join(lines)
        scored["q_tier"] = tier_bins.map(label_map)
    except ValueError as e:
        p(f"  WARNING: Could not create quality tiers: {e}")
        p("  Skipping tier analysis")
        return "\n".join(lines)

    p()
    p("Bug-introducing rate by spec quality tier:")
    p("-" * 50)
    for tier in ["low", "medium", "high"]:
        subset = scored[scored["q_tier"] == tier]
        n = len(subset)
        if n == 0:
            continue
        bugs = subset["szz_bug_introducing"].sum()
        rate = 100 * bugs / n if n else 0
        p(f"  {tier:10s} {bugs:4.0f}/{n:5} ({rate:.1f}%)")

    # Fisher's exact test: low-quality vs high-quality bug-introducing rate.
    low = scored[scored["q_tier"] == "low"]
    high = scored[scored["q_tier"] == "high"]

    if len(low) > 0 and len(high) > 0:
        # 2x2 table: rows = quality tier, cols = [bug_intro, not_bug_intro]
        table = [
            [low["szz_bug_introducing"].sum(), (~low["szz_bug_introducing"]).sum()],
            [high["szz_bug_introducing"].sum(), (~high["szz_bug_introducing"]).sum()],
        ]
        # Convert to int for Fisher's test.
        table = [[int(x) for x in row] for row in table]

        odds_ratio, p_value = scipy_stats.fisher_exact(table)
        p()
        p(f"Fisher's exact test (low vs high quality):")
        p(f"  Odds ratio: {odds_ratio:.3f}")
        p(f"  p-value:    {p_value:.4f}")
        p(f"  Interpretation: {'Significant' if p_value < 0.05 else 'Not significant'} at alpha=0.05")
        p()

        # IMPORTANT CAVEAT: This is a pooled analysis across repos.
        # The real unit of analysis is the repo (N=43), not the PR.
        # A proper analysis would use a mixed-effects model with repo
        # as a random effect. This pooled Fisher's test is indicative
        # but inflates significance due to non-independence of PRs
        # within the same repo.
        p("  CAVEAT: This is a pooled analysis. PRs within the same repo")
        p("  are not independent. Real N is ~43 repos, not ~23,967 PRs.")
        p("  A mixed-effects logistic regression would be more appropriate.")
        p("  Treat this p-value as a rough indicator, not a definitive result.")

    p()

    # Also check: Human vs Augmented bug-introducing rates
    if "classification" in df.columns:
        p("Bug-introducing rate: Human vs Augmented PRs:")
        p("-" * 50)
        for cls in ["human", "augmented"]:
            subset = df[df["classification"] == cls]
            n = len(subset)
            if n == 0:
                continue
            bugs = subset["szz_bug_introducing"].sum()
            rate = 100 * bugs / n if n else 0
            p(f"  {cls:15s} {bugs:5.0f}/{n:6,} ({rate:.1f}%)")

        human = df[df["classification"] == "human"]
        augmented = df[df["classification"] == "augmented"]

        if len(human) > 0 and len(augmented) > 0:
            table = [
                [int(human["szz_bug_introducing"].sum()), int((~human["szz_bug_introducing"]).sum())],
                [int(augmented["szz_bug_introducing"].sum()), int((~augmented["szz_bug_introducing"]).sum())],
            ]
            odds_ratio, p_value = scipy_stats.fisher_exact(table)
            p()
            p(f"  Fisher's exact test (human vs augmented):")
            p(f"    Odds ratio: {odds_ratio:.3f}")
            p(f"    p-value:    {p_value:.4f}")
            p()
            p("  Same caveat about pooled analysis applies here.")

    return "\n".join(lines)


# ===========================================================================
# PART 9: JIT Defect Prediction Features (Kamei et al. 2013)
# ===========================================================================
#
# PRIMARY REFERENCE:
#   Kamei, Y., Shihab, E., Adams, B., Hassan, A.E., Mockus, A., Shar, A.,
#   & Ubayashi, N. (2013). "A Large-Scale Empirical Study of Just-in-Time
#   Quality Assurance." IEEE Transactions on Software Engineering, 39(6),
#   pp. 757-773. DOI: 10.1109/TSE.2012.70
#
#   Table II (p. 762) defines all 14 features across 5 dimensions.
#   Section III-A (pp. 761-763) describes each feature's computation.
#
# SECONDARY REFERENCE (extends JIT to cross-project prediction):
#   Kamei, Y., Fukushima, T., McIntosh, S., Yamashita, K., Ubayashi, N.,
#   & Hassan, A.E. (2016). "Studying Just-in-Time Defect Prediction Using
#   Cross-Project Models." Empirical Software Engineering, 21(5),
#   pp. 2072-2106. DOI: 10.1007/s10664-015-9400-x
#
#   Uses the same 14 features; validates cross-project transferability.
#
# FEATURE TABLE (Kamei 2013, Table II, p. 762):
# ┌────────────┬──────────┬────────────────────────────────────────────────┐
# │ Dimension  │ Feature  │ Description                                    │
# ├────────────┼──────────┼────────────────────────────────────────────────┤
# │ Diffusion  │ NS       │ Number of modified subsystems                  │
# │            │ ND       │ Number of modified directories                 │
# │            │ NF       │ Number of modified files                       │
# │            │ Entropy  │ Distribution of modified code across files     │
# ├────────────┼──────────┼────────────────────────────────────────────────┤
# │ Size       │ LA       │ Lines of code added                            │
# │            │ LD       │ Lines of code deleted                          │
# │            │ LT       │ Lines of code in a file before the change      │
# ├────────────┼──────────┼────────────────────────────────────────────────┤
# │ Purpose    │ FIX      │ Whether the change is a defect fix             │
# ├────────────┼──────────┼────────────────────────────────────────────────┤
# │ History    │ NDEV     │ Number of developers that changed the files    │
# │            │ AGE      │ Average time interval between last and         │
# │            │          │   current change                               │
# │            │ NUC      │ Number of unique changes to the files          │
# ├────────────┼──────────┼────────────────────────────────────────────────┤
# │ Experience │ EXP      │ Developer experience (number of changes)       │
# │            │ REXP     │ Recent developer experience                    │
# │            │ SEXP     │ Developer experience on a subsystem            │
# └────────────┴──────────┴────────────────────────────────────────────────┘
# ===========================================================================

JIT_CSV_COLUMNS = [
    "repo", "pr_number",
    # Diffusion
    "ns", "nd", "nf", "entropy",
    # Size
    "la", "ld", "lt",
    # Purpose
    "fix",
    # History
    "ndev", "age", "nuc",
    # Experience
    "exp", "rexp", "sexp",
]


def _git_cmd(repo_dir: Path, args: list[str], timeout: int = 30) -> str | None:
    """
    Run a git command in the given repo directory and return stdout.
    Returns None on failure (timeout, non-zero exit, etc.).
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_dir)] + args,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if result.returncode == 0:
            return result.stdout
        return None
    except (subprocess.TimeoutExpired, Exception):
        return None


def _get_subsystem(filepath: str) -> str:
    """
    Extract the top-level directory (subsystem) from a file path.

    Kamei et al. define subsystem as the root directory of the file.
    Files at the repository root have subsystem = "." (root).
    """
    parts = filepath.split("/")
    if len(parts) <= 1:
        return "."
    return parts[0]


def _compute_entropy(file_changes: dict[str, int]) -> float:
    """
    Compute Shannon entropy of the distribution of changes across files.

    Kamei et al. 2013, Section III-A, p. 762, Diffusion dimension:
        "The entropy of the change is calculated as the distribution
         of modified code across each file."

    Formula (Shannon 1948):
        H = -sum(p_i * log2(p_i))
    where p_i = (lines changed in file i) / (total lines changed)

    Range: [0, log2(NF)]
        H = 0:        all changes in one file (maximally focused)
        H = log2(NF): changes uniformly spread (maximally diffuse)

    Edge cases:
    - Single file: entropy = 0 (no distribution to measure)
    - Zero total changes: entropy = 0
    - All changes in one file: entropy = 0
    """
    total = sum(file_changes.values())
    if total == 0 or len(file_changes) <= 1:
        return 0.0

    entropy = 0.0
    for count in file_changes.values():
        if count > 0:
            p = count / total
            entropy -= p * math.log2(p)
    return entropy


def _build_author_cache(repo_dir: Path) -> dict:
    """
    Pre-compute per-author commit data for the entire repo.

    Returns a dict with:
        author_commits[email] = list of (timestamp, subsystems) tuples,
            sorted by timestamp ascending.

    This avoids running expensive git log commands per-PR for EXP/REXP/SEXP
    (Kamei 2013, Table II, Experience dimension). Instead of N_prs git
    commands, we parse git log ONCE and binary-search per PR.

    Uses --no-merges to exclude merge commits (which are not "developer
    work" in the Kamei sense — they're process artifacts).

    Subsystems are extracted per-commit for SEXP computation (commits
    in the same top-level directory as the PR being scored).
    """
    log.info("    Building author commit cache (one-time per repo)...")

    # Get all commits with author email, timestamp, and changed files.
    # Format: author_email<TAB>unix_timestamp<TAB>file1<NL>file2<NL>...
    # We use --name-only to get file paths.
    output = _git_cmd(
        repo_dir,
        ["log", "--format=%ae\t%ct", "--name-only", "--no-merges"],
        timeout=120,
    )
    if not output:
        log.warning("    Failed to build author cache (git log failed)")
        return {"author_commits": defaultdict(list)}

    author_commits: dict[str, list[tuple[int, set[str]]]] = defaultdict(list)
    current_email = None
    current_ts = None
    current_files: set[str] = set()

    for line in output.split("\n"):
        line = line.strip()
        if not line:
            # Empty line = separator between commits.
            if current_email is not None and current_ts is not None:
                subsystems = {_get_subsystem(f) for f in current_files if f}
                author_commits[current_email].append((current_ts, subsystems))
                current_email = None
                current_ts = None
                current_files = set()
            continue

        if "\t" in line:
            # This is the header line: email<TAB>timestamp
            # First, flush any pending commit.
            if current_email is not None and current_ts is not None:
                subsystems = {_get_subsystem(f) for f in current_files if f}
                author_commits[current_email].append((current_ts, subsystems))

            parts = line.split("\t", 1)
            current_email = parts[0]
            try:
                current_ts = int(parts[1])
            except ValueError:
                current_ts = None
            current_files = set()
        else:
            # This is a filename line.
            current_files.add(line)

    # Flush the last commit.
    if current_email is not None and current_ts is not None:
        subsystems = {_get_subsystem(f) for f in current_files if f}
        author_commits[current_email].append((current_ts, subsystems))

    # Sort each author's commits by timestamp (ascending).
    for email in author_commits:
        author_commits[email].sort(key=lambda x: x[0])

    total = sum(len(v) for v in author_commits.values())
    log.info(f"    Author cache built: {len(author_commits)} authors, {total} commits")

    return {"author_commits": author_commits}


def compute_jit_features(
    repo_dir: Path,
    merge_commit_sha: str,
    pr_files: list[str],
    pr_additions: int,
    pr_deletions: int,
    author_email: str,
    pr_date_str: str,
    pr_title: str,
    author_cache: dict,
) -> dict | None:
    """
    Compute all 14 Kamei et al. (2013) JIT defect prediction features
    for a single PR / merge commit.

    Args:
        repo_dir:         Path to the cloned repository
        merge_commit_sha: The merge commit SHA for this PR
        pr_files:         List of file paths modified by this PR
        pr_additions:     Lines added (from GitHub API / PR JSON)
        pr_deletions:     Lines deleted (from GitHub API / PR JSON)
        author_email:     Email of the PR author
        pr_date_str:      ISO date string of when the PR was merged
        pr_title:         PR title (for FIX detection)
        author_cache:     Pre-computed author data from _build_author_cache()

    Returns:
        Dict with all 14 features, or None if computation failed entirely.
    """
    if not pr_files:
        return None

    # Parse PR date to a unix timestamp for comparisons.
    try:
        # GitHub dates look like "2023-04-15T10:30:00Z" or similar.
        pr_date = datetime.fromisoformat(pr_date_str.replace("Z", "+00:00"))
        pr_ts = int(pr_date.timestamp())
    except (ValueError, AttributeError):
        return None

    # -----------------------------------------------------------------------
    # DIFFUSION features
    # Kamei et al. 2013, Section III-A, p. 761-762; Table II row "Diffusion"
    #
    # These measure how spread out the change is across the codebase.
    # Higher diffusion = higher risk (change touches more areas).
    # -----------------------------------------------------------------------

    # NF: Number of modified files.
    #   Kamei 2013, Table II: "NF: Number of modified files"
    #   Direct count from PR file list (no git required).
    nf = len(pr_files)

    # ND: Number of unique directories containing modified files.
    #   Kamei 2013, Table II: "ND: Number of modified directories"
    #   Computed from file paths by extracting parent directory.
    #   Files at repo root → directory = "."
    directories = set()
    for f in pr_files:
        d = "/".join(f.split("/")[:-1])
        directories.add(d if d else ".")
    nd = len(directories)

    # NS: Number of unique subsystems (top-level directories).
    #   Kamei 2013, Table II: "NS: Number of modified subsystems"
    #   Section III-A, p. 762: "subsystem is the root directory of a file"
    #   Files at repo root → subsystem = "." (our convention)
    subsystems = set()
    for f in pr_files:
        subsystems.add(_get_subsystem(f))
    ns = len(subsystems)

    # Entropy: Shannon entropy of change distribution across files.
    #   Kamei 2013, Table II: "Entropy: Distribution of modified code
    #     across each file"
    #   Section III-A, p. 762: "calculated as the distribution of
    #     modified code across each file" using Shannon entropy formula
    #     H = -sum(p_i * log2(p_i))
    #   where p_i = (lines changed in file i) / (total lines changed)
    #
    #   Entropy = 0 means all changes in one file (focused).
    #   Entropy = log2(NF) means changes uniformly spread (diffuse).
    #
    #   We need per-file line counts. The PR JSON only has aggregate
    #   additions/deletions. We get per-file stats from git diff --numstat.
    file_changes: dict[str, int] = {}
    diff_stat = _git_cmd(
        repo_dir,
        ["diff", "--numstat", f"{merge_commit_sha}~1..{merge_commit_sha}"],
        timeout=30,
    )
    if diff_stat:
        for line in diff_stat.strip().split("\n"):
            if not line:
                continue
            parts = line.split("\t")
            if len(parts) >= 3:
                added = parts[0]
                deleted = parts[1]
                fname = parts[2]
                # Binary files show "-" for added/deleted.
                if added == "-" or deleted == "-":
                    continue
                try:
                    file_changes[fname] = int(added) + int(deleted)
                except ValueError:
                    continue

    # If git diff failed or returned nothing, entropy is unknown.
    # Do NOT fall back to uniform distribution — that produces maximum
    # entropy (log2(nf)), which is the worst possible estimate and would
    # systematically inflate entropy for PRs with missing diff data.
    if not file_changes:
        entropy = float("nan")
    else:
        entropy = _compute_entropy(file_changes)

    # -----------------------------------------------------------------------
    # SIZE features
    # Kamei et al. 2013, Section III-A, p. 762; Table II row "Size"
    #
    # Larger changes are harder to review and more likely to contain defects.
    # Nagappan & Ball (2005) showed code churn predicts defects with 89% accuracy.
    # -----------------------------------------------------------------------

    # LA: Lines of code added.
    #   Kamei 2013, Table II: "LA: Lines of code added"
    #   Taken directly from GitHub API / PR JSON.
    la = pr_additions

    # LD: Lines of code deleted.
    #   Kamei 2013, Table II: "LD: Lines of code deleted"
    #   Taken directly from GitHub API / PR JSON.
    ld = pr_deletions

    # LT: Lines of code in modified files BEFORE the change.
    #   Kamei 2013, Table II: "LT: Lines of code in a file before the change"
    #   Section III-A, p. 762: sum of lines in all modified files at the
    #   parent commit. Measures the "mass" of code being modified.
    #   New files contribute LT=0 (didn't exist before).
    #   Requires git: `git show {parent}:{file}` and count newlines.
    lt = 0
    parent_sha = f"{merge_commit_sha}~1"
    for f in pr_files:
        # Use git show to get the file content at the parent commit.
        content = _git_cmd(
            repo_dir,
            ["show", f"{parent_sha}:{f}"],
            timeout=15,
        )
        if content is not None:
            # Count lines. An empty file has 0 lines.
            lt += content.count("\n")
        # else: file didn't exist at parent (new file) -> LT contribution = 0.

    # -----------------------------------------------------------------------
    # PURPOSE feature
    # Kamei et al. 2013, Section III-A, p. 762; Table II row "Purpose"
    # -----------------------------------------------------------------------

    # FIX: Whether the change is a defect fix (1/0).
    #   Kamei 2013, Table II: "FIX: Whether or not the change is a defect fix"
    #   Section III-A, p. 762: "determined by searching for keywords such
    #     as 'bug', 'fix', 'defect', 'patch' in the commit message"
    #   We match against PR title using the FIX_PATTERN regex (line ~130).
    #   Our keywords: fix, fixes, fixed, bugfix, hotfix, revert, regression, bug
    fix = 1 if is_fix_pr(pr_title) else 0

    # -----------------------------------------------------------------------
    # HISTORY features
    # Kamei et al. 2013, Section III-A, p. 762; Table II row "History"
    #
    # These measure the prior change activity on the modified files.
    # Files with more prior changes, more developers, and recent activity
    # are more defect-prone (Hassan 2009, "Predicting Faults Using the
    # Complexity of Code Changes").
    #
    # IMPORTANT: All history queries are bounded to merge_commit_sha~1
    # (the commit before this PR). Without this bound, git log walks
    # from HEAD and includes the PR itself plus all later commits,
    # making NDEV, AGE, and NUC systematically wrong.
    # -----------------------------------------------------------------------

    # NDEV: Number of distinct developers who previously modified any of
    # the files in this commit.
    #   Kamei 2013, Table II: "NDEV: The number of developers that
    #     changed the modified files"
    #   Aggregated: union of all prior authors across all files.
    all_devs: set[str] = set()

    # AGE: Average time interval (in days) between the current commit
    # and the last change to each modified file.
    #   Kamei 2013, Table II: "AGE: The average time interval between
    #     the last and the current change"
    #   Computed per-file, then averaged. Older files = less context
    #   in the developer's working memory = higher risk.
    age_days_list: list[float] = []

    # NUC: Number of unique prior changes (commits) to the modified files.
    #   Kamei 2013, Table II: "NUC: The number of unique changes to
    #     the modified files"
    #   Summed across all files. Frequently-changed files = hotspots.
    nuc = 0

    for f in pr_files:
        # NDEV: Get all unique authors who modified this file BEFORE this PR.
        # Must use merge_commit_sha~1 as the revision boundary, not HEAD,
        # otherwise we include the PR itself and all later commits.
        devs_output = _git_cmd(
            repo_dir,
            ["log", f"--format=%ae", f"{merge_commit_sha}~1", "--", f],
            timeout=30,
        )
        if devs_output:
            file_devs = set(devs_output.strip().split("\n")) - {""}
            all_devs.update(file_devs)

        # AGE: Get the timestamp of the last change to this file BEFORE this PR.
        # Bounded to merge_commit_sha~1 so we don't count the PR itself.
        last_change_output = _git_cmd(
            repo_dir,
            ["log", "-1", "--format=%ct", f"{merge_commit_sha}~1", "--", f],
            timeout=15,
        )
        if last_change_output and last_change_output.strip():
            try:
                last_ts = int(last_change_output.strip())
                age_delta = (pr_ts - last_ts) / 86400.0  # seconds -> days
                if age_delta >= 0:
                    age_days_list.append(age_delta)
            except ValueError:
                pass

        # NUC: Count commits to this file BEFORE this PR.
        # Bounded to merge_commit_sha~1, not HEAD.
        nuc_output = _git_cmd(
            repo_dir,
            ["rev-list", "--count", f"{merge_commit_sha}~1", "--", f],
            timeout=15,
        )
        if nuc_output and nuc_output.strip():
            try:
                nuc += int(nuc_output.strip())
            except ValueError:
                pass

    ndev = len(all_devs)
    age = sum(age_days_list) / len(age_days_list) if age_days_list else 0.0

    # -----------------------------------------------------------------------
    # EXPERIENCE features
    # Kamei et al. 2013, Section III-A, p. 762; Table II row "Experience"
    #
    # Developer experience is a strong predictor of code quality.
    # Kamei 2013 found EXP, REXP, and SEXP among the most important
    # features for JIT defect prediction (Section IV-B, Table V).
    #
    # Uses the pre-computed author cache (_build_author_cache) for
    # efficiency — one git log parse per repo instead of per-PR.
    # -----------------------------------------------------------------------

    # EXP: Developer experience — total number of prior commits.
    #   Kamei 2013, Table II: "EXP: Developer experience
    #     (number of changes)"
    #   Counts all commits by this author in the repo before this PR.

    # REXP: Recent developer experience — commits in last 90 days.
    #   Kamei 2013, Table II: "REXP: Recent developer experience"
    #   Measures whether the developer is actively working in this
    #   codebase (vs. returning after a long absence).

    # SEXP: Subsystem developer experience.
    #   Kamei 2013, Table II: "SEXP: Developer experience on a subsystem"
    #   Counts commits by this author in the SAME top-level directories
    #   as the current PR. A developer experienced in "src/" but not
    #   "tests/" has SEXP=0 for changes to "tests/".
    exp = 0
    rexp = 0
    sexp = 0

    ninety_days_seconds = 90 * 86400
    author_data = author_cache.get("author_commits", {})

    # Look up author by email. Try the exact email first.
    commits_for_author = author_data.get(author_email, [])

    if commits_for_author:
        for commit_ts, commit_subsystems in commits_for_author:
            if commit_ts >= pr_ts:
                # This commit is at or after our PR; stop counting.
                # (The list is sorted ascending by timestamp.)
                break

            exp += 1

            # REXP: Within 90 days before the PR.
            if (pr_ts - commit_ts) <= ninety_days_seconds:
                rexp += 1

            # SEXP: In the same subsystems as this PR.
            if commit_subsystems & subsystems:
                sexp += 1

    return {
        "ns": ns,
        "nd": nd,
        "nf": nf,
        "entropy": round(entropy, 4),
        "la": la,
        "ld": ld,
        "lt": lt,
        "fix": fix,
        "ndev": ndev,
        "age": round(age, 2),
        "nuc": nuc,
        "exp": exp,
        "rexp": rexp,
        "sexp": sexp,
    }


def compute_jit_for_repo(
    repo_slug: str,
    repo_dir: Path,
    pr_json: list[dict],
    checkpoint: dict | None = None,
) -> list[dict]:
    """
    Compute JIT features for ALL PRs in a single repository.

    We compute features for every PR (not just fix PRs) because JIT
    defect prediction is about predicting which commits will introduce
    bugs BEFORE they happen. The fix/non-fix status is one feature, not
    a filter.

    Checkpoints every 100 PRs so partial progress survives crashes.

    Returns a list of dicts with repo, pr_number, and the 14 JIT features.
    """
    # Check for partial progress from a previous run.
    done_prs = set()
    if checkpoint is not None:
        done_prs = {
            r["pr_number"] for r in checkpoint.get("all_jit_results", [])
            if r.get("repo") == repo_slug
        }
        if done_prs:
            log.info(f"  Resuming JIT: {len(done_prs)} PRs already computed")

    # Build the author commit cache once for this repo.
    author_cache = _build_author_cache(repo_dir)

    results = []
    total = len(pr_json)
    incomplete_count = 0

    for i, pr in enumerate(pr_json, 1):
        # Skip PRs already computed in a previous partial run.
        if pr["pr_number"] in done_prs:
            continue

        if i % 100 == 0 or i == 1:
            log.info(f"    Computing JIT features: {i}/{total} PRs")

        merge_sha = pr.get("merge_commit_sha", "")
        if not merge_sha:
            incomplete_count += 1
            continue

        # Get file list from PR JSON.
        pr_files = pr.get("files", [])
        if not pr_files:
            incomplete_count += 1
            continue

        # Get author email. The PR JSON has "author" (GitHub login), not email.
        # We try to get the real email from the merge commit in git.
        # If git fails, we fall back to the login — but this won't match
        # the author cache (which stores emails), so EXP/REXP/SEXP will be 0.
        author_email = ""
        email_output = _git_cmd(
            repo_dir,
            ["log", "-1", "--format=%ae", merge_sha],
            timeout=10,
        )
        if email_output and email_output.strip():
            author_email = email_output.strip()
        else:
            # Fallback to GitHub login — experience features will be 0.
            author_email = pr.get("author", "")
            log.debug(f"    PR #{pr.get('pr_number')}: using GitHub login as author (experience features will be 0)")

        features = compute_jit_features(
            repo_dir=repo_dir,
            merge_commit_sha=merge_sha,
            pr_files=pr_files,
            pr_additions=pr.get("additions", 0),
            pr_deletions=pr.get("deletions", 0),
            author_email=author_email,
            pr_date_str=pr.get("merged_at", ""),
            pr_title=pr.get("title", ""),
            author_cache=author_cache,
        )

        if features is None:
            incomplete_count += 1
            continue

        row = {"repo": repo_slug, "pr_number": pr["pr_number"]}
        row.update(features)
        results.append(row)

        # Checkpoint every 100 PRs so partial progress survives crashes.
        if checkpoint is not None and len(results) % 100 == 0:
            checkpoint["all_jit_results"].extend(results)
            results = []  # Reset batch — already saved to checkpoint
            save_checkpoint(checkpoint)
            log.info(f"    JIT checkpoint saved ({i}/{total} PRs processed)")

    # Flush remaining results to checkpoint.
    if checkpoint is not None and results:
        checkpoint["all_jit_results"].extend(results)
        save_checkpoint(checkpoint)

    total_computed = len(results) + len(done_prs)
    if checkpoint is not None:
        total_computed = len([
            r for r in checkpoint.get("all_jit_results", [])
            if r.get("repo") == repo_slug
        ])

    log.info(f"  JIT features computed for {total_computed}/{total} PRs")
    if incomplete_count > 0:
        log.info(f"  {incomplete_count} PRs had incomplete feature computation "
                 f"(missing merge SHA, files, or date)")

    return results


def save_jit_results(all_jit_results: list[dict]) -> None:
    """
    Save JIT feature results to CSV.

    Uses csv.DictWriter for reliable output (no pandas dependency for writing).
    """
    if not all_jit_results:
        log.warning("No JIT results to save")
        return

    with open(JIT_OUTPUT_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=JIT_CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(all_jit_results)

    log.info(f"JIT features saved to {JIT_OUTPUT_CSV} ({len(all_jit_results)} rows)")


# ===========================================================================
# MAIN
# ===========================================================================

def main():
    parser = argparse.ArgumentParser(
        description="SZZ Analysis: Trace bug-introducing commits across 43 repositories.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--repos-dir",
        type=Path,
        required=True,
        help="Directory where repos are/will be cloned. E.g., /tmp/szz-repos",
    )
    parser.add_argument(
        "--clone",
        action="store_true",
        help="Clone repos that aren't already present (requires network access)",
    )
    parser.add_argument(
        "--repo",
        type=str,
        default=None,
        help="Process only this repo (e.g., 'apache/kafka'). Useful for testing.",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Ignore checkpoint and start fresh",
    )
    parser.add_argument(
        "--skip-jit",
        action="store_true",
        help="Skip JIT feature computation (only run SZZ analysis)",
    )
    parser.add_argument(
        "--jit-only",
        action="store_true",
        help="Skip SZZ analysis, only compute JIT defect prediction features",
    )
    parser.add_argument(
        "--batch-id",
        type=str,
        default=None,
        help="Unique batch identifier. Each batch gets its own checkpoint/output files "
             "(e.g., szz-checkpoint-batch1.json). Allows safe parallel execution.",
    )
    args = parser.parse_args()

    if args.skip_jit and args.jit_only:
        log.error("Cannot use --skip-jit and --jit-only together")
        sys.exit(1)

    if args.batch_id:
        apply_batch_id(args.batch_id)
        log.info(f"Batch mode: {args.batch_id}")
        log.info(f"  Checkpoint: {CHECKPOINT_FILE.name}")
        log.info(f"  Results:    {OUTPUT_CSV.name}")
        log.info(f"  JIT:        {JIT_OUTPUT_CSV.name}")

    # Validate inputs.
    if not MASTER_CSV.exists():
        log.error(f"master-prs.csv not found at {MASTER_CSV}")
        sys.exit(1)

    args.repos_dir.mkdir(parents=True, exist_ok=True)

    # -----------------------------------------------------------------------
    # Step 1: Load data
    # -----------------------------------------------------------------------
    master_df = load_master_csv()
    repos = get_repo_list(master_df)

    # If --repo flag is set, filter to just that repo.
    if args.repo:
        if args.repo not in repos:
            log.error(f"Repo '{args.repo}' not found in master-prs.csv")
            log.error(f"Available repos: {repos}")
            sys.exit(1)
        repos = [args.repo]
        log.info(f"Single-repo mode: {args.repo}")

    # -----------------------------------------------------------------------
    # Step 2: Clone repos (if --clone flag is set)
    # -----------------------------------------------------------------------
    if args.clone:
        log.info("Cloning repositories...")
        clone_all_repos(repos, args.repos_dir)
    else:
        # Verify repos exist locally.
        missing = []
        for repo_slug in repos:
            repo_dir = args.repos_dir / repo_slug
            if not (repo_dir / ".git").exists():
                missing.append(repo_slug)
        if missing:
            log.warning(f"{len(missing)} repos not found locally. Use --clone to fetch them.")
            log.warning(f"Missing: {missing[:5]}{'...' if len(missing) > 5 else ''}")
            # Remove missing repos from the processing list.
            repos = [r for r in repos if r not in missing]
            if not repos:
                log.error("No repos available locally. Use --clone first.")
                sys.exit(1)

    # -----------------------------------------------------------------------
    # Step 3: Load checkpoint (for resumability)
    # -----------------------------------------------------------------------
    if args.reset:
        if args.repo:
            # Single-repo reset: only clear that repo's data, preserve others.
            checkpoint = load_checkpoint()
            checkpoint["completed_repos"] = [
                r for r in checkpoint["completed_repos"] if r != args.repo
            ]
            checkpoint["all_results"] = [
                r for r in checkpoint["all_results"] if r["repo"] != args.repo
            ]
            checkpoint["jit_completed_repos"] = [
                r for r in checkpoint["jit_completed_repos"] if r != args.repo
            ]
            checkpoint["all_jit_results"] = [
                r for r in checkpoint["all_jit_results"] if r["repo"] != args.repo
            ]
            log.info(f"Reset {args.repo} only (other repos preserved)")
        else:
            checkpoint = {"completed_repos": [], "all_results": [],
                          "jit_completed_repos": [], "all_jit_results": []}
            log.info("Starting fresh (--reset flag)")
    else:
        checkpoint = load_checkpoint()

    run_szz = not args.jit_only
    run_jit = not args.skip_jit

    # --- SZZ remaining repos ---
    completed = set(checkpoint["completed_repos"])
    all_results = checkpoint["all_results"]

    remaining = [r for r in repos if r not in completed]
    if run_szz:
        if remaining:
            log.info(f"SZZ repos remaining: {len(remaining)}/{len(repos)}")
        else:
            log.info("All SZZ repos already processed (use --reset to rerun)")

    # --- JIT remaining repos ---
    jit_completed = set(checkpoint["jit_completed_repos"])
    all_jit_results = checkpoint["all_jit_results"]

    jit_remaining = [r for r in repos if r not in jit_completed]
    if run_jit:
        if jit_remaining:
            log.info(f"JIT repos remaining: {len(jit_remaining)}/{len(repos)}")
        else:
            log.info("All JIT repos already processed (use --reset to rerun)")

    # -----------------------------------------------------------------------
    # Step 4: SZZ — Process each repo
    # -----------------------------------------------------------------------
    if run_szz and remaining:
        for i, repo_slug in enumerate(remaining, 1):
            log.info(f"")
            log.info(f"{'='*60}")
            log.info(f"SZZ: Processing repo {i}/{len(remaining)}: {repo_slug}")
            log.info(f"{'='*60}")

            repo_dir = args.repos_dir / repo_slug

            # Verify repo exists.
            if not (repo_dir / ".git").exists():
                log.warning(f"  Repo not found at {repo_dir}, skipping")
                continue

            # Load PR JSON for this repo (has merge SHAs).
            pr_json = load_pr_json(repo_slug)
            if not pr_json:
                log.warning(f"  No PR JSON data, skipping")
                continue

            # Record the HEAD hash for reproducibility.
            head_hash = get_repo_head_hash(repo_dir)
            checkpoint["repo_hashes"][repo_slug] = head_hash
            log.info(f"  HEAD: {head_hash[:12]}")

            # Find fix PRs.
            fix_prs = find_fix_prs(repo_slug, pr_json)
            if not fix_prs:
                log.info(f"  No fix PRs found, skipping SZZ")
                checkpoint["completed_repos"].append(repo_slug)
                save_checkpoint(checkpoint)
                continue

            log.info(f"  Running SZZ on {len(fix_prs)} fix PRs...")

            # Run SZZ.
            szz_results = run_szz_for_repo(repo_slug, repo_dir, fix_prs)

            # Map bug-introducing commits to PRs.
            if szz_results:
                szz_results = map_bugs_to_prs(repo_slug, repo_dir, szz_results, pr_json)

            # Save results and checkpoint.
            all_results.extend(szz_results)
            checkpoint["completed_repos"].append(repo_slug)
            checkpoint["all_results"] = all_results
            save_checkpoint(checkpoint)

            log.info(f"  SZZ checkpoint saved. {len(checkpoint['completed_repos'])} repos complete.")

    # -----------------------------------------------------------------------
    # Step 4b: JIT — Compute Kamei et al. (2016) features for each repo
    # -----------------------------------------------------------------------
    if run_jit and jit_remaining:
        for i, repo_slug in enumerate(jit_remaining, 1):
            log.info(f"")
            log.info(f"{'='*60}")
            log.info(f"JIT: Processing repo {i}/{len(jit_remaining)}: {repo_slug}")
            log.info(f"{'='*60}")

            repo_dir = args.repos_dir / repo_slug

            # Verify repo exists.
            if not (repo_dir / ".git").exists():
                log.warning(f"  Repo not found at {repo_dir}, skipping")
                continue

            # Record HEAD hash if not already recorded during SZZ.
            if repo_slug not in checkpoint.get("repo_hashes", {}):
                head_hash = get_repo_head_hash(repo_dir)
                checkpoint.setdefault("repo_hashes", {})[repo_slug] = head_hash
                log.info(f"  HEAD: {head_hash[:12]}")

            # Load PR JSON for this repo.
            pr_json = load_pr_json(repo_slug)
            if not pr_json:
                log.warning(f"  No PR JSON data, skipping JIT")
                continue

            # Compute JIT features for ALL PRs in this repo.
            # Checkpoint is passed in so partial progress is saved every 100 PRs.
            jit_results = compute_jit_for_repo(repo_slug, repo_dir, pr_json, checkpoint=checkpoint)

            # Mark repo as fully complete and save.
            all_jit_results = checkpoint["all_jit_results"]  # May have been extended in-place
            checkpoint["jit_completed_repos"].append(repo_slug)
            save_checkpoint(checkpoint)

            log.info(f"  JIT checkpoint saved. {len(checkpoint['jit_completed_repos'])} repos complete.")

        # Write JIT CSV after all repos are processed.
        save_jit_results(all_jit_results)
    elif run_jit and not jit_remaining:
        # All repos already done; still write the CSV from checkpoint data.
        if all_jit_results:
            save_jit_results(all_jit_results)

    # -----------------------------------------------------------------------
    # Step 6: Score PRs and save results (SZZ only — skipped in --jit-only)
    # -----------------------------------------------------------------------
    if run_szz:
        log.info(f"")
        log.info(f"{'='*60}")
        log.info(f"Scoring PRs and generating output")
        log.info(f"{'='*60}")

        # In single-repo mode, filter to only that repo for scoring/output.
        # We DON'T filter all_results earlier because the checkpoint needs
        # the full list. We also filter master_df so the output CSV doesn't
        # mark unanalyzed repos as "not bug-introducing" (they're "not analyzed").
        scoring_results = all_results
        scoring_df = master_df
        if args.repo:
            scoring_results = [r for r in all_results if r["repo"] == args.repo]
            scoring_df = master_df[master_df["repo"] == args.repo].copy()
            log.info(f"Single-repo scoring: {len(scoring_results)} SZZ links, {len(scoring_df)} PRs")

        scored_df = score_prs(scoring_df, scoring_results)

        # Save the scored DataFrame.
        scored_df.to_csv(OUTPUT_CSV, index=False)
        log.info(f"Results saved to {OUTPUT_CSV}")

        # Print summary.
        summary = print_summary(scored_df, scoring_results)

        # -------------------------------------------------------------------
        # Step 7: Correlation analysis
        # -------------------------------------------------------------------
        correlation_summary = analyze_correlations(scored_df)

        # Save full summary to file.
        with open(OUTPUT_SUMMARY, "w") as f:
            f.write(summary)
            f.write("\n\n")
            f.write(correlation_summary)
        log.info(f"Summary saved to {OUTPUT_SUMMARY}")

    # -----------------------------------------------------------------------
    # Final notes
    # -----------------------------------------------------------------------
    print()
    print("=" * 70)
    print("DONE")
    print("=" * 70)
    if run_szz:
        print(f"SZZ Results:    {OUTPUT_CSV}")
        print(f"SZZ Summary:    {OUTPUT_SUMMARY}")
    if run_jit:
        print(f"JIT Features:   {JIT_OUTPUT_CSV}")
    print(f"Checkpoint:     {CHECKPOINT_FILE}")
    print()
    print("To re-run from scratch:    python3 szz-score.py --repos-dir ... --reset")
    print("To run a single repo:      python3 szz-score.py --repos-dir ... --repo apache/kafka")
    print("To run only JIT features:  python3 szz-score.py --repos-dir ... --jit-only")
    print("To run only SZZ analysis:  python3 szz-score.py --repos-dir ... --skip-jit")
    print()
    print("Known limitations:")
    print("  1. Comment-only changes are not filtered (would need language-specific parsing)")
    print("  2. Commits within PRs (non-merge commits) may not map to PRs")
    print("     because our JSON data has empty commit SHAs")
    print("  3. The age filter (365 days) is a heuristic; some real bugs are older")
    print("  4. Squash-merged PRs map well; merge-committed PRs may have gaps")
    print("  5. The pooled statistical analysis treats PRs as independent")
    print("     observations, but PRs within a repo are correlated")
    if run_jit:
        print("  6. JIT LT feature uses git show on the parent commit; may be slow")
        print("     for repos with very large file counts per PR")
        print("  7. JIT author matching uses git commit email, which may differ from")
        print("     the GitHub login in PR JSON (co-author tag vs committer)")
        print("  8. JIT NDEV/NUC use full file history (not bounded by time window)")
        print("     which matches Kamei et al. (2016) definition")


if __name__ == "__main__":
    main()
