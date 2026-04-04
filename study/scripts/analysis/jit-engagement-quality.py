"""
JIT Defect Prediction Features × Engagement Signals
=====================================================

Tests whether review engagement improves code quality independent of
outcome detection (rework/escape), using JIT risk features as a structural
proxy for defect-prone code.

Motivation: Our rework/escape detectors use a 14-day window for follow-up
PR matching. Many bugs lurk for months or get fixed in unrelated patches.
JIT risk features (Kamei et al. 2016) predict defects from code structure
alone — size, spread, churn, focus — giving us a quality signal that
doesn't depend on the detection window.

IMPORTANT CAVEATS:
- JIT risk score is a COMPOSITE PROXY, not ground truth. It predicts defects
  but IS NOT a defect measurement. Findings should be interpreted as
  "engagement correlates with structurally lower-risk code," not
  "engagement prevents defects."
- The +1 smoothing on churn ratio is Laplace-style to avoid division by zero.
  This is not standard Kamei et al. — their original features assume non-zero
  denominators at commit level. We apply it at PR level.
- 43-repo convenience sample. Cannot generalize beyond this dataset.
- AI classification uses two-bucket approach: Human (classifier says human
  AND no co-author tag, 99% accurate) vs Augmented (tagged OR classifier
  says AI-like). We detect presence, not degree of AI involvement.
"""

import warnings
import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.api as sm
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
DATA_DIR = Path(__file__).resolve().parent / "data"
MASTER_PATH = DATA_DIR / "master-prs.csv"
REVIEW_PATH = DATA_DIR / "review-attention-signals.csv"
OUT_RESULTS = DATA_DIR / "jit-engagement-results.csv"
OUT_SCORES = DATA_DIR / "jit-risk-scores.csv"


def load_and_merge():
    """Load master PRs + review signals, filter, merge."""
    master = pd.read_csv(MASTER_PATH, low_memory=False)
    review = pd.read_csv(REVIEW_PATH)

    print("=" * 72)
    print("DATA LOADING")
    print("=" * 72)
    print(f"Master PRs loaded:  {len(master):,}")
    print(f"Review signals loaded: {len(review):,}")

    # Boolean columns: fillna before casting
    for col in ["is_trivial", "f_is_bot_author"]:
        if col in master.columns:
            master[col] = master[col].fillna(False).astype(bool)

    # Exclude trivial PRs
    if "is_trivial" in master.columns:
        n_trivial = master["is_trivial"].sum()
        master = master[~master["is_trivial"]].copy()
    else:
        n_trivial = 0
        print("  (is_trivial column not in master CSV — skipping trivial filter)")
    print(f"Excluded trivial PRs: {n_trivial:,}")

    # Exclude bot authors
    n_bot = master["f_is_bot_author"].sum()
    master = master[~master["f_is_bot_author"]].copy()
    print(f"Excluded bot authors: {n_bot:,}")
    print(f"After exclusions:   {len(master):,}")

    # Merge with review signals
    df = master.merge(review, on=["repo", "pr_number"], how="left")
    n_no_review = df["review_total_length"].isna().sum()
    print(f"PRs without review signals: {n_no_review:,}")

    # Fill missing review signals with 0 (no review = zero engagement)
    review_cols = [
        "review_total_length", "review_unique_reviewers", "review_rounds",
        "review_genuine_questions", "review_challenge_count",
    ]
    for col in review_cols:
        df[col] = df[col].fillna(0)

    return df


def compute_jit_features(df):
    """Compute JIT risk features (Kamei et al. 2016 adapted to PR level)."""
    df = df.copy()

    # Ensure numeric
    df["additions"] = pd.to_numeric(df["additions"], errors="coerce").fillna(0)
    df["deletions"] = pd.to_numeric(df["deletions"], errors="coerce").fillna(0)
    df["files_count"] = pd.to_numeric(df["files_count"], errors="coerce").fillna(0)

    # JIT features
    df["jit_size"] = df["additions"] + df["deletions"]
    df["jit_spread"] = df["files_count"]
    # Churn ratio: proportion of deletions. +1 Laplace smoothing.
    df["jit_churn"] = df["deletions"] / (df["additions"] + df["deletions"] + 1)
    # Focus: files per line changed (dispersion). +1 smoothing.
    df["jit_focus"] = df["files_count"] / (df["jit_size"] + 1)

    # Min-max normalize each feature to [0, 1]
    jit_cols = ["jit_size", "jit_spread", "jit_churn", "jit_focus"]
    for col in jit_cols:
        col_min = df[col].min()
        col_max = df[col].max()
        if col_max > col_min:
            df[f"{col}_norm"] = (df[col] - col_min) / (col_max - col_min)
        else:
            df[f"{col}_norm"] = 0.0

    # Composite JIT risk score: average of normalized features
    norm_cols = [f"{c}_norm" for c in jit_cols]
    df["jit_risk_score"] = df[norm_cols].mean(axis=1)

    # Engagement density
    df["engagement_density"] = df["review_total_length"] / (df["jit_size"] + 1)

    print(f"\nJIT risk score — mean: {df['jit_risk_score'].mean():.4f}, "
          f"median: {df['jit_risk_score'].median():.4f}, "
          f"std: {df['jit_risk_score'].std():.4f}")
    print(f"Engagement density — mean: {df['engagement_density'].mean():.4f}, "
          f"median: {df['engagement_density'].median():.4f}")

    return df


# ===========================================================================
# Analyses
# ===========================================================================

def analysis_1_quartiles(df):
    """JIT Risk Score by Engagement Density Quartile."""
    print("\n" + "=" * 72)
    print("ANALYSIS 1: JIT Risk Score by Engagement Density Quartile")
    print("=" * 72)
    print("If higher engagement produces structurally better code (lower JIT")
    print("risk), that's evidence engagement improves quality — measured by")
    print("CODE STRUCTURE, not the outcome detector.\n")

    df = df.copy()
    # Many PRs have zero engagement — use rank-based bucketing to handle ties
    df["eng_rank"] = df["engagement_density"].rank(method="first")
    df["eng_quartile"] = pd.qcut(
        df["eng_rank"], q=4, labels=["Q1 (low)", "Q2", "Q3", "Q4 (high)"]
    )

    results = []
    for q in ["Q1 (low)", "Q2", "Q3", "Q4 (high)"]:
        subset = df[df["eng_quartile"] == q]
        results.append({
            "quartile": q,
            "n": len(subset),
            "mean_jit_risk": subset["jit_risk_score"].mean(),
            "median_jit_risk": subset["jit_risk_score"].median(),
            "std_jit_risk": subset["jit_risk_score"].std(),
        })

    res_df = pd.DataFrame(results)
    print(res_df.to_string(index=False))

    # Kruskal-Wallis across quartiles
    groups = [g["jit_risk_score"].values for _, g in df.groupby("eng_quartile")]
    h_stat, p_val = stats.kruskal(*groups)
    print(f"\nKruskal-Wallis H={h_stat:.2f}, p={p_val:.4g}")

    # Effect size: Q1 vs Q4
    q1 = df[df["eng_quartile"] == "Q1 (low)"]["jit_risk_score"]
    q4 = df[df["eng_quartile"] == "Q4 (high)"]["jit_risk_score"]
    cohens_d = (q1.mean() - q4.mean()) / np.sqrt((q1.std()**2 + q4.std()**2) / 2)
    print(f"Cohen's d (Q1 vs Q4): {cohens_d:.4f}")
    print("  Positive d means low-engagement PRs have HIGHER risk.")

    return res_df


def analysis_2_regression(df):
    """OLS: jit_risk ~ engagement_density + log(size controls)."""
    print("\n" + "=" * 72)
    print("ANALYSIS 2: Engagement vs JIT Risk Regression (OLS)")
    print("=" * 72)
    print("Does engagement density predict lower JIT risk after controlling")
    print("for PR size?\n")

    reg_df = df[["jit_risk_score", "engagement_density",
                 "additions", "deletions", "files_count"]].dropna().copy()
    reg_df["log_additions"] = np.log1p(reg_df["additions"])
    reg_df["log_deletions"] = np.log1p(reg_df["deletions"])
    reg_df["log_files"] = np.log1p(reg_df["files_count"])

    X = reg_df[["engagement_density", "log_additions", "log_deletions", "log_files"]]
    X = sm.add_constant(X)
    y = reg_df["jit_risk_score"]

    model = sm.OLS(y, X).fit(cov_type="HC1")  # heteroskedasticity-robust SEs
    print(model.summary())
    print(f"\nN = {int(model.nobs):,}")

    return model


def analysis_3_within_author(df):
    """Within-author comparison: high vs low engagement density."""
    print("\n" + "=" * 72)
    print("ANALYSIS 3: Within-Author JIT Risk (Same Author, Same Repo)")
    print("=" * 72)
    print("If the same person produces lower-risk code when reviewers engage")
    print("more deeply, that's strong causal evidence.\n")

    df = df.copy()
    # Median split within each author-repo pair
    groups = df.groupby(["repo", "author"])

    records = []
    for (repo, author), grp in groups:
        if len(grp) < 4:  # Need enough PRs for meaningful split
            continue
        median_eng = grp["engagement_density"].median()
        high = grp[grp["engagement_density"] >= median_eng]
        low = grp[grp["engagement_density"] < median_eng]
        if len(high) < 2 or len(low) < 2:
            continue
        records.append({
            "repo": repo,
            "author": author,
            "n_high": len(high),
            "n_low": len(low),
            "mean_risk_high_eng": high["jit_risk_score"].mean(),
            "mean_risk_low_eng": low["jit_risk_score"].mean(),
            "diff": low["jit_risk_score"].mean() - high["jit_risk_score"].mean(),
        })

    pairs = pd.DataFrame(records)
    print(f"Author-repo pairs with >= 4 PRs: {len(pairs):,}")

    if len(pairs) == 0:
        print("Not enough data for within-author analysis.")
        return None

    print(f"Mean risk (high engagement): {pairs['mean_risk_high_eng'].mean():.4f}")
    print(f"Mean risk (low engagement):  {pairs['mean_risk_low_eng'].mean():.4f}")
    print(f"Mean difference (low - high): {pairs['diff'].mean():.4f}")

    # Wilcoxon signed-rank test on paired differences
    stat, p_val = stats.wilcoxon(pairs["diff"])
    print(f"\nWilcoxon signed-rank: stat={stat:.1f}, p={p_val:.4g}, N={len(pairs)}")

    # Effect size: matched-pairs r = Z / sqrt(N)
    z_val = stats.norm.ppf(p_val / 2)  # approximate Z from p
    r_effect = abs(z_val) / np.sqrt(len(pairs))
    print(f"Effect size r = {r_effect:.4f}")

    return pairs


def analysis_4_dual_outcome(df):
    """Compare engagement effect on detector-based vs structural measures."""
    print("\n" + "=" * 72)
    print("ANALYSIS 4: Engagement Effect on BOTH Outcome Measures")
    print("=" * 72)
    print("If both detector outcomes and JIT risk point the same direction,")
    print("the finding is robust to detection window.\n")

    # Boolean outcomes: fillna before cast
    for col in ["reworked", "escaped"]:
        df[col] = df[col].fillna(False).astype(bool)

    df = df.copy()
    df["eng_rank"] = df["engagement_density"].rank(method="first")
    df["eng_quartile"] = pd.qcut(
        df["eng_rank"], q=4, labels=["Q1", "Q2", "Q3", "Q4"]
    )

    print("--- Rework/Escape Rates by Engagement Quartile (14-day detector) ---")
    for q in ["Q1", "Q2", "Q3", "Q4"]:
        subset = df[df["eng_quartile"] == q]
        print(f"  {q}: n={len(subset):,}, rework={subset['reworked'].mean():.3f}, "
              f"escape={subset['escaped'].mean():.3f}")

    print("\n--- JIT Risk Score by Engagement Quartile (structural proxy) ---")
    for q in ["Q1", "Q2", "Q3", "Q4"]:
        subset = df[df["eng_quartile"] == q]
        print(f"  {q}: n={len(subset):,}, mean_jit_risk={subset['jit_risk_score'].mean():.4f}, "
              f"median={subset['jit_risk_score'].median():.4f}")

    # Direction check
    q1_rework = df[df["eng_quartile"] == "Q1"]["reworked"].mean()
    q4_rework = df[df["eng_quartile"] == "Q4"]["reworked"].mean()
    q1_risk = df[df["eng_quartile"] == "Q1"]["jit_risk_score"].mean()
    q4_risk = df[df["eng_quartile"] == "Q4"]["jit_risk_score"].mean()

    rework_direction = "higher" if q1_rework > q4_rework else "lower"
    risk_direction = "higher" if q1_risk > q4_risk else "lower"

    print(f"\nDirection check:")
    print(f"  Low engagement (Q1) has {rework_direction} rework rate than Q4")
    print(f"  Low engagement (Q1) has {risk_direction} JIT risk than Q4")
    if rework_direction == risk_direction:
        print("  => CONSISTENT: Both measures agree on engagement direction.")
    else:
        print("  => DIVERGENT: Measures disagree — detection window may be the issue.")


def analysis_5_spec_status(df):
    """JIT Risk by Spec Status (q_overall > 0)."""
    print("\n" + "=" * 72)
    print("ANALYSIS 5: JIT Risk by Spec Status")
    print("=" * 72)
    print("Does having a spec predict lower JIT risk (smaller, more focused PRs)?")
    print("Tests the 'specs constrain scope' mechanism via code structure.\n")

    df = df.copy()
    df["q_overall"] = pd.to_numeric(df["q_overall"], errors="coerce").fillna(0)
    df["specd_flag"] = df["q_overall"] > 0

    specd = df[df["specd_flag"]]
    unspeqd = df[~df["specd_flag"]]

    print(f"Spec'd PRs:   n={len(specd):,}, mean risk={specd['jit_risk_score'].mean():.4f}, "
          f"median={specd['jit_risk_score'].median():.4f}")
    print(f"Unspec'd PRs: n={len(unspeqd):,}, mean risk={unspeqd['jit_risk_score'].mean():.4f}, "
          f"median={unspeqd['jit_risk_score'].median():.4f}")

    # Mann-Whitney U
    u_stat, p_val = stats.mannwhitneyu(
        specd["jit_risk_score"], unspeqd["jit_risk_score"], alternative="two-sided"
    )
    # Rank-biserial effect size: r = 1 - (2U)/(n1*n2)
    n1, n2 = len(specd), len(unspeqd)
    r_rb = 1 - (2 * u_stat) / (n1 * n2)
    print(f"\nMann-Whitney U={u_stat:.0f}, p={p_val:.4g}")
    print(f"Rank-biserial r = {r_rb:.4f}")

    # Also compare size components
    print(f"\n  Spec'd — mean size: {specd['jit_size'].mean():.0f}, "
          f"mean files: {specd['jit_spread'].mean():.1f}")
    print(f"  Unspec'd — mean size: {unspeqd['jit_size'].mean():.0f}, "
          f"mean files: {unspeqd['jit_spread'].mean():.1f}")


def analysis_6_loc_split(df):
    """400-LOC split: does engagement predict lower JIT risk in both groups?"""
    print("\n" + "=" * 72)
    print("ANALYSIS 6: 400-LOC Split on JIT Risk")
    print("=" * 72)
    print("SmartBear/Cisco cognitive threshold: does the engagement effect")
    print("disappear above 400 LOC?\n")

    df = df.copy()
    small = df[df["jit_size"] < 400]
    large = df[df["jit_size"] >= 400]

    for label, subset in [("< 400 LOC", small), (">= 400 LOC", large)]:
        print(f"--- {label} (n={len(subset):,}) ---")
        if len(subset) < 20:
            print("  Too few PRs for analysis.")
            continue

        # Spearman correlation: engagement_density vs jit_risk_score
        rho, p_val = stats.spearmanr(
            subset["engagement_density"], subset["jit_risk_score"]
        )
        print(f"  Spearman rho (engagement vs risk): {rho:.4f}, p={p_val:.4g}")

        # Quartile comparison
        try:
            subset = subset.copy()
            subset["eng_rank"] = subset["engagement_density"].rank(method="first")
            subset["eng_q"] = pd.qcut(
                subset["eng_rank"], q=4,
                labels=["Q1", "Q2", "Q3", "Q4"]
            )
            q1_risk = subset[subset["eng_q"] == "Q1"]["jit_risk_score"].mean()
            q4_risk = subset[subset["eng_q"] == "Q4"]["jit_risk_score"].mean()
            print(f"  Q1 mean risk: {q1_risk:.4f}, Q4 mean risk: {q4_risk:.4f}, "
                  f"diff: {q1_risk - q4_risk:.4f}")
        except ValueError:
            print("  Could not create engagement quartiles (too many ties).")
        print()


def analysis_7_ai_vs_human(df):
    """AI vs Human JIT risk profiles by engagement level."""
    print("\n" + "=" * 72)
    print("ANALYSIS 7: AI vs Human JIT Risk Profiles")
    print("=" * 72)
    print("Two-bucket classification: Human (classifier + no tag) vs")
    print("Augmented (tagged OR classifier). Presence, not degree.\n")

    df = df.copy()
    # Two-bucket AI classification:
    #   Augmented: f_ai_tagged==True OR ai_probability >= 0.5
    #   Human: f_ai_tagged==False AND ai_probability < 0.5
    # PRs missing ai_probability are excluded from this analysis.
    df["f_ai_tagged"] = df["f_ai_tagged"].fillna(False).astype(bool)
    df["ai_probability"] = pd.to_numeric(df["ai_probability"], errors="coerce")
    classifiable = df.dropna(subset=["ai_probability"]).copy()
    classifiable["ai_bucket"] = np.where(
        classifiable["f_ai_tagged"] | (classifiable["ai_probability"] >= 0.5),
        "Augmented", "Human"
    )

    ai = classifiable[classifiable["ai_bucket"] == "Augmented"]
    human = classifiable[classifiable["ai_bucket"] == "Human"]

    print(f"Classifiable PRs: {len(classifiable):,}")
    print(f"  Augmented (tagged OR ai_prob >= 0.5): {len(ai):,}")
    print(f"  Human (not tagged AND ai_prob < 0.5): {len(human):,}")

    if len(ai) < 10 or len(human) < 10:
        print("Not enough classified PRs for comparison.")
        return

    # Overall risk comparison
    print(f"\nOverall JIT risk:")
    print(f"  AI:    mean={ai['jit_risk_score'].mean():.4f}, "
          f"median={ai['jit_risk_score'].median():.4f}")
    print(f"  Human: mean={human['jit_risk_score'].mean():.4f}, "
          f"median={human['jit_risk_score'].median():.4f}")
    u, p = stats.mannwhitneyu(ai["jit_risk_score"], human["jit_risk_score"],
                               alternative="two-sided")
    print(f"  Mann-Whitney U={u:.0f}, p={p:.4g}")

    # Engagement effect by classification
    for label, subset in [("AI/Augmented", ai), ("Human", human)]:
        if len(subset) < 20:
            continue
        rho, p_val = stats.spearmanr(
            subset["engagement_density"], subset["jit_risk_score"]
        )
        print(f"\n  {label} — engagement vs risk: rho={rho:.4f}, p={p_val:.4g}, n={len(subset):,}")

    # AI PRs: spec'd vs unspec'd
    df["q_overall"] = pd.to_numeric(df["q_overall"], errors="coerce").fillna(0)
    ai_specd = ai[ai.index.isin(df[df["q_overall"] > 0].index)]
    ai_unspeqd = ai[ai.index.isin(df[df["q_overall"] <= 0].index)]
    if len(ai_specd) >= 5 and len(ai_unspeqd) >= 5:
        print(f"\n  AI spec'd risk:   mean={ai_specd['jit_risk_score'].mean():.4f}, n={len(ai_specd):,}")
        print(f"  AI unspec'd risk: mean={ai_unspeqd['jit_risk_score'].mean():.4f}, n={len(ai_unspeqd):,}")


def analysis_8_time_to_merge(df):
    """Time-to-merge as engagement proxy."""
    print("\n" + "=" * 72)
    print("ANALYSIS 8: Time-to-Merge as Engagement Proxy")
    print("=" * 72)

    df = df.copy()
    df["time_to_merge_hours"] = pd.to_numeric(
        df["time_to_merge_hours"], errors="coerce"
    )
    valid = df.dropna(subset=["time_to_merge_hours"])
    print(f"PRs with time_to_merge: {len(valid):,}")

    # Correlation: time_to_merge vs engagement_density
    rho, p = stats.spearmanr(valid["time_to_merge_hours"], valid["engagement_density"])
    print(f"\nCorrelation (time_to_merge vs engagement_density):")
    print(f"  Spearman rho={rho:.4f}, p={p:.4g}")

    # Regression: jit_risk ~ time_to_merge + engagement_density
    reg = valid[["jit_risk_score", "time_to_merge_hours", "engagement_density",
                 "additions", "deletions", "files_count"]].dropna().copy()
    reg["log_ttm"] = np.log1p(reg["time_to_merge_hours"])
    reg["log_additions"] = np.log1p(reg["additions"])
    reg["log_deletions"] = np.log1p(reg["deletions"])
    reg["log_files"] = np.log1p(reg["files_count"])

    X = reg[["log_ttm", "engagement_density", "log_additions",
             "log_deletions", "log_files"]]
    X = sm.add_constant(X)
    y = reg["jit_risk_score"]

    model = sm.OLS(y, X).fit(cov_type="HC1")
    print(f"\nOLS: jit_risk ~ log(time_to_merge) + engagement_density + size controls")
    print(model.summary())
    print(f"N = {int(model.nobs):,}")


def analysis_9_cross_validation(df):
    """Temporal cross-validation: train on early half, test on late half."""
    print("\n" + "=" * 72)
    print("ANALYSIS 9: Temporal Cross-Validation")
    print("=" * 72)
    print("Split by median merged_at date. Train engagement->risk model on")
    print("early half, test on late half.\n")

    df = df.copy()
    df["merged_at_dt"] = pd.to_datetime(df["merged_at"], errors="coerce")
    valid = df.dropna(subset=["merged_at_dt"]).copy()
    print(f"PRs with valid merged_at: {len(valid):,}")

    median_date = valid["merged_at_dt"].median()
    print(f"Median merge date: {median_date}")

    early = valid[valid["merged_at_dt"] <= median_date].copy()
    late = valid[valid["merged_at_dt"] > median_date].copy()
    print(f"Early half: {len(early):,}")
    print(f"Late half:  {len(late):,}")

    if len(early) < 50 or len(late) < 50:
        print("Not enough data for cross-validation.")
        return

    def fit_model(subset, label):
        reg = subset[["jit_risk_score", "engagement_density",
                       "additions", "deletions", "files_count"]].dropna().copy()
        reg["log_additions"] = np.log1p(reg["additions"])
        reg["log_deletions"] = np.log1p(reg["deletions"])
        reg["log_files"] = np.log1p(reg["files_count"])

        X = reg[["engagement_density", "log_additions", "log_deletions", "log_files"]]
        X = sm.add_constant(X)
        y = reg["jit_risk_score"]
        model = sm.OLS(y, X).fit(cov_type="HC1")
        eng_coef = model.params["engagement_density"]
        eng_p = model.pvalues["engagement_density"]
        print(f"\n  {label}: engagement_density coef={eng_coef:.6f}, "
              f"p={eng_p:.4g}, R²={model.rsquared:.4f}, N={int(model.nobs):,}")
        return model

    model_early = fit_model(early, "Train (early)")
    model_late = fit_model(late, "Test (late)")

    # Check coefficient sign consistency
    early_sign = np.sign(model_early.params["engagement_density"])
    late_sign = np.sign(model_late.params["engagement_density"])
    if early_sign == late_sign:
        print("\n  => REPLICATES: Same coefficient direction in both halves.")
    else:
        print("\n  => DOES NOT REPLICATE: Coefficient direction flips between halves.")


def save_outputs(df):
    """Save results files."""
    print("\n" + "=" * 72)
    print("SAVING OUTPUTS")
    print("=" * 72)

    # Per-PR JIT risk scores
    score_cols = [
        "repo", "pr_number", "jit_size", "jit_spread", "jit_churn",
        "jit_focus", "jit_risk_score", "engagement_density",
    ]
    scores = df[score_cols].copy()
    scores.to_csv(OUT_SCORES, index=False)
    print(f"Saved per-PR JIT risk scores: {OUT_SCORES}")
    print(f"  Rows: {len(scores):,}")

    # Summary results — one row per repo with aggregated stats
    summary_records = []
    for repo, grp in df.groupby("repo"):
        grp["q_overall_num"] = pd.to_numeric(grp["q_overall"], errors="coerce").fillna(0)
        specd = grp[grp["q_overall_num"] > 0]
        unspeqd = grp[grp["q_overall_num"] <= 0]

        rec = {
            "repo": repo,
            "n_prs": len(grp),
            "mean_jit_risk": grp["jit_risk_score"].mean(),
            "median_jit_risk": grp["jit_risk_score"].median(),
            "mean_engagement_density": grp["engagement_density"].mean(),
            "mean_jit_size": grp["jit_size"].mean(),
            "mean_jit_spread": grp["jit_spread"].mean(),
            "mean_jit_churn": grp["jit_churn"].mean(),
            "n_specd": len(specd),
            "n_unspeqd": len(unspeqd),
            "specd_mean_risk": specd["jit_risk_score"].mean() if len(specd) > 0 else np.nan,
            "unspeqd_mean_risk": unspeqd["jit_risk_score"].mean() if len(unspeqd) > 0 else np.nan,
        }

        # Spearman within repo (skip if either variable is constant)
        if len(grp) >= 10 and grp["engagement_density"].nunique() > 1:
            rho, p = stats.spearmanr(grp["engagement_density"], grp["jit_risk_score"])
            rec["engagement_risk_rho"] = rho
            rec["engagement_risk_p"] = p
        else:
            rec["engagement_risk_rho"] = np.nan
            rec["engagement_risk_p"] = np.nan

        summary_records.append(rec)

    summary = pd.DataFrame(summary_records)
    summary.to_csv(OUT_RESULTS, index=False)
    print(f"Saved repo-level summary: {OUT_RESULTS}")
    print(f"  Repos: {len(summary):,}")


def main():
    df = load_and_merge()
    df = compute_jit_features(df)

    analysis_1_quartiles(df)
    analysis_2_regression(df)
    analysis_3_within_author(df)
    analysis_4_dual_outcome(df)
    analysis_5_spec_status(df)
    analysis_6_loc_split(df)
    analysis_7_ai_vs_human(df)
    analysis_8_time_to_merge(df)
    analysis_9_cross_validation(df)

    save_outputs(df)

    print("\n" + "=" * 72)
    print("DONE")
    print("=" * 72)
    print("\nReminder: JIT risk score is a composite PROXY for defect-prone code.")
    print("It is not a defect measurement. Interpret as 'structurally riskier'")
    print("code, not 'known to have defects.'")
    print("43-repo convenience sample — cannot generalize beyond this dataset.")


if __name__ == "__main__":
    main()
