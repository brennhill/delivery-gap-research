#!/usr/bin/env python3
"""Join spec-quality JSON scores into master-prs.csv.

Reads all spec-quality-*.json files, matches to master-prs.csv rows by
(repo, pr_number), and writes the quality dimensions into the q_* columns.

Then re-runs the quality-tier paradox analysis.
"""

import csv
import json
import shutil
from collections import defaultdict
from pathlib import Path
import sys

import scipy.stats as stats
import numpy as np

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

DATA_DIR = Path(__file__).resolve().parent / "data"
CSV_PATH = DATA_DIR / "master-prs.csv"
BAK_PATH = DATA_DIR / "master-prs.csv.bak"

# Mapping from JSON keys to CSV column names
FIELD_MAP = {
    "overall": "q_overall",
    "outcome_clarity": "q_outcome_clarity",
    "error_states": "q_error_states",
    "scope_boundaries": "q_scope_boundaries",
    "acceptance_criteria": "q_acceptance_criteria",
    "data_contracts": "q_data_contracts",
    "dependency_context": "q_dependency_context",
    "behavioral_specificity": "q_behavioral_specificity",
    "change_type": "q_change_type",
    "spec_length_signal": "q_spec_length_signal",
}


def load_spec_scores():
    """Load all spec-quality JSON files into a dict keyed by (repo, pr_number)."""
    scores = {}
    per_file = {}
    for path in sorted(DATA_DIR.glob("spec-quality-*.json")):
        data = json.loads(path.read_text())
        valid = [d for d in data if "error" not in d and "overall" in d]
        per_file[path.name] = len(valid)
        for entry in valid:
            repo = entry["repo"]
            pr_num = int(entry["pr_number"])
            key = (repo, pr_num)
            scores[key] = entry
    return scores, per_file


def main():
    # --- Step 1: Back up ---
    print(f"Backing up {CSV_PATH.name} -> {BAK_PATH.name}")
    shutil.copy2(CSV_PATH, BAK_PATH)

    # --- Step 2: Load scores ---
    scores, per_file = load_spec_scores()
    print(f"\nLoaded {len(scores)} spec-quality scores from {len(per_file)} files:")
    for fname, count in sorted(per_file.items()):
        print(f"  {fname}: {count}")

    # --- Step 3: Read CSV ---
    with open(CSV_PATH, newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    before_count = sum(1 for r in rows if r.get("q_overall", "").strip())
    print(f"\nRows with q_overall BEFORE join: {before_count}")

    # --- Step 4: Join ---
    matched = defaultdict(int)
    unmatched = defaultdict(int)
    already_had = defaultdict(int)
    newly_joined = 0

    for row in rows:
        repo = row["repo"]
        pr_num = int(row["pr_number"])
        key = (repo, pr_num)

        if key in scores:
            entry = scores[key]
            # Check if already has q_overall
            if row.get("q_overall", "").strip():
                already_had[repo] += 1
            else:
                newly_joined += 1

            # Always write (update existing + fill new)
            for json_key, csv_col in FIELD_MAP.items():
                val = entry.get(json_key, "")
                if val is not None and val != "":
                    row[csv_col] = str(val)

            matched[repo] += 1
        else:
            # Only count as unmatched if this repo HAS a spec-quality file
            pass

    # Count unmatched scores (scores in JSON that don't appear in CSV)
    csv_keys = {(r["repo"], int(r["pr_number"])) for r in rows}
    scores_not_in_csv = defaultdict(int)
    for (repo, pr_num), entry in scores.items():
        if (repo, pr_num) not in csv_keys:
            scores_not_in_csv[repo] += 1

    # --- Step 5: Write ---
    with open(CSV_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    after_count = sum(1 for r in rows if r.get("q_overall", "").strip())
    print(f"Rows with q_overall AFTER join:  {after_count}")
    print(f"Newly joined: {newly_joined}")
    print(f"Already had (updated): {sum(already_had.values())}")

    # Per-repo breakdown
    all_repos = sorted(set(list(matched.keys()) + list(scores_not_in_csv.keys())))
    print(f"\nPer-repo breakdown:")
    print(f"  {'Repo':<35s} {'Matched':>8s} {'Already':>8s} {'Not in CSV':>10s}")
    print(f"  {'-'*35} {'-'*8} {'-'*8} {'-'*10}")
    for repo in all_repos:
        m = matched.get(repo, 0)
        a = already_had.get(repo, 0)
        u = scores_not_in_csv.get(repo, 0)
        print(f"  {repo:<35s} {m:>8d} {a:>8d} {u:>10d}")

    if scores_not_in_csv:
        print(f"\n  NOTE: {sum(scores_not_in_csv.values())} scored specs had no matching row in master-prs.csv")
        print(f"  (different time window, filtered out, etc.)")

    # --- Step 6: Paradox analysis ---
    print("\n" + "=" * 70)
    print("QUALITY TIER PARADOX ANALYSIS")
    print("=" * 70)

    scored = [r for r in rows if r.get("q_overall", "").strip()]
    # Also require reworked and strict_escaped to be present
    scored = [r for r in scored if r.get("reworked", "").strip() and r.get("strict_escaped", "").strip()]

    def tier(q):
        return quality_tier(float(q))

    tier_data = defaultdict(list)
    for r in scored:
        t = tier(r["q_overall"])
        tier_data[t].append(r)

    print(f"\n{'Tier':<26s} {'N':>6s} {'Reworked%':>10s} {'Escaped%':>10s}")
    print(f"{'-'*26} {'-'*6} {'-'*10} {'-'*10}")
    for t in TIER_ORDER:
        group = tier_data[t]
        n = len(group)
        reworked = sum(1 for r in group if r["reworked"].strip().lower() in ("true", "1", "yes"))
        escaped = sum(1 for r in group if r["strict_escaped"].strip().lower() in ("true", "1", "yes"))
        rw_pct = 100 * reworked / n if n else 0
        es_pct = 100 * escaped / n if n else 0
        print(f"{TIER_DISPLAY[t]:<26s} {n:>6d} {rw_pct:>9.1f}% {es_pct:>9.1f}%")

    # Fisher's exact: top decile vs bottom 75%
    print("\nFisher's exact test (TOP10 vs BOTTOM75):")
    for outcome_col, label in [("reworked", "Reworked"), ("strict_escaped", "Escaped")]:
        high = tier_data[TOP_10]
        low = tier_data[BOTTOM_75]
        if not high or not low:
            print(f"  {label}: insufficient data")
            continue

        def count_true(group, col):
            return sum(1 for r in group if r[col].strip().lower() in ("true", "1", "yes"))

        h_yes = count_true(high, outcome_col)
        h_no = len(high) - h_yes
        l_yes = count_true(low, outcome_col)
        l_no = len(low) - l_yes

        table = [[h_yes, h_no], [l_yes, l_no]]
        odds, p = stats.fisher_exact(table)
        print(f"  {label}: TOP10 {h_yes}/{len(high)} vs BOTTOM75 {l_yes}/{len(low)}, OR={odds:.3f}, p={p:.4f}")

    # Repo distribution across tiers
    print(f"\nRepo distribution across tiers:")
    repo_tiers = defaultdict(lambda: defaultdict(int))
    for r in scored:
        t = tier(r["q_overall"])
        repo_tiers[r["repo"]][t] += 1

    print(f"  {'Repo':<35s} {'<58':>6s} {'58-65':>6s} {'66+':>6s} {'Total':>6s}")
    print(f"  {'-'*35} {'-'*6} {'-'*6} {'-'*6} {'-'*6}")
    for repo in sorted(repo_tiers.keys()):
        tiers_d = repo_tiers[repo]
        total = sum(tiers_d.values())
        print(f"  {repo:<35s} {tiers_d[BOTTOM_75]:>6d} {tiers_d[TOP_25_ONLY]:>6d} {tiers_d[TOP_10]:>6d} {total:>6d}")


if __name__ == "__main__":
    main()
