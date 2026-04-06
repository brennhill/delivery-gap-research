#!/usr/bin/env python3
"""Full spec-quality analysis on 6,203 scored PRs across 10 repos."""

import csv
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy import stats
import statsmodels.api as sm

UTIL_DIR = Path(__file__).resolve().parents[1] / "util"
if str(UTIL_DIR) not in sys.path:
    sys.path.insert(0, str(UTIL_DIR))

from quality_tiers import (  # noqa: E402
    BOTTOM_75,
    TOP_10,
    TOP_25_ONLY,
    TIER_ORDER,
    TIER_DISPLAY,
    quality_tier,
)

DATA = "/Users/brenn/dev/ai-augmented-dev/research/study/data/master-prs.csv"
TIER_HEADERS = {
    BOTTOM_75: "<58",
    TOP_25_ONLY: "58-65",
    TOP_10: "66+",
}


def load_data():
    rows = []
    with open(DATA) as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def to_float(v):
    try:
        return float(v)
    except (ValueError, TypeError):
        return None


def to_int(v):
    try:
        return int(v)
    except (ValueError, TypeError):
        return None


def to_bool(v):
    if v in ("True", "true", "1", True):
        return True
    if v in ("False", "false", "0", False, "", None):
        return False
    return None


def tier_label(q):
    return quality_tier(q)


def safe_log(v):
    return math.log(v + 1)


def logit_summary(endog, exog, labels):
    """Run logistic regression and return results dict."""
    try:
        model = sm.Logit(endog, exog)
        result = model.fit(disp=0, maxiter=100)
        return result, labels
    except Exception as e:
        print(f"  Logit failed: {e}")
        return None, labels


def print_logit(result, labels, dv_name):
    if result is None:
        print(f"  Could not fit model for {dv_name}")
        return
    print(f"\n  Logistic Regression — DV: {dv_name}")
    print(f"  {'Variable':<30} {'Coef':>8} {'OR':>8} {'p':>10} {'95% CI OR':>16}")
    print(f"  {'-'*30} {'-'*8} {'-'*8} {'-'*10} {'-'*16}")
    conf = result.conf_int()
    for i, label in enumerate(labels):
        coef = result.params[i]
        p = result.pvalues[i]
        or_val = math.exp(coef)
        ci_lo = math.exp(conf[i, 0])
        ci_hi = math.exp(conf[i, 1])
        sig = ""
        if p < 0.001:
            sig = "***"
        elif p < 0.01:
            sig = "**"
        elif p < 0.05:
            sig = "*"
        print(f"  {label:<30} {coef:>8.4f} {or_val:>8.3f} {p:>9.4f}{sig} [{ci_lo:.3f}-{ci_hi:.3f}]")
    print(f"  Pseudo R²: {result.prsquared:.4f}  |  N: {int(result.nobs)}")


def fisher_2x2(a, b, c, d, label_row="Signal", label_col="Outcome"):
    """Run Fisher's exact on 2x2 table [[a,b],[c,d]]."""
    oddsratio, p = stats.fisher_exact([[a, b], [c, d]])
    return oddsratio, p


# ─────────────────────────────────────────────
# LOAD AND PREP
# ─────────────────────────────────────────────
print("Loading data...")
all_rows = load_data()

# Scored PRs
scored = []
for r in all_rows:
    q = to_float(r["q_overall"])
    if q is not None:
        r["_q"] = q
        r["_tier"] = tier_label(q)
        r["_escaped"] = to_bool(r["strict_escaped"])
        r["_reworked"] = to_bool(r["reworked"])
        r["_additions"] = to_float(r["additions"]) or 0
        r["_deletions"] = to_float(r["deletions"]) or 0
        r["_files"] = to_float(r["files_count"]) or 1
        r["_log_add"] = safe_log(r["_additions"])
        r["_log_del"] = safe_log(r["_deletions"])
        r["_log_files"] = safe_log(r["_files"])
        scored.append(r)

# All PRs (for spec vs no-spec)
all_prepped = []
for r in all_rows:
    r["_has_spec"] = 1 if to_bool(r.get("specd")) is True else 0
    r["_escaped"] = to_bool(r["strict_escaped"])
    r["_reworked"] = to_bool(r["reworked"])
    r["_additions"] = to_float(r["additions"]) or 0
    r["_deletions"] = to_float(r["deletions"]) or 0
    r["_files"] = to_float(r["files_count"]) or 1
    r["_log_add"] = safe_log(r["_additions"])
    r["_log_del"] = safe_log(r["_deletions"])
    r["_log_files"] = safe_log(r["_files"])
    all_prepped.append(r)

print(f"Total PRs: {len(all_rows)}")
print(f"Spec-scored PRs: {len(scored)}")

# Repos with scored PRs
scored_repos = sorted(set(r["repo"] for r in scored))
print(f"Repos with scores: {len(scored_repos)}")

# ─────────────────────────────────────────────
# ANALYSIS 1: REPO DISTRIBUTION ACROSS TIERS
# ─────────────────────────────────────────────
print("\n" + "=" * 70)
print("ANALYSIS 1: REPO DISTRIBUTION ACROSS QUALITY TIERS")
print("=" * 70)

repo_tiers = defaultdict(lambda: {BOTTOM_75: 0, TOP_25_ONLY: 0, TOP_10: 0, "total": 0})
for r in scored:
    repo_tiers[r["repo"]][r["_tier"]] += 1
    repo_tiers[r["repo"]]["total"] += 1

tier_totals = {tier: 0 for tier in TIER_ORDER}
print(
    f"\n{'Repo':<35} "
    f"{TIER_HEADERS[BOTTOM_75]:>6} {TIER_HEADERS[TOP_25_ONLY]:>6} {TIER_HEADERS[TOP_10]:>6} "
    f"{'Total':>6}  {'%<58':>5} {'%58-65':>7} {'%66+':>5}"
)
print("-" * 95)
for repo in sorted(repo_tiers.keys(), key=lambda x: -repo_tiers[x]["total"]):
    d = repo_tiers[repo]
    t = d["total"]
    pct_l = 100 * d[BOTTOM_75] / t
    pct_m = 100 * d[TOP_25_ONLY] / t
    pct_h = 100 * d[TOP_10] / t
    print(
        f"{repo:<35} {d[BOTTOM_75]:>6} {d[TOP_25_ONLY]:>6} {d[TOP_10]:>6} {t:>6}  "
        f"{pct_l:>4.1f}% {pct_m:>6.1f}% {pct_h:>4.1f}%"
    )
    for tier in TIER_ORDER:
        tier_totals[tier] += d[tier]

total = sum(tier_totals.values())
print("-" * 95)
print(
    f"{'TOTAL':<35} {tier_totals[BOTTOM_75]:>6} {tier_totals[TOP_25_ONLY]:>6} {tier_totals[TOP_10]:>6} {total:>6}  "
    f"{100*tier_totals[BOTTOM_75]/total:>4.1f}% "
    f"{100*tier_totals[TOP_25_ONLY]/total:>6.1f}% "
    f"{100*tier_totals[TOP_10]/total:>4.1f}%"
)

# Escape/rework rates by tier
print(f"\n  Outcome rates by tier:")
print(f"  {'Tier':<26} {'N':>6} {'Escaped':>8} {'Esc%':>6} {'Reworked':>8} {'Rwk%':>6}")
print(f"  {'-'*50}")
for tier in TIER_ORDER:
    tier_rows = [r for r in scored if r["_tier"] == tier]
    n = len(tier_rows)
    esc = sum(1 for r in tier_rows if r["_escaped"])
    rwk = sum(1 for r in tier_rows if r["_reworked"])
    print(f"  {TIER_DISPLAY[tier]:<26} {n:>6} {esc:>8} {100*esc/n:>5.1f}% {rwk:>8} {100*rwk/n:>5.1f}%")


# ─────────────────────────────────────────────
# ANALYSIS 2: SPECS VS NO-SPECS (controlling for size)
# ─────────────────────────────────────────────
print("\n" + "=" * 70)
print("ANALYSIS 2: SPECS VS NO-SPECS (controlling for change size)")
print("=" * 70)

# Only use repos that have scored PRs so the spec/no-spec comparison stays
# inside the subset of repos where quality scoring was actually run.
scored_repo_set = set(r["repo"] for r in scored)
repo_rows = [r for r in all_prepped if r["repo"] in scored_repo_set]

# Filter to rows with valid escape/rework
for dv_name, dv_key in [("strict_escaped", "_escaped"), ("reworked", "_reworked")]:
    valid = [r for r in repo_rows if r[dv_key] is not None]

    # Raw rates
    spec_rows = [r for r in valid if r["_has_spec"] == 1]
    nospec_rows = [r for r in valid if r["_has_spec"] == 0]
    spec_rate = sum(1 for r in spec_rows if r[dv_key]) / len(spec_rows) if spec_rows else 0
    nospec_rate = sum(1 for r in nospec_rows if r[dv_key]) / len(nospec_rows) if nospec_rows else 0
    print(f"\n  {dv_name}: spec'd={100*spec_rate:.1f}% (n={len(spec_rows)}) vs unspec'd={100*nospec_rate:.1f}% (n={len(nospec_rows)})")

    # Logistic regression
    y = np.array([1 if r[dv_key] else 0 for r in valid])
    X = np.column_stack([
        np.array([r["_has_spec"] for r in valid]),
        np.array([r["_log_add"] for r in valid]),
        np.array([r["_log_del"] for r in valid]),
        np.array([r["_log_files"] for r in valid]),
    ])
    X = sm.add_constant(X)
    labels = ["const", "has_spec", "log(additions+1)", "log(deletions+1)", "log(files+1)"]
    result, labels = logit_summary(y, X, labels)
    print_logit(result, labels, dv_name)


# ─────────────────────────────────────────────
# ANALYSIS 3: SPEC QUALITY PARADOX (controlling for size)
# ─────────────────────────────────────────────
print("\n" + "=" * 70)
print("ANALYSIS 3: SPEC QUALITY PARADOX (controlling for change size)")
print("=" * 70)

for dv_name, dv_key in [("strict_escaped", "_escaped"), ("reworked", "_reworked")]:
    valid = [r for r in scored if r[dv_key] is not None]

    y = np.array([1 if r[dv_key] else 0 for r in valid])
    X = np.column_stack([
        np.array([r["_q"] for r in valid]),
        np.array([r["_log_add"] for r in valid]),
        np.array([r["_log_del"] for r in valid]),
        np.array([r["_log_files"] for r in valid]),
    ])
    X = sm.add_constant(X)
    labels = ["const", "q_overall", "log(additions+1)", "log(deletions+1)", "log(files+1)"]
    result, labels = logit_summary(y, X, labels)
    print_logit(result, labels, dv_name)


# ─────────────────────────────────────────────
# ANALYSIS 4: ATTENTION SIGNALS
# ─────────────────────────────────────────────
print("\n" + "=" * 70)
print("ANALYSIS 4: ATTENTION SIGNALS (typos, casual, questions)")
print("=" * 70)

# Check attention columns
attention_cols = ["f_typos", "f_casual", "f_questions"]
for r in scored:
    typos = to_bool(r.get("f_typos"))
    casual = to_bool(r.get("f_casual"))
    questions = to_bool(r.get("f_questions"))
    r["_attention"] = 1 if any([typos, casual, questions]) else 0

attn_rows = [r for r in scored if r["_attention"] == 1]
no_attn_rows = [r for r in scored if r["_attention"] == 0]
print(f"\n  Attention signal present: {len(attn_rows)} PRs ({100*len(attn_rows)/len(scored):.1f}%)")
print(f"  No attention signal: {len(no_attn_rows)} PRs ({100*len(no_attn_rows)/len(scored):.1f}%)")

for dv_name, dv_key in [("strict_escaped", "_escaped"), ("reworked", "_reworked")]:
    valid_attn = [r for r in attn_rows if r[dv_key] is not None]
    valid_no = [r for r in no_attn_rows if r[dv_key] is not None]

    attn_pos = sum(1 for r in valid_attn if r[dv_key])
    attn_neg = len(valid_attn) - attn_pos
    no_pos = sum(1 for r in valid_no if r[dv_key])
    no_neg = len(valid_no) - no_pos

    rate_attn = 100 * attn_pos / len(valid_attn) if valid_attn else 0
    rate_no = 100 * no_pos / len(valid_no) if valid_no else 0

    print(f"\n  {dv_name}:")
    print(f"    Attention:    {rate_attn:.1f}% ({attn_pos}/{len(valid_attn)})")
    print(f"    No attention: {rate_no:.1f}% ({no_pos}/{len(valid_no)})")

    # Fisher's exact
    oddsratio, p = fisher_2x2(attn_pos, attn_neg, no_pos, no_neg)
    print(f"    Fisher's exact: OR={oddsratio:.3f}, p={p:.4f}")

    # Logistic regression with size controls
    valid = [r for r in scored if r[dv_key] is not None]
    y = np.array([1 if r[dv_key] else 0 for r in valid])
    X = np.column_stack([
        np.array([r["_attention"] for r in valid]),
        np.array([r["_log_add"] for r in valid]),
        np.array([r["_log_del"] for r in valid]),
        np.array([r["_log_files"] for r in valid]),
    ])
    X = sm.add_constant(X)
    labels = ["const", "attention", "log(additions+1)", "log(deletions+1)", "log(files+1)"]
    result, labels = logit_summary(y, X, labels)
    print_logit(result, labels, dv_name)


# ─────────────────────────────────────────────
# ANALYSIS 5: PARADOX BY INDIVIDUAL REPO
# ─────────────────────────────────────────────
print("\n" + "=" * 70)
print("ANALYSIS 5: SPEC QUALITY PARADOX BY INDIVIDUAL REPO")
print("=" * 70)

repo_results = []
for repo in sorted(scored_repos):
    repo_scored = [r for r in scored if r["repo"] == repo]
    if len(repo_scored) < 50:
        print(f"\n  {repo}: SKIPPED (n={len(repo_scored)}, need >50)")
        continue

    print(f"\n  {repo} (n={len(repo_scored)})")

    # Tier breakdown
    tiers = {tier: [] for tier in TIER_ORDER}
    for r in repo_scored:
        tiers[r["_tier"]].append(r)

    print(f"    {'Tier':<26} {'N':>5} {'Esc%':>6} {'Rwk%':>6}")
    print(f"    {'-'*30}")

    tier_esc_rates = {}
    for tier in TIER_ORDER:
        t_rows = tiers[tier]
        n = len(t_rows)
        if n == 0:
            print(f"    {TIER_DISPLAY[tier]:<26} {0:>5}    n/a    n/a")
            continue
        esc = sum(1 for r in t_rows if r["_escaped"])
        rwk = sum(1 for r in t_rows if r["_reworked"])
        esc_rate = 100 * esc / n
        rwk_rate = 100 * rwk / n
        tier_esc_rates[tier] = esc_rate
        print(f"    {TIER_DISPLAY[tier]:<26} {n:>5} {esc_rate:>5.1f}% {rwk_rate:>5.1f}%")

    # Determine if paradox holds (top decile escape > bottom 75%)
    if TOP_10 in tier_esc_rates and BOTTOM_75 in tier_esc_rates:
        if tier_esc_rates[TOP_10] > tier_esc_rates[BOTTOM_75]:
            direction = "PARADOX (TOP10 > BOTTOM75)"
        elif tier_esc_rates[TOP_10] < tier_esc_rates[BOTTOM_75]:
            direction = "EXPECTED (BOTTOM75 > TOP10)"
        else:
            direction = "EQUAL"
    else:
        direction = "INSUFFICIENT TIERS"

    # Logistic on q_overall within repo
    valid = [r for r in repo_scored if r["_escaped"] is not None]
    if len(valid) > 20 and sum(1 for r in valid if r["_escaped"]) >= 3:
        y = np.array([1 if r["_escaped"] else 0 for r in valid])
        X = np.column_stack([
            np.array([r["_q"] for r in valid]),
            np.array([r["_log_add"] for r in valid]),
            np.array([r["_log_del"] for r in valid]),
            np.array([r["_log_files"] for r in valid]),
        ])
        X = sm.add_constant(X)
        try:
            model = sm.Logit(y, X)
            result = model.fit(disp=0, maxiter=100)
            coef = result.params[1]
            p = result.pvalues[1]
            or_val = math.exp(coef)
            sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""
            print(f"    Logit q_overall: coef={coef:.4f}, OR={or_val:.3f}, p={p:.4f}{sig}")
        except Exception as e:
            print(f"    Logit failed: {e}")
            coef, p, or_val = None, None, None
    else:
        print(f"    Logit: insufficient escapes for regression")
        coef, p, or_val = None, None, None

    repo_results.append({
        "repo": repo,
        "n": len(repo_scored),
        "direction": direction,
        "coef": coef,
        "p": p,
        "or": or_val,
    })


# ─────────────────────────────────────────────
# FINAL SUMMARY
# ─────────────────────────────────────────────
print("\n\n")
print("=" * 70)
print(f"  FULL ANALYSIS ON {len(scored)} SCORED PRs ({len(scored_repos)} REPOS)")
print("=" * 70)

print("\n1. REPO DISTRIBUTION")
print(f"   {'Repo':<35} {'<58':>5} {'58-65':>6} {'66+':>5} {'N':>5}")
print(f"   {'-'*60}")
for repo in sorted(repo_tiers.keys(), key=lambda x: -repo_tiers[x]["total"]):
    d = repo_tiers[repo]
    print(f"   {repo:<35} {d[BOTTOM_75]:>5} {d[TOP_25_ONLY]:>6} {d[TOP_10]:>5} {d['total']:>5}")

print(f"\n   Tier escape rates:")
for tier in TIER_ORDER:
    tier_rows = [r for r in scored if r["_tier"] == tier]
    n = len(tier_rows)
    esc = sum(1 for r in tier_rows if r["_escaped"])
    rwk = sum(1 for r in tier_rows if r["_reworked"])
    print(f"   {TIER_DISPLAY[tier]:<26}: escape={100*esc/n:.1f}%, rework={100*rwk/n:.1f}% (n={n})")

print("\n2. SPECS VS NO-SPECS (with size controls)")
for dv_name, dv_key in [("strict_escaped", "_escaped"), ("reworked", "_reworked")]:
    valid = [r for r in repo_rows if r[dv_key] is not None]
    spec_rows = [r for r in valid if r["_has_spec"] == 1]
    nospec_rows = [r for r in valid if r["_has_spec"] == 0]
    spec_rate = sum(1 for r in spec_rows if r[dv_key]) / len(spec_rows) if spec_rows else 0
    nospec_rate = sum(1 for r in nospec_rows if r[dv_key]) / len(nospec_rows) if nospec_rows else 0
    print(f"   {dv_name}: spec'd={100*spec_rate:.1f}% vs unspec'd={100*nospec_rate:.1f}%")
print(f"   (See regression tables above for controlled estimates)")

print("\n3. QUALITY PARADOX (with size controls)")
print(f"   See regression tables above. Key question: is q_overall coefficient")
print(f"   positive (paradox) or negative (expected) and significant?")

print("\n4. ATTENTION SIGNALS")
print(f"   Attention present: {len(attn_rows)} PRs ({100*len(attn_rows)/len(scored):.1f}%)")
for dv_name, dv_key in [("strict_escaped", "_escaped"), ("reworked", "_reworked")]:
    valid_attn = [r for r in attn_rows if r[dv_key] is not None]
    valid_no = [r for r in no_attn_rows if r[dv_key] is not None]
    rate_a = 100 * sum(1 for r in valid_attn if r[dv_key]) / len(valid_attn) if valid_attn else 0
    rate_n = 100 * sum(1 for r in valid_no if r[dv_key]) / len(valid_no) if valid_no else 0
    print(f"   {dv_name}: attention={rate_a:.1f}% vs none={rate_n:.1f}%")

print("\n5. PER-REPO PARADOX")
for rr in repo_results:
    p_str = f"p={rr['p']:.4f}" if rr["p"] is not None else "n/a"
    or_str = f"OR={rr['or']:.3f}" if rr["or"] is not None else ""
    print(f"   {rr['repo']:<35} {rr['direction']:<25} {p_str} {or_str}")

print("\n" + "=" * 70)
print("  END OF ANALYSIS")
print("=" * 70)
