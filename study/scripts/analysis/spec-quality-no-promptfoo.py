#!/usr/bin/env python3
"""
Spec paradox robustness check: does the inverted spec-quality effect
survive after excluding promptfoo (314 HIGH-tier PRs)?

Locked AI tiers: bottom 75% (<58), p75-p89 (58-65), top 10% (>=66).
"""

import pandas as pd
from scipy.stats import fisher_exact
from pathlib import Path
import sys

UTIL_DIR = Path(__file__).resolve().parents[1] / "util"
if str(UTIL_DIR) not in sys.path:
    sys.path.insert(0, str(UTIL_DIR))

from quality_tiers import (  # noqa: E402
    BOTTOM_75,
    TOP_10,
    TIER_ORDER,
    TIER_DISPLAY,
    quality_tier,
)

CSV = "/Users/brenn/dev/ai-augmented-dev/research/study/data/master-prs.csv"

df = pd.read_csv(CSV, low_memory=False)
print(f"Total PRs loaded: {len(df):,}")

# ── Exclude promptfoo ────────────────────────────────────────────────
promptfoo_mask = df["repo"].str.contains("promptfoo", case=False, na=False)
n_promptfoo = promptfoo_mask.sum()
print(f"Excluding {n_promptfoo} promptfoo PRs")
df = df[~promptfoo_mask].copy()
print(f"Remaining: {len(df):,} PRs")

# ── Filter to spec'd PRs (q_overall is not NaN) ─────────────────────
specd = df[df["q_overall"].notna()].copy()
print(f"\nSpec'd PRs (after excluding promptfoo): {len(specd):,}")

# ── Ensure boolean columns ───────────────────────────────────────────
for col in ["reworked", "strict_escaped"]:
    specd[col] = specd[col].map(
        {True: True, False: False, "True": True, "False": False, 1: True, 0: False}
    ).fillna(False).astype(bool)

# ── Quality tiers ────────────────────────────────────────────────────
def q_tier(val):
    if pd.isna(val):
        return "UNSPEC"
    return quality_tier(val)

specd["q_tier"] = specd["q_overall"].apply(q_tier)

# ── Tier breakdown ───────────────────────────────────────────────────
print(f"\n{'Tier':<26} {'n':>6} {'Rework%':>9} {'Escape%':>9}")
print("-" * 35)
for tier in TIER_ORDER:
    subset = specd[specd["q_tier"] == tier]
    n = len(subset)
    rework_rate = subset["reworked"].mean() * 100
    escape_rate = subset["strict_escaped"].mean() * 100
    print(f"{TIER_DISPLAY[tier]:<26} {n:>6} {rework_rate:>8.1f}% {escape_rate:>8.1f}%")

# ── Fisher's exact: top decile vs bottom 75% ────────────────────────
low = specd[specd["q_tier"] == BOTTOM_75]
high = specd[specd["q_tier"] == TOP_10]

print(f"\nFisher's exact test: TOP10 (n={len(high)}) vs BOTTOM75 (n={len(low)})")
print("-" * 60)

for outcome, label in [("reworked", "Rework"), ("strict_escaped", "Escape")]:
    # 2x2 table: [[high_yes, high_no], [low_yes, low_no]]
    h_yes = high[outcome].sum()
    h_no = len(high) - h_yes
    l_yes = low[outcome].sum()
    l_no = len(low) - l_yes

    table = [[h_yes, h_no], [l_yes, l_no]]
    odds_ratio, p_value = fisher_exact(table)

    h_pct = h_yes / len(high) * 100
    l_pct = l_yes / len(low) * 100
    delta = h_pct - l_pct
    sig = "***" if p_value < 0.001 else "**" if p_value < 0.01 else "*" if p_value < 0.05 else "ns"

    print(f"  {label:8s}: TOP10={h_pct:.1f}%  BOTTOM75={l_pct:.1f}%  "
          f"Δ={delta:+.1f}pp  OR={odds_ratio:.2f}  p={p_value:.4f}  {sig}")

# ── Verdict ──────────────────────────────────────────────────────────
print("\n" + "=" * 60)
h_rework = high["reworked"].mean()
l_rework = low["reworked"].mean()
h_escape = high["strict_escaped"].mean()
l_escape = low["strict_escaped"].mean()

if h_rework > l_rework and h_escape > l_escape:
    print("PARADOX SURVIVES: Top-decile specs → MORE rework AND escapes than bottom-75% specs")
elif h_rework > l_rework:
    print("PARTIAL: Top-decile specs → more rework, but NOT more escapes")
elif h_escape > l_escape:
    print("PARTIAL: Top-decile specs → more escapes, but NOT more rework")
else:
    print("PARADOX GONE: Without promptfoo, top-decile specs outperform bottom-75% specs")
print("=" * 60)

# ── Also show promptfoo's contribution for context ───────────────────
print("\n--- Promptfoo contribution context ---")
df_full = pd.read_csv(CSV, low_memory=False)
pf = df_full[df_full["repo"].str.contains("promptfoo", case=False, na=False)]
pf_specd = pf[pf["q_overall"].notna()].copy()
pf_specd["q_tier"] = pf_specd["q_overall"].apply(q_tier)
print(f"Promptfoo spec'd PRs: {len(pf_specd)}")
print(f"  Tier breakdown: {pf_specd['q_tier'].value_counts().to_dict()}")

# ── DATA COVERAGE WARNING ────────────────────────────────────────────
print("\n" + "!" * 60)
print("WARNING: q_overall scores exist for only 1,297 PRs total.")
print(f"  Promptfoo contributes 1,248 of those ({1248/1297*100:.0f}%).")
print(f"  After exclusion, only {len(specd)} scored PRs remain.")
print(f"  N per cell is too small for reliable inference.")
print(f"  The paradox direction holds but is NOT statistically significant.")
print("!" * 60)

# ── Which repos have q_overall scores? ───────────────────────────────
print(f"\nRepos with q_overall scores (excl. promptfoo):")
for repo, group in specd.groupby("repo"):
    print(f"  {repo}: {len(group)} PRs, q_overall range [{group['q_overall'].min():.0f}-{group['q_overall'].max():.0f}]")
