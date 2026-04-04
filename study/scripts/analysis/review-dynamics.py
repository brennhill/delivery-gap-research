#!/usr/bin/env python3
"""
Review dynamics: Do spec'd PRs get reviewed differently?

If specs improve outcomes through better review, we should see:
  1. More review comments on spec'd PRs
  2. Longer time-to-merge (more careful review)
  3. More review cycles
  4. Lower defect rates GIVEN the extra review

If specs get more review but still have more bugs, the review
mechanism is not the causal pathway.

Also examines spec adoption curves over time.
"""

import pandas as pd
import numpy as np
import statsmodels.api as sm
from scipy import stats
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

df = pd.read_csv(DATA_DIR / "master-prs.csv", low_memory=False)
szz = pd.read_csv(DATA_DIR / "szz-results-merged.csv")

df["merged_at"] = pd.to_datetime(df["merged_at"], utc=True, errors="coerce")
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

# Size controls
df["log_add"] = np.log1p(df["additions"])
df["log_del"] = np.log1p(df["deletions"])
df["log_files"] = np.log1p(df["files_count"])
SIZE_CONTROLS = ["log_add", "log_del", "log_files"]

# Recent window
cutoff = pd.Timestamp("2026-01-01", tz="UTC")
recent = df[df["merged_at"] >= cutoff].copy()

# Identify review columns
review_cols = []
for col in ["review_comments", "comments", "review_cycles",
            "time_to_merge_hours", "time_to_first_review_hours"]:
    if col in df.columns:
        review_cols.append(col)

print(f"Dataset: {len(df):,} PRs (bots excluded)")
print(f"Recent (Jan-Mar 2026): {len(recent):,} PRs")
print(f"Review columns available: {review_cols}")


def within_author_lpm(data, treatment_col, outcome_col, controls=None,
                      min_prs=2, label=""):
    if controls is None:
        controls = SIZE_CONTROLS

    data = data.copy()
    ac = data["author"].value_counts()
    multi = data[data["author"].isin(ac[ac >= min_prs].index)].copy()
    if len(multi) < 50:
        print(f"  [{label}] Too few PRs: {len(multi)}")
        return None

    all_cols = [treatment_col] + controls + [outcome_col]
    for col in all_cols:
        multi[col] = pd.to_numeric(multi[col], errors="coerce")
    multi = multi.dropna(subset=all_cols)

    if len(multi) < 50:
        print(f"  [{label}] Too few complete cases: {len(multi)}")
        return None

    author_var = multi.groupby("author")[treatment_col].agg(["min", "max"])
    n_with_var = (author_var["min"] != author_var["max"]).sum()

    author_means = multi.groupby("author")[all_cols].transform("mean")
    demeaned = multi[all_cols] - author_means
    X = demeaned[[treatment_col] + controls]
    y = demeaned[outcome_col]

    try:
        model = sm.OLS(y, X, hasconst=False).fit(
            cov_type="cluster",
            cov_kwds={"groups": multi["author"]},
        )
    except Exception as e:
        print(f"  [{label}] OLS failed: {e}")
        return None

    coef = model.params[treatment_col]
    pval = model.pvalues[treatment_col]
    sig = "***" if pval < 0.001 else "**" if pval < 0.01 else "*" if pval < 0.05 else ""
    print(f"  [{label}] N={len(multi):,}, authors w/var={n_with_var:,}, "
          f"coef={coef:+.4f}, p={pval:.4f} {sig}")
    return {"coef": coef, "p": pval, "n": len(multi), "n_var": n_with_var}


# ════════════════════════════════════════════════════════════════════
# 1. DO SPEC'D PRs GET MORE REVIEW?
# ════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("1. DO SPEC'D PRs GET MORE REVIEW? (descriptive)")
print("=" * 70)

for dataset_label, dataset in [("Full dataset", df), ("Recent 3 months", recent)]:
    print(f"\n  --- {dataset_label} ---")
    specd = dataset[dataset["specd"]]
    unspesd = dataset[~dataset["specd"]]

    for col in review_cols:
        s_vals = pd.to_numeric(specd[col], errors="coerce").dropna()
        u_vals = pd.to_numeric(unspesd[col], errors="coerce").dropna()
        if len(s_vals) < 30 or len(u_vals) < 30:
            continue
        s_med = s_vals.median()
        u_med = u_vals.median()
        s_mean = s_vals.mean()
        u_mean = u_vals.mean()
        try:
            _, p = stats.mannwhitneyu(s_vals, u_vals, alternative="two-sided")
            sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""
        except Exception:
            p = 1.0
            sig = ""
        print(f"  {col:>30s}: spec'd med={s_med:8.1f}, unspec'd med={u_med:8.1f}, "
              f"ratio={s_med/u_med if u_med != 0 else float('inf'):5.2f}x, p={p:.4f} {sig}")


# ════════════════════════════════════════════════════════════════════
# 2. WITHIN-AUTHOR: DO SPECS CHANGE REVIEW BEHAVIOR?
# ════════════════════════════════════════════════════════════════════
print("\n\n" + "=" * 70)
print("2. WITHIN-AUTHOR: DO SPECS CHANGE REVIEW BEHAVIOR?")
print("=" * 70)
print("(Same author's spec'd vs unspec'd PRs — do they get reviewed differently?)")

for col in review_cols:
    vals = pd.to_numeric(df[col], errors="coerce")
    if vals.notna().sum() < 1000:
        print(f"\n  {col}: too few non-null values ({vals.notna().sum():,})")
        continue

    # Use log transform for skewed review metrics
    df[f"log_{col}"] = np.log1p(vals)
    print(f"\n  Specs → {col} (within-author):")
    within_author_lpm(df, "specd", f"log_{col}", label=f"specs->{col}")


# ════════════════════════════════════════════════════════════════════
# 3. DOES MORE REVIEW REDUCE BUGS? (within-author)
# ════════════════════════════════════════════════════════════════════
print("\n\n" + "=" * 70)
print("3. DOES MORE REVIEW REDUCE BUGS? (within-author)")
print("=" * 70)

szz_repos = set(szz["repo"].unique())
df_szz = df[df["repo"].isin(szz_repos)].copy()

for col in review_cols:
    vals = pd.to_numeric(df_szz[col], errors="coerce")
    if vals.notna().sum() < 1000:
        continue
    df_szz[f"log_{col}"] = np.log1p(vals)
    print(f"\n  {col} → SZZ bugs (within-author):")
    within_author_lpm(df_szz, f"log_{col}", "szz_buggy", label=f"{col}->bugs")


# ════════════════════════════════════════════════════════════════════
# 4. AI vs HUMAN REVIEW DYNAMICS
# ════════════════════════════════════════════════════════════════════
print("\n\n" + "=" * 70)
print("4. AI vs HUMAN REVIEW DYNAMICS (recent 3 months)")
print("=" * 70)

ai_recent = recent[recent["ai_tagged"]]
human_recent = recent[~recent["ai_tagged"]]

print(f"\n  AI PRs: {len(ai_recent):,}, Human PRs: {len(human_recent):,}")

for col in review_cols:
    a_vals = pd.to_numeric(ai_recent[col], errors="coerce").dropna()
    h_vals = pd.to_numeric(human_recent[col], errors="coerce").dropna()
    if len(a_vals) < 30 or len(h_vals) < 30:
        continue
    a_med = a_vals.median()
    h_med = h_vals.median()
    try:
        _, p = stats.mannwhitneyu(a_vals, h_vals, alternative="two-sided")
        sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""
    except Exception:
        p = 1.0
        sig = ""
    print(f"  {col:>30s}: AI med={a_med:8.1f}, Human med={h_med:8.1f}, "
          f"ratio={a_med/h_med if h_med != 0 else float('inf'):5.2f}x, p={p:.4f} {sig}")


# ════════════════════════════════════════════════════════════════════
# 5. SPEC ADOPTION CURVES
# ════════════════════════════════════════════════════════════════════
print("\n\n" + "=" * 70)
print("5. SPEC ADOPTION CURVES BY REPO TYPE")
print("=" * 70)

df["month"] = df["merged_at"].dt.to_period("M")

# Overall adoption
monthly = df.groupby("month").agg(
    n=("specd", "count"),
    spec_rate=("specd", "mean"),
    ai_rate=("ai_tagged", "mean"),
    bug_rate=("szz_buggy", "mean"),
    rework_rate=("reworked", "mean"),
).reset_index()
monthly = monthly[monthly["n"] >= 100]

print(f"\n  {'Month':>10s}  {'N':>7s}  {'Spec%':>6s}  {'AI%':>6s}  {'Bug%':>6s}  {'Rework%':>8s}")
print(f"  {'─'*10}  {'─'*7}  {'─'*6}  {'─'*6}  {'─'*6}  {'─'*8}")
for _, row in monthly.iterrows():
    print(f"  {str(row['month']):>10s}  {row['n']:7,.0f}  {row['spec_rate']*100:5.1f}%  "
          f"{row['ai_rate']*100:5.1f}%  {row['bug_rate']*100:5.1f}%  {row['rework_rate']*100:7.1f}%")

# By AI adoption tier
print("\n\n  --- Adoption curves by repo AI tier ---")

repo_ai_rate = df.groupby("repo")["ai_tagged"].mean()
zero_ai = set(repo_ai_rate[repo_ai_rate == 0].index)
high_ai = set(repo_ai_rate[repo_ai_rate >= repo_ai_rate.quantile(0.75)].index)
low_ai = set(repo_ai_rate.index) - zero_ai - high_ai

for tier_label, tier_repos in [("Zero-AI repos", zero_ai),
                                ("Low-AI repos", low_ai),
                                ("High-AI repos", high_ai)]:
    tier_df = df[df["repo"].isin(tier_repos)]
    tier_monthly = tier_df.groupby("month").agg(
        n=("specd", "count"),
        spec_rate=("specd", "mean"),
        bug_rate=("szz_buggy", "mean"),
    ).reset_index()
    tier_monthly = tier_monthly[tier_monthly["n"] >= 50]

    print(f"\n  {tier_label} ({len(tier_repos)} repos, {len(tier_df):,} PRs):")
    print(f"  {'Month':>10s}  {'N':>6s}  {'Spec%':>6s}  {'Bug%':>6s}")
    for _, row in tier_monthly.iterrows():
        print(f"  {str(row['month']):>10s}  {row['n']:6,.0f}  {row['spec_rate']*100:5.1f}%  "
              f"{row['bug_rate']*100:5.1f}%")


# ════════════════════════════════════════════════════════════════════
# 6. DO REPOS THAT ADOPT SPECS EARLIER SHOW TRAJECTORY CHANGE?
# ════════════════════════════════════════════════════════════════════
print("\n\n" + "=" * 70)
print("6. SPEC ADOPTION AND DEFECT TRAJECTORY (repo-level)")
print("=" * 70)

# For each repo with enough data, compare bug rate before and after spec adoption
szz_df = df[df["repo"].isin(szz_repos)].copy()

print("\n  Per-repo before/after spec adoption comparison:")
print(f"  {'Repo':>40s}  {'Pre-spec bug%':>14s}  {'Post-spec bug%':>15s}  {'Δ':>8s}")
print(f"  {'─'*40}  {'─'*14}  {'─'*15}  {'─'*8}")

results = []
for repo in sorted(szz_df["repo"].unique()):
    repo_df = szz_df[szz_df["repo"] == repo].copy()
    if len(repo_df) < 100:
        continue
    if repo_df["specd"].sum() < 10:
        continue

    # Find first spec'd PR date
    first_spec = repo_df[repo_df["specd"]]["merged_at"].min()
    pre = repo_df[repo_df["merged_at"] < first_spec]
    post = repo_df[repo_df["merged_at"] >= first_spec]

    if len(pre) < 20 or len(post) < 20:
        continue

    pre_bug = pre["szz_buggy"].mean()
    post_bug = post["szz_buggy"].mean()
    delta = post_bug - pre_bug
    results.append({"repo": repo, "pre": pre_bug, "post": post_bug,
                    "delta": delta, "n_pre": len(pre), "n_post": len(post)})
    print(f"  {repo:>40s}  {pre_bug*100:13.1f}%  {post_bug*100:14.1f}%  {delta*100:+7.1f}pp")

if results:
    deltas = [r["delta"] for r in results]
    mean_delta = np.mean(deltas)
    median_delta = np.median(deltas)
    n_improved = sum(1 for d in deltas if d < 0)
    n_worsened = sum(1 for d in deltas if d > 0)
    t_stat, t_p = stats.ttest_1samp(deltas, 0)
    print(f"\n  Summary ({len(results)} repos with enough data):")
    print(f"  Mean Δ bug rate: {mean_delta*100:+.2f}pp")
    print(f"  Median Δ bug rate: {median_delta*100:+.2f}pp")
    print(f"  Improved: {n_improved}, Worsened: {n_worsened}")
    print(f"  t-test H0: Δ=0: t={t_stat:.3f}, p={t_p:.4f}")
