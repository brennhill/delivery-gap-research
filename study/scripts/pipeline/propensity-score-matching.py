#!/usr/bin/env python3
"""
Propensity score matching: spec'd PRs vs. unspec'd PRs with similar JIT risk.

Matches each spec'd PR to its nearest-neighbor unspec'd PR by propensity score
(P(specd=1 | JIT features + size controls)), then compares defect rates between
matched pairs.

Reads:  data/master-prs.csv
        data/szz-results-merged.csv
        data/jit-features-merged.csv
Writes: results/propensity-score-matching.txt
        results/psm-matched-pairs.csv

Methodology notes:
  - Propensity estimated via logistic regression on JIT features + size controls.
  - Nearest-neighbor 1:1 matching without replacement (greedy, ascending ps order).
  - Caliper = 0.05 standard deviations of the logit(ps) distribution.
  - Balance checked via standardized mean difference (SMD) before and after matching.
    SMD < 0.1 is the conventional "well-balanced" threshold (Austin 2011).
  - Treatment effect estimated as difference in proportions (spec'd - matched unspec'd)
    with a McNemar test on the matched pairs.
  - This is a sensitivity analysis, not a causal claim. Selection on observables
    only; unmeasured confounders (e.g., author skill, project maturity) remain.
"""

import pandas as pd
import numpy as np
import statsmodels.api as sm
from scipy.stats import chi2_contingency
import warnings
import sys
from pathlib import Path
from datetime import datetime, timezone

warnings.filterwarnings("ignore")

UTIL_DIR = Path(__file__).resolve().parents[1] / "util"
if str(UTIL_DIR) not in sys.path:
    sys.path.insert(0, str(UTIL_DIR))

from effect_units import format_percentage_point_delta  # noqa: E402
from result_paths import result_path  # noqa: E402
from szz_data import load_szz_results  # noqa: E402

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"
OUT_FILE = result_path(ROOT_DIR, "propensity-score-matching.txt")
PAIRS_FILE = result_path(ROOT_DIR, "psm-matched-pairs.csv")


class Tee:
    def __init__(self, *files):
        self.files = files

    def write(self, obj):
        for f in self.files:
            f.write(obj)
            f.flush()

    def flush(self):
        for f in self.files:
            try:
                f.flush()
            except ValueError:
                pass


out_f = open(OUT_FILE, "w")
sys.stdout = Tee(sys.__stdout__, out_f)

print(f"Analysis run: {datetime.now(timezone.utc).isoformat()}")
print(f"Script: {__file__}")
print()
print("PURPOSE: Match spec'd and unspec'd PRs on JIT risk profile,")
print("then compare defect rates within matched pairs.")
print("If matched effect is smaller than raw effect, JIT features partially")
print("explain the observed spec–defect association.")

# ── Load data ──────────────────────────────────────────────────────────────

df = pd.read_csv(DATA_DIR / "master-prs.csv", low_memory=False)
szz, szz_meta = load_szz_results(DATA_DIR)
jit = pd.read_csv(DATA_DIR / "jit-features-merged.csv")

print(f"\nDataset: {len(df):,} PRs, {df['repo'].nunique()} repos")
print(f"SZZ:     {len(szz):,} blame links, {szz['repo'].nunique()} repos")
if szz_meta["mode"] == "exact_only":
    print(
        "SZZ filter: exact merge-SHA only "
        f"({szz_meta['exact_rows']:,}/{szz_meta['source_rows']:,} rows kept; "
        f"{szz_meta['fallback_rows']:,} fallback, {szz_meta['unmapped_rows']:,} unmapped dropped)"
    )
print(f"JIT:     {len(jit):,} feature rows, {jit['repo'].nunique()} repos")

# ── Prep ────────────────────────────────────────────────────────────────────

df["merged_at"] = pd.to_datetime(df["merged_at"], utc=True, errors="coerce")
for col in ["reworked", "escaped", "strict_escaped", "specd"]:
    df[col] = df[col].fillna(False).astype(bool)

# Mark SZZ bug-introducing PRs
bug_prs = szz[["repo", "bug_pr_number"]].drop_duplicates()
bug_prs = bug_prs.rename(columns={"bug_pr_number": "pr_number"})
bug_prs["szz_buggy"] = True
df = df.merge(bug_prs, on=["repo", "pr_number"], how="left")
df["szz_buggy"] = df["szz_buggy"].fillna(False)

# Merge JIT features
ALL_JIT_COLS = ["ns", "nd", "nf", "entropy", "la", "ld", "lt", "fix",
                "ndev", "age", "nuc", "exp", "rexp", "sexp"]
present_jit = ["repo", "pr_number"] + [c for c in ALL_JIT_COLS if c in jit.columns]
df = df.merge(jit[present_jit], on=["repo", "pr_number"], how="left")

# ── Bot exclusion ──────────────────────────────────────────────────────────────

df["is_bot"] = df["f_is_bot_author"].fillna(False).astype(bool)
n_bots = df["is_bot"].sum()
df = df[~df["is_bot"]].copy()
print(f"Bot exclusion: {n_bots:,} bot PRs removed, {len(df):,} remaining")

# ── Size controls ────────────────────────────────────────────────────────────

df["log_add"]   = np.log1p(df["additions"])
df["log_del"]   = np.log1p(df["deletions"])
df["log_files"] = np.log1p(df["files_count"])

SIZE_CONTROLS = ["log_add", "log_del", "log_files"]

# ── Helper: standardized mean difference ─────────────────────────────────────

def smd(treated_vals, control_vals):
    """Standardized mean difference: (mean_t - mean_c) / pooled_sd.

    Uses pooled SD from the full (pre-match) sample, per Austin (2011).
    Returns NaN if SD is zero.
    """
    m_t = np.nanmean(treated_vals)
    m_c = np.nanmean(control_vals)
    sd_t = np.nanstd(treated_vals, ddof=1)
    sd_c = np.nanstd(control_vals, ddof=1)
    pooled_sd = np.sqrt((sd_t**2 + sd_c**2) / 2)
    if pooled_sd == 0:
        return np.nan
    return (m_t - m_c) / pooled_sd


def print_balance_table(treated, control, matched_treated, matched_control,
                        feature_cols):
    """Print SMD before and after matching for each covariate."""
    print(f"\n  {'Feature':<20} {'SMD before':>12} {'SMD after':>12} {'Balanced?':>10}")
    print(f"  {'-'*20} {'-'*12} {'-'*12} {'-'*10}")
    imbalanced_after = []
    for col in feature_cols:
        if col not in treated.columns:
            continue
        smd_before = smd(treated[col].values, control[col].values)
        smd_after  = smd(matched_treated[col].values, matched_control[col].values)
        balanced   = "yes" if pd.notna(smd_after) and abs(smd_after) < 0.1 else "NO"
        if balanced == "NO":
            imbalanced_after.append(col)
        b_str = f"{smd_before:+.3f}" if pd.notna(smd_before) else "   N/A"
        a_str = f"{smd_after:+.3f}"  if pd.notna(smd_after)  else "   N/A"
        print(f"  {col:<20} {b_str:>12} {a_str:>12} {balanced:>10}")
    if imbalanced_after:
        print(f"\n  WARNING: {len(imbalanced_after)} feature(s) still imbalanced after matching "
              f"(SMD >= 0.1): {imbalanced_after}")
        print("  Interpret matched estimates with caution.")
    else:
        print("\n  All features well-balanced after matching (SMD < 0.1).")
    return imbalanced_after


# ── Nearest-neighbor PSM (manual implementation) ─────────────────────────────

def run_psm(data, treatment_col, outcome_col, feature_cols, caliper_sd_multiplier=0.05,
            label=""):
    """Propensity score matching with nearest-neighbor 1:1 without replacement.

    Steps:
      1. Estimate P(treatment=1 | features) via logistic regression.
      2. Convert to logit(ps) for caliper matching (better scaling).
      3. For each treated unit, find closest control within caliper.
      4. Report: match rate, balance, treatment effect.
    """
    print(f"\n{'='*70}")
    print(f"PSM: {label}")
    print(f"{'='*70}")

    # Drop rows missing any feature or the outcome
    needed = [treatment_col, outcome_col] + feature_cols
    work = data.copy()
    for col in needed:
        work[col] = pd.to_numeric(work[col], errors="coerce")
    work = work.dropna(subset=needed).copy()
    work = work.reset_index(drop=True)

    # Filter to features with variance
    usable = []
    for col in feature_cols:
        if work[col].nunique() > 1:
            usable.append(col)
        else:
            print(f"  Dropping {col}: zero variance after dropna")
    if not usable:
        print(f"  [{label}] No usable features — cannot run PSM.")
        return None
    feature_cols = usable

    n_treated = work[treatment_col].sum()
    n_control = (work[treatment_col] == 0).sum()
    print(f"\n  Sample: {len(work):,} total  |  {int(n_treated):,} treated  |  {int(n_control):,} control")
    print(f"  Outcome: {outcome_col}  (base rate: {work[outcome_col].mean():.3f})")

    # ── Step 1: Estimate propensity scores ──────────────────────────────────
    X_ps = sm.add_constant(work[feature_cols].astype(float))
    y_ps = work[treatment_col].astype(int)

    try:
        ps_model = sm.Logit(y_ps, X_ps).fit(disp=0, maxiter=200)
    except Exception as e:
        print(f"  [{label}] Propensity model failed: {e}")
        return None

    work["ps"] = ps_model.predict(X_ps)

    # Trim extreme ps values (Winsorize to [0.01, 0.99]) to avoid matching
    # on near-deterministic scores
    work["ps"] = work["ps"].clip(0.01, 0.99)

    # Convert to logit scale for caliper
    work["logit_ps"] = np.log(work["ps"] / (1 - work["ps"]))

    logit_sd = work["logit_ps"].std()
    caliper = caliper_sd_multiplier * logit_sd
    print(f"\n  Propensity score: mean={work['ps'].mean():.3f}  "
          f"sd={work['ps'].std():.3f}")
    print(f"  Logit(PS): sd={logit_sd:.3f}  caliper={caliper:.4f} "
          f"({caliper_sd_multiplier} SD)")

    treated_idx  = work[work[treatment_col] == 1].index.tolist()
    control_pool = work[work[treatment_col] == 0].copy()

    # ── Step 2: Nearest-neighbor matching (greedy, no replacement) ──────────
    # Optimized: sort controls by logit_ps and use binary search for caliper

    # Sort treated by ps ascending to reduce systematic bias in greedy matching
    treated_sorted = work.loc[treated_idx].sort_values("logit_ps").index.tolist()

    # Pre-sort controls for binary search
    ctrl_sorted = control_pool.sort_values("logit_ps")
    ctrl_lps = ctrl_sorted["logit_ps"].values
    ctrl_indices = ctrl_sorted.index.values

    matched_pairs = []
    used_controls = set()

    for t_idx in treated_sorted:
        t_lps = work.loc[t_idx, "logit_ps"]

        # Binary search for caliper window
        lo = np.searchsorted(ctrl_lps, t_lps - caliper, side="left")
        hi = np.searchsorted(ctrl_lps, t_lps + caliper, side="right")

        best_dist = float("inf")
        best_idx = None

        for i in range(lo, hi):
            c_idx = ctrl_indices[i]
            if c_idx in used_controls:
                continue
            dist = abs(ctrl_lps[i] - t_lps)
            if dist < best_dist:
                best_dist = dist
                best_idx = c_idx

        if best_idx is not None:
            matched_pairs.append((t_idx, best_idx))
            used_controls.add(best_idx)

    n_matched = len(matched_pairs)
    n_unmatched = len(treated_idx) - n_matched
    print(f"\n  Matched: {n_matched:,} pairs  |  "
          f"Unmatched treated: {n_unmatched:,} "
          f"({n_unmatched/len(treated_idx)*100:.1f}% excluded)")

    if n_matched < 10:
        print(f"  [{label}] Too few matched pairs ({n_matched}) — cannot proceed.")
        return None

    # ── Step 3: Build matched datasets ──────────────────────────────────────

    t_indices = [p[0] for p in matched_pairs]
    c_indices = [p[1] for p in matched_pairs]

    matched_treated = work.loc[t_indices].copy()
    matched_control = work.loc[c_indices].copy()

    # ── Step 4: Covariate balance ────────────────────────────────────────────

    print(f"\n  --- Covariate balance ---")
    all_cov = feature_cols  # check all features used in PS model
    imbalanced = print_balance_table(
        work[work[treatment_col] == 1],
        work[work[treatment_col] == 0],
        matched_treated,
        matched_control,
        all_cov,
    )

    # ── Step 5: Treatment effect ─────────────────────────────────────────────

    rate_treated = matched_treated[outcome_col].mean()
    rate_control = matched_control[outcome_col].mean()
    diff = rate_treated - rate_control

    # McNemar test on matched pairs
    # b = treated=1, control=0   c = treated=0, control=1
    t_outcomes = matched_treated[outcome_col].values.astype(int)
    c_outcomes = matched_control[outcome_col].values.astype(int)
    b = ((t_outcomes == 1) & (c_outcomes == 0)).sum()
    c = ((t_outcomes == 0) & (c_outcomes == 1)).sum()

    if b + c > 0:
        # McNemar chi-square with continuity correction
        mcnemar_stat = (abs(b - c) - 1)**2 / (b + c)
        from scipy.stats import chi2
        mcnemar_p = chi2.sf(mcnemar_stat, df=1)
    else:
        mcnemar_stat = 0.0
        mcnemar_p = 1.0

    print(f"\n  --- Treatment effect in matched sample ---")
    print(f"  Spec'd rate:   {rate_treated:.4f}  ({int(matched_treated[outcome_col].sum())} / {len(matched_treated)} pairs)")
    print(f"  Unspec'd rate: {rate_control:.4f}  ({int(matched_control[outcome_col].sum())} / {len(matched_control)} pairs)")
    print(f"  Difference:    {format_percentage_point_delta(diff)}")
    print(f"  McNemar test:  chi2={mcnemar_stat:.3f}  p={mcnemar_p:.4f}")

    sig = "SIGNIFICANT (p<0.05)" if mcnemar_p < 0.05 else "not significant"
    print(f"  -> {sig}")

    # Raw (unmatched) comparison for reference
    raw_t = work[work[treatment_col] == 1][outcome_col].mean()
    raw_c = work[work[treatment_col] == 0][outcome_col].mean()
    print(f"\n  Raw (unmatched) rates for reference:")
    print(f"  Spec'd: {raw_t:.4f}  Unspec'd: {raw_c:.4f}  Diff: {format_percentage_point_delta(raw_t - raw_c)}")

    attenuation = ((diff - (raw_t - raw_c)) / abs(raw_t - raw_c) * 100
                   if (raw_t - raw_c) != 0 else float("nan"))
    print(f"  Attenuation after matching: {attenuation:+.1f}%")
    if not np.isnan(attenuation):
        if abs(attenuation) > 50:
            print("  *** Large attenuation: matching substantially reduces the effect.")
            print("  *** JIT risk profile explains much of the raw association.")
        elif abs(attenuation) > 20:
            print("  ** Moderate attenuation: partial confounding by JIT features.")
        else:
            print("  Effect is stable after matching. JIT features are not major confounders.")

    return {
        "label": label,
        "n_matched": n_matched,
        "n_unmatched": n_unmatched,
        "rate_treated": rate_treated,
        "rate_control": rate_control,
        "diff": diff,
        "mcnemar_p": mcnemar_p,
        "sig": sig,
        "raw_diff": raw_t - raw_c,
        "attenuation_pct": attenuation,
        "imbalanced_features": imbalanced,
        "matched_treated_idx": t_indices,
        "matched_control_idx": c_indices,
        "work": work,
        "treatment_col": treatment_col,
        "outcome_col": outcome_col,
    }


# ── Build feature list for PS model ─────────────────────────────────────────

# All JIT features except sexp (often zero-variance) — we filter dynamically
CANDIDATE_JIT = ["ns", "nd", "nf", "entropy", "la", "ld", "lt", "fix",
                 "ndev", "age", "nuc", "exp", "rexp"]
PS_FEATURES = SIZE_CONTROLS + [c for c in CANDIDATE_JIT if c in df.columns]

print(f"\nPropensity score features: {PS_FEATURES}")

# Add sexp only if it has variance in the data
if "sexp" in df.columns and df["sexp"].dropna().nunique() > 1:
    PS_FEATURES.append("sexp")
    print(f"  sexp added (has variance)")
else:
    print(f"  sexp excluded (zero or missing variance)")


# ════════════════════════════════════════════════════════════════════════════
# PSM 1: specs → szz_buggy (SZZ repos only)
# ════════════════════════════════════════════════════════════════════════════

szz_repo_set = set(szz["repo"].unique())
szz_df = df[df["repo"].isin(szz_repo_set)].copy()
szz_df["specd_int"] = szz_df["specd"].astype(int)

print(f"\nSZZ subset: {len(szz_df):,} PRs in {szz_df['repo'].nunique()} repos")

r_szz = run_psm(
    szz_df,
    treatment_col="specd_int",
    outcome_col="szz_buggy",
    feature_cols=PS_FEATURES,
    caliper_sd_multiplier=0.05,
    label="specs → SZZ bugs",
)


# ════════════════════════════════════════════════════════════════════════════
# PSM 2: specs → reworked (all repos)
# ════════════════════════════════════════════════════════════════════════════

df["specd_int"] = df["specd"].astype(int)

print(f"\nFull dataset: {len(df):,} PRs in {df['repo'].nunique()} repos")

r_rework = run_psm(
    df,
    treatment_col="specd_int",
    outcome_col="reworked",
    feature_cols=PS_FEATURES,
    caliper_sd_multiplier=0.05,
    label="specs → rework",
)


# ════════════════════════════════════════════════════════════════════════════
# Save matched pairs to CSV
# ════════════════════════════════════════════════════════════════════════════

all_pairs = []

for result in [r_szz, r_rework]:
    if result is None:
        continue
    work = result["work"]
    t_idxs = result["matched_treated_idx"]
    c_idxs = result["matched_control_idx"]
    treatment_col = result["treatment_col"]
    outcome_col   = result["outcome_col"]
    label         = result["label"]

    for t_idx, c_idx in zip(t_idxs, c_idxs):
        t_row = work.loc[t_idx]
        c_row = work.loc[c_idx]
        all_pairs.append({
            "analysis":           label,
            "treated_repo":       t_row.get("repo", ""),
            "treated_pr_number":  t_row.get("pr_number", ""),
            "treated_outcome":    t_row[outcome_col],
            "treated_ps":         t_row.get("ps", np.nan),
            "control_repo":       c_row.get("repo", ""),
            "control_pr_number":  c_row.get("pr_number", ""),
            "control_outcome":    c_row[outcome_col],
            "control_ps":         c_row.get("ps", np.nan),
            "ps_distance":        abs(t_row.get("logit_ps", np.nan) - c_row.get("logit_ps", np.nan)),
        })

if all_pairs:
    pairs_df = pd.DataFrame(all_pairs)
    pairs_df.to_csv(PAIRS_FILE, index=False)
    print(f"\nMatched pairs saved to: {PAIRS_FILE}")
    print(f"  {len(pairs_df):,} total pairs across {pairs_df['analysis'].nunique()} analyses")
else:
    print("\nNo matched pairs to save.")


# ════════════════════════════════════════════════════════════════════════════
# Summary
# ════════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("SUMMARY: PROPENSITY SCORE MATCHING RESULTS")
print("=" * 70)

for result in [r_szz, r_rework]:
    if result is None:
        print(f"\nAnalysis failed — see log above.")
        continue
    print(f"\n{result['label']}:")
    print(f"  Matched pairs: {result['n_matched']:,}  "
          f"(unmatched treated: {result['n_unmatched']:,})")
    print(f"  Spec'd defect rate:    {result['rate_treated']:.4f}")
    print(f"  Matched control rate:  {result['rate_control']:.4f}")
    print(f"  ATT estimate:          {format_percentage_point_delta(result['diff'])}")
    print(f"  McNemar p:             {result['mcnemar_p']:.4f}  [{result['sig']}]")
    print(f"  Raw (unmatched) diff:  {format_percentage_point_delta(result['raw_diff'])}")
    pct = result['attenuation_pct']
    if not np.isnan(pct):
        print(f"  Attenuation:           {pct:+.1f}%")
    if result['imbalanced_features']:
        print(f"  Imbalanced covariates: {result['imbalanced_features']}")

print("""
Interpretation:
  ATT = Average Treatment effect on the Treated (within matched pairs).
  Attenuation = % reduction in effect size after matching vs. raw comparison.
  Large attenuation → JIT features partially explain raw association.
  Stable effect + significance → association is not explained by JIT risk alone.
  CAVEAT: PSM only balances measured covariates. Unmeasured confounders remain.
""")

print(f"Done. Output written to: {OUT_FILE}")
out_f.close()
