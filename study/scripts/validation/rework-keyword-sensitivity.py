#!/usr/bin/env python3
"""
Sensitivity analysis: rework with and without keyword matching.

The rework measure in the study classifies a PR as reworked if a subsequent PR
(a) modifies overlapping files AND (b) has fix/revert/bugfix keywords in the
title or description. A reviewer concern is that repos with structured workflows
(high spec rates) also label fixes more consistently, inflating rework detection
for spec'd PRs (measurement coupling).

This script tests whether the spec-rework association holds when using a
keyword-free rework definition (file overlap only, no keyword requirement).

Approach:
  1. Load all PRs from master-prs.csv with file lists from prs-*.json
  2. Compute two rework measures:
     a. keyword_rework: file overlap + fix/revert keywords in title or body
     b. overlap_rework: file overlap only (keyword-free)
  3. Run within-author LPM for specs -> each rework measure
  4. Compare coefficients — if they're similar, measurement coupling is not
     driving the result

Note: We define "subsequent" as merged within 90 days after the target PR.
We require at least 1 overlapping file between source and target.
"""

import json
import re
from pathlib import Path
from datetime import timedelta

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy.stats import spearmanr
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

# ── Load data ──────────────────────────────────────────────────────────

df = pd.read_csv(DATA_DIR / "master-prs.csv", low_memory=False)
df["merged_at"] = pd.to_datetime(df["merged_at"], utc=True, errors="coerce")

for col in ["specd", "reworked"]:
    df[col] = df[col].fillna(False).astype(bool)

# Bot exclusion
df["is_bot"] = df["f_is_bot_author"].fillna(False).astype(bool)
n_bots = df["is_bot"].sum()
df = df[~df["is_bot"]].copy()
print(f"Bot exclusion: {n_bots:,} removed, {len(df):,} remaining")

# ── Load file lists and bodies from prs-*.json ─────────────────────────

# Build mappings: (repo, pr_number) -> set of files, and -> body text
pr_files = {}
pr_bodies = {}
prs_json_files = sorted(DATA_DIR.glob("prs-*.json"))
print(f"Loading file lists from {len(prs_json_files)} prs-*.json files...")

for pf in prs_json_files:
    try:
        prs_data = json.load(open(pf))
    except (json.JSONDecodeError, OSError):
        continue

    for pr in prs_data:
        repo = pr.get("repo", "")
        num = pr.get("pr_number")
        files = pr.get("files", [])
        body = pr.get("body", "") or ""
        if num is not None:
            key = (repo, int(num))
            if files:
                pr_files[key] = set(files)
            pr_bodies[key] = body

print(f"Loaded file lists for {len(pr_files):,} PRs")
print(f"Loaded bodies for {len(pr_bodies):,} PRs")

# Sanity check: how many df PRs have file lists?
df_keys = set(zip(df["repo"], df["pr_number"].astype(int)))
matched = df_keys & set(pr_files.keys())
print(f"PRs in df with file lists: {len(matched):,} / {len(df):,} ({len(matched)/len(df)*100:.1f}%)")

# ── Compute rework measures ────────────────────────────────────────────

REWORK_WINDOW_DAYS = 90

# Fix/revert keywords (same as the pipeline's heuristic classifier)
FIX_PATTERN = re.compile(
    r"\b(fix|fixes|fixed|fixing|revert|reverts|reverted|reverting|"
    r"bugfix|bug-fix|hotfix|hot-fix|regression|broke|broken)\b",
    re.IGNORECASE,
)

# Group PRs by repo for pairwise comparison
repos = df["repo"].unique()
keyword_reworked = set()  # (repo, pr_number) pairs
overlap_reworked = set()  # (repo, pr_number) pairs

print(f"Computing rework measures across {len(repos)} repos...")

for i, repo in enumerate(repos):
    repo_df = df[df["repo"] == repo].sort_values("merged_at").copy()
    repo_df = repo_df[repo_df["merged_at"].notna()]

    if len(repo_df) < 2:
        continue

    # Build arrays for efficient comparison
    pr_list = []
    for _, row in repo_df.iterrows():
        num = int(row["pr_number"])
        key = (repo, num)
        files = pr_files.get(key, set())
        title = str(row.get("title", ""))
        body = pr_bodies.get(key, "")
        pr_list.append({
            "num": num,
            "merged_at": row["merged_at"],
            "files": files,
            "title": title,
            "title_body": title + " " + body,  # Combined for keyword search
        })

    # For each PR (target), check if any later PR (source) overlaps its files
    for t_idx, target in enumerate(pr_list):
        if not target["files"]:
            continue

        for s_idx in range(t_idx + 1, len(pr_list)):
            source = pr_list[s_idx]

            # Check time window
            delta = source["merged_at"] - target["merged_at"]
            if delta > timedelta(days=REWORK_WINDOW_DAYS):
                break  # Sorted by merge date, all subsequent also beyond window
            if delta < timedelta(0):
                # Should not happen after sort, but guard against it
                continue

            # Check file overlap
            if not source["files"]:
                continue
            overlap = target["files"] & source["files"]
            if not overlap:
                continue

            # Keyword-free: any file overlap within window = rework
            overlap_reworked.add((repo, target["num"]))

            # Keyword: file overlap + fix/revert in source title or body
            if FIX_PATTERN.search(source["title_body"]):
                keyword_reworked.add((repo, target["num"]))

    if (i + 1) % 20 == 0:
        print(f"  Processed {i + 1}/{len(repos)} repos...")

print(f"\nRework counts:")
print(f"  Keyword rework (file overlap + keywords): {len(keyword_reworked):,}")
print(f"  Overlap rework (file overlap only):       {len(overlap_reworked):,}")
print(f"  Original 'reworked' column in CSV:        {df['reworked'].sum():,}")

# Add to dataframe (vectorized via isin)
df_key = list(zip(df["repo"], df["pr_number"].astype(int)))
df["keyword_rework"] = pd.Series(df_key).isin(keyword_reworked).values
df["overlap_rework"] = pd.Series(df_key).isin(overlap_reworked).values

# Concordance: how well does the recomputed keyword_rework match the pipeline?
both = (df["reworked"] & df["keyword_rework"]).sum()
pipeline_only = (df["reworked"] & ~df["keyword_rework"]).sum()
recomputed_only = (~df["reworked"] & df["keyword_rework"]).sum()
neither = (~df["reworked"] & ~df["keyword_rework"]).sum()
print(f"\nConcordance: recomputed keyword_rework vs pipeline reworked:")
print(f"  Both reworked:         {both:,}")
print(f"  Pipeline only:         {pipeline_only:,}")
print(f"  Recomputed only:       {recomputed_only:,}")
print(f"  Neither:               {neither:,}")
agreement = (both + neither) / len(df) * 100
print(f"  Agreement rate:        {agreement:.1f}%")
if (both + pipeline_only) > 0:
    print(f"  Recomputed captures:   {both / (both + pipeline_only) * 100:.1f}% of pipeline rework")

# ── Within-author LPM ──────────────────────────────────────────────────

SIZE_CONTROLS = ["log_adds", "log_dels", "log_files"]
df["log_adds"] = np.log1p(df["additions"].fillna(0))
df["log_dels"] = np.log1p(df["deletions"].fillna(0))
df["log_files"] = np.log1p(df["files_count"].fillna(0))


def within_author_lpm(data, treatment_col, outcome_col, label=""):
    """Within-author LPM with author demeaning and clustered SEs."""
    controls = SIZE_CONTROLS

    ac = data["author"].value_counts()
    multi = data[data["author"].isin(ac[ac >= 2].index)].copy()
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

    # Count identifying authors (those with treatment variation)
    author_var = multi.groupby("author")[treatment_col].agg(["min", "max"])
    n_with_var = (author_var["min"] != author_var["max"]).sum()

    # Demean by author
    for col in [treatment_col] + controls + [outcome_col]:
        multi[f"{col}_dm"] = (
            multi[col] - multi.groupby("author")[col].transform("mean")
        )

    y = multi[f"{outcome_col}_dm"]
    X_cols = [f"{treatment_col}_dm"] + [f"{c}_dm" for c in controls]
    X = multi[X_cols]

    try:
        model = sm.OLS(y, X, hasconst=False).fit(
            cov_type="cluster",
            cov_kwds={"groups": multi["author"]},
            disp=0,
        )
    except Exception as e:
        print(f"  [{label}] OLS failed: {e}")
        return None

    coef = model.params[f"{treatment_col}_dm"]
    pval = model.pvalues[f"{treatment_col}_dm"]

    return {
        "coef": coef,
        "p": pval,
        "n": len(multi),
        "authors_with_variation": n_with_var,
    }


# ── Run comparisons ───────────────────────────────────────────────────

print("\n" + "=" * 70)
print("SENSITIVITY: Specs -> Rework with and without keyword matching")
print("=" * 70)

# Descriptive: rework rates by spec status
for rw_col, rw_name in [
    ("reworked", "Original (from pipeline)"),
    ("keyword_rework", "Keyword rework (recomputed)"),
    ("overlap_rework", "Overlap-only rework"),
]:
    specd_rate = df.loc[df["specd"], rw_col].mean()
    unspecd_rate = df.loc[~df["specd"], rw_col].mean()
    total_rate = df[rw_col].mean()
    print(f"\n  {rw_name}:")
    print(f"    Overall rate:  {total_rate:.3f} ({df[rw_col].sum():,} PRs)")
    print(f"    Spec'd rate:   {specd_rate:.3f}")
    print(f"    Unspec'd rate: {unspecd_rate:.3f}")
    if unspecd_rate > 0:
        print(f"    Raw ratio:     {specd_rate / unspecd_rate:.1f}x")

# Within-author LPM for each rework measure
print(f"\n{'─' * 70}")
print("Within-author LPM: specs -> rework")
print(f"{'─' * 70}")

df["specd_int"] = df["specd"].astype(int)

for rw_col, rw_name in [
    ("reworked", "Original (from pipeline)"),
    ("keyword_rework", "Keyword rework (recomputed)"),
    ("overlap_rework", "Overlap-only rework (no keywords)"),
]:
    df[f"{rw_col}_int"] = df[rw_col].astype(int)
    r = within_author_lpm(df, "specd_int", f"{rw_col}_int", label=rw_name)
    if r:
        print(f"\n  {rw_name}:")
        print(f"    coef = {r['coef']:.4f}, p = {r['p']:.6f}")
        print(f"    N = {r['n']:,}, identifying authors = {r['authors_with_variation']}")
        print(f"    Interpretation: {r['coef']*100:.1f}pp {'increase' if r['coef'] > 0 else 'decrease'}")

# ── Check measurement coupling directly ────────────────────────────────

print(f"\n{'─' * 70}")
print("Measurement coupling check: repo-level spec rate vs rework detection")
print(f"{'─' * 70}")

repo_stats = df.groupby("repo").agg(
    n=("pr_number", "count"),
    spec_rate=("specd", "mean"),
    keyword_rw_rate=("keyword_rework", "mean"),
    overlap_rw_rate=("overlap_rework", "mean"),
    original_rw_rate=("reworked", "mean"),
).query("n >= 50")

for rw_col, rw_name in [
    ("original_rw_rate", "Original rework"),
    ("keyword_rw_rate", "Keyword rework"),
    ("overlap_rw_rate", "Overlap-only rework"),
]:
    rho, p = spearmanr(repo_stats["spec_rate"], repo_stats[rw_col])
    print(f"  Spec rate vs {rw_name}: rho = {rho:.3f} (p = {p:.4f})")

print("\nDone.")
