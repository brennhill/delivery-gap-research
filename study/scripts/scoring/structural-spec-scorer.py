#!/usr/bin/env python3
"""
Deterministic structural spec scorer for PR descriptions.
No LLM involved - pure text analysis, fully reproducible.

Reads raw PR bodies from prs-*.json files, scores them on 8 structural
dimensions, and merges scores into master-prs.csv.
"""

import re
import json
import glob
import os
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import fisher_exact

DATA_DIR = Path(__file__).parent / "data"
MASTER_CSV = DATA_DIR / "master-prs.csv"

# ── Regex patterns ──────────────────────────────────────────────────────

# Structure signals
HEADER_RE = re.compile(r'^#{1,6}\s', re.MULTILINE)
BULLET_RE = re.compile(r'^\s*[-*]\s', re.MULTILINE)
NUMBERED_RE = re.compile(r'^\s*\d+[.)]\s', re.MULTILINE)
CODE_BLOCK_RE = re.compile(r'```')

# Specificity signals
NUMBER_RE = re.compile(r'\b\d+(?:\.\d+)?(?:\s*(?:ms|seconds?|minutes?|hours?|bytes?|KB|MB|GB|%|px|em|rem))\b', re.IGNORECASE)
BARE_NUMBER_RE = re.compile(r'(?<!\w)\d{2,}(?!\w)')  # standalone numbers with 2+ digits
FILE_PATH_RE = re.compile(r'(?:^|\s)[a-zA-Z0-9_./]+\.[a-zA-Z]{1,5}(?:\s|$|[,;)])', re.MULTILINE)
CAMEL_CASE_RE = re.compile(r'\b[A-Z][a-z]+(?:[A-Z][a-z]+)+\b')
SNAKE_CASE_RE = re.compile(r'\b[a-z][a-z0-9]*(?:_[a-z0-9]+)+\b')
API_ENDPOINT_RE = re.compile(r'(?:GET|POST|PUT|PATCH|DELETE|/api/|/v[0-9]+/)[\w/{}:.?=&-]*', re.IGNORECASE)
SLASH_PATH_RE = re.compile(r'(?<!\w)/[a-zA-Z][a-zA-Z0-9_/-]{2,}(?!\w)')

# Error awareness
ERROR_TERMS = re.compile(
    r'\b(?:error|fail(?:s|ed|ure|ing)?|edge\s*case|boundary|'
    r'null|empty|timeout|retry|exception|crash(?:es|ed|ing)?|invalid|'
    r'undefined|overflow|underflow|race\s*condition|deadlock|panic)\b',
    re.IGNORECASE
)

# Scope signals
SCOPE_TERMS = re.compile(
    r'\b(?:out\s+of\s+scope|not\s+included|won\'t|will\s+not|exclude[ds]?|'
    r'skip(?:s|ped|ping)?|defer(?:s|red|ring)?|later|future|'
    r'follow[\s-]*up|beyond\s+scope|outside\s+scope|not\s+(?:in|part\s+of)\s+this)\b',
    re.IGNORECASE
)

# Acceptance criteria
CHECKBOX_RE = re.compile(r'-\s*\[[\sx]\]', re.IGNORECASE)
ACCEPTANCE_TERMS = re.compile(
    r'\b(?:acceptance\s+criteria|definition\s+of\s+done|'
    r'verify\s+that|should\s+be\s+able\s+to|'
    r'expected\s+behavio(?:u)?r|test\s+plan|how\s+to\s+test)\b',
    re.IGNORECASE
)

# Questions
QUESTION_RE = re.compile(r'\?')

# References
ISSUE_REF_RE = re.compile(r'(?:^|\s)#\d{2,}(?:\s|$|[,;.)])', re.MULTILINE)
URL_RE = re.compile(r'https?://\S+')
MENTION_RE = re.compile(r'(?:^|\s)@[a-zA-Z0-9_-]+')
REF_TERMS = re.compile(
    r'\b(?:see\s+also|related\s+to|depends\s+on|blocks?|blocked\s+by|'
    r'fixes\s+#|closes?\s+#|resolves?\s+#|references?\s+#)\b',
    re.IGNORECASE
)


def score_pr(body: str) -> dict:
    """Score a single PR body on all structural dimensions."""
    if not body or not isinstance(body, str):
        body = ""

    words = body.split()
    word_count = len(words)

    # 1. Length (word count)
    s_length = word_count

    # 2. Structure
    s_structure = (
        len(HEADER_RE.findall(body)) +
        len(BULLET_RE.findall(body)) +
        len(NUMBERED_RE.findall(body)) +
        len(CODE_BLOCK_RE.findall(body)) // 2  # pairs of ```
    )

    # 3. Specificity
    s_specificity = (
        len(NUMBER_RE.findall(body)) +
        len(BARE_NUMBER_RE.findall(body)) +
        len(FILE_PATH_RE.findall(body)) +
        len(CAMEL_CASE_RE.findall(body)) +
        len(SNAKE_CASE_RE.findall(body)) +
        len(API_ENDPOINT_RE.findall(body)) +
        len(SLASH_PATH_RE.findall(body))
    )

    # 4. Error awareness
    s_error_awareness = len(ERROR_TERMS.findall(body))

    # 5. Scope signals
    s_scope = len(SCOPE_TERMS.findall(body))

    # 6. Acceptance criteria
    s_acceptance = (
        len(CHECKBOX_RE.findall(body)) +
        len(ACCEPTANCE_TERMS.findall(body))
    )

    # 7. Questions
    s_questions = len(QUESTION_RE.findall(body))

    # 8. References
    s_references = (
        len(ISSUE_REF_RE.findall(body)) +
        len(URL_RE.findall(body)) +
        len(MENTION_RE.findall(body)) +
        len(REF_TERMS.findall(body))
    )

    s_overall = (
        s_length + s_structure + s_specificity +
        s_error_awareness + s_scope + s_acceptance +
        s_questions + s_references
    )

    return {
        "s_length": s_length,
        "s_structure": s_structure,
        "s_specificity": s_specificity,
        "s_error_awareness": s_error_awareness,
        "s_scope": s_scope,
        "s_acceptance": s_acceptance,
        "s_questions": s_questions,
        "s_references": s_references,
        "s_overall": s_overall,
    }


def load_bodies() -> pd.DataFrame:
    """Load PR bodies from all prs-*.json files, return (repo, pr_number, body) DataFrame."""
    json_files = sorted(glob.glob(str(DATA_DIR / "prs-*.json")))
    print(f"Loading bodies from {len(json_files)} prs-*.json files...")

    rows = []
    for jf in json_files:
        with open(jf) as f:
            prs = json.load(f)
        for pr in prs:
            rows.append({
                "repo": pr["repo"],
                "pr_number": pr["pr_number"],
                "body": pr.get("body", "") or "",
            })

    df = pd.DataFrame(rows)
    print(f"  Loaded {len(df)} PR bodies across {df['repo'].nunique()} repos")
    return df


def main():
    # ── Backup ──────────────────────────────────────────────────────────
    bak = MASTER_CSV.with_suffix(".csv.bak")
    if bak.exists():
        bak2 = MASTER_CSV.with_suffix(".csv.bak2")
        if bak2.exists():
            bak_target = MASTER_CSV.with_suffix(".csv.bak3")
        else:
            bak_target = bak2
    else:
        bak_target = bak

    print(f"Backing up master-prs.csv -> {bak_target.name}")
    shutil.copy2(MASTER_CSV, bak_target)

    # ── Load master CSV ─────────────────────────────────────────────────
    master = pd.read_csv(MASTER_CSV, low_memory=False)
    print(f"Master CSV: {len(master)} rows, {master['repo'].nunique()} repos")

    # ── Load bodies and score ───────────────────────────────────────────
    bodies = load_bodies()

    print("Scoring PR descriptions...")
    scores = bodies["body"].apply(score_pr).apply(pd.Series)
    scored = pd.concat([bodies[["repo", "pr_number"]], scores], axis=1)

    # ── Merge ───────────────────────────────────────────────────────────
    # Drop existing s_ columns if re-running
    existing_s_cols = [c for c in master.columns if c.startswith("s_")]
    if existing_s_cols:
        print(f"  Dropping {len(existing_s_cols)} existing s_ columns (re-run)")
        master = master.drop(columns=existing_s_cols)

    merged = master.merge(scored, on=["repo", "pr_number"], how="left")
    unmatched = merged["s_overall"].isna().sum()
    if unmatched > 0:
        print(f"  WARNING: {unmatched} PRs had no matching body (filling with 0)")
        for col in scores.columns:
            merged[col] = merged[col].fillna(0).astype(int)

    print(f"  Merged: {len(merged)} rows")

    # ── Distribution stats ──────────────────────────────────────────────
    overall = merged["s_overall"]
    print("\n" + "=" * 60)
    print("DISTRIBUTION: s_overall")
    print("=" * 60)
    print(f"  mean:   {overall.mean():.1f}")
    print(f"  median: {overall.median():.1f}")
    print(f"  p10:    {np.percentile(overall, 10):.1f}")
    print(f"  p25:    {np.percentile(overall, 25):.1f}")
    print(f"  p75:    {np.percentile(overall, 75):.1f}")
    print(f"  p90:    {np.percentile(overall, 90):.1f}")
    print(f"  min:    {overall.min():.0f}")
    print(f"  max:    {overall.max():.0f}")

    # ── Dimension summaries ─────────────────────────────────────────────
    print(f"\nDIMENSION MEANS:")
    for col in scores.columns:
        print(f"  {col:25s} mean={merged[col].mean():.1f}  median={merged[col].median():.0f}")

    # ── Percentile-based tiers ──────────────────────────────────────────
    p25 = np.percentile(overall, 25)
    p75 = np.percentile(overall, 75)
    merged["s_tier"] = pd.cut(
        overall,
        bins=[-1, p25, p75, float("inf")],
        labels=["LOW", "MED", "HIGH"],
    )

    print(f"\n{'=' * 60}")
    print(f"TIER BREAKDOWN  (LOW <= {p25:.0f}, MED <= {p75:.0f}, HIGH > {p75:.0f})")
    print(f"{'=' * 60}")
    print(f"{'Tier':<6} {'N':>6} {'Reworked%':>10} {'Escaped%':>10}")
    print("-" * 36)

    tier_stats = {}
    for tier in ["LOW", "MED", "HIGH"]:
        sub = merged[merged["s_tier"] == tier]
        n = len(sub)
        reworked_rate = sub["reworked"].mean() * 100 if "reworked" in sub.columns else float("nan")
        escaped_rate = sub["strict_escaped"].mean() * 100 if "strict_escaped" in sub.columns else float("nan")
        tier_stats[tier] = {"n": n, "reworked": reworked_rate, "escaped": escaped_rate}
        print(f"{tier:<6} {n:>6} {reworked_rate:>9.1f}% {escaped_rate:>9.1f}%")

    # ── Fisher's exact: HIGH vs LOW ─────────────────────────────────────
    print(f"\n{'=' * 60}")
    print("FISHER'S EXACT: HIGH vs LOW")
    print("=" * 60)

    for outcome in ["reworked", "strict_escaped"]:
        if outcome not in merged.columns:
            continue
        high = merged[merged["s_tier"] == "HIGH"]
        low = merged[merged["s_tier"] == "LOW"]

        # Build contingency table: [[high_yes, high_no], [low_yes, low_no]]
        h_yes = int(high[outcome].sum())
        h_no = len(high) - h_yes
        l_yes = int(low[outcome].sum())
        l_no = len(low) - l_yes

        table = [[h_yes, h_no], [l_yes, l_no]]
        odds_ratio, p_value = fisher_exact(table)
        print(f"\n  {outcome}:")
        print(f"    HIGH: {h_yes}/{len(high)} ({h_yes/len(high)*100:.1f}%)")
        print(f"    LOW:  {l_yes}/{len(low)} ({l_yes/len(low)*100:.1f}%)")
        print(f"    OR={odds_ratio:.3f}  p={p_value:.4f}")

    # ── Save ────────────────────────────────────────────────────────────
    # Drop the tier column (derived, not raw data)
    merged = merged.drop(columns=["s_tier"])
    merged.to_csv(MASTER_CSV, index=False)
    print(f"\nSaved {len(merged)} rows to {MASTER_CSV}")


if __name__ == "__main__":
    main()
