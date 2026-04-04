#!/usr/bin/env python3
"""
Sample 100 spec'd PRs for human validation of LLM quality scores.

Stratified sample:
  - 25 from bottom quartile (q_overall < p25)
  - 25 from middle (p25 <= q_overall < p75)
  - 25 from top quartile (q_overall >= p75)
  - 25 random (unstratified)

Output: CSV with columns for human scoring + the LLM scores (hidden during rating).
"""

import pandas as pd
import numpy as np
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
OUT_DIR = Path(__file__).resolve().parent.parent.parent / "results"

df = pd.read_csv(DATA_DIR / "master-prs.csv", low_memory=False)

# Only scored PRs
scored = df[df["q_overall"].notna()].copy()
print(f"Scored PRs available: {len(scored):,}")

# Quality distribution
p25 = scored["q_overall"].quantile(0.25)
p75 = scored["q_overall"].quantile(0.75)
print(f"Quality distribution: p25={p25:.1f}, median={scored['q_overall'].median():.1f}, p75={p75:.1f}")

# Stratified sample
np.random.seed(42)

low = scored[scored["q_overall"] < p25].sample(n=min(25, len(scored[scored["q_overall"] < p25])))
mid = scored[(scored["q_overall"] >= p25) & (scored["q_overall"] < p75)].sample(
    n=min(25, len(scored[(scored["q_overall"] >= p25) & (scored["q_overall"] < p75)])))
high = scored[scored["q_overall"] >= p75].sample(n=min(25, len(scored[scored["q_overall"] >= p75])))
rand = scored.sample(n=25)

sample = pd.concat([low, mid, high, rand]).drop_duplicates(subset=["repo", "pr_number"])
sample = sample.sample(frac=1, random_state=42).reset_index(drop=True)  # Shuffle

print(f"Sample size: {len(sample)}")

# Quality dimension columns
q_dims = ["q_outcome_clarity", "q_error_states", "q_scope_boundaries",
           "q_acceptance_criteria", "q_data_contracts", "q_dependency_context",
           "q_behavioral_specificity"]

# Create rating sheet (human sees PR content, rates blind, then we compare)
rating_cols = ["sample_id", "repo", "pr_number", "title", "url"]

# Add human rating columns (to be filled)
for dim in ["outcome_clarity", "error_states", "scope_boundaries",
            "acceptance_criteria", "data_contracts", "dependency_context",
            "behavioral_specificity"]:
    rating_cols.append(f"human_{dim}")

rating_sheet = pd.DataFrame()
rating_sheet["sample_id"] = range(1, len(sample) + 1)
rating_sheet["repo"] = sample["repo"].values
rating_sheet["pr_number"] = sample["pr_number"].values
rating_sheet["title"] = sample["title"].values

# GitHub URL for easy lookup
rating_sheet["url"] = sample.apply(
    lambda r: f"https://github.com/{r['repo']}/pull/{int(r['pr_number'])}", axis=1).values

# Human rating columns (blank — to be filled)
for dim in ["outcome_clarity", "error_states", "scope_boundaries",
            "acceptance_criteria", "data_contracts", "dependency_context",
            "behavioral_specificity"]:
    rating_sheet[f"human_{dim}"] = ""

rating_sheet.to_csv(OUT_DIR / "human-rating-sheet.csv", index=False)
print(f"Rating sheet saved to: {OUT_DIR / 'human-rating-sheet.csv'}")

# Save answer key (LLM scores) separately
answer_key = sample[["repo", "pr_number"] + [c for c in q_dims if c in sample.columns] + ["q_overall"]].copy()
answer_key.to_csv(OUT_DIR / "human-rating-answer-key.csv", index=False)
print(f"Answer key saved to: {OUT_DIR / 'human-rating-answer-key.csv'}")

print(f"""
Instructions for human rating:
1. Open human-rating-sheet.csv
2. For each PR, read the title and body_excerpt
3. Rate each dimension 1-5 (same rubric as the LLM):
   - 1 = Not present at all
   - 2 = Mentioned vaguely
   - 3 = Partially specified
   - 4 = Well specified
   - 5 = Thoroughly specified with examples/detail
4. Save the completed sheet
5. Run compare-human-llm-ratings.py to compute Cohen's kappa
""")
