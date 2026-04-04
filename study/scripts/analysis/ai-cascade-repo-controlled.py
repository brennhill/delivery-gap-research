#!/usr/bin/env python3
"""
Verify: Does the AI cascading rework finding hold within repos?

The concern: AI-tagged PRs cluster in repos that have higher rework rates
for everyone. The 45% vs 11.2% rework|buggy rate could be a repo
composition effect, not an AI effect.

Test: Compute rework|buggy rate for AI vs human within each repo,
then aggregate.
"""

import pandas as pd
import numpy as np
from scipy import stats
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

df = pd.read_csv(DATA_DIR / "master-prs.csv", low_memory=False)
szz = pd.read_csv(DATA_DIR / "szz-results-merged.csv")

for col in ["reworked", "specd"]:
    df[col] = df[col].fillna(False).astype(bool)
df["ai_tagged"] = df["f_ai_tagged"].fillna(False).astype(bool)

# SZZ merge
bug_prs = szz[["repo", "bug_pr_number"]].drop_duplicates()
bug_prs = bug_prs.rename(columns={"bug_pr_number": "pr_number"})
bug_prs["szz_buggy"] = True
df = df.merge(bug_prs, on=["repo", "pr_number"], how="left")
df["szz_buggy"] = df["szz_buggy"].fillna(False).astype(bool)

# Bot exclusion
BOT_PATTERNS = [
    "dependabot", "renovate", "greenkeeper", "snyk", "mergify",
    "codecov", "denobot", "vitess-bot", "ti-chi-bot", "pwshbot",
    "k8s-infra-cherrypick-robot", "robobun", "copilot-swe-agent",
    "medplumbot", "refine-bot", "lobehubbot", "qdrant-cloud-bot",
    "vercel-release-bot", "nextjs-bot", "grafana-delivery-bot",
    "grafana-pr-automation", "github-actions", "scheduled-actions",
    "promptfoobot", "langchain-model-profile-bot", "n8n-assistant",
    "mendral-app",
]
df["is_bot"] = (
    df["f_is_bot_author"].fillna(False).astype(bool) |
    df["author"].str.lower().str.contains("|".join(BOT_PATTERNS), case=False, na=False, regex=True)
)
df = df[~df["is_bot"]].copy()

szz_repos = set(szz["repo"].unique())
df = df[df["repo"].isin(szz_repos)].copy()

# Only buggy PRs
buggy = df[df["szz_buggy"]].copy()

print(f"Buggy PRs: {len(buggy):,}")
print(f"  AI buggy: {buggy['ai_tagged'].sum():,}")
print(f"  Human buggy: {(~buggy['ai_tagged']).sum():,}")

# ── Pooled (what we reported) ──
ai_buggy = buggy[buggy["ai_tagged"]]
human_buggy = buggy[~buggy["ai_tagged"]]
print(f"\nPooled rework|buggy:")
print(f"  AI:    {ai_buggy['reworked'].mean():.1%} ({ai_buggy['reworked'].sum()}/{len(ai_buggy)})")
print(f"  Human: {human_buggy['reworked'].mean():.1%} ({human_buggy['reworked'].sum()}/{len(human_buggy)})")

# ── Within-repo comparison ──
print(f"\n{'=' * 70}")
print("WITHIN-REPO: rework|buggy rate for AI vs Human")
print("=" * 70)

repo_results = []
for repo in sorted(buggy["repo"].unique()):
    repo_buggy = buggy[buggy["repo"] == repo]
    ai_b = repo_buggy[repo_buggy["ai_tagged"]]
    human_b = repo_buggy[~repo_buggy["ai_tagged"]]

    if len(ai_b) < 5 or len(human_b) < 5:
        continue

    ai_rw = ai_b["reworked"].mean()
    human_rw = human_b["reworked"].mean()
    delta = ai_rw - human_rw

    repo_results.append({
        "repo": repo,
        "ai_rework_rate": ai_rw,
        "human_rework_rate": human_rw,
        "delta": delta,
        "n_ai_buggy": len(ai_b),
        "n_human_buggy": len(human_b),
    })

    print(f"  {repo:>40s}: AI={ai_rw:.1%} (n={len(ai_b)}), "
          f"Human={human_rw:.1%} (n={len(human_b)}), Δ={delta:+.1%}")

if repo_results:
    deltas = [r["delta"] for r in repo_results]
    n_higher = sum(1 for d in deltas if d > 0)
    n_lower = sum(1 for d in deltas if d < 0)
    mean_delta = np.mean(deltas)
    median_delta = np.median(deltas)

    # Weighted by min(n_ai, n_human) to account for sample size
    weights = [min(r["n_ai_buggy"], r["n_human_buggy"]) for r in repo_results]
    weighted_delta = np.average(deltas, weights=weights)

    t_stat, t_p = stats.ttest_1samp(deltas, 0)
    try:
        _, wilcox_p = stats.wilcoxon(deltas) if len(deltas) >= 10 else (None, None)
    except ValueError:
        # wilcoxon fails if all deltas are zero (no variance)
        wilcox_p = None

    print(f"\n  Summary ({len(repo_results)} repos with ≥5 AI and ≥5 human buggy PRs):")
    print(f"  AI rework|buggy higher in {n_higher}/{len(repo_results)} repos")
    print(f"  Mean Δ: {mean_delta:+.1%}")
    print(f"  Median Δ: {median_delta:+.1%}")
    print(f"  Weighted mean Δ: {weighted_delta:+.1%}")
    print(f"  t-test H0: Δ=0: t={t_stat:.3f}, p={t_p:.4f}")
    if wilcox_p is not None:
        print(f"  Wilcoxon signed-rank: p={wilcox_p:.4f}")
else:
    print("  Too few repos with both AI and human buggy PRs")


# ── Also check: overall rework rate by repo AI adoption ──
print(f"\n\n{'=' * 70}")
print("REPO-LEVEL: Do AI-heavy repos have higher rework rates for EVERYONE?")
print("=" * 70)

repo_stats = df.groupby("repo").agg(
    ai_rate=("ai_tagged", "mean"),
    rework_rate=("reworked", "mean"),
    bug_rate=("szz_buggy", "mean"),
    n=("reworked", "count"),
).reset_index()
repo_stats = repo_stats[repo_stats["n"] >= 50]

rho, p = stats.spearmanr(repo_stats["ai_rate"], repo_stats["rework_rate"])
print(f"\n  Spearman: AI adoption rate vs rework rate: ρ={rho:.3f}, p={p:.4f}")

rho2, p2 = stats.spearmanr(repo_stats["ai_rate"], repo_stats["bug_rate"])
print(f"  Spearman: AI adoption rate vs bug rate: ρ={rho2:.3f}, p={p2:.4f}")

# Split into terciles
zero_ai_repos = repo_stats[repo_stats["ai_rate"] == 0]
nonzero_ai_repos = repo_stats[repo_stats["ai_rate"] > 0]

print(f"\n  Zero-AI repos: {len(zero_ai_repos)}")
print(f"    Mean rework rate: {zero_ai_repos['rework_rate'].mean():.1%}")
print(f"    Mean bug rate: {zero_ai_repos['bug_rate'].mean():.1%}")

if len(nonzero_ai_repos) > 0:
    ai_median = nonzero_ai_repos["ai_rate"].median()
    low_ai = nonzero_ai_repos[nonzero_ai_repos["ai_rate"] <= ai_median]
    high_ai = nonzero_ai_repos[nonzero_ai_repos["ai_rate"] > ai_median]

    for label, subset in [("Low-AI repos", low_ai), ("High-AI repos", high_ai)]:
        print(f"\n  {label}: {len(subset)}")
        print(f"    Mean AI rate: {subset['ai_rate'].mean():.1%}")
        print(f"    Mean rework rate: {subset['rework_rate'].mean():.1%}")
        print(f"    Mean bug rate: {subset['bug_rate'].mean():.1%}")


# ── Time-to-fix with matched introduction window ──
print(f"\n\n{'=' * 70}")
print("TIME-TO-FIX: Restricted to same introduction window")
print("=" * 70)

df["merged_at"] = pd.to_datetime(df["merged_at"], utc=True, errors="coerce")
pr_dates = df[["repo", "pr_number", "merged_at", "ai_tagged"]].copy()
pr_dates = pr_dates.rename(columns={"pr_number": "bug_pr_number",
                                     "merged_at": "bug_merged_at",
                                     "ai_tagged": "bug_ai_tagged"})

fix_dates = df[["repo", "pr_number", "merged_at"]].copy()
fix_dates = fix_dates.rename(columns={"pr_number": "fix_pr_number",
                                       "merged_at": "fix_merged_at"})

szz_with_dates = szz.merge(pr_dates, on=["repo", "bug_pr_number"], how="inner")
szz_with_dates = szz_with_dates.merge(fix_dates, on=["repo", "fix_pr_number"], how="inner")
szz_pairs = szz_with_dates.drop_duplicates(
    subset=["repo", "bug_pr_number", "fix_pr_number"]
).copy()

szz_pairs["time_to_fix_hours"] = (
    (szz_pairs["fix_merged_at"] - szz_pairs["bug_merged_at"]).dt.total_seconds() / 3600
)
szz_pairs = szz_pairs[szz_pairs["time_to_fix_hours"] > 0].copy()

# Find the earliest AI bug introduction date
ai_pairs = szz_pairs[szz_pairs["bug_ai_tagged"] == True]
if len(ai_pairs) > 0:
    earliest_ai = ai_pairs["bug_merged_at"].min()
    # Restrict BOTH groups to bugs introduced after earliest AI bug
    matched_window = szz_pairs[szz_pairs["bug_merged_at"] >= earliest_ai].copy()

    ai_ttf = matched_window[matched_window["bug_ai_tagged"] == True]["time_to_fix_hours"]
    human_ttf = matched_window[matched_window["bug_ai_tagged"] == False]["time_to_fix_hours"]

    print(f"\n  Window: bugs introduced after {earliest_ai.strftime('%Y-%m-%d')}")
    print(f"  AI pairs: {len(ai_ttf):,}, Human pairs: {len(human_ttf):,}")
    print(f"  AI median: {ai_ttf.median()/24:.1f} days")
    print(f"  Human median: {human_ttf.median()/24:.1f} days")

    _, p = stats.mannwhitneyu(ai_ttf, human_ttf, alternative="two-sided")
    sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""
    print(f"  Mann-Whitney U: p={p:.4f} {sig}")
