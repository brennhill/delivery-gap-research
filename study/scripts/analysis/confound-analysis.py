#!/usr/bin/env python3
"""
Confound analysis for the "polished spec paradox."

The 43-repo study found that higher spec quality scores (q_overall) predict
MORE defects (rework, escapes), not fewer. The leading explanation is
confounding by indication: hard/risky work gets better specs AND more defects.

This script runs three analyses to test whether the paradox is real or an
artifact of confounding:

  1. Matched Pairs — match spec'd PRs to unspec'd PRs of similar size in the
     same repo, then compare outcomes.
  2. Within-Author — compare outcomes for the same author when they write
     specs vs when they don't (within same repo).
  3. Within-Author Quality Gradient — among authors with multiple spec'd PRs
     at varying quality levels, does higher quality predict worse outcomes?
     This is the strongest test: same person, same repo, varying quality.

Data: master-prs.csv from the 43-repo study (23,967 PRs).

Definitions:
  - spec'd PR: q_overall is not NaN (the PR body was scored for quality)
  - unspec'd PR: q_overall is NaN (no quality score — no spec content to score)
"""

import warnings
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

# ---------------------------------------------------------------------------
# Suppress only the specific mixed-type DtypeWarning from pandas CSV reader.
# Some formality columns have mixed types; we don't use them.
# ---------------------------------------------------------------------------
warnings.filterwarnings(
    "ignore",
    message="Columns.*have mixed types",
    category=pd.errors.DtypeWarning,
)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DATA_DIR = Path(__file__).parent / "data"
CSV_PATH = DATA_DIR / "master-prs.csv"
OUTPUT_DIR = DATA_DIR  # save output tables alongside source data

OUTCOMES = ["reworked", "escaped", "strict_escaped"]

# Matching caliper: max ratio between spec'd and unspec'd PR sizes.
# A caliper of 2.0 means the matched PR's size can be at most 2x or 0.5x
# the target PR's size.
SIZE_CALIPER = 2.0

# Minimum number of PRs per author-repo cell to include in within-author
MIN_PRS_PER_CELL = 2


def load_data() -> pd.DataFrame:
    """Load and validate the master PR dataset."""
    print("=" * 72)
    print("LOADING DATA")
    print("=" * 72)

    df = pd.read_csv(CSV_PATH, low_memory=False)
    print(f"  Loaded {len(df):,} PRs from {df['repo'].nunique()} repos")

    # Confirm required columns exist
    required = ["repo", "author", "additions", "deletions", "files_count",
                 "q_overall", "reworked", "escaped", "strict_escaped"]
    missing = [c for c in required if c not in df.columns]
    if missing:
        print(f"  FATAL: missing columns: {missing}")
        sys.exit(1)

    # Drop rows with no author (can't do within-author without it)
    n_before = len(df)
    df = df.dropna(subset=["author"])
    n_dropped = n_before - len(df)
    if n_dropped > 0:
        print(f"  Dropped {n_dropped} rows with missing author")

    # Compute PR size as additions + deletions
    df["size"] = df["additions"].fillna(0) + df["deletions"].fillna(0)

    # Ensure outcome columns are boolean (NaN-safe)
    for col in OUTCOMES:
        df[col] = df[col].fillna(False).astype(bool)

    # Define spec'd vs unspec'd — MUST use q_overall > 0 to match
    # jit-risk-analysis.py. Using just notna() includes PRs with q_overall == 0.
    df["has_spec"] = df["q_overall"].notna() & (df["q_overall"] > 0)

    n_specd = df["has_spec"].sum()
    n_unspecd = (~df["has_spec"]).sum()
    print(f"  Spec'd PRs (q_overall > 0): {n_specd:,}")
    print(f"  Unspec'd PRs (q_overall is NaN): {n_unspecd:,}")
    print(f"  q_overall range: {df['q_overall'].min():.0f} – {df['q_overall'].max():.0f}")
    print(f"  q_overall mean: {df['q_overall'].mean():.1f}, median: {df['q_overall'].median():.1f}")

    # Baseline outcome rates
    print("\n  Baseline outcome rates:")
    for col in OUTCOMES:
        rate_s = df.loc[df["has_spec"], col].mean()
        rate_u = df.loc[~df["has_spec"], col].mean()
        print(f"    {col:20s}  spec'd={rate_s:.3f}  unspec'd={rate_u:.3f}  "
              f"diff={rate_s - rate_u:+.3f}")

    return df


# ===================================================================
# ANALYSIS 1: MATCHED PAIRS
# ===================================================================
def analysis_matched_pairs(df: pd.DataFrame) -> pd.DataFrame:
    """
    For each spec'd PR, find the nearest-size unspec'd PR in the same repo.
    Use greedy nearest-neighbor matching with a size caliper.

    Returns a DataFrame of matched pairs with columns:
      specd_pr, unspecd_pr, repo, size_specd, size_unspecd, and outcomes.
    """
    print("\n" + "=" * 72)
    print("ANALYSIS 1: MATCHED PAIRS (same-repo, size-matched)")
    print("=" * 72)

    specd = df[df["has_spec"]].copy()
    unspecd = df[~df["has_spec"]].copy()

    print(f"  Starting pool: {len(specd):,} spec'd, {len(unspecd):,} unspec'd")

    pairs = []
    used_unspecd_idx = set()

    # Process repo by repo for same-repo matching
    repos = sorted(specd["repo"].unique())
    repos_with_matches = 0

    for repo in repos:
        s_repo = specd[specd["repo"] == repo].sort_values("size")
        u_repo = unspecd[unspecd["repo"] == repo]

        if len(u_repo) == 0:
            continue

        # Build array of available unspec'd sizes for fast lookup
        u_sizes = u_repo["size"].values
        u_indices = u_repo.index.values

        repos_with_matches += 1
        repo_pairs = 0

        for _, s_row in s_repo.iterrows():
            s_size = s_row["size"]

            # Find the closest unspec'd PR by size (that hasn't been used)
            available_mask = np.array([idx not in used_unspecd_idx for idx in u_indices])
            if not available_mask.any():
                break

            avail_sizes = u_sizes[available_mask]
            avail_indices = u_indices[available_mask]

            # Nearest neighbor
            diffs = np.abs(avail_sizes - s_size)
            best_pos = np.argmin(diffs)
            best_u_idx = avail_indices[best_pos]
            best_u_size = avail_sizes[best_pos]

            # Apply caliper: reject if size ratio exceeds threshold
            if s_size == 0 and best_u_size == 0:
                ratio = 1.0  # both zero-size, perfect match
            elif s_size == 0 or best_u_size == 0:
                continue  # one is zero, other isn't — skip
            else:
                ratio = max(s_size, best_u_size) / min(s_size, best_u_size)

            if ratio > SIZE_CALIPER:
                continue

            used_unspecd_idx.add(best_u_idx)

            pair = {
                "repo": repo,
                "specd_pr": s_row["pr_number"],
                "unspecd_pr": df.loc[best_u_idx, "pr_number"],
                "size_specd": s_size,
                "size_unspecd": best_u_size,
                "q_overall": s_row["q_overall"],
            }
            for col in OUTCOMES:
                pair[f"{col}_specd"] = s_row[col]
                pair[f"{col}_unspecd"] = df.loc[best_u_idx, col]

            pairs.append(pair)
            repo_pairs += 1

        # (no per-repo print to avoid noise — summary below)

    pairs_df = pd.DataFrame(pairs)
    print(f"\n  Matched {len(pairs_df):,} pairs across {repos_with_matches} repos")
    print(f"  Unmatched spec'd PRs: {len(specd) - len(pairs_df):,} "
          f"(no same-repo match within {SIZE_CALIPER}x size)")

    if len(pairs_df) == 0:
        print("  NO PAIRS FOUND — cannot proceed")
        return pairs_df

    # Size balance check
    size_ratio = pairs_df["size_specd"] / pairs_df["size_unspecd"].replace(0, np.nan)
    print(f"\n  Size balance (specd/unspecd ratio):")
    print(f"    mean={size_ratio.mean():.2f}, median={size_ratio.median():.2f}, "
          f"std={size_ratio.std():.2f}")

    # Compare outcomes using McNemar's test (appropriate for matched pairs)
    print(f"\n  {'Outcome':20s} {'Spec Rate':>10s} {'Unspec Rate':>12s} "
          f"{'Diff':>8s} {'McNemar χ²':>11s} {'p-value':>10s} {'Direction':>12s}")
    print("  " + "-" * 85)

    for col in OUTCOMES:
        s_vals = pairs_df[f"{col}_specd"].values
        u_vals = pairs_df[f"{col}_unspecd"].values

        rate_s = s_vals.mean()
        rate_u = u_vals.mean()
        diff = rate_s - rate_u

        # McNemar's test contingency table:
        #   b = spec'd positive, unspec'd negative (discordant)
        #   c = spec'd negative, unspec'd positive (discordant)
        b = ((s_vals) & (~u_vals)).sum()  # spec'd bad, unspec'd good
        c = ((~s_vals) & (u_vals)).sum()  # spec'd good, unspec'd bad

        # McNemar's test with continuity correction
        if b + c == 0:
            chi2, p = 0.0, 1.0
        else:
            # Use exact binomial test when b + c < 25 (small sample)
            if b + c < 25:
                # Exact McNemar: under H0, b ~ Binomial(b+c, 0.5)
                p = stats.binom_test(b, b + c, 0.5) if hasattr(stats, 'binom_test') else \
                    stats.binomtest(b, b + c, 0.5).pvalue
                chi2 = float("nan")  # not meaningful for exact test
            else:
                chi2 = (abs(b - c) - 1) ** 2 / (b + c)
                p = stats.chi2.sf(chi2, df=1)

        direction = "PARADOX HOLDS" if diff > 0 else "paradox gone"
        if p > 0.05:
            direction += " (ns)"

        print(f"  {col:20s} {rate_s:10.3f} {rate_u:12.3f} {diff:+8.3f} "
              f"{chi2:11.2f} {p:10.4f} {direction:>12s}")

        # Report discordant pair counts for transparency
        print(f"    (discordant pairs: b={b}, c={c}, concordant: "
              f"both_bad={((s_vals) & (u_vals)).sum()}, "
              f"both_good={((~s_vals) & (~u_vals)).sum()})")

    # Save matched pairs
    out_path = OUTPUT_DIR / "confound-matched-pairs.csv"
    pairs_df.to_csv(out_path, index=False)
    print(f"\n  Saved matched pairs to {out_path}")

    return pairs_df


# ===================================================================
# ANALYSIS 2: WITHIN-AUTHOR
# ===================================================================
def analysis_within_author(df: pd.DataFrame) -> pd.DataFrame:
    """
    Find authors who have BOTH spec'd and unspec'd PRs in the same repo.
    Compare their outcomes when they write specs vs when they don't.

    This is a within-subject design: the author is their own control.
    """
    print("\n" + "=" * 72)
    print("ANALYSIS 2: WITHIN-AUTHOR (same author, same repo)")
    print("=" * 72)

    # Group by (repo, author) and check for both spec'd and unspec'd PRs
    df["author_repo"] = df["author"] + "@@" + df["repo"]

    groups = df.groupby("author_repo").agg(
        n_specd=("has_spec", "sum"),
        n_unspecd=("has_spec", lambda x: (~x).sum()),
        n_total=("has_spec", "count"),
        repo=("repo", "first"),
        author=("author", "first"),
    )

    # Keep only author-repo pairs with at least MIN_PRS_PER_CELL of each type
    eligible = groups[
        (groups["n_specd"] >= MIN_PRS_PER_CELL) &
        (groups["n_unspecd"] >= MIN_PRS_PER_CELL)
    ]

    print(f"  Total author-repo pairs: {len(groups):,}")
    print(f"  Eligible (>= {MIN_PRS_PER_CELL} spec'd AND >= {MIN_PRS_PER_CELL} unspec'd): "
          f"{len(eligible):,}")
    print(f"  Covering {eligible['n_total'].sum():,} PRs "
          f"across {eligible['repo'].nunique()} repos "
          f"and {eligible['author'].nunique()} unique authors")

    if len(eligible) == 0:
        print("  NO ELIGIBLE AUTHOR-REPO PAIRS — cannot proceed")
        return pd.DataFrame()

    # Filter main dataframe to eligible author-repo pairs
    eligible_keys = set(eligible.index)
    df_elig = df[df["author_repo"].isin(eligible_keys)].copy()

    print(f"\n  Filtered to {len(df_elig):,} PRs from eligible author-repo pairs")

    # Compute within-author outcome rates
    print(f"\n  {'Outcome':20s} {'Spec Rate':>10s} {'Unspec Rate':>12s} "
          f"{'Diff':>8s} {'Test':>22s} {'p-value':>10s} {'Direction':>12s}")
    print("  " + "-" * 96)

    summary_rows = []

    for col in OUTCOMES:
        # Per author-repo: compute rate when spec'd vs unspec'd
        author_rates = []
        for ar_key in eligible_keys:
            ar_data = df_elig[df_elig["author_repo"] == ar_key]
            rate_s = ar_data.loc[ar_data["has_spec"], col].mean()
            rate_u = ar_data.loc[~ar_data["has_spec"], col].mean()
            n_s = ar_data["has_spec"].sum()
            n_u = (~ar_data["has_spec"]).sum()
            author_rates.append({
                "author_repo": ar_key,
                "rate_specd": rate_s,
                "rate_unspecd": rate_u,
                "diff": rate_s - rate_u,
                "n_specd": n_s,
                "n_unspecd": n_u,
            })

        rates_df = pd.DataFrame(author_rates)

        # Drop any rows where rates are NaN (shouldn't happen given filters, but be safe)
        n_before = len(rates_df)
        rates_df = rates_df.dropna(subset=["rate_specd", "rate_unspecd"])
        if len(rates_df) < n_before:
            print(f"    (dropped {n_before - len(rates_df)} author-repo pairs "
                  f"with NaN rates for {col})")

        mean_s = rates_df["rate_specd"].mean()
        mean_u = rates_df["rate_unspecd"].mean()
        mean_diff = rates_df["diff"].mean()

        # Paired t-test on within-author differences
        # (each author-repo pair contributes one difference score)
        diffs = rates_df["diff"].values
        if len(diffs) >= 2:
            t_stat, p_val = stats.ttest_rel(
                rates_df["rate_specd"].values,
                rates_df["rate_unspecd"].values
            )
            # Also run Wilcoxon signed-rank as robustness check
            # (doesn't assume normality of differences)
            try:
                w_stat, w_p = stats.wilcoxon(diffs, zero_method="wilcox")
            except ValueError:
                # All differences are zero
                w_stat, w_p = 0.0, 1.0
            test_str = f"t={t_stat:+.2f} (W p={w_p:.4f})"
        else:
            t_stat, p_val = float("nan"), float("nan")
            test_str = "N too small"

        direction = "PARADOX HOLDS" if mean_diff > 0 else "paradox gone"
        if p_val > 0.05:
            direction += " (ns)"

        print(f"  {col:20s} {mean_s:10.3f} {mean_u:12.3f} {mean_diff:+8.3f} "
              f"{test_str:>22s} {p_val:10.4f} {direction:>12s}")

        # Distribution of differences
        print(f"    diffs: mean={mean_diff:+.3f}, median={np.median(diffs):+.3f}, "
              f"std={np.std(diffs):.3f}, "
              f"authors_worse_with_spec={int((diffs > 0).sum())}/{len(diffs)}")

        summary_rows.append({
            "outcome": col,
            "n_author_repo_pairs": len(rates_df),
            "mean_rate_specd": mean_s,
            "mean_rate_unspecd": mean_u,
            "mean_diff": mean_diff,
            "t_stat": t_stat,
            "p_value": p_val,
            "direction": "paradox" if mean_diff > 0 else "expected",
        })

    summary_df = pd.DataFrame(summary_rows)
    out_path = OUTPUT_DIR / "confound-within-author.csv"
    summary_df.to_csv(out_path, index=False)
    print(f"\n  Saved within-author summary to {out_path}")

    return summary_df


# ===================================================================
# ANALYSIS 3: WITHIN-AUTHOR QUALITY GRADIENT
# ===================================================================
def analysis_quality_gradient(df: pd.DataFrame) -> pd.DataFrame:
    """
    Among authors with multiple spec'd PRs at VARYING quality levels,
    do higher-quality specs predict worse outcomes?

    This is the strongest test: same person, same repo, different spec
    quality — isolates spec quality from author ability and project risk.
    """
    print("\n" + "=" * 72)
    print("ANALYSIS 3: WITHIN-AUTHOR QUALITY GRADIENT")
    print("=" * 72)

    # Filter to spec'd PRs only (those with q_overall scores)
    specd = df[df["has_spec"]].copy()
    print(f"  Spec'd PRs with quality scores: {len(specd):,}")

    # Group by (author, repo) and require varying quality scores
    # "Varying" = at least 3 PRs with different q_overall values
    MIN_SPECD_PRS = 3

    groups = specd.groupby("author_repo").agg(
        n_prs=("q_overall", "count"),
        q_std=("q_overall", "std"),
        q_min=("q_overall", "min"),
        q_max=("q_overall", "max"),
        n_unique_q=("q_overall", "nunique"),
        repo=("repo", "first"),
        author=("author", "first"),
    )

    # Require at least MIN_SPECD_PRS PRs with at least 2 distinct quality levels
    eligible = groups[
        (groups["n_prs"] >= MIN_SPECD_PRS) &
        (groups["n_unique_q"] >= 2)
    ]

    print(f"  Author-repo pairs with spec'd PRs: {len(groups):,}")
    print(f"  Eligible (>= {MIN_SPECD_PRS} spec'd PRs, >= 2 distinct quality levels): "
          f"{len(eligible):,}")
    print(f"  Covering {eligible['n_prs'].sum():,} PRs "
          f"across {eligible['repo'].nunique()} repos "
          f"and {eligible['author'].nunique()} unique authors")
    print(f"  Quality range within authors: "
          f"mean span={eligible['q_max'].mean() - eligible['q_min'].mean():.1f} points")

    if len(eligible) == 0:
        print("  NO ELIGIBLE AUTHOR-REPO PAIRS — cannot proceed")
        return pd.DataFrame()

    eligible_keys = set(eligible.index)
    df_elig = specd[specd["author_repo"].isin(eligible_keys)].copy()

    print(f"\n  Filtered to {len(df_elig):,} spec'd PRs from eligible author-repo pairs")

    # --- Approach 1: Per-author-repo correlation between q_overall and outcome ---
    print("\n  --- Per-author-repo correlations (q_overall → outcome) ---")
    print(f"  {'Outcome':20s} {'Mean r':>8s} {'Median r':>10s} "
          f"{'% positive':>12s} {'t-test p':>10s} {'Direction':>12s}")
    print("  " + "-" * 74)

    summary_rows = []

    for col in OUTCOMES:
        correlations = []
        for ar_key in eligible_keys:
            ar_data = df_elig[df_elig["author_repo"] == ar_key]
            q_vals = ar_data["q_overall"].values
            o_vals = ar_data[col].astype(float).values

            # Point-biserial correlation (q_overall continuous, outcome binary)
            if o_vals.std() == 0 or q_vals.std() == 0:
                # No variation in outcome or quality — skip
                continue
            r, _ = stats.pearsonr(q_vals, o_vals)
            correlations.append(r)

        correlations = np.array(correlations)

        if len(correlations) < 2:
            print(f"  {col:20s}  insufficient data (n={len(correlations)})")
            continue

        mean_r = correlations.mean()
        median_r = np.median(correlations)
        pct_positive = (correlations > 0).mean() * 100

        # One-sample t-test: is mean correlation different from zero?
        t_stat, p_val = stats.ttest_1samp(correlations, 0.0)

        direction = "PARADOX HOLDS" if mean_r > 0 else "paradox gone"
        if p_val > 0.05:
            direction += " (ns)"

        print(f"  {col:20s} {mean_r:+8.3f} {median_r:+10.3f} "
              f"{pct_positive:11.1f}% {p_val:10.4f} {direction:>12s}")
        print(f"    n_authors={len(correlations)}, r_std={correlations.std():.3f}, "
              f"r_range=[{correlations.min():.3f}, {correlations.max():.3f}]")

        summary_rows.append({
            "outcome": col,
            "n_author_repo_pairs": len(correlations),
            "mean_r": mean_r,
            "median_r": median_r,
            "pct_positive": pct_positive,
            "t_stat": t_stat,
            "p_value": p_val,
            "direction": "paradox" if mean_r > 0 else "expected",
        })

    # --- Approach 2: Pooled within-author regression ---
    # Demean q_overall within each author-repo pair to get within-author variation,
    # then regress outcome on demeaned quality. This is equivalent to a fixed-effects
    # model (author-repo fixed effects).
    print("\n  --- Fixed-effects approach (author-repo demeaned q_overall) ---")

    df_elig["q_demeaned"] = df_elig.groupby("author_repo")["q_overall"].transform(
        lambda x: x - x.mean()
    )

    for col in OUTCOMES:
        y = df_elig[col].astype(float).values
        x = df_elig["q_demeaned"].values

        # Simple OLS on demeaned quality (equivalent to FE regression)
        # slope = cov(x, y) / var(x)
        valid = ~(np.isnan(x) | np.isnan(y))
        x_v, y_v = x[valid], y[valid]
        slope = np.cov(x_v, y_v)[0, 1] / np.var(x_v)

        # Standard error via bootstrap (1000 iterations)
        # Cluster-bootstrap at the author-repo level to respect correlation structure
        n_boot = 1000
        rng = np.random.RandomState(42)
        ar_keys = df_elig["author_repo"].values
        unique_ars = np.array(list(eligible_keys))
        boot_slopes = []

        for _ in range(n_boot):
            # Resample author-repo clusters
            sampled_ars = rng.choice(unique_ars, size=len(unique_ars), replace=True)
            # Gather all PRs for sampled clusters (with duplication)
            boot_mask = np.zeros(len(df_elig), dtype=bool)
            boot_indices = []
            for ar in sampled_ars:
                boot_indices.extend(np.where(ar_keys == ar)[0].tolist())
            boot_indices = np.array(boot_indices)
            bx = x[boot_indices]
            by = y[boot_indices]
            if np.var(bx) > 0:
                boot_slopes.append(np.cov(bx, by)[0, 1] / np.var(bx))

        boot_slopes = np.array(boot_slopes)
        se = boot_slopes.std()
        ci_lo = np.percentile(boot_slopes, 2.5)
        ci_hi = np.percentile(boot_slopes, 97.5)

        # z-test
        z = slope / se if se > 0 else 0
        p = 2 * stats.norm.sf(abs(z))

        direction = "PARADOX" if slope > 0 else "expected"
        if p > 0.05:
            direction += " (ns)"

        print(f"\n  {col}:")
        print(f"    slope = {slope:+.5f} (per 1-point increase in q_overall)")
        print(f"    95% CI = [{ci_lo:+.5f}, {ci_hi:+.5f}]  (cluster bootstrap)")
        print(f"    z = {z:.2f}, p = {p:.4f}")
        print(f"    Interpretation: a 10-point quality increase → "
              f"{slope * 10:+.3f} change in P({col})")
        print(f"    Direction: {direction}")

    # --- Approach 3: Simple median split within author ---
    # For each author-repo, split their spec'd PRs at their personal median quality.
    # Compare outcome rates above vs below median.
    print("\n  --- Within-author median split ---")
    print(f"  {'Outcome':20s} {'Above-median':>14s} {'Below-median':>14s} "
          f"{'Diff':>8s} {'Wilcoxon p':>12s}")
    print("  " + "-" * 70)

    for col in OUTCOMES:
        above_rates = []
        below_rates = []
        for ar_key in eligible_keys:
            ar_data = df_elig[df_elig["author_repo"] == ar_key]
            q_median = ar_data["q_overall"].median()
            above = ar_data[ar_data["q_overall"] > q_median]
            below = ar_data[ar_data["q_overall"] <= q_median]
            # Need at least 1 PR in each bin
            if len(above) == 0 or len(below) == 0:
                continue
            above_rates.append(above[col].mean())
            below_rates.append(below[col].mean())

        above_rates = np.array(above_rates)
        below_rates = np.array(below_rates)
        diffs = above_rates - below_rates

        if len(diffs) < 2:
            print(f"  {col:20s}  insufficient data")
            continue

        try:
            _, w_p = stats.wilcoxon(diffs, zero_method="wilcox")
        except ValueError:
            w_p = 1.0

        print(f"  {col:20s} {above_rates.mean():14.3f} {below_rates.mean():14.3f} "
              f"{diffs.mean():+8.3f} {w_p:12.4f}")

        summary_rows.append({
            "outcome": col + "_mediansplit",
            "n_author_repo_pairs": len(diffs),
            "mean_above": above_rates.mean(),
            "mean_below": below_rates.mean(),
            "mean_diff": diffs.mean(),
            "wilcoxon_p": w_p,
            "direction": "paradox" if diffs.mean() > 0 else "expected",
        })

    summary_df = pd.DataFrame(summary_rows)
    out_path = OUTPUT_DIR / "confound-quality-gradient.csv"
    summary_df.to_csv(out_path, index=False)
    print(f"\n  Saved quality gradient summary to {out_path}")

    return summary_df


# ===================================================================
# SYNTHESIS
# ===================================================================
def synthesize(pairs_df: pd.DataFrame, within_df: pd.DataFrame,
               gradient_df: pd.DataFrame):
    """Print a synthesis of all three analyses."""
    print("\n" + "=" * 72)
    print("SYNTHESIS: DOES THE POLISHED SPEC PARADOX SURVIVE CONFOUND CONTROLS?")
    print("=" * 72)

    print("""
  The "polished spec paradox" says better specs predict worse outcomes.
  Three confound controls were applied:

  1. MATCHED PAIRS — controls for PR size and repo.
     If the paradox disappears, it was driven by spec'd PRs being larger
     or from harder repos.

  2. WITHIN-AUTHOR — same author, same repo, spec'd vs unspec'd.
     If the paradox disappears, it was driven by who writes specs
     (e.g., senior devs on hard projects).

  3. QUALITY GRADIENT — same author, same repo, varying spec quality.
     If the paradox disappears at this level, the overall pattern was
     confounding by indication (harder work → better specs AND more defects).
     If it PERSISTS even here, there may be a real (alarming) effect.

  CAVEATS:
  - This is a 43-repo convenience sample; cannot generalize
  - Spec quality scoring (q_overall) is a model-based measure — not ground truth
  - "Confounding by indication" is the leading hypothesis, not the only one
  - Small within-author cells may lack power to detect real effects
  - Multiple comparisons across 3 outcomes × 3 analyses — interpret with care
""")


# ===================================================================
# MAIN
# ===================================================================
def main():
    df = load_data()

    pairs_df = analysis_matched_pairs(df)
    within_df = analysis_within_author(df)
    gradient_df = analysis_quality_gradient(df)

    synthesize(pairs_df, within_df, gradient_df)

    print("\nDone. Output files:")
    for f in sorted(OUTPUT_DIR.glob("confound-*.csv")):
        print(f"  {f}")


if __name__ == "__main__":
    main()
