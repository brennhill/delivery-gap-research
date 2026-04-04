#!/usr/bin/env python3
"""
Compare human ratings to LLM (Claude Haiku) ratings.
Reports Cohen's kappa per dimension and overall.

Run AFTER completing human-rating-sheet.csv.
"""

import pandas as pd
import numpy as np
from sklearn.metrics import cohen_kappa_score
from scipy import stats
from pathlib import Path

RESULTS_DIR = Path(__file__).resolve().parent.parent.parent / "results"

human = pd.read_csv(RESULTS_DIR / "human-rating-sheet.csv")
llm = pd.read_csv(RESULTS_DIR / "human-rating-answer-key.csv")

# Merge on repo + pr_number
merged = human.merge(llm, on=["repo", "pr_number"], how="inner")

dimensions = [
    "outcome_clarity", "error_states", "scope_boundaries",
    "acceptance_criteria", "data_contracts", "dependency_context",
    "behavioral_specificity",
]

print("=" * 70)
print("INTER-RATER RELIABILITY: Human vs LLM (Claude Haiku)")
print("=" * 70)

kappas = []
for dim in dimensions:
    h_col = f"human_{dim}"
    l_col = f"q_{dim}"

    if h_col not in merged.columns or l_col not in merged.columns:
        print(f"  {dim}: MISSING COLUMN")
        continue

    h_vals = pd.to_numeric(merged[h_col], errors="coerce") * 10  # Human scored 0-10, LLM scored 0-100
    l_vals = pd.to_numeric(merged[l_col], errors="coerce")

    valid = h_vals.notna() & l_vals.notna()
    if valid.sum() < 10:
        print(f"  {dim}: Too few valid ratings ({valid.sum()})")
        continue

    h = h_vals[valid].astype(int).values
    l = l_vals[valid].astype(int).values

    # Cohen's kappa (linear weights for ordinal scale)
    k_linear = cohen_kappa_score(h, l, weights="linear")
    k_quadratic = cohen_kappa_score(h, l, weights="quadratic")

    # Pearson correlation
    r, p = stats.pearsonr(h, l)

    # Mean absolute difference
    mad = np.mean(np.abs(h - l))

    kappas.append(k_quadratic)

    print(f"\n  {dim}:")
    print(f"    N = {valid.sum()}")
    print(f"    Cohen's κ (linear):    {k_linear:.3f}")
    print(f"    Cohen's κ (quadratic): {k_quadratic:.3f}")
    print(f"    Pearson r:             {r:.3f} (p={p:.4f})")
    print(f"    Mean absolute diff:    {mad:.2f}")

# Overall (compute on flattened arrays of all dimensions)
print(f"\n{'=' * 70}")
print("OVERALL")
print("=" * 70)

all_h = []
all_l = []
for dim in dimensions:
    h_col = f"human_{dim}"
    l_col = f"q_{dim}"
    if h_col in merged.columns and l_col in merged.columns:
        h_vals = pd.to_numeric(merged[h_col], errors="coerce") * 10  # Human scored 0-10, LLM scored 0-100
        l_vals = pd.to_numeric(merged[l_col], errors="coerce")
        valid = h_vals.notna() & l_vals.notna()
        all_h.extend(h_vals[valid].astype(int).tolist())
        all_l.extend(l_vals[valid].astype(int).tolist())

if len(all_h) > 20:
    k_overall = cohen_kappa_score(all_h, all_l, weights="quadratic")
    r_overall, p_overall = stats.pearsonr(all_h, all_l)
    mad_overall = np.mean(np.abs(np.array(all_h) - np.array(all_l)))

    print(f"  Total rating pairs: {len(all_h)}")
    print(f"  Overall κ (quadratic): {k_overall:.3f}")
    print(f"  Overall Pearson r:     {r_overall:.3f}")
    print(f"  Overall MAD:           {mad_overall:.2f}")

    if kappas:
        print(f"\n  Mean per-dimension κ:  {np.mean(kappas):.3f}")
        print(f"  Min per-dimension κ:   {np.min(kappas):.3f}")
        print(f"  Max per-dimension κ:   {np.max(kappas):.3f}")

    print(f"\n  Interpretation (Landis & Koch 1977):")
    print(f"    <0.00 = Poor, 0.00-0.20 = Slight, 0.21-0.40 = Fair")
    print(f"    0.41-0.60 = Moderate, 0.61-0.80 = Substantial, 0.81-1.00 = Almost perfect")
else:
    print("  Not enough valid ratings to compute overall kappa.")
