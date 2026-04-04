#!/bin/bash
set -e

# Run SZZ + JIT on the 16 repos that failed in previous batches (clone timeouts).

STUDY_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
REPOS_DIR="/tmp/szz-repos"
SCRIPT="$STUDY_DIR/scripts/collection/szz-score.py"

MISSING_REPOS=(
    # Small/medium repos first
    "Aider-AI/aider"
    "getmaxun/maxun"
    "liam-hq/liam"
    "nestjs/nest"
    "nats-io/nats-server"
    "containerd/containerd"
    "etcd-io/etcd"
    "nocodb/nocodb"
    "langflow-ai/langflow"
    "qdrant/qdrant"
    "haskell/cabal"
    # Large repos — these may timeout on clone
    "quarkusio/quarkus"
    "godotengine/godot"
    "cockroachdb/cockroach"
    "ClickHouse/ClickHouse"
    "rust-lang/rust"
)

echo "Running SZZ on ${#MISSING_REPOS[@]} missing repos"
echo "Repos dir: $REPOS_DIR"
echo "Batch: b11"
echo ""

for repo in "${MISSING_REPOS[@]}"; do
    echo "=========================================="
    echo "Processing: $repo"
    echo "=========================================="
    python3 "$SCRIPT" \
        --repos-dir "$REPOS_DIR" \
        --clone \
        --batch-id b11 \
        --repo "$repo" \
        2>&1 || echo "FAILED: $repo (continuing...)"
    echo ""
done

echo "=========================================="
echo "DONE — all ${#MISSING_REPOS[@]} repos attempted"
echo "=========================================="
echo "Checkpoint: $STUDY_DIR/data/szz-checkpoint-b11.json"
