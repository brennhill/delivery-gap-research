#!/usr/bin/env python3
"""
Robustness check: Issue-linked specs — every cut.

Tests whether linked GitHub issues (the closest proxy for pre-implementation
specifications) reduce defects or rework across every meaningful subgroup:

  1. Issue-linked vs no spec (cleanest comparison)
  2. Issue-linked vs everything else
  3. AI + issue-linked
  4. Human + issue-linked
  5. Issue-linked on top-20% complexity tasks
  6. Issue-linked quality → bugs/rework
  7. Top-20% quality issue-linked vs no spec
  8. Issue-linked vs ticket-only specs
  9. Recent 3 months: issue-linked
  10. Recent 3 months: AI + issue-linked
  11. Dose-response: quality tiers within issue-linked

Uses within-author LPM with full demeaning + clustered SEs.
"""

import pandas as pd
import numpy as np
import statsmodels.api as sm
import json
import re
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
OUT_FILE = result_path(ROOT_DIR, "robustness-issue-linked.txt")

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

print(f"Issue-linked robustness run: {datetime.now(timezone.utc).isoformat()}")
print(f"Script: {__file__}")

# ── Load and prep ─────────────────────────────────────────────────────

df = pd.read_csv(DATA_DIR / "master-prs.csv", low_memory=False)
szz, szz_meta = load_szz_results(DATA_DIR)
if szz_meta["mode"] == "exact_only":
    print(
        "SZZ filter: exact merge-SHA only "
        f"({szz_meta['exact_rows']:,}/{szz_meta['source_rows']:,} rows kept; "
        f"{szz_meta['fallback_rows']:,} fallback, {szz_meta['unmapped_rows']:,} unmapped dropped)"
    )

for col in ["reworked", "specd"]:
    if col in df.columns:
        df[col] = df[col].fillna(False).astype(bool)

bug_prs = szz[["repo", "bug_pr_number"]].drop_duplicates()
bug_prs = bug_prs.rename(columns={"bug_pr_number": "pr_number"})
bug_prs["szz_buggy"] = True
df = df.merge(bug_prs, on=["repo", "pr_number"], how="left")
df["szz_buggy"] = df["szz_buggy"].fillna(False).astype(int)

df["ai_tagged"] = df["f_ai_tagged"].fillna(False).astype(bool)
df["is_bot"] = df["f_is_bot_author"].fillna(False).astype(bool)
df = df[~df["is_bot"]].copy()
df["reworked"] = df["reworked"].astype(int)
df["merged_at"] = pd.to_datetime(df["merged_at"], utc=True, errors="coerce")

df["log_add"] = np.log1p(df["additions"].astype(float))
df["log_del"] = np.log1p(df["deletions"].astype(float))
df["log_files"] = np.log1p(df["files_count"].astype(float))
df["total_churn"] = df["additions"].fillna(0) + df["deletions"].fillna(0)

szz_repo_set = set(szz["repo"].unique())
df["in_szz"] = df["repo"].isin(szz_repo_set)

SIZE_CONTROLS = ["log_add", "log_del", "log_files"]

# ── Identify issue-linked PRs ────────────────────────────────────────

issue_linked = set()
ticket_only = set()
for p in sorted(DATA_DIR.glob("spec-signals-*.json")):
    with open(p) as f:
        data = json.load(f)
    repo = data.get("repo", "")
    for pr in data["coverage"]["prs"]:
        if not pr.get("specd"):
            continue
        src = str(pr.get("spec_source", "") or "")
        if re.match(r"#\d+$", src) or ("github.com" in src and "/issues/" in src):
            issue_linked.add((repo, int(pr["number"])))
        elif "-" in src and src.split("-")[0].isupper() and not src.startswith("#"):
            ticket_only.add((repo, int(pr["number"])))

df["has_issue"] = df.apply(lambda r: (r["repo"], r["pr_number"]) in issue_linked, axis=1)
df["has_ticket"] = df.apply(lambda r: (r["repo"], r["pr_number"]) in ticket_only, axis=1)

print(f"\nDataset: {len(df):,} PRs (non-bot)")
print(f"  Issue-linked: {df['has_issue'].sum():,}")
print(f"  Ticket-only: {df['has_ticket'].sum():,}")
print(f"  Spec'd (any): {df['specd'].sum():,}")
print(f"  No spec: {(~df['specd']).sum():,}")
print(f"  Quality scored: {df['q_overall'].notna().sum():,}")
print(f"  AI-tagged: {df['ai_tagged'].sum():,}")


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
    ci = model.conf_int().loc[treatment_col]
    sig = "***" if pval < 0.001 else "**" if pval < 0.01 else "*" if pval < 0.05 else ""

    print(f"  [{label}] N={len(multi):,}, authors={n_authors:,} "
          f"({n_with_var:,} with variation)")
    print(f"  coef={coef:+.4f}, p={pval:.4f}, 95% CI [{ci[0]:+.4f}, {ci[1]:+.4f}] {sig}")

    return {"coef": coef, "p": pval, "n": len(multi),
            "n_authors": n_authors, "n_with_var": n_with_var}


def run_test(subset, treatment, label, run_quality=True):
    """Run bugs + rework + quality tests on a subset."""
    subset = subset.copy()
    szz_sub = subset[subset["in_szz"]].copy()
    n = len(subset)
    if n == 0:
        print(f"  EMPTY — skipping")
        return {}

    n_treat = subset[treatment].sum()
    results = {}

    # Raw rates
    treat_szz = szz_sub[szz_sub[treatment] == 1]
    ctrl_szz = szz_sub[szz_sub[treatment] == 0]
    treat_all = subset[subset[treatment] == 1]
    ctrl_all = subset[subset[treatment] == 0]
    if len(treat_szz) > 0 and len(ctrl_szz) > 0:
        print(f"  Raw rates: bugs {treat_szz['szz_buggy'].mean():.1%} vs {ctrl_szz['szz_buggy'].mean():.1%} | "
              f"rework {treat_all['reworked'].mean():.1%} vs {ctrl_all['reworked'].mean():.1%}")

    # Bugs
    if len(szz_sub) > 100 and szz_sub[treatment].sum() > 10:
        print(f"\n  → bugs:")
        results["bugs"] = within_author_lpm(szz_sub, treatment, "szz_buggy",
                                            label=f"{label}-bugs")
    else:
        print(f"\n  → bugs: SKIPPED")
        results["bugs"] = None

    # Rework
    if n_treat > 10:
        print(f"  → rework:")
        results["rework"] = within_author_lpm(subset, treatment, "reworked",
                                              label=f"{label}-rework")
    else:
        results["rework"] = None

    # Quality → bugs/rework (within treated subset)
    if run_quality:
        scored_szz = szz_sub[szz_sub["q_overall"].notna() & (szz_sub[treatment] == 1)].copy()
        if len(scored_szz) > 50:
            print(f"  → quality → bugs (N={len(scored_szz):,} scored):")
            results["q_bugs"] = within_author_lpm(scored_szz, "q_overall", "szz_buggy",
                                                  label=f"{label}-q-bugs")
        else:
            results["q_bugs"] = None

        scored_all = subset[subset["q_overall"].notna() & (subset[treatment] == 1)].copy()
        if len(scored_all) > 50:
            print(f"  → quality → rework (N={len(scored_all):,} scored):")
            results["q_rework"] = within_author_lpm(scored_all, "q_overall", "reworked",
                                                    label=f"{label}-q-rework")
        else:
            results["q_rework"] = None

    return results


# ════════════════════════════════════════════════════════════════════
# TEST 1: ISSUE-LINKED vs NO SPEC
# ════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("TEST 1: ISSUE-LINKED vs NO SPEC (cleanest comparison)")
print("=" * 70)

t1 = df[df["has_issue"] | ~df["specd"]].copy()
t1["treat"] = t1["has_issue"].astype(int)
print(f"  Treated: {t1['treat'].sum():,} | Control: {(t1['treat']==0).sum():,}")
r1 = run_test(t1, "treat", "issue-vs-none")


# ════════════════════════════════════════════════════════════════════
# TEST 2: ISSUE-LINKED vs EVERYTHING ELSE
# ════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("TEST 2: ISSUE-LINKED vs EVERYTHING ELSE")
print("=" * 70)

df["issue_int"] = df["has_issue"].astype(int)
print(f"  Treated: {df['issue_int'].sum():,} | Control: {(df['issue_int']==0).sum():,}")
r2 = run_test(df, "issue_int", "issue-vs-all")


# ════════════════════════════════════════════════════════════════════
# TEST 3: AI + ISSUE-LINKED vs AI + NO SPEC
# ════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("TEST 3: AI-TAGGED + ISSUE-LINKED vs AI + NO SPEC")
print("=" * 70)

ai = df[df["ai_tagged"]].copy()
ai_test = ai[ai["has_issue"] | ~ai["specd"]].copy()
ai_test["treat"] = ai_test["has_issue"].astype(int)
print(f"  AI + issue: {ai_test['treat'].sum():,} | AI + no spec: {(ai_test['treat']==0).sum():,}")
r3 = run_test(ai_test, "treat", "ai-issue-vs-none")


# ════════════════════════════════════════════════════════════════════
# TEST 4: HUMAN + ISSUE-LINKED vs HUMAN + NO SPEC
# ════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("TEST 4: HUMAN-ONLY + ISSUE-LINKED vs HUMAN + NO SPEC")
print("=" * 70)

human = df[~df["ai_tagged"]].copy()
human_test = human[human["has_issue"] | ~human["specd"]].copy()
human_test["treat"] = human_test["has_issue"].astype(int)
print(f"  Human + issue: {human_test['treat'].sum():,} | Human + no spec: {(human_test['treat']==0).sum():,}")
r4 = run_test(human_test, "treat", "human-issue-vs-none")


# ════════════════════════════════════════════════════════════════════
# TEST 5: ISSUE-LINKED ON TOP-20% COMPLEXITY
# ════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("TEST 5: ISSUE-LINKED ON TOP-20% COMPLEXITY (by churn)")
print("=" * 70)

p80_churn = df["total_churn"].quantile(0.80)
hard = df[df["total_churn"] >= p80_churn].copy()
hard_test = hard[hard["has_issue"] | ~hard["specd"]].copy()
hard_test["treat"] = hard_test["has_issue"].astype(int)
print(f"  P80 churn threshold: {p80_churn:.0f}")
print(f"  Hard + issue: {hard_test['treat'].sum():,} | Hard + no spec: {(hard_test['treat']==0).sum():,}")
r5 = run_test(hard_test, "treat", "hard-issue-vs-none")


# ════════════════════════════════════════════════════════════════════
# TEST 6: TOP-20% QUALITY ISSUE-LINKED vs NO SPEC
# ════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("TEST 6: TOP-20% QUALITY ISSUE-LINKED vs NO SPEC")
print("=" * 70)

issue_scored = df[df["has_issue"] & df["q_overall"].notna()]
if len(issue_scored) > 100:
    p80_q = issue_scored["q_overall"].quantile(0.80)
    print(f"  Quality P80 threshold: {p80_q:.0f}")
    print(f"  Quality distribution: median={issue_scored['q_overall'].median():.0f}, "
          f"p80={p80_q:.0f}, p90={issue_scored['q_overall'].quantile(0.90):.0f}")

    t6 = df[(df["has_issue"] & df["q_overall"].notna() & (df["q_overall"] >= p80_q)) |
            ~df["specd"]].copy()
    t6["treat"] = (t6["has_issue"] & t6["q_overall"].notna() & (t6["q_overall"] >= p80_q)).astype(int)
    print(f"  Top-20% issue: {t6['treat'].sum():,} | No spec: {(~t6['specd']).sum():,}")
    r6 = run_test(t6, "treat", "top20q-issue-vs-none", run_quality=False)

    # Also top 10%
    p90_q = issue_scored["q_overall"].quantile(0.90)
    t6b = df[(df["has_issue"] & df["q_overall"].notna() & (df["q_overall"] >= p90_q)) |
             ~df["specd"]].copy()
    t6b["treat"] = (t6b["has_issue"] & t6b["q_overall"].notna() & (t6b["q_overall"] >= p90_q)).astype(int)
    print(f"\n  Top-10% issue (threshold={p90_q:.0f}): {t6b['treat'].sum():,}")
    r6b = run_test(t6b, "treat", "top10q-issue-vs-none", run_quality=False)
else:
    print("  SKIPPED (too few scored issue-linked PRs)")
    r6 = {}


# ════════════════════════════════════════════════════════════════════
# TEST 7: ISSUE-LINKED vs TICKET-ONLY
# ════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("TEST 7: ISSUE-LINKED vs TICKET-ONLY SPECS")
print("=" * 70)

spec_compare = df[df["has_issue"] | df["has_ticket"]].copy()
spec_compare["is_issue"] = spec_compare["has_issue"].astype(int)
print(f"  Issue-linked: {spec_compare['is_issue'].sum():,} | "
      f"Ticket-only: {(spec_compare['is_issue']==0).sum():,}")
r7 = run_test(spec_compare, "is_issue", "issue-vs-ticket", run_quality=False)


# ════════════════════════════════════════════════════════════════════
# TEST 8: RECENT 3 MONTHS — ISSUE-LINKED
# ════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("TEST 8: RECENT 3 MONTHS — ISSUE-LINKED vs NO SPEC")
print("=" * 70)

last_date = df["merged_at"].max()
if pd.notna(last_date):
    cutoff = (last_date.replace(day=1) - pd.DateOffset(months=3)).replace(day=1)
    recent = df[df["merged_at"] >= cutoff].copy()
    recent_test = recent[recent["has_issue"] | ~recent["specd"]].copy()
    recent_test["treat"] = recent_test["has_issue"].astype(int)
    print(f"  Window: {cutoff.date()} to {last_date.date()}")
    print(f"  Recent PRs: {len(recent):,}")
    print(f"  Recent + issue: {recent_test['treat'].sum():,} | "
          f"Recent + no spec: {(recent_test['treat']==0).sum():,}")
    r8 = run_test(recent_test, "treat", "recent-issue-vs-none")
else:
    print("  SKIPPED (no valid dates)")
    r8 = {}


# ════════════════════════════════════════════════════════════════════
# TEST 9: RECENT 3 MONTHS — AI + ISSUE-LINKED
# ════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("TEST 9: RECENT 3 MONTHS — AI + ISSUE-LINKED vs AI + NO SPEC")
print("=" * 70)

if pd.notna(last_date):
    recent_ai = recent[recent["ai_tagged"]].copy()
    recent_ai_test = recent_ai[recent_ai["has_issue"] | ~recent_ai["specd"]].copy()
    recent_ai_test["treat"] = recent_ai_test["has_issue"].astype(int)
    print(f"  Recent AI + issue: {recent_ai_test['treat'].sum():,} | "
          f"Recent AI + no spec: {(recent_ai_test['treat']==0).sum():,}")
    r9 = run_test(recent_ai_test, "treat", "recent-ai-issue", run_quality=False)
else:
    r9 = {}


# ════════════════════════════════════════════════════════════════════
# TEST 10: RECENT 3 MONTHS — HUMAN + ISSUE-LINKED
# ════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("TEST 10: RECENT 3 MONTHS — HUMAN + ISSUE-LINKED vs HUMAN + NO SPEC")
print("=" * 70)

if pd.notna(last_date):
    recent_human = recent[~recent["ai_tagged"]].copy()
    recent_human_test = recent_human[recent_human["has_issue"] | ~recent_human["specd"]].copy()
    recent_human_test["treat"] = recent_human_test["has_issue"].astype(int)
    print(f"  Recent human + issue: {recent_human_test['treat'].sum():,} | "
          f"Recent human + no spec: {(recent_human_test['treat']==0).sum():,}")
    r10 = run_test(recent_human_test, "treat", "recent-human-issue", run_quality=False)
else:
    r10 = {}


# ════════════════════════════════════════════════════════════════════
# TEST 11: DOSE-RESPONSE WITHIN ISSUE-LINKED
# ════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("TEST 11: DOSE-RESPONSE — QUALITY TIERS WITHIN ISSUE-LINKED")
print("=" * 70)

if len(issue_scored) > 100:
    quartiles = issue_scored["q_overall"].quantile([0.25, 0.50, 0.75, 0.90])
    print(f"  Quality quartiles: p25={quartiles[0.25]:.0f}, p50={quartiles[0.50]:.0f}, "
          f"p75={quartiles[0.75]:.0f}, p90={quartiles[0.90]:.0f}")

    # Each tier vs no spec — shows gradient (or lack thereof)
    for threshold, label in [(quartiles[0.25], "Bottom quartile (≤p25)"),
                              (quartiles[0.50], "Below median (≤p50)"),
                              (quartiles[0.75], "Top quartile (≥p75)"),
                              (quartiles[0.90], "Top decile (≥p90)")]:
        if "Top" in label:
            treat_mask = df["has_issue"] & df["q_overall"].notna() & (df["q_overall"] >= threshold)
        else:
            treat_mask = df["has_issue"] & df["q_overall"].notna() & (df["q_overall"] <= threshold)

        tier = df[treat_mask | ~df["specd"]].copy()
        tier["treat"] = treat_mask[tier.index].fillna(False).astype(int)

        n_treat = tier["treat"].sum()
        tier_szz = tier[tier["in_szz"]].copy()
        print(f"\n  {label} (N={n_treat:,}, threshold={threshold:.0f}) vs no spec:")

        if len(tier_szz) > 100 and tier_szz["treat"].sum() > 10:
            within_author_lpm(tier_szz, "treat", "szz_buggy",
                              label=f"dose-{label[:8]}-bugs")
        else:
            print(f"    bugs: SKIPPED")

        if n_treat > 10:
            within_author_lpm(tier, "treat", "reworked",
                              label=f"dose-{label[:8]}-rework")
else:
    print("  SKIPPED")


# ════════════════════════════════════════════════════════════════════
# SUMMARY TABLE
# ════════════════════════════════════════════════════════════════════
print("\n\n" + "=" * 70)
print("SUMMARY: ISSUE-LINKED SPECS — EVERY CUT")
print("=" * 70)

def fmt(r, key):
    d = r.get(key) if r else None
    if d:
        sig = "***" if d["p"] < 0.001 else "**" if d["p"] < 0.01 else "*" if d["p"] < 0.05 else ""
        return f"{d['coef']:+.4f}", f"{d['p']:.4f}{sig}"
    return "—", "—"

print(f"\n{'Test':>45s}  {'→ Bugs':>10s}  {'p':>10s}  {'→ Rework':>10s}  {'p':>10s}")
print(f"{'─'*45}  {'─'*10}  {'─'*10}  {'─'*10}  {'─'*10}")

for label, r in [
    ("Issue vs no spec", r1),
    ("Issue vs everything", r2),
    ("AI + issue vs AI + no spec", r3),
    ("Human + issue vs human + no spec", r4),
    ("Hard tasks (top 20% churn) + issue", r5),
    ("Top-20% quality issue vs no spec", r6),
    ("Issue vs ticket-only", r7),
    ("Recent 3mo: issue vs no spec", r8),
    ("Recent 3mo: AI + issue", r9),
    ("Recent 3mo: human + issue", r10),
]:
    bc, bp = fmt(r, "bugs")
    rc, rp = fmt(r, "rework")
    print(f"{label:>45s}  {bc:>10s}  {bp:>10s}  {rc:>10s}  {rp:>10s}")

print(f"""
Interpretation:
  If linked GitHub issues (pre-implementation specs) prevent defects,
  we should see NEGATIVE bug coefficients in at least some cuts.

  Positive coefficients = confounding by indication.
  Null across all cuts = specs do not prevent defects regardless of
  how they are operationalized.
""")

print(f"Results saved to: {OUT_FILE}")
out_f.close()
sys.stdout = sys.__stdout__
print(f"Issue-linked robustness complete. Results in {OUT_FILE}")
