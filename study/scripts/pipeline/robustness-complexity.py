#!/usr/bin/env python3
"""
Robustness check: Do specs help on the HARDEST tasks?

If specs have value, it should show on complex tasks where ambiguity
is highest. We stratify by top-20% on multiple complexity measures
and test H1-H4 within each stratum.

Complexity measures:
  1. Code churn (additions + deletions) — top 20%
  2. Lines added — top 20%
  3. Files changed — top 20%
  4. Change entropy (JIT feature) — top 20%
  5. Composite JIT risk — top 20% by predicted defect probability

Uses within-author LPM with full demeaning + clustered SEs.
"""

import pandas as pd
import numpy as np
import statsmodels.api as sm
import sys
from pathlib import Path
from datetime import datetime, timezone

UTIL_DIR = Path(__file__).resolve().parents[1] / "util"
if str(UTIL_DIR) not in sys.path:
    sys.path.insert(0, str(UTIL_DIR))

from result_paths import result_path  # noqa: E402
from szz_data import load_szz_results  # noqa: E402

ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"
OUT_FILE = result_path(ROOT_DIR, "robustness-complexity.txt")

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

print(f"Complexity stratification run: {datetime.now(timezone.utc).isoformat()}")
print(f"Script: {__file__}")

# ── Load and prep ─────────────────────────────────────────────────────

df = pd.read_csv(DATA_DIR / "master-prs.csv", low_memory=False)
szz, szz_meta = load_szz_results(DATA_DIR)
jit = pd.read_csv(DATA_DIR / "jit-features-merged.csv")
if szz_meta["mode"] == "exact_only":
    print(
        "SZZ filter: exact merge-SHA only "
        f"({szz_meta['exact_rows']:,}/{szz_meta['source_rows']:,} rows kept; "
        f"{szz_meta['fallback_rows']:,} fallback, {szz_meta['unmapped_rows']:,} unmapped dropped)"
    )

for col in ["reworked", "specd"]:
    df[col] = df[col].fillna(False).astype(bool)

# SZZ buggy
bug_prs = szz[["repo", "bug_pr_number"]].drop_duplicates()
bug_prs = bug_prs.rename(columns={"bug_pr_number": "pr_number"})
bug_prs["szz_buggy"] = True
df = df.merge(bug_prs, on=["repo", "pr_number"], how="left")
df["szz_buggy"] = df["szz_buggy"].fillna(False)

# JIT features
jit_cols = [c for c in ["repo", "pr_number", "ns", "nd", "nf", "entropy",
            "la", "ld", "lt", "fix", "ndev", "age", "nuc", "exp", "rexp", "sexp"]
            if c in jit.columns]
df = df.merge(jit[jit_cols], on=["repo", "pr_number"], how="left")

# AI and bot
df["ai_tagged"] = df["f_ai_tagged"].fillna(False).astype(bool)
df["is_bot"] = df["f_is_bot_author"].fillna(False).astype(bool)
df = df[~df["is_bot"]].copy()

# Size controls
df["log_add"] = np.log1p(df["additions"].astype(float))
df["log_del"] = np.log1p(df["deletions"].astype(float))
df["log_files"] = np.log1p(df["files_count"].astype(float))
df["total_churn"] = df["additions"].fillna(0) + df["deletions"].fillna(0)

# SZZ repos
szz_repo_set = set(szz["repo"].unique())
df["in_szz"] = df["repo"].isin(szz_repo_set)

SIZE_CONTROLS = ["log_add", "log_del", "log_files"]

print(f"\nDataset: {len(df):,} PRs (non-bot), {df['in_szz'].sum():,} in SZZ repos")
print(f"Spec'd: {df['specd'].sum():,} ({df['specd'].mean():.1%})")
print(f"Quality scored: {df['q_overall'].notna().sum():,}")

# ── Within-author LPM ────────────────────────────────────────────────

def within_author_lpm(data, treatment_col, outcome_col, controls=None,
                      min_prs=2, label=""):
    if controls is None:
        controls = SIZE_CONTROLS

    ac = data["author"].value_counts()
    multi = data[data["author"].isin(ac[ac >= min_prs].index)].copy()
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

    author_var = multi.groupby("author")[treatment_col].agg(["min", "max"])
    n_with_var = (author_var["min"] != author_var["max"]).sum()
    n_authors = multi["author"].nunique()

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
    sig = "***" if pval < 0.001 else "**" if pval < 0.01 else "*" if pval < 0.05 else ""

    print(f"  [{label}] N={len(multi):,}, authors={n_authors:,} "
          f"({n_with_var:,} with variation)")
    print(f"  coef={coef:+.4f}, p={pval:.4f} {sig}")

    return {"coef": coef, "p": pval, "n": len(multi),
            "n_authors": n_authors, "n_with_var": n_with_var}


def run_stratum(subset, label):
    """Run H1-H4 on a complexity stratum."""
    print(f"\n{'─' * 60}")
    print(f"  {label}")
    print(f"{'─' * 60}")

    subset = subset.copy()
    subset["specd_int"] = subset["specd"].astype(int)

    n = len(subset)
    if n == 0:
        print(f"  EMPTY stratum — skipping")
        return {"h1": None, "h2": None, "h3": None, "h4": None}
    n_szz = subset["in_szz"].sum()
    n_specd = subset["specd"].sum()
    n_scored = subset["q_overall"].notna().sum()

    print(f"  PRs: {n:,} | Spec'd: {n_specd:,} ({n_specd/n*100:.1f}%) | "
          f"In SZZ: {n_szz:,} | Quality scored: {n_scored:,}")

    szz_sub = subset[subset["in_szz"]].copy()
    szz_sub["specd_int"] = szz_sub["specd"].astype(int)
    results = {}

    # H1: Specs → bugs
    if len(szz_sub) > 100 and szz_sub["specd"].sum() > 10:
        print(f"\n  H1: Specs → bugs:")
        results["h1"] = within_author_lpm(szz_sub, "specd_int", "szz_buggy",
                                          label=f"{label}-H1")
    else:
        print(f"\n  H1: SKIPPED (too few)")
        results["h1"] = None

    # H2: Specs → rework
    if n_specd > 10:
        print(f"\n  H2: Specs → rework:")
        results["h2"] = within_author_lpm(subset, "specd_int", "reworked",
                                          label=f"{label}-H2")
    else:
        results["h2"] = None

    # H3: Quality → bugs
    scored_szz = szz_sub[szz_sub["q_overall"].notna()].copy()
    if len(scored_szz) > 50:
        print(f"\n  H3: Spec quality → bugs (N={len(scored_szz):,} scored):")
        results["h3"] = within_author_lpm(scored_szz, "q_overall", "szz_buggy",
                                          label=f"{label}-H3")
    else:
        print(f"\n  H3: SKIPPED ({len(scored_szz)} scored PRs)")
        results["h3"] = None

    # H4: Quality → rework
    scored_all = subset[subset["q_overall"].notna()].copy()
    if len(scored_all) > 50:
        print(f"\n  H4: Spec quality → rework (N={len(scored_all):,} scored):")
        results["h4"] = within_author_lpm(scored_all, "q_overall", "reworked",
                                          label=f"{label}-H4")
    else:
        print(f"\n  H4: SKIPPED ({len(scored_all)} scored PRs)")
        results["h4"] = None

    return results


# ════════════════════════════════════════════════════════════════════
# COMPLEXITY STRATA
# ════════════════════════════════════════════════════════════════════

all_results = {}

# 1. Code churn (additions + deletions)
print("\n" + "=" * 70)
print("STRATUM 1: TOP 20% BY CODE CHURN (additions + deletions)")
print("=" * 70)
p80_churn = df["total_churn"].quantile(0.80)
print(f"  P80 threshold: {p80_churn:.0f}")
top_churn = df[df["total_churn"] >= p80_churn]
bottom_churn = df[df["total_churn"] < p80_churn]
all_results["top20_churn"] = run_stratum(top_churn, "Top 20% churn")
all_results["bottom80_churn"] = run_stratum(bottom_churn, "Bottom 80% churn")

# 2. Lines added
print("\n" + "=" * 70)
print("STRATUM 2: TOP 20% BY LINES ADDED")
print("=" * 70)
p80_add = df["additions"].quantile(0.80)
print(f"  P80 threshold: {p80_add:.0f}")
top_add = df[df["additions"] >= p80_add]
bottom_add = df[df["additions"] < p80_add]
all_results["top20_additions"] = run_stratum(top_add, "Top 20% additions")
all_results["bottom80_additions"] = run_stratum(bottom_add, "Bottom 80% additions")

# 3. Files changed
print("\n" + "=" * 70)
print("STRATUM 3: TOP 20% BY FILES CHANGED")
print("=" * 70)
p80_files = df["files_count"].quantile(0.80)
print(f"  P80 threshold: {p80_files:.0f}")
top_files = df[df["files_count"] >= p80_files]
bottom_files = df[df["files_count"] < p80_files]
all_results["top20_files"] = run_stratum(top_files, "Top 20% files")
all_results["bottom80_files"] = run_stratum(bottom_files, "Bottom 80% files")

# 4. Change entropy (JIT feature — measures how spread the change is)
print("\n" + "=" * 70)
print("STRATUM 4: TOP 20% BY CHANGE ENTROPY")
print("=" * 70)
has_entropy = df[df["entropy"].notna()] if "entropy" in df.columns else pd.DataFrame()
if len(has_entropy) > 1000:
    p80_entropy = has_entropy["entropy"].quantile(0.80)
    print(f"  P80 threshold: {p80_entropy:.2f} (N with entropy: {len(has_entropy):,})")
    top_entropy = has_entropy[has_entropy["entropy"] >= p80_entropy]
    bottom_entropy = has_entropy[has_entropy["entropy"] < p80_entropy]
    all_results["top20_entropy"] = run_stratum(top_entropy, "Top 20% entropy")
    all_results["bottom80_entropy"] = run_stratum(bottom_entropy, "Bottom 80% entropy")
else:
    print("  SKIPPED (too few PRs with entropy data)")

# 5. Composite JIT risk score (mean of normalized JIT features)
print("\n" + "=" * 70)
print("STRATUM 5: TOP 20% BY COMPOSITE JIT RISK")
print("=" * 70)
jit_features = ["ns", "nd", "nf", "entropy", "la", "ld", "ndev", "nuc"]
jit_available = [c for c in jit_features if c in df.columns]
has_jit = df[df[jit_available].notna().all(axis=1)].copy()
if len(has_jit) > 1000:
    # Rank-normalize each feature (percentile rank), then average
    # Rank normalization is outlier-robust unlike min-max
    for c in jit_available:
        has_jit[f"{c}_rank"] = has_jit[c].rank(pct=True)
    rank_cols = [f"{c}_rank" for c in jit_available]
    has_jit["jit_risk"] = has_jit[rank_cols].mean(axis=1)

    p80_risk = has_jit["jit_risk"].quantile(0.80)
    print(f"  P80 threshold: {p80_risk:.3f} (N with JIT: {len(has_jit):,})")
    top_risk = has_jit[has_jit["jit_risk"] >= p80_risk]
    bottom_risk = has_jit[has_jit["jit_risk"] < p80_risk]
    all_results["top20_jit_risk"] = run_stratum(top_risk, "Top 20% JIT risk")
    all_results["bottom80_jit_risk"] = run_stratum(bottom_risk, "Bottom 80% JIT risk")
else:
    print("  SKIPPED (too few PRs with JIT features)")


# ════════════════════════════════════════════════════════════════════
# SUMMARY TABLE
# ════════════════════════════════════════════════════════════════════
print("\n\n" + "=" * 70)
print("SUMMARY: DO SPECS HELP ON THE HARDEST TASKS?")
print("=" * 70)

print(f"""
If specs have value, they should show it on complex tasks where
ambiguity is highest and the cost of getting it wrong is greatest.

{'Stratum':>25s}  {'H1 bugs':>10s}  {'p':>8s}  {'H2 rework':>10s}  {'p':>8s}  {'H3 q→bug':>10s}  {'p':>8s}  {'H4 q→rwk':>10s}  {'p':>8s}""")
print(f"{'─'*25}  {'─'*10}  {'─'*8}  {'─'*10}  {'─'*8}  {'─'*10}  {'─'*8}  {'─'*10}  {'─'*8}")

for label, key in [
    ("Top 20% churn", "top20_churn"),
    ("Bottom 80% churn", "bottom80_churn"),
    ("Top 20% additions", "top20_additions"),
    ("Bottom 80% additions", "bottom80_additions"),
    ("Top 20% files", "top20_files"),
    ("Bottom 80% files", "bottom80_files"),
    ("Top 20% entropy", "top20_entropy"),
    ("Bottom 80% entropy", "bottom80_entropy"),
    ("Top 20% JIT risk", "top20_jit_risk"),
    ("Bottom 80% JIT risk", "bottom80_jit_risk"),
]:
    r = all_results.get(key, {})
    vals = []
    for h in ["h1", "h2", "h3", "h4"]:
        d = r.get(h)
        if d:
            vals.append(f"{d['coef']:+.4f}")
            vals.append(f"{d['p']:.4f}")
        else:
            vals.extend(["—", "—"])
    print(f"{label:>25s}  {vals[0]:>10s}  {vals[1]:>8s}  "
          f"{vals[2]:>10s}  {vals[3]:>8s}  {vals[4]:>10s}  {vals[5]:>8s}  "
          f"{vals[6]:>10s}  {vals[7]:>8s}")

print(f"""
Interpretation:
  If specs help on hard tasks, the top-20% strata should show NEGATIVE
  coefficients (specs reduce bugs/rework) even if the full dataset doesn't.
  If the top-20% shows the same null or reversed pattern, complexity
  stratification does not rescue the SDD claims.
""")

print(f"Results saved to: {OUT_FILE}")
out_f.close()
sys.stdout = sys.__stdout__
print(f"Complexity stratification complete. Results in {OUT_FILE}")
