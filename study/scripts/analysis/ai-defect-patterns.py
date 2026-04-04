#!/usr/bin/env python3
"""
AI defect patterns: How do AI-introduced bugs differ from human bugs?

Questions:
  1. Are AI bugs caught faster (time from introduction to fix)?
  2. Do AI bugs cluster in different file types?
  3. Are AI bugs bigger or smaller fixes?
  4. Are AI bugs more likely to be reworked vs caught by SZZ?
  5. Do AI bugs affect different subsystems?
"""

import pandas as pd
import numpy as np
from scipy import stats
from pathlib import Path
from collections import Counter

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

df = pd.read_csv(DATA_DIR / "master-prs.csv", low_memory=False)
szz = pd.read_csv(DATA_DIR / "szz-results-merged.csv")

df["merged_at"] = pd.to_datetime(df["merged_at"], utc=True, errors="coerce")
for col in ["reworked", "specd"]:
    df[col] = df[col].fillna(False).astype(bool)
df["ai_tagged"] = df["f_ai_tagged"].fillna(False).astype(bool)

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

# SZZ merge — keep the full blame link data for time-to-fix analysis
bug_prs = szz[["repo", "bug_pr_number"]].drop_duplicates()
bug_prs = bug_prs.rename(columns={"bug_pr_number": "pr_number"})
bug_prs["szz_buggy"] = True
df = df.merge(bug_prs, on=["repo", "pr_number"], how="left")
df["szz_buggy"] = df["szz_buggy"].fillna(False).astype(bool)

szz_repos = set(szz["repo"].unique())
df_szz = df[df["repo"].isin(szz_repos)].copy()

# Recent window
cutoff = pd.Timestamp("2026-01-01", tz="UTC")
recent = df_szz[df_szz["merged_at"] >= cutoff].copy()

print(f"Dataset: {len(df_szz):,} PRs in SZZ repos (bots excluded)")
print(f"Recent (Jan-Mar 2026): {len(recent):,}")
print(f"AI-tagged: {df_szz['ai_tagged'].sum():,} ({df_szz['ai_tagged'].mean():.1%})")


# ════════════════════════════════════════════════════════════════════
# 1. TIME FROM BUG INTRODUCTION TO FIX
# ════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("1. TIME FROM BUG INTRODUCTION TO FIX")
print("=" * 70)

# SZZ has fix_pr_number and bug_pr_number — we can compute time between them
# Need to get merge dates for both
pr_dates = df[["repo", "pr_number", "merged_at", "ai_tagged"]].copy()
pr_dates = pr_dates.rename(columns={"pr_number": "bug_pr_number",
                                     "merged_at": "bug_merged_at",
                                     "ai_tagged": "bug_ai_tagged"})

fix_dates = df[["repo", "pr_number", "merged_at"]].copy()
fix_dates = fix_dates.rename(columns={"pr_number": "fix_pr_number",
                                       "merged_at": "fix_merged_at"})

# Merge SZZ blame links with dates
szz_with_dates = szz.merge(pr_dates, on=["repo", "bug_pr_number"], how="inner")
szz_with_dates = szz_with_dates.merge(fix_dates, on=["repo", "fix_pr_number"], how="inner")

# Deduplicate: one row per (bug_pr, fix_pr) pair
szz_pairs = szz_with_dates.drop_duplicates(
    subset=["repo", "bug_pr_number", "fix_pr_number"]
).copy()

szz_pairs["time_to_fix_hours"] = (
    (szz_pairs["fix_merged_at"] - szz_pairs["bug_merged_at"]).dt.total_seconds() / 3600
)

# Filter out negative (fix before bug — SZZ artifact) and very old (>365 days)
szz_pairs = szz_pairs[
    (szz_pairs["time_to_fix_hours"] > 0) &
    (szz_pairs["time_to_fix_hours"] < 365 * 24)
].copy()

ai_bugs = szz_pairs[szz_pairs["bug_ai_tagged"] == True]
human_bugs = szz_pairs[szz_pairs["bug_ai_tagged"] == False]

print(f"\n  Bug→fix pairs: {len(szz_pairs):,}")
print(f"  AI-introduced bugs: {len(ai_bugs):,}")
print(f"  Human-introduced bugs: {len(human_bugs):,}")

if len(ai_bugs) > 10:
    ai_ttf = ai_bugs["time_to_fix_hours"]
    human_ttf = human_bugs["time_to_fix_hours"]

    print(f"\n  Time to fix (hours):")
    print(f"  {'':>20s}  {'Median':>10s}  {'Mean':>10s}  {'p25':>10s}  {'p75':>10s}")
    print(f"  {'AI bugs':>20s}  {ai_ttf.median():10.1f}  {ai_ttf.mean():10.1f}  "
          f"{ai_ttf.quantile(0.25):10.1f}  {ai_ttf.quantile(0.75):10.1f}")
    print(f"  {'Human bugs':>20s}  {human_ttf.median():10.1f}  {human_ttf.mean():10.1f}  "
          f"{human_ttf.quantile(0.25):10.1f}  {human_ttf.quantile(0.75):10.1f}")

    # Days is more intuitive
    print(f"\n  Time to fix (days):")
    print(f"  {'AI bugs':>20s}  median={ai_ttf.median()/24:.1f} days")
    print(f"  {'Human bugs':>20s}  median={human_ttf.median()/24:.1f} days")

    _, p = stats.mannwhitneyu(ai_ttf, human_ttf, alternative="two-sided")
    sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""
    direction = "faster" if ai_ttf.median() < human_ttf.median() else "slower"
    print(f"\n  Mann-Whitney U: p={p:.4f} {sig}")
    print(f"  AI bugs are caught {direction} than human bugs")
else:
    print("  Too few AI bug→fix pairs for comparison")


# ════════════════════════════════════════════════════════════════════
# 2. FILE TYPE DISTRIBUTION OF BUGS
# ════════════════════════════════════════════════════════════════════
print("\n\n" + "=" * 70)
print("2. FILE TYPES WHERE BUGS ARE INTRODUCED")
print("=" * 70)

# Get file extensions from SZZ blame data
szz["file_ext"] = szz["file"].apply(
    lambda f: ("." + f.rsplit(".", 1)[-1].lower()) if isinstance(f, str) and "." in f else "none"
)

# Tag each blame link as AI or human
szz_tagged = szz.merge(
    df[["repo", "pr_number", "ai_tagged"]].rename(
        columns={"pr_number": "bug_pr_number", "ai_tagged": "bug_ai_tagged"}
    ),
    on=["repo", "bug_pr_number"],
    how="inner",
)

ai_exts = szz_tagged[szz_tagged["bug_ai_tagged"] == True]["file_ext"]
human_exts = szz_tagged[szz_tagged["bug_ai_tagged"] == False]["file_ext"]

print(f"\n  AI blame links: {len(ai_exts):,}")
print(f"  Human blame links: {len(human_exts):,}")

# Top 15 extensions
ai_counts = Counter(ai_exts)
human_counts = Counter(human_exts)
all_exts = set(e for e, _ in ai_counts.most_common(15)) | set(e for e, _ in human_counts.most_common(15))

# Compute rates
ai_total = len(ai_exts)
human_total = len(human_exts)

print(f"\n  {'Extension':>12s}  {'AI %':>8s}  {'Human %':>8s}  {'AI/Human':>10s}")
print(f"  {'─'*12}  {'─'*8}  {'─'*8}  {'─'*10}")

ext_data = []
for ext in sorted(all_exts, key=lambda e: -(ai_counts.get(e, 0) + human_counts.get(e, 0))):
    ai_pct = ai_counts.get(ext, 0) / ai_total * 100 if ai_total > 0 else 0
    human_pct = human_counts.get(ext, 0) / human_total * 100 if human_total > 0 else 0
    ratio = ai_pct / human_pct if human_pct > 0 else float("inf")
    ext_data.append((ext, ai_pct, human_pct, ratio))

ext_data.sort(key=lambda x: -(x[1] + x[2]))
for ext, ai_pct, human_pct, ratio in ext_data[:15]:
    print(f"  {ext:>12s}  {ai_pct:7.1f}%  {human_pct:7.1f}%  {ratio:9.2f}x")


# ════════════════════════════════════════════════════════════════════
# 3. FIX SIZE: AI BUGS vs HUMAN BUGS
# ════════════════════════════════════════════════════════════════════
print("\n\n" + "=" * 70)
print("3. FIX SIZE: HOW BIG ARE THE FIXES FOR AI vs HUMAN BUGS?")
print("=" * 70)

# Get fix PR sizes
fix_sizes = df[["repo", "pr_number", "additions", "deletions"]].copy()
fix_sizes = fix_sizes.rename(columns={
    "pr_number": "fix_pr_number",
    "additions": "fix_additions",
    "deletions": "fix_deletions",
})
fix_sizes["fix_churn"] = fix_sizes["fix_additions"].fillna(0) + fix_sizes["fix_deletions"].fillna(0)

# Deduplicate on fix_pr_number: each fix PR's size counted once,
# tagged by whether it fixes an AI or human bug. If a fix PR fixes
# both AI and human bugs, it appears in both groups (rare).
szz_fixes = szz_tagged.drop_duplicates(
    subset=["repo", "bug_pr_number", "fix_pr_number"]
).merge(fix_sizes, on=["repo", "fix_pr_number"], how="inner")

# For fix-size comparison, deduplicate per fix PR per AI tag
szz_fixes_dedup = szz_fixes.drop_duplicates(
    subset=["repo", "fix_pr_number", "bug_ai_tagged"]
)

ai_fixes = szz_fixes_dedup[szz_fixes_dedup["bug_ai_tagged"] == True]["fix_churn"].dropna()
human_fixes = szz_fixes_dedup[szz_fixes_dedup["bug_ai_tagged"] == False]["fix_churn"].dropna()

if len(ai_fixes) > 10:
    print(f"\n  Fix churn (lines changed to fix the bug):")
    print(f"  {'':>20s}  {'Median':>10s}  {'Mean':>10s}  {'p75':>10s}")
    print(f"  {'AI bug fixes':>20s}  {ai_fixes.median():10.1f}  {ai_fixes.mean():10.1f}  "
          f"{ai_fixes.quantile(0.75):10.1f}")
    print(f"  {'Human bug fixes':>20s}  {human_fixes.median():10.1f}  {human_fixes.mean():10.1f}  "
          f"{human_fixes.quantile(0.75):10.1f}")

    _, p = stats.mannwhitneyu(ai_fixes, human_fixes, alternative="two-sided")
    sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""
    print(f"\n  Mann-Whitney U: p={p:.4f} {sig}")


# ════════════════════════════════════════════════════════════════════
# 4. AI BUGS: REWORK vs SZZ DETECTION
# ════════════════════════════════════════════════════════════════════
print("\n\n" + "=" * 70)
print("4. HOW ARE BUGS DETECTED? REWORK vs SZZ")
print("=" * 70)

for label, subset in [("AI-tagged", df_szz[df_szz["ai_tagged"]]),
                       ("Human", df_szz[~df_szz["ai_tagged"]])]:
    n = len(subset)
    buggy = subset["szz_buggy"].sum()
    reworked = subset["reworked"].sum()
    both = ((subset["szz_buggy"]) & (subset["reworked"])).sum()
    either = ((subset["szz_buggy"]) | (subset["reworked"])).sum()

    print(f"\n  {label} PRs: {n:,}")
    print(f"    SZZ buggy:     {buggy:,} ({buggy/n*100:.1f}%)")
    print(f"    Reworked:      {reworked:,} ({reworked/n*100:.1f}%)")
    print(f"    Both:          {both:,} ({both/n*100:.1f}%)")
    print(f"    Either:        {either:,} ({either/n*100:.1f}%)")
    if buggy > 0:
        print(f"    Rework|buggy:  {both/buggy*100:.1f}% of SZZ bugs also reworked")


# ════════════════════════════════════════════════════════════════════
# 5. SUBSYSTEM CONCENTRATION
# ════════════════════════════════════════════════════════════════════
print("\n\n" + "=" * 70)
print("5. SUBSYSTEM CONCENTRATION OF BUGS")
print("=" * 70)

szz_tagged["subsystem"] = szz_tagged["file"].apply(
    lambda f: f.split("/")[0] if isinstance(f, str) and "/" in f else "(root)"
)

ai_subs = Counter(szz_tagged[szz_tagged["bug_ai_tagged"] == True]["subsystem"])
human_subs = Counter(szz_tagged[szz_tagged["bug_ai_tagged"] == False]["subsystem"])

# How concentrated are bugs?
ai_top5 = sum(c for _, c in ai_subs.most_common(5))
human_top5 = sum(c for _, c in human_subs.most_common(5))

print(f"\n  AI bugs: top 5 subsystems account for {ai_top5/ai_total*100:.1f}% of blame links")
print(f"  Human bugs: top 5 subsystems account for {human_top5/human_total*100:.1f}% of blame links")

print(f"\n  AI top 10 subsystems:")
for sub, count in ai_subs.most_common(10):
    print(f"    {sub:>30s}: {count:,} ({count/ai_total*100:.1f}%)")

print(f"\n  Human top 10 subsystems:")
for sub, count in human_subs.most_common(10):
    print(f"    {sub:>30s}: {count:,} ({count/human_total*100:.1f}%)")


# ════════════════════════════════════════════════════════════════════
# 6. SELF-FIX RATE: DO AUTHORS FIX THEIR OWN BUGS?
# ════════════════════════════════════════════════════════════════════
print("\n\n" + "=" * 70)
print("6. SELF-FIX RATE: WHO FIXES AI vs HUMAN BUGS?")
print("=" * 70)

# Get bug author and fix author
bug_authors = df[["repo", "pr_number", "author"]].rename(
    columns={"pr_number": "bug_pr_number", "author": "bug_author"}
)
fix_authors = df[["repo", "pr_number", "author"]].rename(
    columns={"pr_number": "fix_pr_number", "author": "fix_author"}
)

szz_authorship = szz_tagged.drop_duplicates(
    subset=["repo", "bug_pr_number", "fix_pr_number"]
).merge(bug_authors, on=["repo", "bug_pr_number"], how="inner"
).merge(fix_authors, on=["repo", "fix_pr_number"], how="inner")

szz_authorship["self_fix"] = szz_authorship["bug_author"] == szz_authorship["fix_author"]

ai_self = szz_authorship[szz_authorship["bug_ai_tagged"] == True]
human_self = szz_authorship[szz_authorship["bug_ai_tagged"] == False]

if len(ai_self) > 10:
    ai_self_rate = ai_self["self_fix"].mean()
    human_self_rate = human_self["self_fix"].mean()

    print(f"\n  AI bug self-fix rate:    {ai_self_rate:.1%} ({ai_self['self_fix'].sum()}/{len(ai_self)})")
    print(f"  Human bug self-fix rate: {human_self_rate:.1%} ({human_self['self_fix'].sum()}/{len(human_self)})")

    _, p = stats.fisher_exact([
        [ai_self["self_fix"].sum(), (~ai_self["self_fix"]).sum()],
        [human_self["self_fix"].sum(), (~human_self["self_fix"]).sum()],
    ])
    sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""
    print(f"  Fisher's exact: p={p:.4f} {sig}")
