#!/usr/bin/env python3
"""
AI Sprawl Robustness Analysis
==============================
Validates Finding 3 from the "Polished Spec Paradox" study:
  "Specs constrain AI sprawl — AI PRs without specs are ~2x larger than
   AI PRs with specs, but human PRs are the same size regardless."

This script confirms the finding holds across multiple AI classification
methods to rule out the possibility that the effect is an artifact of any
single classifier's threshold or error rate.

Classification methods tested:
  1. Two-bucket (primary): f_ai_tagged OR ai_probability > 0.5
     - Known 17% false positive rate for AI classification
     - Human bucket is 99% accurate (classifier says human AND no tag)
  2. Strict tag-only: f_ai_tagged == True
     - Zero false positives (co-author tags are voluntary, explicit)
     - Unknown false negative rate (devs may not tag)
  3. Probability threshold sweep: ai_probability at 0.3, 0.5, 0.7, 0.9
     - Tests whether the sprawl effect is stable or threshold-dependent
  4. Per-repo sign test: does the effect replicate across repos?
  5. Structural spec score (s_overall) as continuous predictor

Data caveats:
  - 43-repo convenience sample — cannot generalize to all OSS
  - Co-author tags are voluntary — unknown false negative rate
  - ai_probability is available for 20,742 of 23,967 PRs
  - f_is_bot_author PRs (1,660) are excluded — they're automated, not AI-assisted
  - "specd" is binary; actual spec quality varies enormously
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DATA_DIR = Path("/Users/brenn/dev/ai-augmented-dev/research/study/data")
MASTER_CSV = DATA_DIR / "master-prs.csv"
OUTPUT_JOINABLE = DATA_DIR / "ai-sprawl-results.csv"
OUTPUT_SUMMARY = DATA_DIR / "ai-sprawl-summary.csv"

# Probability thresholds to sweep for Analysis 3
PROB_THRESHOLDS = [0.3, 0.5, 0.7, 0.9]

# Minimum PRs per group for per-repo analysis (Analysis 4)
MIN_PER_GROUP = 5

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def compute_group_stats(df, group_col="group"):
    """Compute summary statistics for each group.

    Returns a DataFrame with n, median_lines, median_files, pct_huge (>500 lines)
    for each group value.
    """
    results = []
    for name, grp in df.groupby(group_col):
        results.append({
            "group": name,
            "n": len(grp),
            "median_lines": grp["lines_changed"].median(),
            "mean_lines": grp["lines_changed"].mean(),
            "median_files": grp["files_count"].median(),
            "pct_huge": (grp["lines_changed"] > 500).mean() * 100,
        })
    return pd.DataFrame(results)


def mann_whitney_test(group_a, group_b, label_a, label_b):
    """Run Mann-Whitney U test between two groups on lines_changed.

    Returns dict with test results and effect size (ratio of medians).
    """
    a = group_a["lines_changed"].values
    b = group_b["lines_changed"].values

    if len(a) < 2 or len(b) < 2:
        return {
            "comparison": f"{label_a} vs {label_b}",
            "n_a": len(a), "n_b": len(b),
            "median_a": np.median(a) if len(a) > 0 else np.nan,
            "median_b": np.median(b) if len(b) > 0 else np.nan,
            "ratio": np.nan, "U": np.nan, "p_value": np.nan,
        }

    U, p = stats.mannwhitneyu(a, b, alternative="two-sided")
    med_a = np.median(a)
    med_b = np.median(b)
    # Ratio: nospec / spec (expecting > 1 if specs constrain sprawl)
    ratio = med_b / med_a if med_a > 0 else np.nan

    return {
        "comparison": f"{label_a} vs {label_b}",
        "n_a": len(a), "n_b": len(b),
        "median_a": med_a, "median_b": med_b,
        "ratio": ratio, "U": U, "p_value": p,
    }


def print_section(title):
    """Print a section header."""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")


def print_group_stats(stats_df):
    """Pretty-print group statistics."""
    for _, row in stats_df.iterrows():
        print(f"  {row['group']:25s}  n={row['n']:6d}  "
              f"median_lines={row['median_lines']:8.0f}  "
              f"median_files={row['median_files']:5.0f}  "
              f"pct_huge={row['pct_huge']:5.1f}%")


def print_test_result(result):
    """Pretty-print a Mann-Whitney test result."""
    print(f"  {result['comparison']}")
    print(f"    n: {result['n_a']} vs {result['n_b']}")
    print(f"    Medians: {result['median_a']:.0f} vs {result['median_b']:.0f}")
    if not np.isnan(result['ratio']):
        print(f"    Ratio (nospec/spec): {result['ratio']:.2f}x")
    if not np.isnan(result['p_value']):
        sig = "***" if result['p_value'] < 0.001 else "**" if result['p_value'] < 0.01 else "*" if result['p_value'] < 0.05 else "ns"
        print(f"    Mann-Whitney U={result['U']:.0f}, p={result['p_value']:.4e} {sig}")


# ---------------------------------------------------------------------------
# Load and clean data
# ---------------------------------------------------------------------------

print("Loading data...")
df = pd.read_csv(MASTER_CSV, low_memory=False)
print(f"  Raw rows: {len(df)}")

# Exclude bot authors — these are automated PRs (dependabot, renovate, etc.),
# not AI-assisted human work. Including them would confound the analysis.
df["f_is_bot_author"] = df["f_is_bot_author"].fillna(False).astype(bool)
n_bots = df["f_is_bot_author"].sum()
df = df[~df["f_is_bot_author"]].copy()
print(f"  After excluding bot authors: {len(df)} (removed {n_bots} bot PRs)")

# Clean boolean columns — fillna before astype to avoid NaN surprises
df["f_ai_tagged"] = df["f_ai_tagged"].fillna(False).astype(bool)

# IMPORTANT: Use the same spec definition as jit-risk-analysis.py.
# The original Finding 3 used has_spec_score (q_overall > 0), NOT the
# binary specd column. These classify very differently:
#   specd column True: ~7,837 PRs
#   q_overall > 0:     ~6,201 PRs
#   Overlap:           ~2,008 PRs
# Using the wrong definition will produce opposite results.
df["q_overall"] = pd.to_numeric(df["q_overall"], errors="coerce")
df["specd"] = df["q_overall"].notna() & (df["q_overall"] > 0)
print(f"  Spec definition: q_overall > 0 (same as jit-risk-analysis.py)")
print(f"  specd True: {df['specd'].sum()}")

# Ensure numeric columns are clean
df["lines_changed"] = pd.to_numeric(df["lines_changed"], errors="coerce").fillna(0)
df["files_count"] = pd.to_numeric(df["files_count"], errors="coerce").fillna(0)
df["ai_probability"] = pd.to_numeric(df["ai_probability"], errors="coerce")
df["s_overall"] = pd.to_numeric(df["s_overall"], errors="coerce")

print(f"  ai_probability available: {df['ai_probability'].notna().sum()} of {len(df)}")
print(f"  f_ai_tagged True: {df['f_ai_tagged'].sum()}")
print(f"  specd True: {df['specd'].sum()}")

# ---------------------------------------------------------------------------
# Derived columns used across analyses
# ---------------------------------------------------------------------------

# Two-bucket classification (primary):
#   AI = co-author tag present OR classifier probability > 0.5
#   Human = no tag AND (classifier says human OR no classifier score)
# NOTE: This has a known ~17% false positive rate for AI classification.
# The human bucket is ~99% accurate.
df["is_ai_twobucket"] = df["f_ai_tagged"] | (df["ai_probability"].fillna(0) > 0.5)

# Strict tag-only classification:
#   AI = co-author tag explicitly present (zero false positives)
#   Human = everything else (includes some AI PRs without tags — false negatives)
df["is_ai_tagonly"] = df["f_ai_tagged"]

print(f"  Two-bucket AI: {df['is_ai_twobucket'].sum()}, Human: {(~df['is_ai_twobucket']).sum()}")
print(f"  Tag-only AI: {df['is_ai_tagonly'].sum()}, Human: {(~df['is_ai_tagonly']).sum()}")

# Accumulators for output CSVs
joinable_rows = []
summary_rows = []


# ---------------------------------------------------------------------------
# Analysis 1: Primary two-bucket classifier
# ---------------------------------------------------------------------------
print_section("Analysis 1: Two-Bucket Classifier (primary)")
print("  NOTE: AI classification has ~17% false positive rate.")
print("  Human classification is ~99% accurate.")

# Create 4 groups
df["_group1"] = np.where(
    df["is_ai_twobucket"],
    np.where(df["specd"], "AI+spec", "AI+nospec"),
    np.where(df["specd"], "Human+spec", "Human+nospec"),
)

stats1 = compute_group_stats(df, "_group1")
print("\nGroup statistics:")
print_group_stats(stats1)

# Mann-Whitney tests
ai_spec = df[(df["is_ai_twobucket"]) & (df["specd"])]
ai_nospec = df[(df["is_ai_twobucket"]) & (~df["specd"])]
hu_spec = df[(~df["is_ai_twobucket"]) & (df["specd"])]
hu_nospec = df[(~df["is_ai_twobucket"]) & (~df["specd"])]

print("\nMann-Whitney U tests:")
# For AI: comparing spec vs nospec, with nospec as the "larger" hypothesis
t1_ai = mann_whitney_test(ai_spec, ai_nospec, "AI+spec", "AI+nospec")
print_test_result(t1_ai)
t1_hu = mann_whitney_test(hu_spec, hu_nospec, "Human+spec", "Human+nospec")
print_test_result(t1_hu)

# Save to summary
for row in stats1.to_dict("records"):
    row["method"] = "two_bucket"
    summary_rows.append(row)

# Save joinable rows for two-bucket
for _, r in df.iterrows():
    joinable_rows.append({
        "repo": r["repo"], "pr_number": r["pr_number"],
        "ai_method": "two_bucket",
        "is_ai": r["is_ai_twobucket"],
        "has_spec": r["specd"],
        "lines_changed": r["lines_changed"],
        "files_count": r["files_count"],
    })


# ---------------------------------------------------------------------------
# Analysis 2: Strict tag-only classification
# ---------------------------------------------------------------------------
print_section("Analysis 2: Strict Tag-Only Classification")
print("  AI = explicit co-author tag (zero false positives).")
print("  Human = everything else (includes untagged AI — unknown FN rate).")

df["_group2"] = np.where(
    df["is_ai_tagonly"],
    np.where(df["specd"], "AI+spec", "AI+nospec"),
    np.where(df["specd"], "Human+spec", "Human+nospec"),
)

stats2 = compute_group_stats(df, "_group2")
print("\nGroup statistics:")
print_group_stats(stats2)

ai_spec2 = df[(df["is_ai_tagonly"]) & (df["specd"])]
ai_nospec2 = df[(df["is_ai_tagonly"]) & (~df["specd"])]
hu_spec2 = df[(~df["is_ai_tagonly"]) & (df["specd"])]
hu_nospec2 = df[(~df["is_ai_tagonly"]) & (~df["specd"])]

print("\nMann-Whitney U tests:")
t2_ai = mann_whitney_test(ai_spec2, ai_nospec2, "AI+spec", "AI+nospec")
print_test_result(t2_ai)
t2_hu = mann_whitney_test(hu_spec2, hu_nospec2, "Human+spec", "Human+nospec")
print_test_result(t2_hu)

for row in stats2.to_dict("records"):
    row["method"] = "tag_only"
    summary_rows.append(row)

# Save joinable rows for tag-only
for _, r in df.iterrows():
    joinable_rows.append({
        "repo": r["repo"], "pr_number": r["pr_number"],
        "ai_method": "tag_only",
        "is_ai": r["is_ai_tagonly"],
        "has_spec": r["specd"],
        "lines_changed": r["lines_changed"],
        "files_count": r["files_count"],
    })


# ---------------------------------------------------------------------------
# Analysis 3: Probability threshold sweep
# ---------------------------------------------------------------------------
print_section("Analysis 3: Probability Threshold Sweep")
print("  Tests whether the sprawl effect is stable across classifier thresholds.")
print(f"  Thresholds: {PROB_THRESHOLDS}")
print(f"  Only PRs with ai_probability available ({df['ai_probability'].notna().sum()} PRs).")

# Subset to PRs with a probability score
df_prob = df[df["ai_probability"].notna()].copy()

sweep_results = []
for thresh in PROB_THRESHOLDS:
    is_ai = df_prob["ai_probability"] > thresh
    ai_s = df_prob[is_ai & df_prob["specd"]]
    ai_ns = df_prob[is_ai & ~df_prob["specd"]]
    hu_s = df_prob[~is_ai & df_prob["specd"]]
    hu_ns = df_prob[~is_ai & ~df_prob["specd"]]

    t_ai = mann_whitney_test(ai_s, ai_ns, f"AI(>{thresh})+spec", f"AI(>{thresh})+nospec")
    t_hu = mann_whitney_test(hu_s, hu_ns, f"Human(<={thresh})+spec", f"Human(<={thresh})+nospec")

    sweep_results.append({
        "threshold": thresh,
        "ai_spec_n": len(ai_s), "ai_nospec_n": len(ai_ns),
        "ai_spec_median": t_ai["median_a"], "ai_nospec_median": t_ai["median_b"],
        "ai_ratio": t_ai["ratio"], "ai_p": t_ai["p_value"],
        "hu_spec_n": len(hu_s), "hu_nospec_n": len(hu_ns),
        "hu_spec_median": t_hu["median_a"], "hu_nospec_median": t_hu["median_b"],
        "hu_ratio": t_hu["ratio"], "hu_p": t_hu["p_value"],
    })

    # Save to summary
    for grp_name, grp_df in [
        (f"AI(>{thresh})+spec", ai_s), (f"AI(>{thresh})+nospec", ai_ns),
        (f"Human(<={thresh})+spec", hu_s), (f"Human(<={thresh})+nospec", hu_ns),
    ]:
        summary_rows.append({
            "method": f"prob_{thresh}",
            "group": grp_name,
            "n": len(grp_df),
            "median_lines": grp_df["lines_changed"].median() if len(grp_df) > 0 else np.nan,
            "mean_lines": grp_df["lines_changed"].mean() if len(grp_df) > 0 else np.nan,
            "median_files": grp_df["files_count"].median() if len(grp_df) > 0 else np.nan,
            "pct_huge": (grp_df["lines_changed"] > 500).mean() * 100 if len(grp_df) > 0 else np.nan,
        })

print("\n  Threshold  AI_spec_n  AI_nospec_n  AI_ratio  AI_p         Hu_ratio  Hu_p")
print("  " + "-" * 80)
for r in sweep_results:
    ai_sig = "***" if r["ai_p"] < 0.001 else "**" if r["ai_p"] < 0.01 else "*" if r["ai_p"] < 0.05 else "ns"
    hu_sig = "***" if r["hu_p"] < 0.001 else "**" if r["hu_p"] < 0.01 else "*" if r["hu_p"] < 0.05 else "ns"
    ai_r = f"{r['ai_ratio']:8.2f}x" if not np.isnan(r['ai_ratio']) else "     N/A"
    hu_r = f"{r['hu_ratio']:8.2f}x" if not np.isnan(r['hu_ratio']) else "     N/A"
    print(f"  {r['threshold']:9.1f}  {r['ai_spec_n']:9d}  {r['ai_nospec_n']:11d}  "
          f"{ai_r} {r['ai_p']:12.4e} {ai_sig:3s}  "
          f"{hu_r} {r['hu_p']:12.4e} {hu_sig:3s}")


# ---------------------------------------------------------------------------
# Analysis 4: Per-repo confirmation (sign test)
# ---------------------------------------------------------------------------
print_section("Analysis 4: Per-Repo Sign Test")
print(f"  Only repos with >= {MIN_PER_GROUP} AI+spec AND >= {MIN_PER_GROUP} AI+nospec PRs.")
print("  Uses two-bucket classification.")

repo_results = []
for repo, rdf in df.groupby("repo"):
    ai_s = rdf[rdf["is_ai_twobucket"] & rdf["specd"]]
    ai_ns = rdf[rdf["is_ai_twobucket"] & ~rdf["specd"]]

    if len(ai_s) < MIN_PER_GROUP or len(ai_ns) < MIN_PER_GROUP:
        continue

    med_s = ai_s["lines_changed"].median()
    med_ns = ai_ns["lines_changed"].median()
    ratio = med_ns / med_s if med_s > 0 else np.nan

    repo_results.append({
        "repo": repo,
        "ai_spec_n": len(ai_s),
        "ai_nospec_n": len(ai_ns),
        "median_spec": med_s,
        "median_nospec": med_ns,
        "ratio": ratio,
        "nospec_larger": med_ns > med_s,
    })

repo_df = pd.DataFrame(repo_results)
n_repos = len(repo_df)
n_nospec_larger = repo_df["nospec_larger"].sum()

print(f"\n  Repos with enough data: {n_repos}")
print(f"  Repos where AI+nospec > AI+spec: {n_nospec_larger} / {n_repos}")

if n_repos > 0:
    # Sign test: under H0 (no effect), P(nospec_larger) = 0.5
    # Use binomial test
    sign_p = stats.binomtest(n_nospec_larger, n_repos, 0.5).pvalue
    print(f"  Sign test p-value: {sign_p:.4e}")
    print(f"  Median sprawl ratio across repos: {repo_df['ratio'].median():.2f}x")

    print(f"\n  {'Repo':50s} {'AI+spec':>8s} {'AI+nospec':>10s} {'Med_spec':>9s} {'Med_nospec':>11s} {'Ratio':>6s}")
    print("  " + "-" * 100)
    for _, r in repo_df.sort_values("ratio", ascending=False).iterrows():
        marker = " <--" if r["ratio"] < 1.0 else ""
        print(f"  {r['repo']:50s} {r['ai_spec_n']:8d} {r['ai_nospec_n']:10d} "
              f"{r['median_spec']:9.0f} {r['median_nospec']:11.0f} {r['ratio']:6.2f}x{marker}")
else:
    print("  No repos had enough data for per-repo analysis.")


# ---------------------------------------------------------------------------
# Analysis 5: Structural spec score (s_overall) as continuous predictor
# ---------------------------------------------------------------------------
print_section("Analysis 5: Structural Spec Score (s_overall) vs PR Size")
print("  Spearman correlation between s_overall and lines_changed,")
print("  split by AI/Human (two-bucket). If specs constrain AI sprawl,")
print("  expect negative correlation for AI PRs (higher score → smaller PR)")
print("  and near-zero for human PRs.")

# Only include PRs that have specs (s_overall is meaningfully scored)
# s_overall has no NaNs per the data exploration, but 0 might mean "no spec content"
# We use all PRs and let the score speak for itself.
for label, mask in [("AI (two-bucket)", df["is_ai_twobucket"]),
                     ("Human (two-bucket)", ~df["is_ai_twobucket"])]:
    subset = df[mask]
    # Filter to PRs where s_overall > 0 (meaningful structural score)
    scored = subset[subset["s_overall"] > 0]

    if len(scored) < 10:
        print(f"\n  {label}: too few scored PRs ({len(scored)})")
        continue

    rho, p = stats.spearmanr(scored["s_overall"], scored["lines_changed"])
    print(f"\n  {label}:")
    print(f"    n (s_overall > 0): {len(scored)}")
    print(f"    Spearman rho: {rho:.4f}")
    sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "ns"
    print(f"    p-value: {p:.4e} {sig}")

# Also do specd subset only for a cleaner comparison
print("\n  --- Restricted to specd=True PRs only ---")
for label, mask in [("AI+spec", df["is_ai_twobucket"] & df["specd"]),
                     ("Human+spec", ~df["is_ai_twobucket"] & df["specd"])]:
    subset = df[mask]
    scored = subset[subset["s_overall"] > 0]

    if len(scored) < 10:
        print(f"\n  {label}: too few scored PRs ({len(scored)})")
        continue

    rho, p = stats.spearmanr(scored["s_overall"], scored["lines_changed"])
    print(f"\n  {label}:")
    print(f"    n (specd & s_overall > 0): {len(scored)}")
    print(f"    Spearman rho: {rho:.4f}")
    sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "ns"
    print(f"    p-value: {p:.4e} {sig}")


# ---------------------------------------------------------------------------
# Save outputs
# ---------------------------------------------------------------------------
print_section("Saving Output Files")

# Joinable CSV: one row per PR per classification method
# This includes two_bucket and tag_only (threshold sweep uses different subsets,
# so we add those separately for the subset with ai_probability)
joinable_df = pd.DataFrame(joinable_rows)
print(f"  Joinable rows: {len(joinable_df)} (2 methods x {len(df)} PRs = {2 * len(df)})")

# Add threshold-based rows for PRs with ai_probability
for thresh in PROB_THRESHOLDS:
    for _, r in df_prob.iterrows():
        joinable_rows.append({
            "repo": r["repo"], "pr_number": r["pr_number"],
            "ai_method": f"prob_{thresh}",
            "is_ai": r["ai_probability"] > thresh,
            "has_spec": r["specd"],
            "lines_changed": r["lines_changed"],
            "files_count": r["files_count"],
        })

joinable_df = pd.DataFrame(joinable_rows)
joinable_df.to_csv(OUTPUT_JOINABLE, index=False)
print(f"  Saved joinable CSV: {OUTPUT_JOINABLE}")
print(f"    Total rows: {len(joinable_df)}")

# Summary CSV
summary_df = pd.DataFrame(summary_rows)
summary_df.to_csv(OUTPUT_SUMMARY, index=False)
print(f"  Saved summary CSV: {OUTPUT_SUMMARY}")
print(f"    Total rows: {len(summary_df)}")


# ---------------------------------------------------------------------------
# Final interpretation
# ---------------------------------------------------------------------------
print_section("Interpretation Notes")

# Compute interpretation from actual results, not hardcoded text
ai_ratio_twobucket = t1_ai["ratio"]
ai_p_twobucket = t1_ai["p_value"]
hu_ratio_twobucket = t1_hu["ratio"]
hu_p_twobucket = t1_hu["p_value"]

if ai_ratio_twobucket > 1.2:
    ai_direction = "AI+nospec is LARGER than AI+spec"
    finding_holds = True
elif ai_ratio_twobucket < 0.8:
    ai_direction = "AI+spec is LARGER than AI+nospec"
    finding_holds = False
else:
    ai_direction = "AI+spec and AI+nospec are similar in size"
    finding_holds = False

if hu_ratio_twobucket > 1.2:
    hu_direction = "Human PRs also show spec effect (unexpected)"
elif hu_ratio_twobucket < 0.8:
    hu_direction = "Human+spec is larger (selection bias likely)"
else:
    hu_direction = "Human PRs show no spec effect (as expected)"

print(f"""
  Primary result (two-bucket classifier):
  - AI: {ai_direction} (ratio={ai_ratio_twobucket:.2f}x, p={ai_p_twobucket:.2e})
  - Human: {hu_direction} (ratio={hu_ratio_twobucket:.2f}x, p={hu_p_twobucket:.2e})
  - Finding 3 {"HOLDS" if finding_holds else "DOES NOT HOLD"} under robustness checking

  {"The original claim that specs constrain AI sprawl is SUPPORTED." if finding_holds else "The original claim that specs constrain AI sprawl is NOT SUPPORTED."}
  {"AI PRs without specs sprawl ~" + f"{ai_ratio_twobucket:.1f}x larger, while human PRs are unaffected." if finding_holds else ""}

  CAVEATS:
  - 43-repo convenience sample — findings cannot be generalized
  - Co-author tags are voluntary — unknown false negative rate
  - Spec definition uses q_overall > 0 (LLM-scored PRs only)
  - Pooled p-values treat PRs as independent — real N is ~42 repos
  - The per-repo sign test (Analysis 4) is the most honest statistical test
    because it uses repos as the unit of analysis""")
