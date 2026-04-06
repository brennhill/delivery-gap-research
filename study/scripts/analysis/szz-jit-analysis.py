#!/usr/bin/env python3
"""
Approximate SZZ bug-introduction analysis and JIT feature comparison
by spec quality tier, using the 43-repo master-prs.csv dataset.
"""

import pandas as pd
import numpy as np
from scipy.stats import fisher_exact
import statsmodels.api as sm
import warnings
from pathlib import Path
import sys
# Only suppress specific known-harmless warnings, not everything.
warnings.filterwarnings("ignore", message=".*divide by zero.*")
warnings.filterwarnings("ignore", message=".*invalid value.*")

UTIL_DIR = Path(__file__).resolve().parents[1] / "util"
if str(UTIL_DIR) not in sys.path:
    sys.path.insert(0, str(UTIL_DIR))

from quality_tiers import (  # noqa: E402
    BOTTOM_75,
    TOP_10,
    TOP_25_ONLY,
    TIER_ORDER,
    TIER_DISPLAY,
    UNSCORED,
    quality_tier,
)

CSV = "/Users/brenn/dev/ai-augmented-dev/research/study/data/master-prs.csv"

# ── Load data ──────────────────────────────────────────────────────────────
df = pd.read_csv(CSV, low_memory=False)
print(f"Loaded {len(df):,} PRs across {df['repo'].nunique()} repos")
print(f"\nAll columns ({len(df.columns)}):")
for i, c in enumerate(df.columns):
    print(f"  {i+1:2d}. {c}")

# Parse dates
df["merged_at"] = pd.to_datetime(df["merged_at"], utc=True, errors="coerce")

# Ensure boolean columns — fillna(False) first so NaN doesn't become True
for col in ["reworked", "escaped", "strict_escaped"]:
    df[col] = df[col].fillna(False).astype(bool)

# ── Quality tiers ──────────────────────────────────────────────────────────
def q_tier(val):
    if pd.isna(val):
        return UNSCORED
    return quality_tier(val)

df["q_tier"] = df["q_overall"].apply(q_tier)
print(f"\nSpec quality tier distribution:")
for tier in [*TIER_ORDER, UNSCORED]:
    n_tier = (df["q_tier"] == tier).sum()
    print(f"  {TIER_DISPLAY.get(tier, 'Unscored'):<26} {n_tier:>8,}")

# ══════════════════════════════════════════════════════════════════════════
# ANALYSIS 1: Approximate SZZ
# ══════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("ANALYSIS 1: APPROXIMATE SZZ BUG-INTRODUCTION")
print("=" * 70)

# Step 1: Identify fix PRs
fix_pattern = r"\b(fix|revert|hotfix|bug)\b"
df["is_fix"] = df["title"].str.contains(fix_pattern, case=False, na=False)
n_fix = df["is_fix"].sum()
print(f"\nFix PRs identified: {n_fix:,} / {len(df):,} ({n_fix/len(df)*100:.1f}%)")
print(f"  Pattern: title contains 'fix', 'revert', 'hotfix', or 'bug' (word boundary)")

# Step 2: For each fix PR, mark the immediately preceding PR in the
# same repo as a candidate bug-introducer.
# (No file-level overlap data in CSV, so we use temporal heuristic.)
df_sorted = df.sort_values(["repo", "merged_at"]).reset_index(drop=True)

# Build a set of candidate bug-introducing PRs by (repo, pr_number).
# We use PR identity — NOT positional indices — because df_sorted has
# different row ordering than df. Using positional indices would label
# the wrong PRs.
buggy_prs = set()  # set of (repo, pr_number) tuples
fix_link_count = 0

for repo, group in df_sorted.groupby("repo"):
    fix_rows = group[group["is_fix"]]
    for _, fix_row in fix_rows.iterrows():
        fix_date = fix_row["merged_at"]
        if pd.isna(fix_date):
            continue
        # Find PRs merged before the fix, within 90 days
        window_start = fix_date - pd.Timedelta(days=90)
        candidates = group[
            (group["merged_at"] < fix_date)
            & (group["merged_at"] >= window_start)
            & (~group["is_fix"])  # don't blame other fixes
        ]
        if len(candidates) > 0:
            # Take the most recent prior PR as the candidate bug-introducer
            best = candidates.loc[candidates["merged_at"].idxmax()]
            buggy_prs.add((repo, best["pr_number"]))
            fix_link_count += 1

# Mark bug-introducing PRs on the original df using PR identity
df["szz_buggy"] = df.apply(
    lambda row: (row["repo"], row["pr_number"]) in buggy_prs, axis=1
)

print(f"Bug-introducing candidates identified: {df['szz_buggy'].sum():,}")
print(f"Fix→candidate links created: {fix_link_count:,}")

# Step 3: SZZ buggy rate by spec quality tier
print(f"\n{'Tier':<10} {'N':>6} {'SZZ Buggy':>10} {'Rate':>8}  {'strict_escaped':>15} {'Esc Rate':>9}")
print("-" * 65)
for tier in [*TIER_ORDER, UNSCORED]:
    subset = df[df["q_tier"] == tier]
    n = len(subset)
    buggy = subset["szz_buggy"].sum()
    rate = buggy / n if n > 0 else 0
    esc = subset["strict_escaped"].sum()
    esc_rate = esc / n if n > 0 else 0
    label = TIER_DISPLAY.get(tier, "Unscored")
    print(f"{label:<26} {n:>6,} {buggy:>10,} {rate:>8.3f}  {esc:>15,} {esc_rate:>9.3f}")

# Step 4: Fisher's exact test top decile vs bottom 75%
spec_df = df[df["q_tier"].isin([TOP_10, BOTTOM_75])]
high = spec_df[spec_df["q_tier"] == TOP_10]
low = spec_df[spec_df["q_tier"] == BOTTOM_75]

# SZZ buggy contingency table
table_szz = np.array([
    [high["szz_buggy"].sum(), (~high["szz_buggy"]).sum()],
    [low["szz_buggy"].sum(), (~low["szz_buggy"]).sum()],
])
odds_szz, p_szz = fisher_exact(table_szz)
print(f"\nFisher's exact (SZZ buggy): TOP10 vs BOTTOM75")
print(f"  TOP10: {high['szz_buggy'].mean():.3f}  BOTTOM75: {low['szz_buggy'].mean():.3f}")
print(f"  Odds ratio: {odds_szz:.3f}, p = {p_szz:.4f}")

# Strict escaped comparison
table_esc = np.array([
    [high["strict_escaped"].sum(), (~high["strict_escaped"]).sum()],
    [low["strict_escaped"].sum(), (~low["strict_escaped"]).sum()],
])
odds_esc, p_esc = fisher_exact(table_esc)
print(f"\nFisher's exact (strict_escaped): TOP10 vs BOTTOM75")
print(f"  TOP10: {high['strict_escaped'].mean():.3f}  BOTTOM75: {low['strict_escaped'].mean():.3f}")
print(f"  Odds ratio: {odds_esc:.3f}, p = {p_esc:.4f}")

# Reworked comparison
table_rw = np.array([
    [high["reworked"].sum(), (~high["reworked"]).sum()],
    [low["reworked"].sum(), (~low["reworked"]).sum()],
])
odds_rw, p_rw = fisher_exact(table_rw)
print(f"\nFisher's exact (reworked): TOP10 vs BOTTOM75")
print(f"  TOP10: {high['reworked'].mean():.3f}  BOTTOM75: {low['reworked'].mean():.3f}")
print(f"  Odds ratio: {odds_rw:.3f}, p = {p_rw:.4f}")

# ══════════════════════════════════════════════════════════════════════════
# ANALYSIS 2: JIT FEATURE COMPARISON
# ══════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("ANALYSIS 2: JIT FEATURE COMPARISON BY SPEC QUALITY TIER")
print("=" * 70)

# Available JIT-style features from the CSV
jit_features = {
    "additions": "Lines added (la)",
    "deletions": "Lines deleted (ld)",
    "lines_changed": "Lines changed (lt)",
    "files_count": "Files changed (nf)",
    "review_cycles": "Review cycles",
    "time_to_merge_hours": "Time to merge (hrs)",
}

# Convert to numeric
for col in jit_features:
    df[col] = pd.to_numeric(df[col], errors="coerce")

# Only look at spec'd PRs (those with a quality score)
spec_only = df[df["q_tier"].isin(TIER_ORDER)].copy()
print(f"\nSpec'd PRs with quality scores: {len(spec_only):,}")

# Median table
print(f"\n{'Feature':<25} {'<58':>10} {'58-65':>10} {'66+':>10}  {'Interpretation'}")
print("-" * 85)
for col, label in jit_features.items():
    medians = {}
    for tier in TIER_ORDER:
        subset = spec_only[spec_only["q_tier"] == tier]
        medians[tier] = subset[col].median()
    # Interpretation
    if pd.notna(medians[TOP_10]) and pd.notna(medians[BOTTOM_75]):
        ratio = medians[TOP_10] / medians[BOTTOM_75] if medians[BOTTOM_75] > 0 else float("inf")
        if ratio > 1.2:
            interp = f"TOP10 {ratio:.1f}x larger"
        elif ratio < 0.8:
            interp = f"TOP10 {1/ratio:.1f}x smaller"
        else:
            interp = "~similar"
    else:
        interp = "N/A"
    print(f"{label:<25} {medians[BOTTOM_75]:>10.1f} {medians[TOP_25_ONLY]:>10.1f} {medians[TOP_10]:>10.1f}  {interp}")

# ── Logistic regression: strict_escaped ~ q_overall + JIT features ─────
print("\n" + "-" * 70)
print("LOGISTIC REGRESSION: strict_escaped ~ q_overall + JIT features")
print("-" * 70)

reg_cols = ["q_overall", "additions", "deletions", "files_count",
            "review_cycles", "time_to_merge_hours"]
reg_df = spec_only[["strict_escaped"] + reg_cols].dropna().copy()
reg_df["strict_escaped"] = reg_df["strict_escaped"].astype(int)

# Log-transform skewed size features (add 1 to avoid log(0))
for col in ["additions", "deletions", "files_count"]:
    reg_df[f"log_{col}"] = np.log1p(reg_df[col])

iv_cols = ["q_overall", "log_additions", "log_deletions", "log_files_count",
           "review_cycles", "time_to_merge_hours"]

X = reg_df[iv_cols]
X = sm.add_constant(X)
y = reg_df["strict_escaped"]

print(f"\nRegression sample: {len(reg_df):,} PRs")
print(f"Outcome (strict_escaped): {y.sum():,} escapes ({y.mean()*100:.1f}%)")

if y.sum() >= 5:
    try:
        model = sm.Logit(y, X)
        result = model.fit(disp=0, maxiter=100)
        print("\n" + result.summary2().as_text())

        print("\nKey finding: q_overall coefficient")
        coef = result.params.get("q_overall", None)
        pval = result.pvalues.get("q_overall", None)
        if coef is not None:
            direction = "LOWER" if coef < 0 else "HIGHER"
            sig = "SIGNIFICANT" if pval < 0.05 else "NOT significant"
            print(f"  Coefficient: {coef:.4f} (higher quality → {direction} escape risk)")
            print(f"  p-value: {pval:.4f} ({sig} at α=0.05)")
            print(f"  After controlling for: log(additions), log(deletions), "
                  f"log(files_count), review_cycles, time_to_merge_hours")
    except Exception as e:
        print(f"  Logit failed: {e}")
else:
    print("  Too few escapes for logistic regression")

# ── Also try with reworked as DV ───────────────────────────────────────
print("\n" + "-" * 70)
print("LOGISTIC REGRESSION: reworked ~ q_overall + JIT features")
print("-" * 70)

reg_df2 = spec_only[["reworked"] + reg_cols].dropna().copy()
reg_df2["reworked"] = reg_df2["reworked"].astype(int)
for col in ["additions", "deletions", "files_count"]:
    reg_df2[f"log_{col}"] = np.log1p(reg_df2[col])

X2 = reg_df2[iv_cols]
X2 = sm.add_constant(X2)
y2 = reg_df2["reworked"]

print(f"\nRegression sample: {len(reg_df2):,} PRs")
print(f"Outcome (reworked): {y2.sum():,} reworks ({y2.mean()*100:.1f}%)")

if y2.sum() >= 5:
    try:
        model2 = sm.Logit(y2, X2)
        result2 = model2.fit(disp=0, maxiter=100)
        print("\n" + result2.summary2().as_text())

        print("\nKey finding: q_overall coefficient")
        coef2 = result2.params.get("q_overall", None)
        pval2 = result2.pvalues.get("q_overall", None)
        if coef2 is not None:
            direction2 = "LOWER" if coef2 < 0 else "HIGHER"
            sig2 = "SIGNIFICANT" if pval2 < 0.05 else "NOT significant"
            print(f"  Coefficient: {coef2:.4f} (higher quality → {direction2} rework risk)")
            print(f"  p-value: {pval2:.4f} ({sig2} at α=0.05)")
            print(f"  After controlling for: log(additions), log(deletions), "
                  f"log(files_count), review_cycles, time_to_merge_hours")
    except Exception as e:
        print(f"  Logit failed: {e}")
else:
    print("  Too few reworks for logistic regression")

# ── Summary ────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
print("CAVEATS")
print("=" * 70)
print("""
1. Approximate SZZ: Without file-level overlap, we use a temporal heuristic
   (most recent non-fix PR in same repo within 90 days). This will have
   both false positives and false negatives.
2. Spec quality is only available for {n_spec} of {n_total} PRs ({pct:.0f}%).
   Unspec'd PRs are excluded from tier comparisons.
3. The fix-PR regex is broad — 'fix' in a title could be a typo fix,
   not a bug fix. This inflates the fix count.
4. JIT features are limited to what's in the CSV (no subsystem/directory
   counts, no author experience metrics).
5. N for spec'd PRs is {n_spec} — adequate for regressions but modest.
""".format(
    n_spec=len(spec_only),
    n_total=len(df),
    pct=len(spec_only) / len(df) * 100,
))
