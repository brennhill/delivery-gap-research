"""
Questions Predict Quality: Do attention signals in PRs predict fewer defects?

Prior analysis found p=0.029 on n=221 that description-level attention signals
(questions, typos, hedging) predict fewer production escapes. With review comment
attention signals for 1,527 PRs, we now have a 7x expansion.

Caveat: 43-repo convenience sample, pooled analysis. Real N is ~42 repos.
"""

import sys
import numpy as np
import pandas as pd
from scipy import stats
from pathlib import Path

# Optional imports with graceful degradation
try:
    import statsmodels.api as sm
    from statsmodels.formula.api import logit
    HAS_STATSMODELS = True
except ImportError:
    HAS_STATSMODELS = False
    print("WARNING: statsmodels not available. Logistic regression analyses will be skipped.")

DATA_DIR = Path(__file__).parent / "data"

OUTCOMES = ["reworked", "escaped", "strict_escaped"]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def fisher_exact_with_or(table):
    """Fisher's exact test returning odds ratio, p-value, and the 2x2 table."""
    odds_ratio, p_value = stats.fisher_exact(table)
    return odds_ratio, p_value


def print_header(title):
    print(f"\n{'='*80}")
    print(f"  {title}")
    print(f"{'='*80}\n")


def outcome_comparison(df, group_col, outcomes, label=""):
    """Compare outcome rates between two groups defined by a boolean column."""
    rows = []
    for outcome in outcomes:
        if outcome not in df.columns:
            continue
        grp = df.groupby(group_col)[outcome]
        n_true = df[group_col].sum()
        n_false = (~df[group_col]).sum()

        rate_true = df.loc[df[group_col], outcome].mean()
        rate_false = df.loc[~df[group_col], outcome].mean()

        # 2x2 table: [[outcome_yes_group, outcome_no_group], [no_outcome_yes_group, no_outcome_no_group]]
        a = df.loc[df[group_col] & df[outcome]].shape[0]
        b = df.loc[~df[group_col] & df[outcome]].shape[0]
        c = df.loc[df[group_col] & ~df[outcome]].shape[0]
        d = df.loc[~df[group_col] & ~df[outcome]].shape[0]

        table = np.array([[a, b], [c, d]])
        odds_ratio, p_value = fisher_exact_with_or(table)

        row = {
            "label": label,
            "outcome": outcome,
            f"n_{group_col}=True": int(n_true),
            f"n_{group_col}=False": int(n_false),
            f"rate_{group_col}=True": round(rate_true, 4),
            f"rate_{group_col}=False": round(rate_false, 4),
            "odds_ratio": round(odds_ratio, 4),
            "p_value": round(p_value, 4),
        }
        rows.append(row)

        print(f"  {outcome}:")
        print(f"    With attention:    {a:>5}/{int(n_true):>5} = {rate_true:.4f}")
        print(f"    Without attention: {b:>5}/{int(n_false):>5} = {rate_false:.4f}")
        print(f"    Odds ratio: {odds_ratio:.4f}  p-value: {p_value:.4f}")
        direction = "LOWER with attention" if odds_ratio < 1 else "HIGHER with attention" if odds_ratio > 1 else "NO DIFFERENCE"
        print(f"    Direction: {direction}")
        print()

    return rows


# ---------------------------------------------------------------------------
# Load and prepare data
# ---------------------------------------------------------------------------

def load_data():
    print_header("DATA LOADING")

    master = pd.read_csv(DATA_DIR / "master-prs.csv", low_memory=False)
    print(f"Master PRs loaded: {len(master)} rows")

    review = pd.read_csv(DATA_DIR / "review-attention-signals.csv")
    print(f"Review attention signals loaded: {len(review)} rows")

    # Merge
    df = master.merge(review, on=["repo", "pr_number"], how="left")
    print(f"After left join: {len(df)} rows ({df['has_review_attention'].notna().sum()} with review data)")

    # Fill NAs for review columns
    for col in ["review_questions", "review_genuine_questions", "review_hedging_count",
                 "review_challenge_count", "review_total_length", "review_unique_reviewers",
                 "review_rounds"]:
        if col in df.columns:
            df[col] = df[col].fillna(0)

    df["has_review_attention"] = df["has_review_attention"].fillna(False).astype(bool)

    # Boolean columns — fillna before astype
    for col in ["reworked", "escaped", "strict_escaped", "is_trivial", "f_is_bot_author"]:
        if col in df.columns:
            df[col] = df[col].fillna(False).astype(bool)

    # Ensure numeric for description-level signals
    for col in ["f_questions", "f_typos", "f_casual"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    # Exclude trivial PRs and bot authors
    n_before = len(df)
    if "is_trivial" in df.columns:
        df["is_trivial"] = df["is_trivial"].fillna(False).astype(bool)
        n_trivial = df["is_trivial"].sum()
        df = df[~df["is_trivial"]].copy()
    else:
        n_trivial = 0
        print("  (is_trivial column not in master CSV — skipping trivial filter)")
    n_bot = df["f_is_bot_author"].sum() if "f_is_bot_author" in df.columns else 0
    if "f_is_bot_author" in df.columns:
        df = df[~df["f_is_bot_author"]].copy()
    print(f"\nExcluded {n_trivial} trivial PRs and {n_bot} bot-authored PRs")
    print(f"Analysis dataset: {len(df)} PRs (from {n_before})")

    # Build combined attention signal
    df["has_desc_attention"] = (df["f_questions"] > 0) | (df["f_typos"] > 0) | (df["f_casual"] > 0)
    df["has_any_attention"] = df["has_desc_attention"] | df["has_review_attention"]

    # Total question count (description + review)
    df["total_questions"] = df["f_questions"] + df["review_genuine_questions"]

    # Log-transformed size variables (add 1 to avoid log(0))
    df["log_additions"] = np.log1p(df["additions"])
    df["log_deletions"] = np.log1p(df["deletions"])
    df["log_files_count"] = np.log1p(df["files_count"])

    # Spec'd
    df["is_specd"] = (pd.to_numeric(df["q_overall"], errors="coerce") > 0)

    # AI classification: tagged OR classifier says AI-like (two-bucket approach)
    df["f_ai_tagged"] = df["f_ai_tagged"].fillna(False).astype(bool)
    df["ai_probability"] = pd.to_numeric(df["ai_probability"], errors="coerce").fillna(0)
    df["is_ai"] = df["f_ai_tagged"] | (df["ai_probability"] >= 0.5)

    print(f"\nAI classification: {df['is_ai'].sum()} / {len(df)} ({df['is_ai'].mean():.1%}) classified as AI/augmented")
    print(f"\nAttention signal coverage:")
    print(f"  has_desc_attention:   {df['has_desc_attention'].sum():>5} / {len(df)} ({df['has_desc_attention'].mean():.1%})")
    print(f"  has_review_attention: {df['has_review_attention'].sum():>5} / {len(df)} ({df['has_review_attention'].mean():.1%})")
    print(f"  has_any_attention:    {df['has_any_attention'].sum():>5} / {len(df)} ({df['has_any_attention'].mean():.1%})")

    print(f"\nOutcome base rates:")
    for o in OUTCOMES:
        if o in df.columns:
            print(f"  {o}: {df[o].sum():>5} / {len(df)} ({df[o].mean():.4f})")

    return df


# ---------------------------------------------------------------------------
# Analysis 1: Expanded Attention Signals vs Outcomes
# ---------------------------------------------------------------------------

def analysis_1(df):
    print_header("ANALYSIS 1: Expanded Attention Signals vs Outcomes")
    print(f"n = {len(df)}")
    print(f"PRs with any attention signal: {df['has_any_attention'].sum()}")
    print(f"PRs without attention signal:  {(~df['has_any_attention']).sum()}")
    print()

    rows = outcome_comparison(df, "has_any_attention", OUTCOMES, label="any_attention")
    return rows


# ---------------------------------------------------------------------------
# Analysis 2: Logistic Regression with Confounders
# ---------------------------------------------------------------------------

def analysis_2(df):
    print_header("ANALYSIS 2: Logistic Regression with Confounders")

    if not HAS_STATSMODELS:
        print("SKIPPED: statsmodels not installed")
        return []

    rows = []

    # Prepare variables
    reg_df = df[["escaped", "reworked", "strict_escaped",
                 "f_questions", "review_genuine_questions",
                 "log_additions", "log_deletions", "log_files_count",
                 "review_total_length", "review_unique_reviewers"]].copy()

    # Drop rows with any NaN
    reg_df = reg_df.dropna()
    print(f"Regression sample: n = {len(reg_df)}")

    # Convert booleans to int for statsmodels
    for col in OUTCOMES:
        if col in reg_df.columns:
            reg_df[col] = reg_df[col].astype(int)

    # Has questions (binary) for interpretability alongside count
    reg_df["has_questions"] = (reg_df["f_questions"] > 0).astype(int)

    formula_base = ("has_questions + review_genuine_questions + "
                    "log_additions + log_deletions + log_files_count + "
                    "review_total_length + review_unique_reviewers")

    for outcome in OUTCOMES:
        if outcome not in reg_df.columns:
            continue

        n_pos = reg_df[outcome].sum()
        if n_pos < 10:
            print(f"\n  {outcome}: Only {n_pos} positive cases — skipping (too few for logistic regression)")
            continue

        formula = f"{outcome} ~ {formula_base}"
        print(f"\n  Model: {formula}")
        print(f"  Positive cases: {n_pos} / {len(reg_df)}")

        try:
            model = logit(formula, data=reg_df).fit(disp=0, maxiter=100)
            print(f"\n  {'Variable':<30} {'Coef':>8} {'OR':>8} {'p-value':>10} {'95% CI OR':>18}")
            print(f"  {'-'*76}")

            for var in model.params.index:
                coef = model.params[var]
                pval = model.pvalues[var]
                ci = model.conf_int().loc[var]
                or_val = np.exp(coef)
                or_lo = np.exp(ci[0])
                or_hi = np.exp(ci[1])

                sig = ""
                if pval < 0.001:
                    sig = " ***"
                elif pval < 0.01:
                    sig = " **"
                elif pval < 0.05:
                    sig = " *"

                print(f"  {var:<30} {coef:>8.4f} {or_val:>8.4f} {pval:>10.4f} [{or_lo:.3f}, {or_hi:.3f}]{sig}")

                if var != "Intercept":
                    rows.append({
                        "analysis": "logistic_regression",
                        "outcome": outcome,
                        "variable": var,
                        "coefficient": round(coef, 4),
                        "odds_ratio": round(or_val, 4),
                        "p_value": round(pval, 4),
                        "ci_lower": round(or_lo, 4),
                        "ci_upper": round(or_hi, 4),
                        "n": len(reg_df),
                    })

            print(f"\n  Pseudo R-squared: {model.prsquared:.4f}")
            print(f"  AIC: {model.aic:.1f}")

        except Exception as e:
            print(f"  ERROR fitting model for {outcome}: {e}")

    return rows


# ---------------------------------------------------------------------------
# Analysis 3: Dose-Response
# ---------------------------------------------------------------------------

def analysis_3(df):
    print_header("ANALYSIS 3: Dose-Response (Total Question Count)")

    # Bin by total question count
    def question_bin(q):
        if q == 0:
            return "0"
        elif q == 1:
            return "1"
        elif q <= 3:
            return "2-3"
        else:
            return "4+"

    df = df.copy()
    df["q_bin"] = df["total_questions"].apply(question_bin)
    df["q_bin"] = pd.Categorical(df["q_bin"], categories=["0", "1", "2-3", "4+"], ordered=True)

    rows = []

    print(f"Question count distribution:")
    print(df["q_bin"].value_counts().sort_index().to_string())
    print()

    for outcome in OUTCOMES:
        if outcome not in df.columns:
            continue

        print(f"  {outcome} rates by question bin:")
        grouped = df.groupby("q_bin", observed=False)[outcome]
        for bin_label in ["0", "1", "2-3", "4+"]:
            grp = df[df["q_bin"] == bin_label]
            n = len(grp)
            n_pos = grp[outcome].sum()
            rate = grp[outcome].mean() if n > 0 else float("nan")
            print(f"    {bin_label:>4}: {n_pos:>4}/{n:>5} = {rate:.4f}")

            rows.append({
                "analysis": "dose_response",
                "outcome": outcome,
                "question_bin": bin_label,
                "n": n,
                "n_positive": int(n_pos),
                "rate": round(rate, 4),
            })

        # Logistic regression with question count as continuous for trend test
        if HAS_STATSMODELS:
            try:
                trend_df = df[["total_questions", outcome]].dropna().copy()
                trend_df[outcome] = trend_df[outcome].astype(int)
                model = logit(f"{outcome} ~ total_questions", data=trend_df).fit(disp=0)
                coef = model.params["total_questions"]
                pval = model.pvalues["total_questions"]
                or_val = np.exp(coef)
                direction = "decreasing" if coef < 0 else "increasing"
                print(f"    Trend test (logistic): coef={coef:.4f}, OR={or_val:.4f}, p={pval:.4f} ({direction})")
            except Exception as e:
                print(f"    Trend test failed: {e}")
        print()

    return rows


# ---------------------------------------------------------------------------
# Analysis 4: Within-Repo Analysis
# ---------------------------------------------------------------------------

def analysis_4(df):
    print_header("ANALYSIS 4: Within-Repo Analysis")

    rows = []

    for outcome in OUTCOMES:
        if outcome not in df.columns:
            continue

        print(f"  {outcome} — repos with >=20 PRs in each group:")

        repo_results = []
        for repo, grp in df.groupby("repo"):
            n_attn = grp["has_any_attention"].sum()
            n_no_attn = (~grp["has_any_attention"]).sum()

            if n_attn < 20 or n_no_attn < 20:
                continue

            rate_attn = grp.loc[grp["has_any_attention"], outcome].mean()
            rate_no_attn = grp.loc[~grp["has_any_attention"], outcome].mean()

            repo_results.append({
                "repo": repo,
                "n_attn": int(n_attn),
                "n_no_attn": int(n_no_attn),
                "rate_attn": rate_attn,
                "rate_no_attn": rate_no_attn,
                "attn_lower": rate_attn < rate_no_attn,
            })

        if not repo_results:
            print("    No repos meet the minimum sample size requirement")
            print()
            continue

        repo_df = pd.DataFrame(repo_results)
        n_repos = len(repo_df)
        n_lower = repo_df["attn_lower"].sum()
        n_higher = n_repos - n_lower

        print(f"    {n_repos} repos qualify")
        for _, r in repo_df.iterrows():
            direction = "LOWER" if r["attn_lower"] else "HIGHER"
            print(f"      {r['repo']:<40} attn={r['rate_attn']:.4f} vs no_attn={r['rate_no_attn']:.4f} [{direction}]")

        # Sign test
        sign_p = stats.binomtest(n_lower, n_repos, 0.5).pvalue
        print(f"\n    Sign test: {n_lower}/{n_repos} repos show lower {outcome} with attention")
        print(f"    p-value (two-sided binomial): {sign_p:.4f}")

        rows.append({
            "analysis": "within_repo",
            "outcome": outcome,
            "n_repos": n_repos,
            "n_lower_with_attention": int(n_lower),
            "n_higher_with_attention": int(n_higher),
            "sign_test_p": round(sign_p, 4),
        })
        print()

    return rows


# ---------------------------------------------------------------------------
# Analysis 5: Question Source Comparison
# ---------------------------------------------------------------------------

def analysis_5(df):
    print_header("ANALYSIS 5: Question Source Comparison")

    df = df.copy()

    # Source categories
    has_desc_q = df["f_questions"] > 0
    has_review_q = df["review_genuine_questions"] > 0

    df["q_source"] = "none"
    df.loc[has_desc_q & ~has_review_q, "q_source"] = "desc_only"
    df.loc[~has_desc_q & has_review_q, "q_source"] = "review_only"
    df.loc[has_desc_q & has_review_q, "q_source"] = "both"

    print(f"Question source distribution:")
    print(df["q_source"].value_counts().to_string())
    print()

    rows = []

    for outcome in OUTCOMES:
        if outcome not in df.columns:
            continue

        print(f"  {outcome} by question source:")
        for src in ["none", "desc_only", "review_only", "both"]:
            grp = df[df["q_source"] == src]
            n = len(grp)
            n_pos = grp[outcome].sum()
            rate = grp[outcome].mean() if n > 0 else float("nan")
            print(f"    {src:<15}: {n_pos:>4}/{n:>5} = {rate:.4f}")

            rows.append({
                "analysis": "question_source",
                "outcome": outcome,
                "source": src,
                "n": n,
                "n_positive": int(n_pos),
                "rate": round(rate, 4),
            })

        # Compare each source vs none using Fisher's exact
        baseline = df[df["q_source"] == "none"]
        for src in ["desc_only", "review_only", "both"]:
            grp = df[df["q_source"] == src]
            if len(grp) < 5:
                continue

            a = grp[outcome].sum()
            b = baseline[outcome].sum()
            c = len(grp) - a
            d = len(baseline) - b
            table = np.array([[int(a), int(b)], [int(c), int(d)]])
            or_val, p_val = fisher_exact_with_or(table)
            print(f"    {src} vs none: OR={or_val:.4f}, p={p_val:.4f}")

        print()

    # If statsmodels available, test whether combining adds signal
    if HAS_STATSMODELS:
        print("  Logistic regression: does combining sources add signal?")
        for outcome in OUTCOMES:
            if outcome not in df.columns:
                continue

            reg_df = df[["f_questions", "review_genuine_questions", outcome]].dropna().copy()
            reg_df[outcome] = reg_df[outcome].astype(int)
            reg_df["has_desc_q"] = (reg_df["f_questions"] > 0).astype(int)
            reg_df["has_review_q"] = (reg_df["review_genuine_questions"] > 0).astype(int)

            n_pos = reg_df[outcome].sum()
            if n_pos < 10:
                print(f"    {outcome}: too few positive cases ({n_pos}), skipping")
                continue

            try:
                model = logit(f"{outcome} ~ has_desc_q + has_review_q", data=reg_df).fit(disp=0)
                print(f"\n    {outcome}:")
                for var in ["has_desc_q", "has_review_q"]:
                    coef = model.params[var]
                    pval = model.pvalues[var]
                    or_val = np.exp(coef)
                    sig = "*" if pval < 0.05 else ""
                    print(f"      {var}: OR={or_val:.4f}, p={pval:.4f} {sig}")
            except Exception as e:
                print(f"    {outcome}: model failed — {e}")

    return rows


# ---------------------------------------------------------------------------
# Analysis 6: Robustness Checks
# ---------------------------------------------------------------------------

def analysis_6(df, df_full_with_trivial):
    print_header("ANALYSIS 6: Robustness Checks")

    rows = []

    # 6a: Compare full dataset vs non-trivial
    print("  6a: Effect of excluding trivial PRs")
    print(f"      Full dataset (excl bots):        n = {len(df_full_with_trivial)}")
    print(f"      Non-trivial dataset (excl bots):  n = {len(df)}")
    print()

    for outcome in OUTCOMES:
        if outcome not in df.columns:
            continue

        # Non-trivial (our main analysis set)
        n_attn = df["has_any_attention"].sum()
        n_no = (~df["has_any_attention"]).sum()
        rate_attn = df.loc[df["has_any_attention"], outcome].mean()
        rate_no = df.loc[~df["has_any_attention"], outcome].mean()

        a = int(df.loc[df["has_any_attention"] & df[outcome]].shape[0])
        b = int(df.loc[~df["has_any_attention"] & df[outcome]].shape[0])
        c = int(n_attn - a)
        d = int(n_no - b)
        or_nt, p_nt = fisher_exact_with_or(np.array([[a, b], [c, d]]))

        # Full (including trivial)
        ft = df_full_with_trivial
        n_attn_f = ft["has_any_attention"].sum()
        n_no_f = (~ft["has_any_attention"]).sum()
        rate_attn_f = ft.loc[ft["has_any_attention"], outcome].mean()
        rate_no_f = ft.loc[~ft["has_any_attention"], outcome].mean()

        a_f = int(ft.loc[ft["has_any_attention"] & ft[outcome]].shape[0])
        b_f = int(ft.loc[~ft["has_any_attention"] & ft[outcome]].shape[0])
        c_f = int(n_attn_f - a_f)
        d_f = int(n_no_f - b_f)
        or_f, p_f = fisher_exact_with_or(np.array([[a_f, b_f], [c_f, d_f]]))

        print(f"    {outcome}:")
        print(f"      Non-trivial: OR={or_nt:.4f}, p={p_nt:.4f}  (attn={rate_attn:.4f}, no_attn={rate_no:.4f})")
        print(f"      Full:        OR={or_f:.4f}, p={p_f:.4f}  (attn={rate_attn_f:.4f}, no_attn={rate_no_f:.4f})")

        consistent = (or_nt < 1 and or_f < 1) or (or_nt > 1 and or_f > 1)
        print(f"      Direction consistent: {consistent}")
        print()

        rows.append({
            "analysis": "robustness_trivial",
            "outcome": outcome,
            "subset": "non_trivial",
            "or": round(or_nt, 4),
            "p": round(p_nt, 4),
            "n": len(df),
        })
        rows.append({
            "analysis": "robustness_trivial",
            "outcome": outcome,
            "subset": "full",
            "or": round(or_f, 4),
            "p": round(p_f, 4),
            "n": len(ft),
        })

    # 6b: AI vs Human PRs
    print("\n  6b: Effect by classification (AI vs Human)")

    for classification_label, mask in [("human", ~df["is_ai"]), ("ai/augmented", df["is_ai"])]:
        subset = df[mask].copy()
        print(f"\n    {classification_label} PRs: n = {len(subset)}")
        n_attn = subset["has_any_attention"].sum()
        n_no = (~subset["has_any_attention"]).sum()
        print(f"      With attention: {n_attn}, Without: {n_no}")

        if n_attn < 10 or n_no < 10:
            print(f"      Too few in one group — skipping")
            continue

        for outcome in OUTCOMES:
            if outcome not in subset.columns:
                continue

            a = int(subset.loc[subset["has_any_attention"] & subset[outcome]].shape[0])
            b = int(subset.loc[~subset["has_any_attention"] & subset[outcome]].shape[0])
            c = int(n_attn - a)
            d = int(n_no - b)

            table = np.array([[a, b], [c, d]])
            or_val, p_val = fisher_exact_with_or(table)

            rate_attn = subset.loc[subset["has_any_attention"], outcome].mean()
            rate_no = subset.loc[~subset["has_any_attention"], outcome].mean()

            print(f"      {outcome}: OR={or_val:.4f}, p={p_val:.4f}  (attn={rate_attn:.4f}, no_attn={rate_no:.4f})")

            rows.append({
                "analysis": "robustness_classification",
                "outcome": outcome,
                "classification": classification_label,
                "or": round(or_val, 4),
                "p": round(p_val, 4),
                "n": len(subset),
            })

    return rows


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    df = load_data()

    # Keep a version with trivial PRs for robustness check
    # Reload to get the full dataset (excl bots only)
    master = pd.read_csv(DATA_DIR / "master-prs.csv", low_memory=False)
    review = pd.read_csv(DATA_DIR / "review-attention-signals.csv")
    df_full = master.merge(review, on=["repo", "pr_number"], how="left")

    for col in ["review_questions", "review_genuine_questions", "review_hedging_count",
                 "review_challenge_count", "review_total_length", "review_unique_reviewers",
                 "review_rounds"]:
        if col in df_full.columns:
            df_full[col] = df_full[col].fillna(0)
    df_full["has_review_attention"] = df_full["has_review_attention"].fillna(False).astype(bool)
    for col in ["reworked", "escaped", "strict_escaped", "is_trivial", "f_is_bot_author"]:
        if col in df_full.columns:
            df_full[col] = df_full[col].fillna(False).astype(bool)
    for col in ["f_questions", "f_typos", "f_casual"]:
        if col in df_full.columns:
            df_full[col] = pd.to_numeric(df_full[col], errors="coerce").fillna(0)

    df_full = df_full[~df_full["f_is_bot_author"]].copy()
    df_full["has_desc_attention"] = (df_full["f_questions"] > 0) | (df_full["f_typos"] > 0) | (df_full["f_casual"] > 0)
    df_full["has_any_attention"] = df_full["has_desc_attention"] | df_full["has_review_attention"]
    df_full["f_ai_tagged"] = df_full["f_ai_tagged"].fillna(False).astype(bool)
    df_full["ai_probability"] = pd.to_numeric(df_full["ai_probability"], errors="coerce").fillna(0)
    df_full["is_ai"] = df_full["f_ai_tagged"] | (df_full["ai_probability"] >= 0.5)

    all_rows = []

    # Run all analyses
    all_rows.extend(analysis_1(df))
    all_rows.extend(analysis_2(df))
    all_rows.extend(analysis_3(df))
    all_rows.extend(analysis_4(df))
    all_rows.extend(analysis_5(df))
    all_rows.extend(analysis_6(df, df_full))

    # ---------------------------------------------------------------------------
    # Summary
    # ---------------------------------------------------------------------------
    print_header("SUMMARY")
    print("Caveat: 43-repo convenience sample. Pooled analysis treats PRs as")
    print("independent, but they are clustered within repos. Real N is ~42 repos.")
    print("p-values from pooled Fisher's exact tests are anti-conservative.")
    print()

    # Save results
    if all_rows:
        results_df = pd.DataFrame(all_rows)
        out_path = DATA_DIR / "questions-quality-results.csv"
        results_df.to_csv(out_path, index=False)
        print(f"Results saved to {out_path}")
        print(f"Total result rows: {len(results_df)}")
    else:
        print("No results to save.")


if __name__ == "__main__":
    main()
