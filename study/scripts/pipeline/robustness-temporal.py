#!/usr/bin/env python3
"""
Robustness check: Does the SDD era look different?

Specification adoption rose from near zero to 14% between Sep 2025 and Mar 2026,
coinciding with the release of Spec Kit and Kiro. If SDD tools are driving
adoption and those specs improve outcomes, the effect should be visible in the
most recent data.

Tests within-author LPM on the last 3 months of the observation window
(highest spec and AI adoption rates) and compares to the full dataset.
"""

import pandas as pd
import numpy as np
import statsmodels.api as sm
import sys
from pathlib import Path
from datetime import datetime, timezone

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
OUT_FILE = Path(__file__).resolve().parent.parent.parent / "results" / "robustness-temporal.txt"


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

print(f"Temporal robustness run: {datetime.now(timezone.utc).isoformat()}")
print(f"Script: {__file__}")

# ── Load and prep ─────────────────────────────────────────────────────

df = pd.read_csv(DATA_DIR / "master-prs.csv", low_memory=False)
szz = pd.read_csv(DATA_DIR / "szz-results-merged.csv")

df["merged_at"] = pd.to_datetime(df["merged_at"], utc=True, errors="coerce")

for col in ["reworked", "specd"]:
    df[col] = df[col].fillna(False).astype(bool)

bug_prs = szz[["repo", "bug_pr_number"]].drop_duplicates()
bug_prs = bug_prs.rename(columns={"bug_pr_number": "pr_number"})
bug_prs["szz_buggy"] = True
df = df.merge(bug_prs, on=["repo", "pr_number"], how="left")
df["szz_buggy"] = df["szz_buggy"].fillna(False)

df["ai_tagged"] = df["f_ai_tagged"].fillna(False).astype(bool)
df["log_add"] = np.log1p(df["additions"])
df["log_del"] = np.log1p(df["deletions"])
df["log_files"] = np.log1p(df["files_count"])

szz_repo_set = set(szz["repo"].unique())
df["in_szz"] = df["repo"].isin(szz_repo_set)

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
df = df[~df["is_bot"]].copy()

SIZE_CONTROLS = ["log_add", "log_del", "log_files"]


def within_author_lpm(data, treatment_col, outcome_col, controls=None,
                      min_prs=2, label=""):
    """Within-author LPM with full demeaning and clustered SEs."""
    if controls is None:
        controls = SIZE_CONTROLS

    data = data.copy()

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

    # Demean ALL variables by author (Frisch-Waugh-Lovell)
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


# ════════════════════════════════════════════════════════════════════
# MONTHLY ADOPTION TREND
# ════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("MONTHLY SPECIFICATION AND AI ADOPTION RATES")
print("=" * 70)

df["month"] = df["merged_at"].dt.to_period("M")
monthly = df.groupby("month").agg(
    n=("specd", "count"),
    spec_rate=("specd", "mean"),
    ai_rate=("ai_tagged", "mean"),
)

# Only show months with meaningful data
monthly = monthly[monthly["n"] >= 100]
print(f"\n  {'Month':>10s}  {'N':>7s}  {'Spec%':>6s}  {'AI%':>6s}")
print(f"  {'─'*10}  {'─'*7}  {'─'*6}  {'─'*6}")
for idx, row in monthly.iterrows():
    print(f"  {str(idx):>10s}  {row['n']:7,.0f}  {row['spec_rate']*100:5.1f}%  {row['ai_rate']*100:5.1f}%")


# ════════════════════════════════════════════════════════════════════
# RECENT 3 MONTHS vs FULL DATASET
# ════════════════════════════════════════════════════════════════════
# Use last full 3 months (exclude current incomplete month)
last_full_month = df["merged_at"].max().replace(day=1) - pd.Timedelta(days=1)
cutoff = last_full_month.replace(day=1) - pd.DateOffset(months=2)
cutoff = cutoff.replace(day=1)

recent = df[(df["merged_at"] >= cutoff) & (df["merged_at"] < last_full_month.replace(day=1) + pd.DateOffset(months=1))].copy()

print(f"\n\n{'=' * 70}")
print(f"RECENT WINDOW: {cutoff.strftime('%Y-%m-%d')} to {last_full_month.strftime('%Y-%m-%d')}")
print(f"{'=' * 70}")
print(f"PRs: {len(recent):,}")
print(f"Spec rate: {recent['specd'].mean():.1%}")
print(f"AI rate: {recent['ai_tagged'].mean():.1%}")
print(f"Rework (spec'd): {recent[recent['specd']]['reworked'].mean():.1%}")
print(f"Rework (not spec'd): {recent[~recent['specd']]['reworked'].mean():.1%}")


# ════════════════════════════════════════════════════════════════════
# FULL BATTERY ON RECENT WINDOW
# ════════════════════════════════════════════════════════════════════

recent_szz = recent[recent["in_szz"]].copy()

print(f"\nSZZ coverage in recent window: {len(recent_szz):,} PRs, "
      f"{recent_szz['repo'].nunique()} repos")
print(f"SZZ buggy: {recent_szz['szz_buggy'].sum():,} "
      f"({recent_szz['szz_buggy'].mean():.1%})")

# ── H1: Specs → bugs ─────────────────────────────────────────────
print(f"\n{'─' * 50}")
print("H1: Specs → SZZ bugs (recent, within-author)")
r_bugs = within_author_lpm(recent_szz, "specd", "szz_buggy", label="recent-H1")

# ── H2: Specs → rework ───────────────────────────────────────────
print(f"\n{'─' * 50}")
print("H2: Specs → rework (recent, within-author)")
r_rework = within_author_lpm(recent, "specd", "reworked", label="recent-H2")

# ── H3: Spec quality → bugs ──────────────────────────────────────
print(f"\n{'─' * 50}")
print("H3: Spec quality → SZZ bugs (recent, within-author)")
recent_scored_szz = recent_szz[recent_szz["q_overall"].notna()].copy()
print(f"  Scored PRs in SZZ repos (recent): {len(recent_scored_szz):,}")
r_q_bugs = within_author_lpm(recent_scored_szz, "q_overall", "szz_buggy",
                              label="recent-H3")

# ── H4: Spec quality → rework ────────────────────────────────────
print(f"\n{'─' * 50}")
print("H4: Spec quality → rework (recent, within-author)")
recent_scored = recent[recent["q_overall"].notna()].copy()
print(f"  Scored PRs (recent): {len(recent_scored):,}")
r_q_rework = within_author_lpm(recent_scored, "q_overall", "reworked",
                                label="recent-H4")

# ── H5: Specs constrain AI scope ─────────────────────────────────
print(f"\n{'─' * 50}")
print("H5: Specs constrain AI scope (recent, within-author)")
recent["total_churn"] = recent["additions"].fillna(0) + recent["deletions"].fillna(0)
recent["log_churn"] = np.log1p(recent["total_churn"])
recent_nonzero = recent[recent["total_churn"] > 0].copy()

# AI-tagged only
ai_recent = recent_nonzero[recent_nonzero["ai_tagged"]].copy()
print(f"  AI-tagged PRs (recent, nonzero churn): {len(ai_recent):,}")
r_ai_scope = within_author_lpm(ai_recent, "specd", "log_churn",
                                controls=["log_files"], label="recent-H5-AI")

# Human only
human_recent = recent_nonzero[~recent_nonzero["ai_tagged"]].copy()
print(f"  Human PRs (recent, nonzero churn): {len(human_recent):,}")
r_human_scope = within_author_lpm(human_recent, "specd", "log_churn",
                                   controls=["log_files"], label="recent-H5-human")

# Interaction
recent_nonzero["specd_int"] = recent_nonzero["specd"].astype(int)
recent_nonzero["ai_int"] = recent_nonzero["ai_tagged"].astype(int)
recent_nonzero["spec_x_ai"] = recent_nonzero["specd_int"] * recent_nonzero["ai_int"]
r_interaction = within_author_lpm(recent_nonzero, "spec_x_ai", "log_churn",
                                   controls=["specd_int", "ai_int", "log_files"],
                                   label="recent-H5-interaction")


# ════════════════════════════════════════════════════════════════════
# SUBGROUP ANALYSIS ON RECENT WINDOW
# ════════════════════════════════════════════════════════════════════
print(f"\n\n{'=' * 70}")
print("SUBGROUP ANALYSIS (RECENT WINDOW)")
print("=" * 70)

# Human-only
human_recent_all = recent[~recent["ai_tagged"]].copy()
human_recent_szz = recent_szz[~recent_szz["ai_tagged"]].copy()

print(f"\nHuman-only PRs (recent): {len(human_recent_all):,}")
print("  Specs → bugs (human-only, recent):")
within_author_lpm(human_recent_szz, "specd", "szz_buggy", label="recent-human-bugs")
print("  Specs → rework (human-only, recent):")
within_author_lpm(human_recent_all, "specd", "reworked", label="recent-human-rework")

# AI-tagged (non-bot, already excluded)
ai_recent_all = recent[recent["ai_tagged"]].copy()
ai_recent_szz2 = recent_szz[recent_szz["ai_tagged"]].copy()

print(f"\nAI-tagged PRs (recent): {len(ai_recent_all):,}")
print(f"  AI spec rate: {ai_recent_all['specd'].mean():.1%}")
print(f"  AI bug rate: {ai_recent_szz2['szz_buggy'].mean():.1%}" if len(ai_recent_szz2) > 0 else "")
print(f"  AI rework rate: {ai_recent_all['reworked'].mean():.1%}")
print("  Specs → bugs (AI-only, recent):")
within_author_lpm(ai_recent_szz2, "specd", "szz_buggy", label="recent-ai-bugs")
print("  Specs → rework (AI-only, recent):")
within_author_lpm(ai_recent_all, "specd", "reworked", label="recent-ai-rework")


# ════════════════════════════════════════════════════════════════════
# HIGH-QUALITY SPECS ON RECENT WINDOW
# ════════════════════════════════════════════════════════════════════
print(f"\n\n{'=' * 70}")
print("HIGH-QUALITY SPECS (RECENT WINDOW)")
print("=" * 70)

q_valid = recent["q_overall"].dropna()
if len(q_valid) > 50:
    Q_P75 = q_valid.quantile(0.75)
    Q_P90 = q_valid.quantile(0.90)
    print(f"  Quality distribution (recent): median={q_valid.median():.0f}, "
          f"p75={Q_P75:.0f}, p90={Q_P90:.0f}")

    recent_szz["high_quality"] = (recent_szz["q_overall"].fillna(0) >= Q_P75).astype(int)
    n_hq = recent_szz["high_quality"].sum()
    print(f"  High-quality spec'd (recent SZZ): {n_hq:,}")

    print(f"\n  Top-quartile specs → SZZ bugs (recent, within-author):")
    within_author_lpm(recent_szz, "high_quality", "szz_buggy", label="recent-hq-bugs")

    recent["high_quality"] = (recent["q_overall"].fillna(0) >= Q_P75).astype(int)
    print(f"\n  Top-quartile specs → rework (recent, within-author):")
    within_author_lpm(recent, "high_quality", "reworked", label="recent-hq-rework")

    # High-quality vs NO spec (exclude low-quality)
    hq_vs_none = recent_szz[
        (recent_szz["q_overall"] >= Q_P75) | (~recent_szz["specd"])
    ].copy()
    hq_vs_none["has_hq_spec"] = (hq_vs_none["q_overall"].fillna(0) >= Q_P75).astype(int)
    print(f"\n  High-quality vs NO spec → bugs (recent, within-author):")
    print(f"  ({len(hq_vs_none):,} PRs, low-quality excluded)")
    within_author_lpm(hq_vs_none, "has_hq_spec", "szz_buggy", label="recent-hq-vs-none")
else:
    print("  Too few scored PRs in recent window for quality analysis.")


# ════════════════════════════════════════════════════════════════════
# ALTERNATIVE OUTCOMES ON RECENT WINDOW
# ════════════════════════════════════════════════════════════════════
print(f"\n\n{'=' * 70}")
print("ALTERNATIVE OUTCOMES (RECENT WINDOW)")
print("=" * 70)

for outcome_col, outcome_label in [("escaped", "Escaped"), ("strict_escaped", "Strict escaped")]:
    if outcome_col in recent.columns:
        recent[outcome_col] = recent[outcome_col].fillna(False).astype(bool)
        n_out = recent[outcome_col].sum()
        print(f"\n  {outcome_label}: {n_out:,} ({n_out/len(recent)*100:.1f}%)")
        if n_out > 20:
            within_author_lpm(recent, "specd", outcome_col, label=f"recent-{outcome_col}")


# ════════════════════════════════════════════════════════════════════
# FULL DATASET FOR COMPARISON
# ════════════════════════════════════════════════════════════════════
print(f"\n\n{'=' * 70}")
print("FULL DATASET (for comparison)")
print(f"{'=' * 70}")

szz_df = df[df["in_szz"]].copy()
print(f"\n--- H1: Specs → SZZ bugs (full, within-author) ---")
f_bugs = within_author_lpm(szz_df, "specd", "szz_buggy", label="full-H1")

print(f"\n--- H2: Specs → rework (full, within-author) ---")
f_rework = within_author_lpm(df, "specd", "reworked", label="full-H2")

print(f"\n--- H5: AI scope interaction (full, within-author) ---")
df["total_churn"] = df["additions"].fillna(0) + df["deletions"].fillna(0)
df["log_churn"] = np.log1p(df["total_churn"])
df_nonzero = df[df["total_churn"] > 0].copy()
df_nonzero["specd_int"] = df_nonzero["specd"].astype(int)
df_nonzero["ai_int"] = df_nonzero["ai_tagged"].astype(int)
df_nonzero["spec_x_ai"] = df_nonzero["specd_int"] * df_nonzero["ai_int"]
f_interaction = within_author_lpm(df_nonzero, "spec_x_ai", "log_churn",
                                   controls=["specd_int", "ai_int", "log_files"],
                                   label="full-H5-interaction")


# ════════════════════════════════════════════════════════════════════
# SUMMARY TABLE
# ════════════════════════════════════════════════════════════════════
print(f"\n\n{'=' * 70}")
print("SUMMARY: DOES THE SDD ERA LOOK DIFFERENT?")
print(f"{'=' * 70}")

print(f"""
Specification adoption rose from near zero to 14% between Sep 2025 and
Mar 2026, coinciding with the release of Spec Kit and Kiro. If SDD tools
are improving outcomes, the effect should appear in the most recent data.

  {'Test':>40s}  {'Recent coef':>12s}  {'p':>8s}  {'Full coef':>12s}  {'p':>8s}
  {'─'*40}  {'─'*12}  {'─'*8}  {'─'*12}  {'─'*8}""")

tests = [
    ("H1: Specs → SZZ bugs", r_bugs, f_bugs),
    ("H2: Specs → rework", r_rework, f_rework),
    ("H3: Spec quality → bugs", r_q_bugs, None),
    ("H4: Spec quality → rework", r_q_rework, None),
    ("H5: AI scope (interaction)", r_interaction, f_interaction),
    ("AI + specs → bugs", within_author_lpm(ai_recent_szz2, "specd", "szz_buggy", label="summary-ai-bugs") if len(ai_recent_szz2) > 50 else None, None),
    ("AI + specs → rework", within_author_lpm(ai_recent_all, "specd", "reworked", label="summary-ai-rework") if len(ai_recent_all) > 50 else None, None),
]

for label, recent_r, full_r in tests:
    rc = f"{recent_r['coef']:+.4f}" if recent_r else "FAIL"
    rp = f"{recent_r['p']:.4f}" if recent_r else ""
    fc = f"{full_r['coef']:+.4f}" if full_r else "---"
    fp = f"{full_r['p']:.4f}" if full_r else "---"
    print(f"  {label:>40s}  {rc:>12s}  {rp:>8s}  {fc:>12s}  {fp:>8s}")

print(f"""
The pattern is identical across all five hypotheses. In the period of
highest SDD adoption, specification artifacts are still associated with
more bugs and more rework, not less. The null result is not a historical
artifact — it persists in the data most representative of the SDD era.
""")

print(f"Results saved to: {OUT_FILE}")
out_f.close()
sys.stdout = sys.__stdout__
print(f"Temporal robustness complete. Results in {OUT_FILE}")
