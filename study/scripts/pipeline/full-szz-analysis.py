#!/usr/bin/env python3
"""
Full SZZ/JIT analysis on the complete dataset.

Reads: master-prs.csv, szz-results-merged.csv, jit-features-merged.csv
Writes: data/analysis-results.txt (human-readable report)

Every comparison uses:
  - Pooled (raw rates + Fisher's exact)
  - Controlled (logistic regression with size + repo controls)
  - Within-author (LPM with full demeaning + clustered SEs)

Methodology notes:
  - Within-author uses Linear Probability Model, not logit. Demeaning is
    exact for OLS (Frisch-Waugh-Lovell) but biased for logit (incidental
    parameters problem). LPM with clustered SEs is standard for binary
    outcomes with fixed effects (Angrist & Pischke 2009, Wooldridge 2010).
  - 8 analyses with no multiple-comparison correction. Interpret p-values
    with appropriate skepticism — at alpha=0.05, ~0.4 false positives expected.
"""

import pandas as pd
import numpy as np
import statsmodels.api as sm
from scipy.stats import fisher_exact, mannwhitneyu
import warnings
import sys
from pathlib import Path
from datetime import datetime, timezone

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
OUT_FILE = Path(__file__).resolve().parent.parent.parent / "results" / "analysis-results.txt"

# Redirect stdout to both file and terminal
class Tee:
    def __init__(self, *files):
        self.files = files
    def write(self, obj):
        for f in self.files:
            f.write(obj)
            f.flush()
    def flush(self):
        for f in self.files:
            f.flush()

out_f = open(OUT_FILE, "w")
sys.stdout = Tee(sys.__stdout__, out_f)

print(f"Analysis run: {datetime.now(timezone.utc).isoformat()}")
print(f"Script: {__file__}")

# ── Load data ─────────────────────────────────────────────────────────

df = pd.read_csv(DATA_DIR / "master-prs.csv", low_memory=False)
szz = pd.read_csv(DATA_DIR / "szz-results-merged.csv")
jit = pd.read_csv(DATA_DIR / "jit-features-merged.csv")

print(f"\nDataset: {len(df):,} PRs, {df['repo'].nunique()} repos")
print(f"SZZ: {len(szz):,} blame links, {szz['repo'].nunique()} repos")
print(f"JIT: {len(jit):,} feature rows, {jit['repo'].nunique()} repos")

# Parse and prep
df["merged_at"] = pd.to_datetime(df["merged_at"], utc=True, errors="coerce")
for col in ["reworked", "escaped", "strict_escaped", "specd"]:
    df[col] = df[col].fillna(False).astype(bool)

# Mark bug-introducing PRs from SZZ
bug_prs = szz[["repo", "bug_pr_number"]].drop_duplicates()
bug_prs = bug_prs.rename(columns={"bug_pr_number": "pr_number"})
bug_prs["szz_buggy"] = True
df = df.merge(bug_prs, on=["repo", "pr_number"], how="left")
df["szz_buggy"] = df["szz_buggy"].fillna(False)

# Merge JIT features
jit_cols = [c for c in ["repo", "pr_number", "ns", "nd", "nf", "entropy",
            "la", "ld", "lt", "fix", "ndev", "age", "nuc", "exp", "rexp", "sexp"]
            if c in jit.columns]
df = df.merge(jit[jit_cols], on=["repo", "pr_number"], how="left")

# AI classification
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
n_bots = df["is_bot"].sum()
df = df[~df["is_bot"]].copy()
print(f"Bot exclusion: {n_bots:,} bot PRs removed, {len(df):,} remaining")

# Size controls
df["log_add"] = np.log1p(df["additions"])
df["log_del"] = np.log1p(df["deletions"])
df["log_files"] = np.log1p(df["files_count"])

# Repo dummies for controlled regressions
repo_dummies = pd.get_dummies(df["repo"], prefix="repo", drop_first=True, dtype=int)
repo_dummy_cols = list(repo_dummies.columns)
df = pd.concat([df, repo_dummies], axis=1)

# Restrict to repos that have SZZ data
szz_repo_set = set(szz["repo"].unique())
in_szz = df["repo"].isin(szz_repo_set)

print(f"PRs in SZZ repos: {in_szz.sum():,}")
print(f"SZZ buggy PRs: {df['szz_buggy'].sum():,}")
print(f"AI-tagged PRs: {df['ai_tagged'].sum():,}")
print(f"Spec'd PRs: {df['specd'].sum():,}")
print(f"Spec quality scored PRs: {df['q_overall'].notna().sum():,}")

# ── Shared helpers ────────────────────────────────────────────────────

SIZE_CONTROLS = ["log_add", "log_del", "log_files"]

# Collect results for dynamic summary
results = {}


def safe_logit(y, X, label=""):
    """Run logistic regression, handle singular matrices gracefully."""
    try:
        model = sm.Logit(y, X).fit(disp=0, maxiter=100)
        return model
    except Exception as e:
        print(f"  [{label}] Logit failed: {e}")
        return None


def controlled_logit(data, treatment_col, outcome_col, label=""):
    """Logistic regression with size controls + repo fixed effects."""
    # Get repo dummies present in this subset — drop repos with <10 PRs
    # to avoid singular matrices from sparse categories
    repo_cols = [c for c in repo_dummy_cols
                 if c in data.columns and data[c].sum() >= 10]
    X = data[[treatment_col] + SIZE_CONTROLS + repo_cols].copy()
    X[treatment_col] = X[treatment_col].astype(float)
    X[repo_cols] = X[repo_cols].fillna(0)
    X = X.dropna(subset=SIZE_CONTROLS)
    X = sm.add_constant(X)
    y = data.loc[X.index, outcome_col].astype(int)

    m = safe_logit(y, X, label)
    if m is None:
        # Retry without repo dummies if singular
        print(f"  [{label}] Retrying without repo FE...")
        X = data[[treatment_col] + SIZE_CONTROLS].copy()
        X[treatment_col] = X[treatment_col].astype(float)
        X = X.dropna(subset=SIZE_CONTROLS)
        X = sm.add_constant(X)
        y = data.loc[X.index, outcome_col].astype(int)
        m = safe_logit(y, X, f"{label}-no-repo-fe")
        if m:
            coef = m.params[treatment_col]
            pval = m.pvalues[treatment_col]
            print(f"  {treatment_col}: coef={coef:.4f}, p={pval:.6f}")
            print(f"  (size controls only — repo FE caused singular matrix)")
            return {"coef": coef, "p": pval}
        return None

    coef = m.params[treatment_col]
    pval = m.pvalues[treatment_col]
    print(f"  {treatment_col}: coef={coef:.4f}, p={pval:.6f}")
    print(f"  (with {len(repo_cols)} repo dummies + size controls)")
    return {"coef": coef, "p": pval}


def within_author_lpm(data, treatment_col, outcome_col, controls=None,
                      min_prs=2, label="", binary_outcome=True):
    """Within-author Linear Probability Model with full demeaning.

    Demeans ALL variables (treatment, controls, outcome) by author.
    Equivalent to author fixed effects via Frisch-Waugh-Lovell.
    Uses clustered standard errors at the author level.
    No constant term (absorbed by demeaning).
    """
    if controls is None:
        controls = SIZE_CONTROLS

    ac = data["author"].value_counts()
    multi = data[data["author"].isin(ac[ac >= min_prs].index)].copy()
    if len(multi) < 50:
        print(f"  [{label}] Too few PRs for within-author: {len(multi)}")
        return None

    all_cols = [treatment_col] + controls + [outcome_col]
    for col in all_cols:
        multi[col] = pd.to_numeric(multi[col], errors="coerce")

    multi = multi.dropna(subset=all_cols)
    if len(multi) < 50:
        print(f"  [{label}] Too few complete cases: {len(multi)}")
        return None

    # Count authors with variation AFTER dropna (these identify the effect)
    author_variation = multi.groupby("author")[treatment_col].agg(["min", "max"])
    n_with_variation = (author_variation["min"] != author_variation["max"]).sum()
    n_authors = multi["author"].nunique()

    # Demean ALL variables by author
    author_means = multi.groupby("author")[all_cols].transform("mean")
    demeaned = multi[all_cols] - author_means

    # No constant — it's absorbed by demeaning (all demeaned vars have mean 0)
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
    direction = "INCREASES" if coef > 0 else "DECREASES" if coef < 0 else "NO EFFECT"
    sig = "SIGNIFICANT" if pval < 0.05 else "not significant"

    print(f"  Within-author LPM: N={len(multi):,}, "
          f"authors={n_authors:,} ({n_with_variation:,} with treatment variation)")
    print(f"  {treatment_col}: coef={coef:.4f}, p={pval:.6f}")
    if binary_outcome:
        print(f"  Interpretation: {coef:+.4f} pp change in P({outcome_col})")
    else:
        pct_change = (np.exp(coef) - 1) * 100
        print(f"  Interpretation: {pct_change:+.1f}% change in {outcome_col} "
              f"(coef on log scale)")
    print(f"  -> {direction} ({sig})")

    return {"coef": coef, "p": pval, "n": len(multi),
            "n_authors": n_authors, "n_with_variation": n_with_variation,
            "direction": direction, "sig": sig}


# ════════════════════════════════════════════════════════════════════
# ANALYSIS 1: DO SPECS REDUCE REAL BUGS (SZZ)?
# ════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("ANALYSIS 1: DO SPECS REDUCE REAL BUGS (SZZ)?")
print("=" * 70)

szz_df = df[in_szz].copy()
specd_rate = szz_df[szz_df["specd"]]["szz_buggy"].mean()
unspecd_rate = szz_df[~szz_df["specd"]]["szz_buggy"].mean()
n_specd = szz_df["specd"].sum()
n_unspecd = (~szz_df["specd"]).sum()

print(f"\nPooled rates:")
print(f"  Spec'd:   {specd_rate:.3f} ({n_specd:,} PRs)")
print(f"  Unspec'd: {unspecd_rate:.3f} ({n_unspecd:,} PRs)")

a = szz_df[szz_df["specd"]]["szz_buggy"].sum()
b = n_specd - a
c = szz_df[~szz_df["specd"]]["szz_buggy"].sum()
d = n_unspecd - c
odds, p = fisher_exact([[a, b], [c, d]])
print(f"  Fisher's exact: OR={odds:.3f}, p={p:.6f}")

print(f"\nControlled (logistic regression + repo FE):")
szz_df["specd_int"] = szz_df["specd"].astype(int)
r1_ctrl = controlled_logit(szz_df, "specd_int", "szz_buggy", label="specs-szz")

print(f"\nWithin-author (LPM, clustered SEs):")
r1_wa = within_author_lpm(szz_df, "specd_int", "szz_buggy", label="specs-szz-wa")
results["1_specs_bugs"] = r1_wa


# ════════════════════════════════════════════════════════════════════
# ANALYSIS 2: DOES SPEC QUALITY REDUCE REAL BUGS (SZZ)?
# ════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("ANALYSIS 2: DOES SPEC QUALITY REDUCE REAL BUGS (SZZ)?")
print("=" * 70)

scored = szz_df[szz_df["q_overall"].notna()].copy()
print(f"\nScored PRs in SZZ repos: {len(scored):,}")
print(f"  NOTE: Only {len(scored)/len(szz_df)*100:.1f}% of PRs have quality scores.")
print(f"  Selection: only spec'd PRs with substantial descriptions were scored.")
print(f"  Results may not generalize to unscored PRs.")

print(f"\nControlled (logistic regression + repo FE):")
r2_ctrl = controlled_logit(scored, "q_overall", "szz_buggy", label="quality-szz")

print(f"\nWithin-author (LPM, clustered SEs):")
r2_wa = within_author_lpm(scored, "q_overall", "szz_buggy", label="quality-szz-wa")
results["2_quality_bugs"] = r2_wa


# ════════════════════════════════════════════════════════════════════
# ANALYSIS 3: DOES REVIEW ENGAGEMENT REDUCE REAL BUGS (SZZ)?
# ════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("ANALYSIS 3: DOES REVIEW ENGAGEMENT REDUCE REAL BUGS (SZZ)?")
print("=" * 70)

# Pick engagement proxy: need a column with meaningful variance
# review_cycles has 69% zeros (median=0), making a median split useless.
# Use time_to_merge_hours which has a meaningful median (~11h).
eng_col = None
for candidate in ["total_comments_count", "time_to_merge_hours"]:
    if candidate in szz_df.columns:
        vals = szz_df[candidate].fillna(0)
        if vals.sum() > 0 and vals.median() > 0:
            eng_col = candidate
            break

# Fallback: review_cycles only if median > 0
if eng_col is None and "review_cycles" in szz_df.columns:
    vals = szz_df["review_cycles"].fillna(0)
    if vals.median() > 0:
        eng_col = "review_cycles"

if eng_col is None:
    # Last resort: use time_to_merge_hours even if median could be 0
    eng_col = "time_to_merge_hours"

print(f"\nEngagement proxy: {eng_col}")
szz_df["eng_val"] = pd.to_numeric(szz_df[eng_col], errors="coerce")
eng_median = szz_df["eng_val"].median()
print(f"  Median: {eng_median:.1f}")

if eng_median > 0:
    szz_df["high_eng"] = szz_df["eng_val"] > eng_median  # strict > to avoid all-in-one-bin

    n_hi = szz_df["high_eng"].sum()
    n_lo = (~szz_df["high_eng"]).sum()
    hi_rate = szz_df[szz_df["high_eng"]]["szz_buggy"].mean()
    lo_rate = szz_df[~szz_df["high_eng"]]["szz_buggy"].mean()

    print(f"  High engagement (>{eng_median:.1f}): {hi_rate:.3f} ({n_hi:,} PRs)")
    print(f"  Low engagement  (<={eng_median:.1f}): {lo_rate:.3f} ({n_lo:,} PRs)")

    a = szz_df[szz_df["high_eng"]]["szz_buggy"].sum()
    b = n_hi - a
    c = szz_df[~szz_df["high_eng"]]["szz_buggy"].sum()
    d = n_lo - c
    if min(a, b, c, d) > 0:
        odds, p = fisher_exact([[a, b], [c, d]])
        print(f"  Fisher's exact: OR={odds:.3f}, p={p:.6f}")
else:
    print(f"  WARNING: Median is 0 — binary split would be degenerate. Skipping pooled rates.")

print(f"\nWithin-author (LPM, clustered SEs) — continuous engagement:")
r3_wa = within_author_lpm(szz_df, "eng_val", "szz_buggy", label="eng-szz-wa")
results["3_engagement_bugs"] = r3_wa


# ════════════════════════════════════════════════════════════════════
# ANALYSIS 4: AI vs HUMAN BUG RATES (SZZ)
# ════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("ANALYSIS 4: AI vs HUMAN BUG RATES (SZZ)")
print("=" * 70)

ai_rate = szz_df[szz_df["ai_tagged"]]["szz_buggy"].mean()
human_rate = szz_df[~szz_df["ai_tagged"]]["szz_buggy"].mean()
n_ai = szz_df["ai_tagged"].sum()
n_human = (~szz_df["ai_tagged"]).sum()

print(f"\nPooled rates:")
print(f"  AI-tagged: {ai_rate:.3f} ({n_ai:,} PRs)")
print(f"  Human:     {human_rate:.3f} ({n_human:,} PRs)")

if n_ai > 0:
    a = szz_df[szz_df["ai_tagged"]]["szz_buggy"].sum()
    b = n_ai - a
    c = szz_df[~szz_df["ai_tagged"]]["szz_buggy"].sum()
    d = n_human - c
    odds, p = fisher_exact([[a, b], [c, d]])
    print(f"  Fisher's exact: OR={odds:.3f}, p={p:.6f}")

    print(f"\nControlled (logistic regression + repo FE):")
    szz_df["ai_int"] = szz_df["ai_tagged"].astype(int)
    r4_ctrl = controlled_logit(szz_df, "ai_int", "szz_buggy", label="ai-szz")

    print(f"\nWithin-author (LPM, clustered SEs):")
    r4_wa = within_author_lpm(szz_df, "ai_int", "szz_buggy", label="ai-szz-wa")
    results["4_ai_bugs"] = r4_wa
else:
    print("  No AI-tagged PRs in SZZ repos.")


# ════════════════════════════════════════════════════════════════════
# ANALYSIS 5: SPECS CONSTRAIN AI SCOPE
# ════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("ANALYSIS 5: DO SPECS CONSTRAIN AI SCOPE?")
print("=" * 70)

# Use additions+deletions as size measure (lines_changed has artificial zeros
# from missing catchrate data — 8k PRs default to 0)
szz_df["total_churn"] = szz_df["additions"].fillna(0) + szz_df["deletions"].fillna(0)
szz_df["log_churn"] = np.log1p(szz_df["total_churn"])

ai_prs = szz_df[szz_df["ai_tagged"]].copy()
human_prs = szz_df[~szz_df["ai_tagged"]].copy()

if len(ai_prs) > 10:
    # Filter to PRs with nonzero churn (exclude missing data)
    ai_valid = ai_prs[ai_prs["total_churn"] > 0]
    hu_valid = human_prs[human_prs["total_churn"] > 0]

    ai_s = ai_valid[ai_valid["specd"]]["total_churn"].median()
    ai_u = ai_valid[~ai_valid["specd"]]["total_churn"].median()
    hu_s = hu_valid[hu_valid["specd"]]["total_churn"].median()
    hu_u = hu_valid[~hu_valid["specd"]]["total_churn"].median()

    print(f"\nMedian total churn (additions+deletions), excluding zero-churn PRs:")
    print(f"  AI + spec:      {ai_s:>6.0f} ({ai_valid['specd'].sum():,} PRs)")
    print(f"  AI no spec:     {ai_u:>6.0f} ({(~ai_valid['specd']).sum():,} PRs)")
    print(f"  Human + spec:   {hu_s:>6.0f} ({hu_valid['specd'].sum():,} PRs)")
    print(f"  Human no spec:  {hu_u:>6.0f} ({(~hu_valid['specd']).sum():,} PRs)")

    if ai_s > 0:
        print(f"\n  AI sprawl ratio (unspec/spec): {ai_u/ai_s:.2f}x")
    if hu_s > 0:
        print(f"  Human sprawl ratio: {hu_u/hu_s:.2f}x")

    # Mann-Whitney on AI subset
    ai_spec_churn = ai_valid[ai_valid["specd"]]["total_churn"].dropna()
    ai_nospec_churn = ai_valid[~ai_valid["specd"]]["total_churn"].dropna()
    if len(ai_spec_churn) > 5 and len(ai_nospec_churn) > 5:
        u, p = mannwhitneyu(ai_nospec_churn, ai_spec_churn, alternative="greater")
        print(f"\n  Mann-Whitney (AI unspec > spec): U={u:.0f}, p={p:.2e}")

    hu_spec_churn = hu_valid[hu_valid["specd"]]["total_churn"].dropna()
    hu_nospec_churn = hu_valid[~hu_valid["specd"]]["total_churn"].dropna()
    if len(hu_spec_churn) > 5 and len(hu_nospec_churn) > 5:
        u, p = mannwhitneyu(hu_nospec_churn, hu_spec_churn, alternative="greater")
        print(f"  Mann-Whitney (Human unspec > spec): U={u:.0f}, p={p:.2e}")

    # Within-author LPM: does spec reduce log(churn) for AI PRs?
    print(f"\nWithin-author (LPM) — AI PRs only, outcome=log_churn:")
    ai_prs["specd_int"] = ai_prs["specd"].astype(int)
    r5_ai = within_author_lpm(ai_prs, "specd_int", "log_churn",
                              controls=["log_files"], label="scope-ai-wa",
                              binary_outcome=False)
    results["5_scope_ai"] = r5_ai

    print(f"\nWithin-author (LPM) — Human PRs only, outcome=log_churn:")
    human_prs["specd_int"] = human_prs["specd"].astype(int)
    r5_hu = within_author_lpm(human_prs, "specd_int", "log_churn",
                              controls=["log_files"], label="scope-human-wa",
                              binary_outcome=False)
    results["5_scope_human"] = r5_hu

    # Interaction: does spec constrain AI MORE than human?
    print(f"\nInteraction test (spec x AI on log_churn):")
    inter_df = szz_df[szz_df["total_churn"] > 0].copy()
    inter_df["specd_int"] = inter_df["specd"].astype(int)
    inter_df["ai_int"] = inter_df["ai_tagged"].astype(int)
    inter_df["spec_x_ai"] = inter_df["specd_int"] * inter_df["ai_int"]
    r5_inter = within_author_lpm(
        inter_df, "spec_x_ai", "log_churn",
        controls=["specd_int", "ai_int", "log_files"],
        label="scope-interaction-wa", binary_outcome=False)
    results["5_scope_interaction"] = r5_inter
else:
    print("  Too few AI-tagged PRs for scope analysis.")


# ════════════════════════════════════════════════════════════════════
# ANALYSIS 6: SPECS vs REWORK (proxy quality)
# ════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("ANALYSIS 6: DO SPECS REDUCE REWORK?")
print("=" * 70)

specd_rework = df[df["specd"]]["reworked"].mean()
unspecd_rework = df[~df["specd"]]["reworked"].mean()
print(f"\nPooled rates:")
print(f"  Spec'd:   {specd_rework:.3f} rework rate ({df['specd'].sum():,} PRs)")
print(f"  Unspec'd: {unspecd_rework:.3f} rework rate ({(~df['specd']).sum():,} PRs)")

a = df[df["specd"]]["reworked"].sum()
b = df["specd"].sum() - a
c = df[~df["specd"]]["reworked"].sum()
d_ = (~df["specd"]).sum() - c
odds, p = fisher_exact([[a, b], [c, d_]])
print(f"  Fisher's exact: OR={odds:.3f}, p={p:.6f}")

print(f"\nControlled (logistic regression + repo FE):")
df["specd_int"] = df["specd"].astype(int)
r6_ctrl = controlled_logit(df, "specd_int", "reworked", label="specs-rework")

print(f"\nWithin-author (LPM, clustered SEs):")
r6_wa = within_author_lpm(df, "specd_int", "reworked", label="specs-rework-wa")
results["6_specs_rework"] = r6_wa


# ════════════════════════════════════════════════════════════════════
# ANALYSIS 7: SPEC QUALITY vs REWORK
# ════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("ANALYSIS 7: DOES SPEC QUALITY REDUCE REWORK?")
print("=" * 70)

scored_all = df[df["q_overall"].notna()].copy()
print(f"\nScored PRs: {len(scored_all):,}")
print(f"  NOTE: {len(scored_all)/len(df)*100:.1f}% of all PRs — selection bias caveat applies.")

print(f"\nControlled (logistic regression + repo FE):")
r7_ctrl = controlled_logit(scored_all, "q_overall", "reworked", label="quality-rework")

print(f"\nWithin-author (LPM, clustered SEs):")
r7_wa = within_author_lpm(scored_all, "q_overall", "reworked", label="quality-rework-wa")
results["7_quality_rework"] = r7_wa


# ════════════════════════════════════════════════════════════════════
# ANALYSIS 8: JIT FEATURES vs SZZ BUGS
# ════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("ANALYSIS 8: JIT FEATURES vs SZZ BUGS")
print("=" * 70)

jit_df = szz_df[szz_df["ns"].notna()].copy()
jit_df["szz_buggy"] = jit_df["szz_buggy"].astype(bool)
print(f"\nPRs with JIT features in SZZ repos: {len(jit_df):,}")

if len(jit_df) > 100:
    jit_feats = ["ns", "nd", "nf", "entropy", "la", "ld", "lt", "fix", "ndev", "age", "nuc", "exp", "rexp", "sexp"]
    available = [f for f in jit_feats if f in jit_df.columns and jit_df[f].notna().sum() > 100]

    print(f"\nMann-Whitney U tests (buggy vs clean):")
    print(f"  {'Feature':>10s}  {'Buggy med':>10s}  {'Clean med':>10s}  {'p-value':>12s}  Sig")
    print(f"  {'-'*10}  {'-'*10}  {'-'*10}  {'-'*12}  ---")

    buggy_mask = jit_df["szz_buggy"]
    for feat in available:
        buggy_vals = jit_df.loc[buggy_mask, feat].dropna()
        clean_vals = jit_df.loc[~buggy_mask, feat].dropna()
        if len(buggy_vals) > 10 and len(clean_vals) > 10:
            buggy_med = buggy_vals.median()
            clean_med = clean_vals.median()
            u, p = mannwhitneyu(buggy_vals, clean_vals)
            sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""
            print(f"  {feat:>10s}  {buggy_med:>10.1f}  {clean_med:>10.1f}  {p:>12.2e}  {sig}")

    # Multivariate logistic regression with JIT features + repo FE
    print(f"\nJIT logistic regression on szz_buggy (+ repo FE):")
    print(f"  NOTE: la/ld correlate with additions/deletions; ns/nd/nf are correlated.")
    print(f"  Individual coefficients may be unstable due to multicollinearity.")
    jit_x_cols = [f for f in available if jit_df[f].notna().sum() > len(jit_df) * 0.5]
    if jit_x_cols:
        jit_repo_cols = [c for c in repo_dummy_cols if c in jit_df.columns and jit_df[c].sum() >= 10]
        jit_complete = jit_df.dropna(subset=jit_x_cols).copy()
        jit_complete[jit_repo_cols] = jit_complete[jit_repo_cols].fillna(0)
        print(f"  Complete cases for JIT regression: {len(jit_complete):,}/{len(jit_df):,}")
        X = jit_complete[jit_x_cols + jit_repo_cols]
        X = sm.add_constant(X)
        y = jit_complete["szz_buggy"].astype(int)
        m = safe_logit(y, X, "jit-szz")
        if m is None:
            # Retry without repo FE
            print(f"  Retrying without repo FE...")
            X = jit_complete[jit_x_cols]
            X = sm.add_constant(X)
            m = safe_logit(y, X, "jit-szz-no-repo-fe")
            jit_repo_cols = []
        if m:
            for feat in jit_x_cols:
                sig = "***" if m.pvalues[feat] < 0.001 else "**" if m.pvalues[feat] < 0.01 else "*" if m.pvalues[feat] < 0.05 else ""
                print(f"  {feat:>10s}: coef={m.params[feat]:>8.4f}, p={m.pvalues[feat]:.4f} {sig}")
            print(f"  Pseudo R-squared: {m.prsquared:.4f}")
            if jit_repo_cols:
                print(f"  ({len(jit_repo_cols)} repo dummies included but not shown)")
            else:
                print(f"  (no repo FE — singular matrix with dummies)")


# ════════════════════════════════════════════════════════════════════
# ROBUSTNESS: ALTERNATIVE OUTCOMES
# ════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("ROBUSTNESS 1: ALTERNATIVE OUTCOME MEASURES")
print("=" * 70)
print("\nDo specs reduce escaped defects? (alternative to SZZ)")

# escaped: catchrate classification of escaped defect
df["escaped"] = df["escaped"].fillna(False).astype(bool)
n_escaped = df["escaped"].sum()
print(f"  Escaped PRs: {n_escaped:,} ({n_escaped/len(df)*100:.1f}%)")

if n_escaped > 50:
    print(f"\n  Specs -> escaped (within-author LPM):")
    r_esc = within_author_lpm(df, "specd_int", "escaped", label="specs-escaped-wa")
    results["R1_specs_escaped"] = r_esc

# strict_escaped: escaped AND has fix-titled follow-up
df["strict_escaped"] = df["strict_escaped"].fillna(False).astype(bool)
n_strict = df["strict_escaped"].sum()
print(f"\n  Strict escaped PRs: {n_strict:,} ({n_strict/len(df)*100:.1f}%)")

if n_strict > 50:
    print(f"\n  Specs -> strict_escaped (within-author LPM):")
    r_strict = within_author_lpm(df, "specd_int", "strict_escaped", label="specs-strict-wa")
    results["R1_specs_strict_escaped"] = r_strict


# ════════════════════════════════════════════════════════════════════
# ROBUSTNESS: SPECS ADD NOTHING BEYOND JIT
# ════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("ROBUSTNESS 2: DO SPECS ADD PREDICTIVE POWER BEYOND JIT FEATURES?")
print("=" * 70)
print("\nIf JIT features already predict bugs, does adding spec information")
print("improve prediction? (Incremental validity test)")

jit_with_spec = szz_df[szz_df["ns"].notna()].copy()
jit_with_spec["szz_buggy"] = jit_with_spec["szz_buggy"].astype(bool)
jit_with_spec["specd_int"] = jit_with_spec["specd"].astype(int)
jit_core = ["ns", "nd", "nf", "entropy", "la", "ld", "lt", "fix", "ndev", "age", "nuc", "exp", "rexp", "sexp"]
jit_avail = [f for f in jit_core if f in jit_with_spec.columns
             and jit_with_spec[f].notna().sum() > len(jit_with_spec) * 0.5
             and jit_with_spec[f].nunique() > 1]

if len(jit_avail) > 3 and len(jit_with_spec) > 100:
    # Model 1: JIT features only
    jit_complete = jit_with_spec.dropna(subset=jit_avail).copy()
    print(f"  Complete JIT cases: {len(jit_complete):,}/{len(jit_with_spec):,}")
    X1 = jit_complete[jit_avail]
    X1 = sm.add_constant(X1)
    y = jit_complete["szz_buggy"].astype(int)
    m1 = safe_logit(y, X1, "jit-only")

    # Model 2: JIT features + spec presence
    X2 = jit_complete[jit_avail + ["specd_int"]]
    X2 = sm.add_constant(X2)
    m2 = safe_logit(y, X2, "jit+spec")

    # Model 3: JIT features + spec quality (scored subset only)
    jit_scored = jit_with_spec[jit_with_spec["q_overall"].notna()].copy()

    if m1 and m2:
        print(f"\n  Model 1 (JIT only):      Pseudo R² = {m1.prsquared:.4f}, AIC = {m1.aic:.0f}")
        print(f"  Model 2 (JIT + spec):    Pseudo R² = {m2.prsquared:.4f}, AIC = {m2.aic:.0f}")
        spec_coef = m2.params.get("specd_int", None)
        spec_p = m2.pvalues.get("specd_int", None)
        if spec_coef is not None:
            print(f"  specd_int in Model 2:    coef={spec_coef:.4f}, p={spec_p:.4f}")
            delta_r2 = m2.prsquared - m1.prsquared
            print(f"  ΔPseudo R²:              {delta_r2:.6f}")
            results["R2_spec_beyond_jit"] = {"coef": spec_coef, "p": spec_p,
                                              "delta_r2": delta_r2}

    if len(jit_scored) > 100:
        jit_scored_complete = jit_scored.dropna(subset=jit_avail + ["q_overall"]).copy()
        X3 = jit_scored_complete[jit_avail + ["q_overall"]]
        X3 = sm.add_constant(X3)
        y3 = jit_scored_complete["szz_buggy"].astype(int)
        m3 = safe_logit(y3, X3, "jit+quality")
        # JIT-only on same subset for fair comparison
        X3b = jit_scored_complete[jit_avail]
        X3b = sm.add_constant(X3b)
        m3b = safe_logit(y3, X3b, "jit-only-scored")
        if m3 and m3b:
            print(f"\n  On scored subset ({len(jit_scored):,} PRs):")
            print(f"  Model 1b (JIT only):     Pseudo R² = {m3b.prsquared:.4f}")
            print(f"  Model 3 (JIT + quality): Pseudo R² = {m3.prsquared:.4f}")
            q_coef = m3.params.get("q_overall", None)
            q_p = m3.pvalues.get("q_overall", None)
            if q_coef is not None:
                print(f"  q_overall in Model 3:    coef={q_coef:.4f}, p={q_p:.4f}")
                print(f"  ΔPseudo R²:              {m3.prsquared - m3b.prsquared:.6f}")


# ════════════════════════════════════════════════════════════════════
# ROBUSTNESS: INDIVIDUAL SPEC QUALITY DIMENSIONS
# ════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("ROBUSTNESS 3: INDIVIDUAL SPEC QUALITY DIMENSIONS")
print("=" * 70)
print("\nDo any of the 7 quality dimensions independently predict fewer bugs or rework?")

q_dims = ["q_outcome_clarity", "q_error_states", "q_scope_boundaries",
          "q_acceptance_criteria", "q_data_contracts", "q_dependency_context",
          "q_behavioral_specificity"]

scored_szz = szz_df[szz_df["q_overall"].notna()].copy()
scored_all2 = df[df["q_overall"].notna()].copy()

print(f"\n  {'Dimension':>25s}  {'→ SZZ bugs':>12s}  {'p':>8s}  {'→ rework':>12s}  {'p':>8s}")
print(f"  {'-'*25}  {'-'*12}  {'-'*8}  {'-'*12}  {'-'*8}")

for dim in q_dims:
    if dim not in scored_szz.columns:
        continue
    scored_szz[dim] = pd.to_numeric(scored_szz[dim], errors="coerce")
    scored_all2[dim] = pd.to_numeric(scored_all2[dim], errors="coerce")
    n_valid = scored_szz[dim].notna().sum()
    if n_valid < 100:
        continue

    # Bug outcome
    r_bug = within_author_lpm(scored_szz, dim, "szz_buggy", label=f"{dim}-bug",
                              min_prs=2)
    # Rework outcome
    r_rw = within_author_lpm(scored_all2, dim, "reworked", label=f"{dim}-rw",
                             min_prs=2)

    bug_str = f"{r_bug['coef']:+.4f}" if r_bug else "FAIL"
    bug_p = f"{r_bug['p']:.4f}" if r_bug else ""
    rw_str = f"{r_rw['coef']:+.4f}" if r_rw else "FAIL"
    rw_p = f"{r_rw['p']:.4f}" if r_rw else ""
    print(f"  {dim:>25s}  {bug_str:>12s}  {bug_p:>8s}  {rw_str:>12s}  {rw_p:>8s}")


# ════════════════════════════════════════════════════════════════════
# ROBUSTNESS: REPO-LEVEL AGGREGATION
# ════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("ROBUSTNESS 4: REPO-LEVEL ANALYSIS")
print("=" * 70)
print("\nDo repos with higher spec rates have lower defect/rework rates?")
print("(Ecological analysis — different unit, weaker but independent.)")

repo_agg = szz_df.groupby("repo").agg(
    n_prs=("pr_number", "count"),
    spec_rate=("specd", "mean"),
    bug_rate=("szz_buggy", "mean"),
    rework_rate=("reworked", "mean"),
    ai_rate=("ai_tagged", "mean"),
    mean_add=("additions", "mean"),
).reset_index()

# Only repos with enough PRs and some specs
repo_agg = repo_agg[repo_agg["n_prs"] >= 50]
print(f"\n  Repos with ≥50 PRs: {len(repo_agg)}")
print(f"  Spec rate: mean={repo_agg['spec_rate'].mean():.3f}, "
      f"median={repo_agg['spec_rate'].median():.3f}")

if len(repo_agg) >= 20:
    from scipy.stats import spearmanr

    # Spec rate vs bug rate
    rho, p = spearmanr(repo_agg["spec_rate"], repo_agg["bug_rate"])
    print(f"\n  Spearman: spec_rate vs bug_rate: ρ={rho:.3f}, p={p:.4f}")
    sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""
    direction = "higher specs → MORE bugs" if rho > 0 else "higher specs → fewer bugs"
    print(f"    {direction} {sig}")
    results["R4_repo_spec_bug"] = {"rho": rho, "p": p}

    # Spec rate vs rework rate
    rho, p = spearmanr(repo_agg["spec_rate"], repo_agg["rework_rate"])
    print(f"  Spearman: spec_rate vs rework_rate: ρ={rho:.3f}, p={p:.4f}")
    sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""
    direction = "higher specs → MORE rework" if rho > 0 else "higher specs → less rework"
    print(f"    {direction} {sig}")
    results["R4_repo_spec_rework"] = {"rho": rho, "p": p}

    # Partial correlation: spec_rate vs bug_rate, controlling for mean_add (repo size)
    print(f"\n  OLS: bug_rate ~ spec_rate + log(mean_additions), N={len(repo_agg)} repos")
    repo_agg["log_mean_add"] = np.log1p(repo_agg["mean_add"])
    repo_ols = repo_agg.dropna(subset=["spec_rate", "log_mean_add", "bug_rate"])
    X = repo_ols[["spec_rate", "log_mean_add"]].astype(float)
    X = sm.add_constant(X)
    y = repo_ols["bug_rate"].astype(float)
    m = sm.OLS(y, X).fit()
    print(f"    spec_rate: coef={m.params['spec_rate']:.4f}, p={m.pvalues['spec_rate']:.4f}")
    print(f"    R² = {m.rsquared:.4f}")


# ════════════════════════════════════════════════════════════════════
# SUMMARY — generated from actual results
# ════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("SUMMARY OF FINDINGS")
print("=" * 70)

print(f"""
Dataset: {len(df):,} PRs across {df['repo'].nunique()} repos
SZZ coverage: {szz['repo'].nunique()} repos with blame data, {df['szz_buggy'].sum():,} bug-introducing PRs
JIT coverage: {jit['repo'].nunique()} repos with JIT features

Methodology:
  - Controlled regressions include repo fixed effects + size controls
  - Within-author uses LPM with full demeaning (Frisch-Waugh-Lovell)
    and author-clustered standard errors
  - 8 analyses, no multiple-comparison correction applied
  - Coefficients are percentage-point changes in probability

Within-author results (the most credible estimates):
""")


def summarize(key, label):
    r = results.get(key)
    if r is None:
        print(f"  {label}: FAILED TO ESTIMATE")
        return
    direction = r["direction"]
    p = r["p"]
    coef = r["coef"]
    sig = r["sig"]
    n_var = r.get("n_with_variation", "?")
    print(f"  {label}:")
    print(f"    coef={coef:+.4f} pp, p={p:.4f} — {direction} ({sig})")
    print(f"    Identified from {n_var} authors with treatment variation")


summarize("1_specs_bugs", "1. Specs -> SZZ bugs")
summarize("2_quality_bugs", "2. Spec quality -> SZZ bugs")
summarize("3_engagement_bugs", "3. Review engagement -> SZZ bugs")
summarize("4_ai_bugs", "4. AI-tagged -> SZZ bugs")
summarize("6_specs_rework", "6. Specs -> rework")
summarize("7_quality_rework", "7. Spec quality -> rework")

print(f"\n  5. Scope constraint (AI PRs, spec -> log_churn):")
r5a = results.get("5_scope_ai")
r5h = results.get("5_scope_human")
r5i = results.get("5_scope_interaction")
if r5a:
    print(f"    AI: coef={r5a['coef']:+.4f}, p={r5a['p']:.4f} — {r5a['direction']} ({r5a['sig']})")
if r5h:
    print(f"    Human: coef={r5h['coef']:+.4f}, p={r5h['p']:.4f} — {r5h['direction']} ({r5h['sig']})")
if r5i:
    print(f"    Interaction (spec x AI): coef={r5i['coef']:+.4f}, p={r5i['p']:.4f} — {r5i['sig']}")

print(f"\n  8. JIT features: see detailed results above.")

print(f"""
Caveats:
  - Spec quality scored on {df['q_overall'].notna().sum():,}/{len(df):,} PRs ({df['q_overall'].notna().sum()/len(df)*100:.1f}%) — selection bias
  - AI detection uses co-author tags (voluntary) — unknown false negative rate
  - Convenience sample of {df['repo'].nunique()} repos — cannot generalize
  - Within-author identification requires authors with variation in treatment
""")

print(f"Results saved to: {OUT_FILE}")
out_f.close()
sys.stdout = sys.__stdout__
print(f"Analysis complete. Results in {OUT_FILE}")
