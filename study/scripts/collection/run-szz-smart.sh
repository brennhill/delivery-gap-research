#!/bin/bash
set -e

# Smart SZZ/JIT runner. Figures out what each repo needs and runs accordingly.
#
# Usage:
#   bash run-szz-smart.sh              # run everything needed
#   bash run-szz-smart.sh --dry-run    # show plan without executing

STUDY_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
REPOS_DIR="/tmp/szz-repos"
SCRIPT="$STUDY_DIR/scripts/collection/szz-score.py"
ANALYZE="$STUDY_DIR/scripts/collection/analyze-szz-state.py"
BATCH_ID="b12"
DRY_RUN=false
MAX_PARALLEL=3

[ "$1" = "--dry-run" ] && DRY_RUN=true

echo "Smart SZZ/JIT runner"
echo "  Study dir: $STUDY_DIR"
echo "  Repos dir: $REPOS_DIR"
echo "  Batch: $BATCH_ID"
echo ""

# ── Step 1: Analyze state ─────────────────────────────────────────────────

cd "$STUDY_DIR"
ANALYSIS=$(python3 "$ANALYZE" "$REPOS_DIR" 2>&1)

echo "$ANALYSIS" | grep "^STATUS"
echo ""

NEEDS_SZZ=$(echo "$ANALYSIS" | grep "^NEEDS_SZZ" | sed 's/^NEEDS_SZZ //')
NEEDS_JIT=$(echo "$ANALYSIS" | grep "^NEEDS_JIT" | sed 's/^NEEDS_JIT //')
NEEDS_BOTH=$(echo "$ANALYSIS" | grep "^NEEDS_BOTH" | sed 's/^NEEDS_BOTH //')

echo "Plan:"
[ -n "$NEEDS_SZZ" ] && echo "  SZZ retry:        $NEEDS_SZZ"
[ -n "$NEEDS_JIT" ] && echo "  JIT only:         $NEEDS_JIT"
[ -n "$NEEDS_BOTH" ] && echo "  Both SZZ + JIT:   $NEEDS_BOTH"
[ -z "$NEEDS_SZZ$NEEDS_JIT$NEEDS_BOTH" ] && echo "  Nothing to do!" && exit 0
echo ""

[ "$DRY_RUN" = true ] && echo "[DRY RUN] Would proceed with the above plan." && exit 0

# ── Step 2: Unshallow clones that need SZZ ─────────────────────────────────

echo "Unshallowing clones that need SZZ..."
for repo in $NEEDS_SZZ $NEEDS_BOTH; do
    repo_dir="$REPOS_DIR/$repo"
    if [ -f "$repo_dir/.git/shallow" ]; then
        echo "  Unshallowing: $repo"
        git -C "$repo_dir" fetch --unshallow 2>&1 | tail -1 || echo "  WARNING: failed for $repo"
    fi
done
echo ""

# ── Step 3: Clear stale zero-result SZZ entries ───────────────────────────

CHECKPOINT="$STUDY_DIR/data/szz-checkpoint-${BATCH_ID}.json"
if [ -f "$CHECKPOINT" ] && [ -n "$NEEDS_SZZ$NEEDS_BOTH" ]; then
    echo "Clearing stale SZZ entries for retry repos..."
    python3 - "$CHECKPOINT" "$NEEDS_SZZ $NEEDS_BOTH" <<'PYEOF'
import json, sys
cp_file, retry_str = sys.argv[1], sys.argv[2]
cp = json.load(open(cp_file))
retry = set(retry_str.split())
retry.discard("")
cp["completed_repos"] = [r for r in cp.get("completed_repos", []) if r not in retry]
cp["all_results"] = [r for r in cp.get("all_results", []) if r.get("repo") not in retry]
json.dump(cp, open(cp_file, "w"), indent=2)
print(f"  Cleared {len(retry)} repos from SZZ completed list")
PYEOF
    echo ""
fi

# ── Step 4: Run ───────────────────────────────────────────────────────────

run_repo() {
    local repo=$1
    local mode=$2
    local flags="--repos-dir $REPOS_DIR --clone --batch-id $BATCH_ID --repo $repo"

    case $mode in
        szz-only)  flags="$flags --skip-jit" ;;
        jit-only)  flags="$flags --jit-only" ;;
    esac

    echo "=== [$mode] $repo ==="
    python3 "$SCRIPT" $flags 2>&1 || echo "FAILED: $repo (continuing...)"
}

# JIT-only repos can run in parallel (independent, no shared SZZ state)
if [ -n "$NEEDS_JIT" ]; then
    echo "Running JIT-only repos (parallel, max $MAX_PARALLEL)..."
    pids=()
    for repo in $NEEDS_JIT; do
        run_repo "$repo" "jit-only" &
        pids+=($!)
        if [ ${#pids[@]} -ge $MAX_PARALLEL ]; then
            wait "${pids[0]}" || true
            pids=("${pids[@]:1}")
        fi
    done
    for pid in "${pids[@]}"; do wait "$pid" || true; done
    echo ""
fi

# SZZ repos must be sequential (shared checkpoint)
if [ -n "$NEEDS_SZZ" ]; then
    echo "Running SZZ-retry repos (sequential)..."
    for repo in $NEEDS_SZZ; do
        run_repo "$repo" "szz-only"
    done
    echo ""
fi

# Both-needed repos sequential
if [ -n "$NEEDS_BOTH" ]; then
    echo "Running SZZ+JIT repos (sequential)..."
    for repo in $NEEDS_BOTH; do
        run_repo "$repo" "both"
    done
    echo ""
fi

echo "=========================================="
echo "DONE"
echo "=========================================="
echo "Next: bash scripts/pipeline/run-all-analysis.sh"
