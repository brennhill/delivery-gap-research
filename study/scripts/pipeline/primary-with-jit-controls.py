#!/usr/bin/env python3
"""
H1/H2 within-author LPM with JIT features as additional controls.

Reviewer criticism: JIT features explain all variance that specs claim to provide.
This script reruns the primary H1 (specs → SZZ bugs) and H2 (specs → rework)
models with JIT features added alongside size controls, so we can see whether
the spec coefficient shrinks or becomes insignificant when JIT is controlled.

Reads:  data/master-prs.csv
        data/szz-results-merged.csv
        data/jit-features-merged.csv
Writes: results/primary-with-jit-controls.txt
"""

import pandas as pd
import numpy as np
import statsmodels.api as sm
import warnings
import sys
from pathlib import Path
from datetime import datetime, timezone

warnings.filterwarnings("ignore")

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
OUT_FILE = Path(__file__).resolve().parent.parent.parent / "results" / "primary-with-jit-controls.txt"

OUT_FILE.parent.mkdir(parents=True, exist_ok=True)


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
print("PURPOSE: Does adding JIT features change the spec coefficient?")
print("If spec coef shrinks substantially (>50%) or loses significance,")
print("reviewer concern is supported: JIT features confound the spec effect.")

# ── Load data ──────────────────────────────────────────────────────────────

df = pd.read_csv(DATA_DIR / "master-prs.csv", low_memory=False)
szz = pd.read_csv(DATA_DIR / "szz-results-merged.csv")
jit = pd.read_csv(DATA_DIR / "jit-features-merged.csv")

print(f"\nDataset: {len(df):,} PRs, {df['repo'].nunique()} repos")
print(f"SZZ:     {len(szz):,} blame links, {szz['repo'].nunique()} repos")
print(f"JIT:     {len(jit):,} feature rows, {jit['repo'].nunique()} repos")

# ── Prep ────────────────────────────────────────────────────────────────────

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
ALL_JIT_COLS = ["ns", "nd", "nf", "entropy", "la", "ld", "lt", "fix",
                "ndev", "age", "nuc", "exp", "rexp", "sexp"]
present_jit = ["repo", "pr_number"] + [c for c in ALL_JIT_COLS if c in jit.columns]
df = df.merge(jit[present_jit], on=["repo", "pr_number"], how="left")

# ── Bot exclusion ──────────────────────────────────────────────────────────────

df["is_bot"] = df["f_is_bot_author"].fillna(False).astype(bool)
n_bots = df["is_bot"].sum()
df = df[~df["is_bot"]].copy()
print(f"Bot exclusion: {n_bots:,} bot PRs removed, {len(df):,} remaining")

# ── Size controls and treatment ──────────────────────────────────────────────

df["log_add"]   = np.log1p(df["additions"])
df["log_del"]   = np.log1p(df["deletions"])
df["log_files"] = np.log1p(df["files_count"])
df["specd_int"] = df["specd"].astype(int)

SIZE_CONTROLS = ["log_add", "log_del", "log_files"]

# ── Restrict to SZZ repos ───────────────────────────────────────────────────

szz_repo_set = set(szz["repo"].unique())
szz_df = df[df["repo"].isin(szz_repo_set)].copy()

print(f"\nPRs in SZZ repos: {len(szz_df):,}")
print(f"SZZ buggy PRs:    {szz_df['szz_buggy'].sum():,}")
print(f"Spec'd PRs:       {szz_df['specd'].sum():,}")
print(f"Reworked PRs:     {szz_df['reworked'].sum():,}")

# ── Determine which JIT features have usable variance ───────────────────────

def select_jit_features(data, candidates):
    """Return JIT features that exist in data and have nunique > 1.

    Excludes any feature with zero variance (would cause singular matrix).
    Also drops sexp if it has near-zero variance (often all-zero in practice).
    """
    selected = []
    skipped = []
    for col in candidates:
        if col not in data.columns:
            skipped.append(f"{col} (not in data)")
            continue
        n_unique = data[col].dropna().nunique()
        if n_unique <= 1:
            skipped.append(f"{col} (nunique={n_unique}, zero variance)")
            continue
        selected.append(col)
    return selected, skipped


# ── Within-author LPM (shared helper) ───────────────────────────────────────

def within_author_lpm(data, treatment_col, outcome_col, controls,
                      min_prs=2, label=""):
    """Within-author LPM with full demeaning and author-clustered SEs.

    Equivalent to author fixed effects via Frisch-Waugh-Lovell theorem.
    No constant (absorbed by demeaning).
    """
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
        print(f"  [{label}] Too few complete cases after dropna: {len(multi)}")
        return None

    author_variation = multi.groupby("author")[treatment_col].agg(["min", "max"])
    n_with_variation = (author_variation["min"] != author_variation["max"]).sum()
    n_authors = multi["author"].nunique()

    # Demean all variables by author
    author_means = multi.groupby("author")[all_cols].transform("mean")
    demeaned = multi[all_cols] - author_means

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
    ci_lo = model.conf_int().loc[treatment_col, 0]
    ci_hi = model.conf_int().loc[treatment_col, 1]
    sig = "p<0.05" if pval < 0.05 else "p≥0.05"

    print(f"  N={len(multi):,}, authors={n_authors:,} "
          f"({n_with_variation:,} with treatment variation)")
    print(f"  specd_int: coef={coef:+.4f}  95%CI [{ci_lo:+.4f}, {ci_hi:+.4f}]  "
          f"p={pval:.4f}  [{sig}]")
    print(f"  Controls: {', '.join(controls)}")

    return {
        "coef": coef, "p": pval, "ci_lo": ci_lo, "ci_hi": ci_hi,
        "n": len(multi), "n_authors": n_authors,
        "n_with_variation": n_with_variation, "sig": sig,
        "controls": controls,
    }


def compare_results(r_base, r_jit, label):
    """Print a side-by-side comparison of baseline vs JIT-controlled results."""
    print(f"\n  --- {label}: Comparison ---")
    if r_base is None or r_jit is None:
        print("  Cannot compare — one or both models failed.")
        return

    coef_base = r_base["coef"]
    coef_jit  = r_jit["coef"]
    pct_change = ((coef_jit - coef_base) / abs(coef_base) * 100) if coef_base != 0 else float("nan")

    print(f"  Baseline (size only): coef={coef_base:+.4f}  {r_base['sig']}")
    print(f"  + JIT controls:       coef={coef_jit:+.4f}  {r_jit['sig']}")
    print(f"  Change in coef:       {pct_change:+.1f}%")

    if abs(pct_change) > 50:
        print(f"  *** LARGE CHANGE: JIT features explain >50% of spec effect.")
        print(f"  *** Reviewer concern is SUPPORTED for this outcome.")
    elif abs(pct_change) > 25:
        print(f"  ** MODERATE CHANGE: JIT features explain 25-50% of spec effect.")
        print(f"  ** Partial confounding — worth disclosing.")
    else:
        print(f"  Spec coef is STABLE (<25% change). JIT features do not explain away the effect.")

    if r_base["sig"] == "p<0.05" and r_jit["sig"] != "p<0.05":
        print(f"  *** SIGNIFICANCE LOST after adding JIT controls.")
    elif r_base["sig"] != "p<0.05" and r_jit["sig"] == "p<0.05":
        print(f"  ** Became significant after adding JIT controls (unexpected).")


# ════════════════════════════════════════════════════════════════════════════
# H1: specd → szz_buggy
# ════════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("H1: SPECS → SZZ BUGS (within-author LPM)")
print("=" * 70)

jit_features_h1, skipped_h1 = select_jit_features(
    szz_df, [c for c in ALL_JIT_COLS if c != "sexp"] + ["sexp"]
)
print(f"\nJIT features selected for H1: {jit_features_h1}")
if skipped_h1:
    print(f"Skipped: {skipped_h1}")

print(f"\n-- H1 baseline (size controls only) --")
r_h1_base = within_author_lpm(
    szz_df, "specd_int", "szz_buggy",
    controls=SIZE_CONTROLS,
    label="H1-baseline",
)

print(f"\n-- H1 + JIT controls --")
r_h1_jit = within_author_lpm(
    szz_df, "specd_int", "szz_buggy",
    controls=SIZE_CONTROLS + jit_features_h1,
    label="H1-jit",
)

compare_results(r_h1_base, r_h1_jit, "H1 (specs → SZZ bugs)")


# ════════════════════════════════════════════════════════════════════════════
# H2: specd → reworked
# ════════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("H2: SPECS → REWORK (within-author LPM)")
print("=" * 70)

# H2 uses all PRs (not just SZZ repos), since rework doesn't require SZZ
jit_features_h2, skipped_h2 = select_jit_features(
    df, [c for c in ALL_JIT_COLS if c != "sexp"] + ["sexp"]
)
print(f"\nJIT features selected for H2: {jit_features_h2}")
if skipped_h2:
    print(f"Skipped: {skipped_h2}")

print(f"\nAll PRs (H2 not restricted to SZZ repos): {len(df):,}")

print(f"\n-- H2 baseline (size controls only) --")
r_h2_base = within_author_lpm(
    df, "specd_int", "reworked",
    controls=SIZE_CONTROLS,
    label="H2-baseline",
)

print(f"\n-- H2 + JIT controls --")
r_h2_jit = within_author_lpm(
    df, "specd_int", "reworked",
    controls=SIZE_CONTROLS + jit_features_h2,
    label="H2-jit",
)

compare_results(r_h2_base, r_h2_jit, "H2 (specs → rework)")


# ════════════════════════════════════════════════════════════════════════════
# Summary
# ════════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("SUMMARY: JIT CONTROL ROBUSTNESS CHECK")
print("=" * 70)

for label, r_base, r_jit in [
    ("H1 (specs → SZZ bugs)", r_h1_base, r_h1_jit),
    ("H2 (specs → rework)",   r_h2_base, r_h2_jit),
]:
    print(f"\n{label}:")
    if r_base is None or r_jit is None:
        print("  Model failed — no result.")
        continue
    coef_base = r_base["coef"]
    coef_jit  = r_jit["coef"]
    pct_change = ((coef_jit - coef_base) / abs(coef_base) * 100) if coef_base != 0 else float("nan")
    print(f"  Coef (size only):  {coef_base:+.4f}  [{r_base['sig']}]")
    print(f"  Coef (+ JIT):      {coef_jit:+.4f}  [{r_jit['sig']}]")
    print(f"  Change:            {pct_change:+.1f}%")

print("\nInterpretation guide:")
print("  <25% coef change  → JIT controls do not materially confound spec effect")
print("  25–50% change     → Partial confounding; disclose in limitations")
print("  >50% change       → JIT features substantially absorb the spec effect")
print("  Significance lost → Effect not robust to JIT controls")

print(f"\nDone. Output written to: {OUT_FILE}")
out_f.close()
