#!/bin/bash
set -e

# Run the full analysis pipeline.
# Run from the study root: bash scripts/pipeline/run-all-analysis.sh
#
# Source data (never modified):
#   data/prs-*.json           — raw PR data per repo
#   data/szz-checkpoint-b*.json — SZZ/JIT checkpoints per batch
#   data/*-scores.json        — scorer outputs
#
# Derived data (regenerated each run):
#   data/unified-prs.csv      — all PRs from JSON files
#   data/master-prs.csv       — unified + scores + features
#   data/szz-results-merged.csv — merged SZZ from checkpoints
#   data/jit-features-merged.csv — merged JIT from checkpoints
#
# Analysis outputs:
#   results/analysis-results.txt     — main analysis report
#   results/robustness-subgroups.txt — subgroup robustness checks

STUDY_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$STUDY_DIR"

echo "Study dir: $STUDY_DIR"

echo ""
echo "=========================================="
echo "Step 1/9: Merge SZZ/JIT checkpoints"
echo "=========================================="
python3 -c "
import json, pandas as pd
from pathlib import Path

data_dir = Path('data')
all_szz, all_jit, all_repos = [], [], set()

for cp_file in sorted(data_dir.glob('szz-checkpoint-b*.json')):
    cp = json.load(open(cp_file))
    batch = cp_file.stem.replace('szz-checkpoint-', '')
    n_repos = len(cp.get('completed_repos', []))
    n_szz = len(cp.get('all_results', []))
    n_jit = len(cp.get('all_jit_results', []))
    all_szz.extend(cp.get('all_results', []))
    all_jit.extend(cp.get('all_jit_results', []))
    all_repos.update(cp.get('completed_repos', []))
    print(f'  {batch}: {n_repos} repos, {n_szz} SZZ, {n_jit} JIT')

print(f'Total: {len(all_repos)} repos, {len(all_szz)} SZZ, {len(all_jit)} JIT')

szz_df = pd.DataFrame(all_szz)
if len(szz_df) > 0:
    szz_df = szz_df.drop_duplicates(subset=['repo', 'fix_pr_number', 'bug_commit_sha', 'file'], keep='last')
    szz_df.to_csv('data/szz-results-merged.csv', index=False)
    print(f'SZZ merged: {len(szz_df)} rows, {szz_df[\"repo\"].nunique()} repos')

jit_df = pd.DataFrame(all_jit)
if len(jit_df) > 0:
    jit_df = jit_df.drop_duplicates(subset=['repo', 'pr_number'], keep='last')
    jit_df.to_csv('data/jit-features-merged.csv', index=False)
    print(f'JIT merged: {len(jit_df)} rows, {jit_df[\"repo\"].nunique()} repos')
"

echo ""
echo "=========================================="
echo "Step 2/9: Build unified CSV"
echo "=========================================="
python3 scripts/pipeline/build-unified-csv.py

echo ""
echo "=========================================="
echo "Step 3/9: Build master CSV"
echo "=========================================="
python3 scripts/pipeline/build-master-csv.py

echo ""
echo "=========================================="
echo "Step 4/9: Run main analysis"
echo "=========================================="
python3 scripts/pipeline/full-szz-analysis.py

echo ""
echo "=========================================="
echo "Step 5/9: Run subgroup robustness"
echo "=========================================="
python3 scripts/pipeline/robustness-subgroups.py

echo ""
echo "=========================================="
echo "Step 6/9: Run high-quality spec robustness"
echo "=========================================="
python3 scripts/pipeline/robustness-highquality.py

echo ""
echo "=========================================="
echo "Step 7/9: Run temporal robustness"
echo "=========================================="
python3 scripts/pipeline/robustness-temporal.py

echo ""
echo "=========================================="
echo "Step 8/9: Run complexity stratification"
echo "=========================================="
python3 scripts/pipeline/robustness-complexity.py

echo ""
echo "=========================================="
echo "Step 9/9: Run JIT controls + PSM"
echo "=========================================="
python3 scripts/pipeline/primary-with-jit-controls.py
python3 scripts/pipeline/propensity-score-matching.py

echo ""
echo "=========================================="
echo "DONE"
echo "=========================================="
echo "Results:"
echo "  results/analysis-results.txt"
echo "  results/robustness-subgroups.txt"
echo "  results/robustness-highquality.txt"
echo "  results/robustness-temporal.txt"
echo "  results/robustness-complexity.txt"
echo "  results/propensity-score-matching.txt"
echo ""
echo "Source data untouched:"
echo "  prs-*.json: $(ls data/prs-*.json 2>/dev/null | wc -l | tr -d ' ') files"
echo "  szz-checkpoint-b*.json: $(ls data/szz-checkpoint-b*.json 2>/dev/null | wc -l | tr -d ' ') files"
