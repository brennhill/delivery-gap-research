#!/usr/bin/env python3
"""Test whether human cognitive engagement during code review predicts
software quality outcomes (rework and escape rates).

Run: python3 engagement-predicts-quality.py
Reads: data/master-prs.csv, data/review-attention-signals.csv
Output: prints results, saves data/engagement-quality-results.csv

Background
----------
Prior analyses showed:
  - Spec quality doesn't predict outcomes (confounding with repo culture)
  - Questions don't survive confounder adjustment (proxy for review depth)
  - Review depth (review_total_length, review_unique_reviewers) was significant
    in logistic regression

This script tests whether that review-depth finding is real or another confound
by attacking it from multiple angles: normalizing for PR size, controlling for
author skill, size-matching, testing against the 400-LOC cognitive limit,
decomposing engagement components, checking AI vs human interaction, and running
a per-repo sign test (the honest unit of analysis).

Key definitions
---------------
  - engagement_density: review_total_length / (additions + deletions + 1)
    Characters of review per line of code changed. Normalizes out the trivial
    relationship "bigger PRs get more review."
  - spec'd: q_overall > 0 (consistent with other study scripts)
  - Excluded: trivial PRs (is_trivial == True) and bot authors (f_is_bot_author)
"""

import csv
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy import stats

STUDY_DIR = Path(__file__).resolve().parent
MASTER_CSV = STUDY_DIR / "data" / "master-prs.csv"
REVIEW_CSV = STUDY_DIR / "data" / "review-attention-signals.csv"
OUTPUT_CSV = STUDY_DIR / "data" / "engagement-quality-results.csv"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def sf(v, default=0.0):
    """Safe-float: convert v to float, returning default on failure."""
    try:
        return float(v)
    except (ValueError, TypeError):
        return default


def sb(v):
    """Safe-bool: convert v to bool, treating empty/missing as False."""
    if v is None or v == "":
        return False
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in ("true", "1", "yes")


def rate(subset, field):
    """Return (pct, n_positive, n_total) for rows where field is truthy."""
    if not subset:
        return 0.0, 0, 0
    count = sum(1 for r in subset if sb(r.get(field)))
    return count / len(subset) * 100, count, len(subset)


def cohens_d(group1_vals, group2_vals):
    """Compute Cohen's d for two groups of numeric values."""
    n1, n2 = len(group1_vals), len(group2_vals)
    if n1 < 2 or n2 < 2:
        return float("nan")
    m1, m2 = np.mean(group1_vals), np.mean(group2_vals)
    s1, s2 = np.var(group1_vals, ddof=1), np.var(group2_vals, ddof=1)
    pooled = math.sqrt(((n1 - 1) * s1 + (n2 - 1) * s2) / (n1 + n2 - 2))
    if pooled == 0:
        return float("nan")
    return (m1 - m2) / pooled


def odds_ratio(a, b, c, d):
    """Odds ratio from a 2x2 table: (a/b) / (c/d). Returns nan on zero."""
    if b == 0 or c == 0 or d == 0:
        return float("nan")
    return (a / b) / (c / d)


def print_header(title):
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}")


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_data():
    """Load and merge master PRs with review attention signals."""
    # Load master PRs
    master_rows = []
    with open(MASTER_CSV) as f:
        for r in csv.DictReader(f):
            master_rows.append(r)
    print(f"Loaded {len(master_rows)} rows from master-prs.csv")

    # Load review signals
    review_rows = {}
    with open(REVIEW_CSV) as f:
        for r in csv.DictReader(f):
            key = (r["repo"], r["pr_number"])
            review_rows[key] = r
    print(f"Loaded {len(review_rows)} rows from review-attention-signals.csv")

    # Merge
    merged = []
    matched = 0
    for r in master_rows:
        key = (r["repo"], r["pr_number"])
        if key in review_rows:
            r.update(review_rows[key])
            matched += 1
        merged.append(r)
    print(f"Merged: {matched} PRs matched review signals, "
          f"{len(merged) - matched} had no review data")

    return merged


def apply_filters(rows):
    """Exclude trivial PRs and bot authors. Log counts."""
    total = len(rows)

    # Filter bots
    non_bot = [r for r in rows if not sb(r.get("f_is_bot_author"))]
    bots_removed = total - len(non_bot)
    print(f"Removed {bots_removed} bot-authored PRs ({total} -> {len(non_bot)})")

    # Filter trivial
    non_trivial = [r for r in non_bot if not sb(r.get("is_trivial"))]
    trivial_removed = len(non_bot) - len(non_trivial)
    print(f"Removed {trivial_removed} trivial PRs ({len(non_bot)} -> {len(non_trivial)})")

    return non_trivial


def compute_engagement_density(rows):
    """Add engagement_density to each row. Returns rows that have review data."""
    has_review = []
    no_review = 0
    for r in rows:
        review_len = sf(r.get("review_total_length"))
        if review_len <= 0:
            no_review += 1
            continue
        adds = sf(r.get("additions"), 0)
        dels = sf(r.get("deletions"), 0)
        r["engagement_density"] = review_len / (adds + dels + 1)
        has_review.append(r)
    print(f"Engagement density computed: {len(has_review)} PRs with review data, "
          f"{no_review} without")
    return has_review


# ---------------------------------------------------------------------------
# Analysis 1: Engagement Density Quartiles
# ---------------------------------------------------------------------------

def analysis_1(rows, results):
    print_header("Analysis 1: Engagement Density Quartiles")

    densities = [r["engagement_density"] for r in rows]
    q25, q50, q75 = np.percentile(densities, [25, 50, 75])
    print(f"Engagement density quartile boundaries: Q25={q25:.2f}, "
          f"Q50={q50:.2f}, Q75={q75:.2f}")

    quartiles = {"Q1": [], "Q2": [], "Q3": [], "Q4": []}
    for r in rows:
        d = r["engagement_density"]
        if d <= q25:
            quartiles["Q1"].append(r)
        elif d <= q50:
            quartiles["Q2"].append(r)
        elif d <= q75:
            quartiles["Q3"].append(r)
        else:
            quartiles["Q4"].append(r)

    print(f"\n{'Quartile':<10} {'N':>6} {'Rework%':>8} {'Escape%':>8} "
          f"{'StrictEsc%':>10}")
    print("-" * 50)
    for q_name in ["Q1", "Q2", "Q3", "Q4"]:
        subset = quartiles[q_name]
        rw_pct, rw_n, rw_total = rate(subset, "reworked")
        esc_pct, esc_n, esc_total = rate(subset, "escaped")
        sesc_pct, sesc_n, sesc_total = rate(subset, "strict_escaped")
        print(f"{q_name:<10} {len(subset):>6} {rw_pct:>7.1f}% {esc_pct:>7.1f}% "
              f"{sesc_pct:>9.1f}%")

    # Mann-Whitney Q1 vs Q4
    q1_escaped = [1 if sb(r.get("strict_escaped")) else 0 for r in quartiles["Q1"]]
    q4_escaped = [1 if sb(r.get("strict_escaped")) else 0 for r in quartiles["Q4"]]
    if len(q1_escaped) > 0 and len(q4_escaped) > 0:
        u_stat, p_val = stats.mannwhitneyu(q1_escaped, q4_escaped,
                                           alternative="two-sided")
        d = cohens_d(q1_escaped, q4_escaped)
        q1_rate = sum(q1_escaped) / len(q1_escaped) * 100
        q4_rate = sum(q4_escaped) / len(q4_escaped) * 100
        or_val = odds_ratio(sum(q1_escaped), len(q1_escaped) - sum(q1_escaped),
                            sum(q4_escaped), len(q4_escaped) - sum(q4_escaped))
        print(f"\nQ1 vs Q4 (strict_escaped) Mann-Whitney: U={u_stat:.0f}, "
              f"p={p_val:.4f}")
        print(f"  Q1 escape rate: {q1_rate:.1f}%, Q4 escape rate: {q4_rate:.1f}%")
        print(f"  Delta: {q1_rate - q4_rate:+.1f}pp, Cohen's d: {d:.3f}, "
              f"OR: {or_val:.3f}")
        print(f"  Caveat: pooled across repos; real N is ~{len(set(r['repo'] for r in rows))} repos")
        results.append({
            "analysis": "1_quartile_q1_vs_q4",
            "metric": "strict_escaped",
            "n_q1": len(quartiles["Q1"]),
            "n_q4": len(quartiles["Q4"]),
            "q1_rate": f"{q1_rate:.1f}",
            "q4_rate": f"{q4_rate:.1f}",
            "delta_pp": f"{q1_rate - q4_rate:.1f}",
            "p_value": f"{p_val:.4f}",
            "cohens_d": f"{d:.3f}",
            "odds_ratio": f"{or_val:.3f}",
        })
    else:
        print("\nInsufficient data for Q1 vs Q4 comparison.")

    # Also for rework
    q1_rework = [1 if sb(r.get("reworked")) else 0 for r in quartiles["Q1"]]
    q4_rework = [1 if sb(r.get("reworked")) else 0 for r in quartiles["Q4"]]
    if len(q1_rework) > 0 and len(q4_rework) > 0:
        u_stat, p_val = stats.mannwhitneyu(q1_rework, q4_rework,
                                           alternative="two-sided")
        d = cohens_d(q1_rework, q4_rework)
        q1_rate = sum(q1_rework) / len(q1_rework) * 100
        q4_rate = sum(q4_rework) / len(q4_rework) * 100
        or_val = odds_ratio(sum(q1_rework), len(q1_rework) - sum(q1_rework),
                            sum(q4_rework), len(q4_rework) - sum(q4_rework))
        print(f"\nQ1 vs Q4 (reworked) Mann-Whitney: U={u_stat:.0f}, p={p_val:.4f}")
        print(f"  Q1 rework rate: {q1_rate:.1f}%, Q4 rework rate: {q4_rate:.1f}%")
        print(f"  Delta: {q1_rate - q4_rate:+.1f}pp, Cohen's d: {d:.3f}, "
              f"OR: {or_val:.3f}")
        results.append({
            "analysis": "1_quartile_q1_vs_q4",
            "metric": "reworked",
            "n_q1": len(quartiles["Q1"]),
            "n_q4": len(quartiles["Q4"]),
            "q1_rate": f"{q1_rate:.1f}",
            "q4_rate": f"{q4_rate:.1f}",
            "delta_pp": f"{q1_rate - q4_rate:.1f}",
            "p_value": f"{p_val:.4f}",
            "cohens_d": f"{d:.3f}",
            "odds_ratio": f"{or_val:.3f}",
        })


# ---------------------------------------------------------------------------
# Analysis 2: Within-Author Engagement
# ---------------------------------------------------------------------------

def analysis_2(rows, results):
    print_header("Analysis 2: Within-Author Engagement")

    # Group by author-repo
    author_repo = defaultdict(list)
    for r in rows:
        key = (r["author"], r["repo"])
        author_repo[key].append(r)

    # Keep only pairs with enough variation
    pairs_above = []  # above-median engagement density escaped rates
    pairs_below = []
    valid_pairs = 0
    skipped_single = 0
    skipped_no_variation = 0

    for (author, repo), prs in author_repo.items():
        if len(prs) < 4:  # need enough PRs to split meaningfully
            skipped_single += 1
            continue
        densities = [pr["engagement_density"] for pr in prs]
        med = np.median(densities)
        above = [pr for pr in prs if pr["engagement_density"] > med]
        below = [pr for pr in prs if pr["engagement_density"] <= med]
        if len(above) < 2 or len(below) < 2:
            skipped_no_variation += 1
            continue
        valid_pairs += 1
        above_esc = sum(1 for pr in above if sb(pr.get("strict_escaped"))) / len(above)
        below_esc = sum(1 for pr in below if sb(pr.get("strict_escaped"))) / len(below)
        pairs_above.append(above_esc)
        pairs_below.append(below_esc)

    print(f"Author-repo pairs: {len(author_repo)} total, "
          f"{skipped_single} with <4 PRs, "
          f"{skipped_no_variation} with insufficient variation, "
          f"{valid_pairs} valid")

    if valid_pairs >= 5:
        diffs = [a - b for a, b in zip(pairs_above, pairs_below)]
        t_stat, p_val = stats.ttest_rel(pairs_above, pairs_below)
        mean_above = np.mean(pairs_above) * 100
        mean_below = np.mean(pairs_below) * 100
        d = cohens_d(pairs_above, pairs_below) if valid_pairs >= 3 else float("nan")
        print(f"\nWithin-author paired t-test (strict_escaped):")
        print(f"  Above-median engagement: {mean_above:.1f}% escape rate")
        print(f"  Below-median engagement: {mean_below:.1f}% escape rate")
        print(f"  Delta: {mean_above - mean_below:+.1f}pp")
        print(f"  t={t_stat:.3f}, p={p_val:.4f}, Cohen's d={d:.3f}")
        print(f"  N={valid_pairs} author-repo pairs")
        results.append({
            "analysis": "2_within_author",
            "metric": "strict_escaped",
            "n_pairs": str(valid_pairs),
            "above_median_rate": f"{mean_above:.1f}",
            "below_median_rate": f"{mean_below:.1f}",
            "delta_pp": f"{mean_above - mean_below:.1f}",
            "p_value": f"{p_val:.4f}",
            "cohens_d": f"{d:.3f}",
        })
    else:
        print(f"\nInsufficient valid pairs ({valid_pairs}) for paired t-test.")
        results.append({
            "analysis": "2_within_author",
            "metric": "strict_escaped",
            "note": f"insufficient pairs ({valid_pairs})",
        })


# ---------------------------------------------------------------------------
# Analysis 3: Size-Matched Engagement Comparison
# ---------------------------------------------------------------------------

def analysis_3(rows, results):
    print_header("Analysis 3: Size-Matched Engagement Comparison")

    # Group by repo
    by_repo = defaultdict(list)
    for r in rows:
        by_repo[r["repo"]].append(r)

    high_eng_escaped = 0
    high_eng_total = 0
    low_eng_escaped = 0
    low_eng_total = 0
    repos_used = 0

    for repo, prs in by_repo.items():
        if len(prs) < 10:
            continue
        repos_used += 1

        # Bucket by size (log2 buckets so each bucket covers ~2x range)
        size_buckets = defaultdict(list)
        for pr in prs:
            size = sf(pr.get("additions"), 0) + sf(pr.get("deletions"), 0)
            if size <= 0:
                continue
            bucket = int(math.log2(max(size, 1)))
            size_buckets[bucket].append(pr)

        for bucket_prs in size_buckets.values():
            if len(bucket_prs) < 4:
                continue
            med = np.median([pr["engagement_density"] for pr in bucket_prs])
            high = [pr for pr in bucket_prs if pr["engagement_density"] > med]
            low = [pr for pr in bucket_prs if pr["engagement_density"] <= med]
            high_eng_escaped += sum(1 for pr in high if sb(pr.get("strict_escaped")))
            high_eng_total += len(high)
            low_eng_escaped += sum(1 for pr in low if sb(pr.get("strict_escaped")))
            low_eng_total += len(low)

    print(f"Repos used: {repos_used}")
    print(f"High engagement (size-matched): {high_eng_total} PRs, "
          f"{high_eng_escaped} escapes")
    print(f"Low engagement (size-matched):  {low_eng_total} PRs, "
          f"{low_eng_escaped} escapes")

    if high_eng_total > 0 and low_eng_total > 0:
        high_rate = high_eng_escaped / high_eng_total * 100
        low_rate = low_eng_escaped / low_eng_total * 100
        # Fisher's exact test
        table = np.array([
            [high_eng_escaped, high_eng_total - high_eng_escaped],
            [low_eng_escaped, low_eng_total - low_eng_escaped]
        ])
        or_val, p_val = stats.fisher_exact(table)
        print(f"\nHigh engagement escape rate: {high_rate:.1f}%")
        print(f"Low engagement escape rate:  {low_rate:.1f}%")
        print(f"Delta: {high_rate - low_rate:+.1f}pp")
        print(f"Fisher's exact: OR={or_val:.3f}, p={p_val:.4f}")
        results.append({
            "analysis": "3_size_matched",
            "metric": "strict_escaped",
            "n_high": str(high_eng_total),
            "n_low": str(low_eng_total),
            "high_rate": f"{high_rate:.1f}",
            "low_rate": f"{low_rate:.1f}",
            "delta_pp": f"{high_rate - low_rate:.1f}",
            "p_value": f"{p_val:.4f}",
            "odds_ratio": f"{or_val:.3f}",
        })
    else:
        print("\nInsufficient data for size-matched comparison.")


# ---------------------------------------------------------------------------
# Analysis 4: 400-LOC Threshold Test
# ---------------------------------------------------------------------------

def analysis_4(rows, results):
    print_header("Analysis 4: 400-LOC Threshold Test (SmartBear/Cisco)")

    small = [r for r in rows
             if sf(r.get("additions"), 0) + sf(r.get("deletions"), 0) < 400]
    large = [r for r in rows
             if sf(r.get("additions"), 0) + sf(r.get("deletions"), 0) >= 400]
    print(f"Small PRs (<400 LOC): {len(small)}")
    print(f"Large PRs (>=400 LOC): {len(large)}")

    for label, subset in [("Small (<400 LOC)", small), ("Large (>=400 LOC)", large)]:
        if len(subset) < 20:
            print(f"\n{label}: too few PRs ({len(subset)}), skipping")
            continue

        densities = [r["engagement_density"] for r in subset]
        med = np.median(densities)
        high = [r for r in subset if r["engagement_density"] > med]
        low = [r for r in subset if r["engagement_density"] <= med]

        high_esc_pct, high_esc_n, high_total = rate(high, "strict_escaped")
        low_esc_pct, low_esc_n, low_total = rate(low, "strict_escaped")

        # Fisher's exact
        table = np.array([
            [high_esc_n, high_total - high_esc_n],
            [low_esc_n, low_total - low_esc_n]
        ])
        if high_total > 0 and low_total > 0:
            or_val, p_val = stats.fisher_exact(table)
        else:
            or_val, p_val = float("nan"), float("nan")

        print(f"\n{label}:")
        print(f"  High engagement: {high_total} PRs, {high_esc_pct:.1f}% escape")
        print(f"  Low engagement:  {low_total} PRs, {low_esc_pct:.1f}% escape")
        print(f"  Delta: {high_esc_pct - low_esc_pct:+.1f}pp")
        print(f"  Fisher's exact: OR={or_val:.3f}, p={p_val:.4f}")

        tag = "small" if "Small" in label else "large"
        results.append({
            "analysis": f"4_400loc_{tag}",
            "metric": "strict_escaped",
            "n_high": str(high_total),
            "n_low": str(low_total),
            "high_rate": f"{high_esc_pct:.1f}",
            "low_rate": f"{low_esc_pct:.1f}",
            "delta_pp": f"{high_esc_pct - low_esc_pct:.1f}",
            "p_value": f"{p_val:.4f}",
            "odds_ratio": f"{or_val:.3f}",
        })


# ---------------------------------------------------------------------------
# Analysis 5: Decompose Engagement (Logistic Regression)
# ---------------------------------------------------------------------------

def analysis_5(rows, results):
    print_header("Analysis 5: Decompose Engagement (Logistic Regression)")

    try:
        import statsmodels.api as sm
    except ImportError:
        print("statsmodels not installed -- skipping logistic regression")
        results.append({
            "analysis": "5_decompose",
            "note": "statsmodels not installed",
        })
        return

    # Build feature matrix
    features = []
    y = []
    skipped = 0
    for r in rows:
        adds = sf(r.get("additions"), 0)
        dels = sf(r.get("deletions"), 0)
        files = sf(r.get("files_count"), 0)
        eng_dens = r.get("engagement_density")
        reviewers = sf(r.get("review_unique_reviewers"), 0)
        rounds = sf(r.get("review_rounds"), 0)
        genuine_q = sf(r.get("review_genuine_questions"), 0)
        challenges = sf(r.get("review_challenge_count"), 0)

        if eng_dens is None or adds <= 0 or dels < 0 or files <= 0:
            skipped += 1
            continue

        features.append([
            eng_dens,
            reviewers,
            rounds,
            genuine_q,
            challenges,
            math.log(adds + 1),
            math.log(dels + 1),
            math.log(files + 1),
        ])
        y.append(1 if sb(r.get("escaped")) else 0)

    print(f"Logistic regression sample: {len(y)} PRs ({skipped} skipped, "
          f"missing data)")
    print(f"Escaped rate in sample: {sum(y)}/{len(y)} = "
          f"{sum(y)/len(y)*100:.1f}%")

    if len(y) < 50 or sum(y) < 10:
        print("Too few events for logistic regression.")
        results.append({
            "analysis": "5_decompose",
            "note": f"too few events ({sum(y)} escapes in {len(y)} PRs)",
        })
        return

    X = np.array(features)
    y_arr = np.array(y)
    X_const = sm.add_constant(X)
    col_names = ["const", "engagement_density", "unique_reviewers",
                 "review_rounds", "genuine_questions", "challenge_count",
                 "log_additions", "log_deletions", "log_files"]

    try:
        model = sm.Logit(y_arr, X_const)
        result = model.fit(disp=0, maxiter=100)
        print(f"\nLogistic regression results (DV: escaped):")
        print(f"{'Variable':<22} {'Coef':>8} {'SE':>8} {'z':>8} {'p':>8} {'OR':>8}")
        print("-" * 62)
        for i, name in enumerate(col_names):
            coef = result.params[i]
            se = result.bse[i]
            z = result.tvalues[i]
            p = result.pvalues[i]
            or_val = math.exp(coef)
            sig = "*" if p < 0.05 else ""
            print(f"{name:<22} {coef:>8.4f} {se:>8.4f} {z:>8.3f} {p:>8.4f} "
                  f"{or_val:>8.3f} {sig}")
            if name != "const":
                results.append({
                    "analysis": "5_decompose",
                    "variable": name,
                    "coefficient": f"{coef:.4f}",
                    "std_error": f"{se:.4f}",
                    "z_value": f"{z:.3f}",
                    "p_value": f"{p:.4f}",
                    "odds_ratio": f"{or_val:.3f}",
                    "significant": "yes" if p < 0.05 else "no",
                })
        print(f"\nPseudo R-squared: {result.prsquared:.4f}")
        print(f"AIC: {result.aic:.1f}")
        print(f"N: {result.nobs:.0f}")
    except Exception as e:
        print(f"Logistic regression failed: {e}")
        results.append({
            "analysis": "5_decompose",
            "note": f"regression failed: {e}",
        })


# ---------------------------------------------------------------------------
# Analysis 6: AI vs Human Interaction
# ---------------------------------------------------------------------------

def analysis_6(rows, results):
    print_header("Analysis 6: AI vs Human Interaction")

    # Two-bucket classification: augmented = f_ai_tagged OR ai_probability > 0.5
    augmented_prs = [r for r in rows
                     if sb(r.get("f_ai_tagged")) or sf(r.get("ai_probability")) > 0.5]
    aug_ids = set(id(r) for r in augmented_prs)
    human_prs = [r for r in rows if id(r) not in aug_ids]
    print(f"Human PRs: {len(human_prs)}, Augmented PRs: {len(augmented_prs)} "
          f"(two-bucket: f_ai_tagged OR ai_probability > 0.5)")

    for label, subset in [("Human", human_prs), ("Augmented", augmented_prs)]:
        if len(subset) < 20:
            print(f"\n{label}: too few PRs ({len(subset)}), skipping")
            continue

        densities = [r["engagement_density"] for r in subset]
        q25, q75 = np.percentile(densities, [25, 75])
        q1 = [r for r in subset if r["engagement_density"] <= q25]
        q4 = [r for r in subset if r["engagement_density"] > q75]

        q1_esc_pct, q1_esc_n, q1_total = rate(q1, "strict_escaped")
        q4_esc_pct, q4_esc_n, q4_total = rate(q4, "strict_escaped")

        if q1_total > 0 and q4_total > 0:
            table = np.array([
                [q1_esc_n, q1_total - q1_esc_n],
                [q4_esc_n, q4_total - q4_esc_n]
            ])
            or_val, p_val = stats.fisher_exact(table)
        else:
            or_val, p_val = float("nan"), float("nan")

        print(f"\n{label} PRs:")
        print(f"  Q1 (lowest engagement): {q1_total} PRs, {q1_esc_pct:.1f}% escape")
        print(f"  Q4 (highest engagement): {q4_total} PRs, {q4_esc_pct:.1f}% escape")
        print(f"  Delta: {q1_esc_pct - q4_esc_pct:+.1f}pp")
        print(f"  Fisher's exact: OR={or_val:.3f}, p={p_val:.4f}")

        results.append({
            "analysis": f"6_ai_interaction_{label.lower()}",
            "metric": "strict_escaped",
            "n_q1": str(q1_total),
            "n_q4": str(q4_total),
            "q1_rate": f"{q1_esc_pct:.1f}",
            "q4_rate": f"{q4_esc_pct:.1f}",
            "delta_pp": f"{q1_esc_pct - q4_esc_pct:.1f}",
            "p_value": f"{p_val:.4f}",
            "odds_ratio": f"{or_val:.3f}",
        })

    # Compare effect sizes
    if len(human_prs) >= 20 and len(augmented_prs) >= 20:
        print("\nInterpretation: Compare the delta and OR between Human and "
              "Augmented groups.")
        print("If augmented shows a larger effect, AI code specifically needs "
              "more review scrutiny.")
        print("If similar, it's a general review quality effect.")


# ---------------------------------------------------------------------------
# Analysis 7: Per-Repo Sign Test
# ---------------------------------------------------------------------------

def analysis_7(rows, results):
    print_header("Analysis 7: Per-Repo Sign Test")

    by_repo = defaultdict(list)
    for r in rows:
        by_repo[r["repo"]].append(r)

    positive = 0  # higher engagement -> fewer escapes
    negative = 0  # higher engagement -> more escapes
    tied = 0
    repo_details = []

    for repo, prs in sorted(by_repo.items()):
        if len(prs) < 20:
            continue

        med = np.median([pr["engagement_density"] for pr in prs])
        high = [pr for pr in prs if pr["engagement_density"] > med]
        low = [pr for pr in prs if pr["engagement_density"] <= med]

        if len(high) < 5 or len(low) < 5:
            continue

        high_esc = sum(1 for pr in high if sb(pr.get("strict_escaped"))) / len(high)
        low_esc = sum(1 for pr in low if sb(pr.get("strict_escaped"))) / len(low)

        if low_esc > high_esc:
            positive += 1
            direction = "+"
        elif high_esc > low_esc:
            negative += 1
            direction = "-"
        else:
            tied += 1
            direction = "="

        repo_details.append({
            "repo": repo,
            "n": len(prs),
            "high_esc": high_esc * 100,
            "low_esc": low_esc * 100,
            "direction": direction,
        })

    total_repos = positive + negative + tied
    print(f"Repos with sufficient data (>=20 PRs, >=5 per split): {total_repos}")
    print(f"  Positive (higher engagement -> fewer escapes): {positive}")
    print(f"  Negative (higher engagement -> more escapes): {negative}")
    print(f"  Tied: {tied}")

    # Print per-repo details
    print(f"\n{'Repo':<45} {'N':>5} {'HighEng%':>8} {'LowEng%':>8} {'Dir':>4}")
    print("-" * 75)
    for d in repo_details:
        print(f"{d['repo']:<45} {d['n']:>5} {d['high_esc']:>7.1f}% "
              f"{d['low_esc']:>7.1f}% {d['direction']:>4}")

    # Sign test (excluding ties)
    n_nontied = positive + negative
    if n_nontied >= 3:
        # Binomial test: under null, P(positive) = 0.5
        p_val = stats.binomtest(positive, n_nontied, 0.5).pvalue
        print(f"\nSign test: {positive}/{n_nontied} repos show engagement "
              f"reduces escapes")
        print(f"  p={p_val:.4f} (binomial, two-sided)")
        print(f"  This is the most honest test: repos are the real unit of analysis")
        results.append({
            "analysis": "7_per_repo_sign",
            "n_repos": str(total_repos),
            "positive": str(positive),
            "negative": str(negative),
            "tied": str(tied),
            "p_value": f"{p_val:.4f}",
        })
    else:
        print(f"\nToo few repos ({n_nontied}) for sign test.")
        results.append({
            "analysis": "7_per_repo_sign",
            "note": f"too few repos ({n_nontied})",
        })


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print("=" * 70)
    print("  Engagement Predicts Quality: Testing the Review Depth Finding")
    print("=" * 70)

    # Load and filter
    rows = load_data()
    rows = apply_filters(rows)

    # Compute engagement density (only rows with review data)
    rows = compute_engagement_density(rows)

    if len(rows) < 50:
        print(f"\nFATAL: Only {len(rows)} PRs with review data after filtering. "
              f"Cannot run analyses.")
        sys.exit(1)

    print(f"\nFinal analysis population: {len(rows)} PRs across "
          f"{len(set(r['repo'] for r in rows))} repos")

    # Check for NaN/inf in engagement_density
    nan_count = sum(1 for r in rows
                    if math.isnan(r["engagement_density"])
                    or math.isinf(r["engagement_density"]))
    if nan_count > 0:
        print(f"WARNING: {nan_count} rows with NaN/inf engagement_density, "
              f"removing")
        rows = [r for r in rows
                if not math.isnan(r["engagement_density"])
                and not math.isinf(r["engagement_density"])]

    results = []

    analysis_1(rows, results)
    analysis_2(rows, results)
    analysis_3(rows, results)
    analysis_4(rows, results)
    analysis_5(rows, results)
    analysis_6(rows, results)
    analysis_7(rows, results)

    # Save results
    if results:
        # Collect all keys
        all_keys = []
        for r in results:
            for k in r.keys():
                if k not in all_keys:
                    all_keys.append(k)
        with open(OUTPUT_CSV, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=all_keys)
            writer.writeheader()
            writer.writerows(results)
        print(f"\nResults saved to {OUTPUT_CSV}")

    print("\n" + "=" * 70)
    print("  Summary")
    print("=" * 70)
    print("If engagement density predicts quality across multiple analyses,")
    print("the review-depth finding from logistic regression is likely real.")
    print("If it only shows up in pooled analysis but not within-author or")
    print("per-repo, it's a confound (repo culture or author skill).")
    print("If it works for small PRs but not large, it matches the known")
    print("cognitive limit (SmartBear/Cisco 400-LOC threshold).")


if __name__ == "__main__":
    main()
