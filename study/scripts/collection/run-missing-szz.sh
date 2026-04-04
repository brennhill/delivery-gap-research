#!/bin/bash
set -e

# Run SZZ + JIT on the 19 repos missing from batches b1-b9.
# Each repo runs independently with --repo flag.
# All results go into batch b10 checkpoint.

STUDY_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
REPOS_DIR="/tmp/szz-repos"
SCRIPT="$STUDY_DIR/scripts/collection/szz-score.py"

MISSING_REPOS=(
    "Aider-AI/aider"
    "BerriAI/litellm"
    "ClickHouse/ClickHouse"
    "apache/spark"
    "cockroachdb/cockroach"
    "containerd/containerd"
    "etcd-io/etcd"
    "getmaxun/maxun"
    "godotengine/godot"
    "haskell/cabal"
    "langflow-ai/langflow"
    "liam-hq/liam"
    "lm-sys/FastChat"
    "nats-io/nats-server"
    "nestjs/nest"
    "nocodb/nocodb"
    "qdrant/qdrant"
    "quarkusio/quarkus"
    "rust-lang/rust"
)

echo "Running SZZ on ${#MISSING_REPOS[@]} missing repos"
echo "Repos dir: $REPOS_DIR"
echo "Batch: b10"
echo ""

for repo in "${MISSING_REPOS[@]}"; do
    echo "=========================================="
    echo "Processing: $repo"
    echo "=========================================="
    python3 "$SCRIPT" \
        --repos-dir "$REPOS_DIR" \
        --clone \
        --batch-id b10 \
        --repo "$repo" \
        2>&1 || echo "FAILED: $repo (continuing...)"
    echo ""
done

echo "=========================================="
echo "DONE — all 19 repos attempted"
echo "=========================================="
echo "Checkpoint: $STUDY_DIR/data/szz-checkpoint-b10.json"
