# SZZ Defect Tracing Methodology

**Date:** 2026-04-01
**Script:** `szz-score.py`
**Dataset:** 116 repos, 80,973 PRs (master-prs.csv)

---

## What SZZ Is

The SZZ algorithm (Śliwerski, Zimmermann, and Zeller 2005) traces bug-fixing changes back to the commits that introduced the bug. It is the standard method in empirical software engineering for linking fixes to their root causes.

**Original paper:** Śliwerski, J., Zimmermann, T., and Zeller, A., "When Do Changes Induce Fixes?" *Proceedings of the 2005 International Workshop on Mining Software Repositories (MSR 2005)*, pp. 1-5. ACM, 2005.

The algorithm works in two phases:

1. **Identify fix commits.** The original paper linked CVS commits to Bugzilla bug reports by matching bug IDs in commit messages. Later variants (Kim et al. 2006) used keyword matching on commit messages.

2. **Trace backwards via blame.** For each fix commit, examine which lines were deleted or modified. Run `git blame` (or `cvs annotate` in the original) on the parent version of those lines to find which earlier commit last introduced them. That earlier commit is the candidate "bug-introducing" change.

## Our Implementation

### Phase 1: Fix Identification

**Deviation from original:** Śliwerski 2005 used Bugzilla issue links. We use PR title keyword matching because open-source GitHub repos lack consistent bug tracker linkage. This is the standard adaptation used in post-2005 SZZ studies.

**Keyword matching** (`is_fix_pr()`, line 312):
- Pattern: word-boundary match on `fix`, `bug`, `hotfix`, `patch`, `resolve`, `revert`, `regression`, `crash`, `error`, `broken`, `defect`
- Matched against **PR title only**, not body. PR bodies frequently mention "fix" casually ("this refactors the handler to fix a flaky test"), inflating false positives. Title-only matching is more conservative.
- We intentionally DO NOT match: `refactor`, `update`, `improve`, `clean`, `enhance` — these are not bug fixes

**What this means:** A PR is classified as a "fix" if its title contains fix-related keywords. Only fix PRs are traced backwards. Non-fix PRs are never the starting point of a blame trace — they can only be the *target* (i.e., identified as bug-introducing by a fix that traces back to them).

### Phase 2: Blame Tracing

**Core operation** (`run_szz_for_fix()`, line 369):

For each fix PR's merge commit:
1. Get the commit's diff (which files and lines were changed)
2. For each deleted or modified line, run `git blame -w` on the file at the **parent commit** to find which earlier commit last introduced that line
3. That blamed commit is the candidate bug-introducing commit
4. Map the blamed commit back to a PR using merge commit SHA matching

We use PyDriller's `git.get_commits_last_modified_lines(commit)` which implements this logic. Under the hood, PyDriller:
- Gets the diff of the given commit
- For each modified file, for each deleted/changed line:
  - Runs `git blame` on the file at the PARENT commit
  - Records which commit last touched that line
- Returns `{filepath: set of commit hashes}`

### AG-SZZ Filters

We apply the AG-SZZ improvements from Kim et al. 2006 and Davies et al. 2014:

1. **Whitespace-only changes ignored.** PyDriller uses `git blame -w`, which ignores whitespace when assigning blame. A commit that only reformatted indentation will not be blamed.

2. **Age filter.** Blamed commits older than 365 days before the fix are excluded. If a fix touches a line that has been stable for years, the original author is unlikely to be the bug introducer — more likely the fix is extending or refactoring stable code. (Configurable via `MAX_BUG_INTRO_AGE_DAYS`.)

3. **Self-blame filter.** The fix commit cannot blame itself. This can happen with merge commits where one parent is the fix.

### What We Do NOT Filter (Known Limitations)

1. **Comment-only changes.** PyDriller's `_useless_line` filter handles common comment prefixes (`//`, `#`, `/*`, triple-quotes) but misses other languages (XML, SQL) and mid-line comments. The RA-SZZ variant (Neto et al. 2018) handles this with language-specific parsing. We accept the noise and note it as a limitation.

2. **Cosmetic changes.** Renames, import reordering, and mechanical refactors that happen to touch lines later fixed will be falsely blamed. This is a known SZZ limitation across all variants.

3. **Squash merge ambiguity.** Squash-merged PRs map well (one merge commit = one PR). Merge-committed PRs may have multiple commits that don't all map back to the PR's merge SHA.

## Mapping Blamed Commits to PRs

After blame tracing identifies bug-introducing commit SHAs, we map them to PRs:

1. For each repo, build a lookup from commit SHA → PR number using the `merge_commit_sha` field in our PR JSON data
2. A blamed commit that maps to a PR labels that PR as "bug-introducing"
3. Blamed commits that don't map to any PR in our dataset are counted but not analyzed (they may predate our data window or be direct pushes to main)

## JIT Defect Prediction Features

In addition to SZZ blame tracing, the script computes the full 14-feature Kamei et al. JIT defect prediction model for every PR. This is a separate computation from SZZ — it uses PR metadata and git history, not blame tracing.

**Reference:** Kamei, Y., Shihab, E., Adams, B., Hassan, A.E., Mockus, A., Sinha, A., and Ubayashi, N., "A Large-Scale Empirical Study of Just-in-Time Quality Assurance," *IEEE Transactions on Software Engineering*, 39(6), 757-773, 2013. Table II, p. 762.

The 14 features across 5 dimensions:
- **Diffusion:** NS (subsystems), ND (directories), NF (files), Entropy (change spread)
- **Size:** LA (lines added), LD (lines deleted), LT (lines in touched files pre-change)
- **Purpose:** FIX (whether the change is a fix)
- **History:** NDEV (prior developers on touched files), AGE (weighted age of touched files), NUC (prior changes to touched files)
- **Experience:** EXP (author's total commits), REXP (author's recent commits, exponentially decayed), SEXP (author's commits to touched subsystems)

JIT features are computed from the cloned repo's git history, bounded to the merge commit's parent (not HEAD, not including the PR itself or future commits).

## Shallow Clone and Data Window

**Clone depth:** `--shallow-since=2024-04-01` (environment variable `SZZ_SHALLOW_SINCE`). This limits git history to ~2 years, sufficient for our PR data window (~1 year of fetched PRs) plus the 365-day age filter for blame tracing.

**Implication:** Bug-introducing commits older than the shallow clone boundary cannot be found by blame. This is acceptable because:
- Our PR JSON data covers approximately 1 year per repo
- The age filter already caps blame at 365 days before the fix
- Any bug introduced >2 years ago and fixed within our data window would be excluded, but this is a small fraction

**As-of hash:** For each repo processed, the clone's HEAD commit at processing time should be recorded. The checkpoint file (`szz-checkpoint.json`) records which repos have been processed but does not currently record the HEAD hash. This is noted as a reproducibility gap.

## Output Files

- `szz-results.csv` — One row per blame trace: fix PR → bug-introducing PR, with file path
- `szz-summary.txt` — Human-readable summary of fix rates and bug-introducing rates
- `jit-features-full.csv` — Full 14-feature Kamei JIT for every PR
- `szz-checkpoint.json` — Resumable checkpoint (completed repos, accumulated results)

## Differences from Original SZZ (Śliwerski 2005)

| Aspect | Original (2005) | Our Implementation |
|--------|----------------|-------------------|
| Fix identification | Bugzilla issue links in CVS commit messages | PR title keyword matching (standard post-2005 adaptation) |
| VCS | CVS + `cvs annotate` | Git + `git blame -w` via PyDriller |
| Granularity | Individual commits | PRs (mapped via merge commit SHA) |
| Whitespace handling | Not filtered | Filtered (`-w` flag, AG-SZZ) |
| Age filter | None | 365 days (AG-SZZ) |
| Comment filtering | None | Partial (PyDriller `_useless_line`, not language-specific) |
| Data source | Mozilla/Eclipse CVS + Bugzilla | 116 GitHub repos, PR JSON via GraphQL API |

## References

- Śliwerski, J., Zimmermann, T., Zeller, A. "When Do Changes Induce Fixes?" MSR 2005.
- Kim, S., Zimmermann, T., Pan, K., Whitehead, E.J. "Automatic Identification of Bug-Introducing Changes." ASE 2006. (AG-SZZ: annotation graph, whitespace/comment filtering)
- Davies, S., Roper, M., Wood, M. "Comparing Text-Based and Dependence-Based Approaches for Determining the Origins of Bugs." JSS, 2014. (Validates AG-SZZ improvements)
- Neto, E.C., da Costa, D.A., Kulesza, U. "The Impact of Refactoring Changes on the SZZ Algorithm." SANER 2018. (RA-SZZ: refactoring-aware variant)
- Kamei, Y., et al. "A Large-Scale Empirical Study of Just-in-Time Quality Assurance." IEEE TSE, 39(6), 2013. (14-feature JIT model)
- Rosa, G., et al. "Evaluating SZZ Implementations Through a Developer-informed Oracle." ICSE 2021. (Benchmarks SZZ implementations; PyDriller's implementation evaluated)
