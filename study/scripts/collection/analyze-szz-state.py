#!/usr/bin/env python3
"""Analyze SZZ/JIT state for each repo and output a plan."""

import json
import sys
from pathlib import Path

repos_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("/tmp/szz-repos")
study_dir = Path(__file__).resolve().parent.parent.parent

ALL_REPOS = [
    "Aider-AI/aider", "getmaxun/maxun", "liam-hq/liam", "nestjs/nest",
    "nats-io/nats-server", "containerd/containerd", "etcd-io/etcd",
    "nocodb/nocodb", "langflow-ai/langflow", "qdrant/qdrant",
    "haskell/cabal", "quarkusio/quarkus", "godotengine/godot",
    "cockroachdb/cockroach", "ClickHouse/ClickHouse", "rust-lang/rust",
]

# Load all checkpoints
all_szz_repos = set()
all_jit_repos = set()
all_szz_results = {}

for cp_file in sorted(study_dir.glob("data/szz-checkpoint-b*.json")):
    cp = json.load(open(cp_file))
    for repo in cp.get("completed_repos", []):
        all_szz_repos.add(repo)
    for repo in cp.get("jit_completed_repos", []):
        all_jit_repos.add(repo)
    for r in cp.get("all_results", []):
        repo = r.get("repo", "")
        all_szz_results[repo] = all_szz_results.get(repo, 0) + 1

needs_szz = []
needs_jit = []
needs_both = []

for repo in ALL_REPOS:
    szz_has_results = repo in all_szz_repos and all_szz_results.get(repo, 0) > 0
    szz_ran_zero = repo in all_szz_repos and all_szz_results.get(repo, 0) == 0
    jit_done = repo in all_jit_repos

    repo_dir = repos_dir / repo
    clone_exists = (repo_dir / ".git").exists()
    is_shallow = (repo_dir / ".git" / "shallow").exists() if clone_exists else False

    if szz_has_results and jit_done:
        status = "SKIP"
    elif szz_ran_zero and jit_done:
        status = "SZZ-only"
        needs_szz.append(repo)
    elif szz_has_results and not jit_done:
        status = "JIT-only"
        needs_jit.append(repo)
    else:
        status = "BOTH"
        needs_both.append(repo)

    tags = []
    if is_shallow:
        tags.append("SHALLOW")
    if not clone_exists:
        tags.append("NO_CLONE")
    tag_str = " [" + ", ".join(tags) + "]" if tags else ""
    szz_str = f" (szz={all_szz_results.get(repo, 0)} links)" if repo in all_szz_repos else ""

    print(f"STATUS {repo}: {status}{tag_str}{szz_str}")

print(f"NEEDS_SZZ {' '.join(needs_szz)}")
print(f"NEEDS_JIT {' '.join(needs_jit)}")
print(f"NEEDS_BOTH {' '.join(needs_both)}")
