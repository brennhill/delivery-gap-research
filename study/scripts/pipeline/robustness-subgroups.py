#!/usr/bin/env python3
"""
Robustness check: Do the null results hold across subgroups?

Tests whether specs reduce defects/rework within:
  1. Human-only PRs (excluding all bots)
  2. AI-tagged PRs only (excluding bots)
  3. Repos with high AI adoption vs low AI adoption

Bot exclusion: removes dependabot, renovate, and any author flagged
by is_bot_author or matching common bot name patterns.

Uses the same within-author LPM methodology as the main analysis.
"""

import pandas as pd
import numpy as np
import statsmodels.api as sm
import sys
from pathlib import Path
from datetime import datetime, timezone

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
OUT_FILE = Path(__file__).resolve().parent.parent.parent / "results" / "robustness-subgroups.txt"

# ── Tee stdout to file ────────────────────────────────────────────────
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

print(f"Subgroup robustness run: {datetime.now(timezone.utc).isoformat()}")
print(f"Script: {__file__}")

# ── Load and prep (same as main analysis) ─────────────────────────────

df = pd.read_csv(DATA_DIR / "master-prs.csv", low_memory=False)
szz = pd.read_csv(DATA_DIR / "szz-results-merged.csv")

for col in ["reworked", "escaped", "strict_escaped", "specd"]:
    df[col] = df[col].fillna(False).astype(bool)

# Mark bug-introducing PRs from SZZ
bug_prs = szz[["repo", "bug_pr_number"]].drop_duplicates()
bug_prs = bug_prs.rename(columns={"bug_pr_number": "pr_number"})
bug_prs["szz_buggy"] = True
df = df.merge(bug_prs, on=["repo", "pr_number"], how="left")
df["szz_buggy"] = df["szz_buggy"].fillna(False)

# AI classification
df["ai_tagged"] = df["f_ai_tagged"].fillna(False).astype(bool)

# Size controls
df["log_add"] = np.log1p(df["additions"])
df["log_del"] = np.log1p(df["deletions"])
df["log_files"] = np.log1p(df["files_count"])

# Restrict to SZZ repos
szz_repo_set = set(szz["repo"].unique())
df["in_szz"] = df["repo"].isin(szz_repo_set)

# ── Bot exclusion ─────────────────────────────────────────────────────

df["is_bot"] = df["f_is_bot_author"].fillna(False).astype(bool)

n_bot = df["is_bot"].sum()
n_human = (~df["is_bot"]).sum()
print(f"\nBot exclusion:")
print(f"  Bot PRs removed: {n_bot:,}")
print(f"  Human PRs remaining: {n_human:,}")
print(f"  AI-tagged (non-bot): {(df['ai_tagged'] & ~df['is_bot']).sum():,}")
print(f"  AI-tagged (bot): {(df['ai_tagged'] & df['is_bot']).sum():,}")

SIZE_CONTROLS = ["log_add", "log_del", "log_files"]


# ── Within-author LPM (same as main analysis) ────────────────────────

def within_author_lpm(data, treatment_col, outcome_col, controls=None,
                      min_prs=2, label=""):
    """Within-author LPM with full demeaning and clustered SEs.

    Demeans ALL variables by author (Frisch-Waugh-Lovell).
    No constant (absorbed by demeaning).
    Clusters SEs at author level.
    """
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

    # Count identifying authors AFTER dropna (those with treatment variation)
    author_var = multi.groupby("author")[treatment_col].agg(["min", "max"])
    n_with_var = (author_var["min"] != author_var["max"]).sum()
    n_authors = multi["author"].nunique()

    # Demean ALL variables by author
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
    direction = "INCREASES" if coef > 0 else "DECREASES" if coef < 0 else "NO EFFECT"
    sig = "***" if pval < 0.001 else "**" if pval < 0.01 else "*" if pval < 0.05 else ""

    print(f"  N={len(multi):,}, authors={n_authors:,} "
          f"({n_with_var:,} with variation)")
    print(f"  coef={coef:+.4f}, p={pval:.4f} → {direction} {sig}")

    return {"coef": coef, "p": pval, "n": len(multi),
            "n_authors": n_authors, "n_with_var": n_with_var,
            "direction": direction, "sig": sig}


def run_battery(subset, label):
    """Run specs→bugs and specs→rework on a subset."""
    print(f"\n{'─' * 60}")
    print(f"  {label}")
    print(f"{'─' * 60}")

    subset = subset.copy()
    subset["specd_int"] = subset["specd"].astype(int)

    n = len(subset)
    n_szz = subset["in_szz"].sum()
    n_specd = subset["specd"].sum()
    n_buggy = subset[subset["in_szz"]]["szz_buggy"].sum() if n_szz > 0 else 0
    n_reworked = subset["reworked"].sum()

    print(f"  PRs: {n:,} | Spec'd: {n_specd:,} ({n_specd/n*100:.1f}%) | "
          f"In SZZ: {n_szz:,}")
    print(f"  Bug rate: {n_buggy/n_szz*100:.1f}% | " if n_szz > 0 else f"  Bug rate: N/A (no SZZ repos) | ",
          end="")
    print(f"Rework rate: {n_reworked/n*100:.1f}%" if n > 0 else "Rework rate: N/A")

    # Specs → SZZ bugs (SZZ repos only)
    szz_sub = subset[subset["in_szz"]].copy()
    szz_sub["specd_int"] = szz_sub["specd"].astype(int)
    if len(szz_sub) > 100 and szz_sub["specd"].sum() > 10:
        print(f"\n  Specs → SZZ bugs:")
        r_bug = within_author_lpm(szz_sub, "specd_int", "szz_buggy",
                                  label=f"{label}-bugs")
    else:
        print(f"\n  Specs → SZZ bugs: SKIPPED (too few spec'd PRs)")
        r_bug = None

    # Specs → rework (all repos)
    if n_specd > 10:
        print(f"\n  Specs → rework:")
        r_rw = within_author_lpm(subset, "specd_int", "reworked",
                                 label=f"{label}-rework")
    else:
        print(f"\n  Specs → rework: SKIPPED (too few spec'd PRs)")
        r_rw = None

    # Spec quality → bugs (scored subset)
    scored = szz_sub[szz_sub["q_overall"].notna()].copy()
    if len(scored) > 50:
        print(f"\n  Spec quality → SZZ bugs (N={len(scored):,} scored):")
        r_q = within_author_lpm(scored, "q_overall", "szz_buggy",
                                label=f"{label}-quality")
    else:
        print(f"\n  Spec quality → SZZ bugs: SKIPPED ({len(scored)} scored PRs)")
        r_q = None

    return {"bugs": r_bug, "rework": r_rw, "quality": r_q}


# ════════════════════════════════════════════════════════════════════
# SUBGROUP 1: HUMAN-ONLY (no bots, no AI tags)
# ════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("SUBGROUP 1: HUMAN-ONLY PRs (no bots, no AI tags)")
print("=" * 70)

human_only = df[~df["is_bot"] & ~df["ai_tagged"]]
r_human = run_battery(human_only, "Human-only")


# ════════════════════════════════════════════════════════════════════
# SUBGROUP 2: AI-TAGGED (non-bot)
# ════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("SUBGROUP 2: AI-TAGGED PRs (excluding bots)")
print("=" * 70)

ai_nonbot = df[df["ai_tagged"] & ~df["is_bot"]]
r_ai = run_battery(ai_nonbot, "AI-tagged (non-bot)")


# ════════════════════════════════════════════════════════════════════
# SUBGROUP 3: HIGH-AI-ADOPTION REPOS vs LOW-AI-ADOPTION REPOS
# ════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("SUBGROUP 3: REPOS BY AI ADOPTION RATE")
print("=" * 70)

# Exclude bots for AI rate calculation
nonbot = df[~df["is_bot"]]
repo_ai_rate = nonbot.groupby("repo")["ai_tagged"].mean()
median_ai = repo_ai_rate[repo_ai_rate > 0].median()
# Some repos have 0 AI — separate them
zero_ai_repos = set(repo_ai_rate[repo_ai_rate == 0].index)
high_ai_repos = set(repo_ai_rate[repo_ai_rate > median_ai].index) - zero_ai_repos
low_ai_repos = set(repo_ai_rate[(repo_ai_rate > 0) & (repo_ai_rate <= median_ai)].index)

print(f"\nRepo AI adoption (non-bot):")
print(f"  Zero AI repos: {len(zero_ai_repos)}")
print(f"  Low AI repos (>0, ≤{median_ai:.3f}): {len(low_ai_repos)}")
print(f"  High AI repos (>{median_ai:.3f}): {len(high_ai_repos)}")

# Exclude bots from all subgroups
nonbot_szz = nonbot.copy()

print(f"\n── Zero-AI repos ──")
zero_ai = nonbot_szz[nonbot_szz["repo"].isin(zero_ai_repos)]
r_zero = run_battery(zero_ai, "Zero-AI repos")

print(f"\n── Low-AI repos ──")
low_ai = nonbot_szz[nonbot_szz["repo"].isin(low_ai_repos)]
r_low = run_battery(low_ai, "Low-AI repos")

print(f"\n── High-AI repos ──")
high_ai = nonbot_szz[nonbot_szz["repo"].isin(high_ai_repos)]
r_high = run_battery(high_ai, "High-AI repos")


# ════════════════════════════════════════════════════════════════════
# SUBGROUP 4: ALL PRs WITH BOTS EXCLUDED
# ════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("SUBGROUP 4: ALL PRs (bots excluded) — MAIN RESULT REPLICATION")
print("=" * 70)

r_all_nonbot = run_battery(nonbot, "All non-bot PRs")


# ════════════════════════════════════════════════════════════════════
# SUMMARY TABLE
# ════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("SUMMARY: SPEC EFFECTS ACROSS SUBGROUPS")
print("=" * 70)

print(f"\n{'Subgroup':>30s}  {'→ Bugs coef':>12s}  {'p':>8s}  "
      f"{'→ Rework coef':>14s}  {'p':>8s}")
print(f"{'─'*30}  {'─'*12}  {'─'*8}  {'─'*14}  {'─'*8}")

def fmt_result(r, key):
    if r and r.get(key):
        d = r[key]
        return f"{d['coef']:+.4f}", f"{d['p']:.4f}"
    return "—", "—"

for label, r in [("All non-bot PRs", r_all_nonbot),
                 ("Human-only (no AI)", r_human),
                 ("AI-tagged (non-bot)", r_ai),
                 ("Zero-AI repos", r_zero),
                 ("Low-AI repos", r_low),
                 ("High-AI repos", r_high)]:
    bc, bp = fmt_result(r, "bugs")
    rc, rp = fmt_result(r, "rework")
    print(f"{label:>30s}  {bc:>12s}  {bp:>8s}  {rc:>14s}  {rp:>8s}")

print(f"""
Interpretation:
  If SDD claims held, we would see NEGATIVE coefficients (specs reduce bugs/rework).
  Positive coefficients = confounding by indication (harder tasks get specs).
  The null result should hold across all subgroups.
""")

print(f"Results saved to: {OUT_FILE}")
out_f.close()
sys.stdout = sys.__stdout__
print(f"Subgroup analysis complete. Results in {OUT_FILE}")
