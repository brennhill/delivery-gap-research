#!/usr/bin/env python3
"""Fetch PR data for 56 new repos (expanding study from 43 to 99).

This uses the same pipeline as runner.py but only fetches + runs CatchRate.
LLM scoring is deferred to score_all.py (run separately).

Usage:
    python fetch-new-repos.py                    # fetch all 56
    python fetch-new-repos.py --repo rails/rails  # fetch one
    python fetch-new-repos.py --dry-run           # show what would run
    python fetch-new-repos.py --batch strong      # only strong-enforcement repos
    python fetch-new-repos.py --batch weak        # only weak-enforcement repos
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

STUDY_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(STUDY_DIR))

from runner import run_all, DATA_DIR

# ── 56 new repos ────────────────────────────────────────────────────────
# Batch 1: 36 repos (verified 2026-03-26, all ≥200 merged PRs/yr)
# Batch 2: 20 repos (verified 2026-03-26, all ≥200 merged PRs/yr)

NEW_REPOS: list[dict[str, str]] = [
    # === STRONG ENFORCEMENT (expected) ===
    # Data engineering
    {"repo": "apache/airflow",           "lang": "Python",       "tier": "new-strong"},
    {"repo": "dagster-io/dagster",       "lang": "Python",       "tier": "new-strong"},
    {"repo": "prefecthq/prefect",        "lang": "Python",       "tier": "new-strong"},
    {"repo": "dbt-labs/dbt-core",        "lang": "Python",       "tier": "new-strong"},
    {"repo": "apache/flink",             "lang": "Java",         "tier": "new-strong"},
    # Databases
    {"repo": "ClickHouse/ClickHouse",    "lang": "C++",          "tier": "new-strong"},
    {"repo": "weaviate/weaviate",        "lang": "Go",           "tier": "new-strong"},
    {"repo": "vitessio/vitess",          "lang": "Go",           "tier": "new-strong"},
    {"repo": "etcd-io/etcd",             "lang": "Go",           "tier": "new-strong"},
    {"repo": "tikv/tikv",                "lang": "Rust",         "tier": "new-strong"},
    # Security / IaC
    {"repo": "hashicorp/vault",          "lang": "Go",           "tier": "new-strong"},
    {"repo": "hashicorp/terraform",      "lang": "Go",           "tier": "new-strong"},
    # Runtimes / frameworks
    {"repo": "rails/rails",              "lang": "Ruby",         "tier": "new-strong"},
    {"repo": "dotnet/runtime",           "lang": "C#",           "tier": "new-strong"},
    {"repo": "dotnet/maui",              "lang": "C#",           "tier": "new-strong"},
    {"repo": "quarkusio/quarkus",        "lang": "Java",         "tier": "new-strong"},
    {"repo": "containerd/containerd",    "lang": "Go",           "tier": "new-strong"},
    # Python ecosystem
    {"repo": "pydantic/pydantic",        "lang": "Python",       "tier": "new-strong"},
    {"repo": "pytest-dev/pytest",        "lang": "Python",       "tier": "new-strong"},
    {"repo": "celery/celery",            "lang": "Python",       "tier": "new-strong"},
    # ML / distributed
    {"repo": "ray-project/ray",          "lang": "Python",       "tier": "new-strong"},
    # Mobile
    {"repo": "flutter/flutter",          "lang": "Dart",         "tier": "new-strong"},
    # Rust systems
    {"repo": "tokio-rs/tokio",           "lang": "Rust",         "tier": "new-strong"},
    {"repo": "oxc-project/oxc",          "lang": "Rust",         "tier": "new-strong"},
    # Embedded / IoT
    {"repo": "zephyrproject-rtos/zephyr","lang": "C",            "tier": "new-strong"},
    {"repo": "home-assistant/core",      "lang": "Python",       "tier": "new-strong"},
    # Healthcare
    {"repo": "medplum/medplum",          "lang": "TypeScript",   "tier": "new-strong"},
    {"repo": "openmrs/openmrs-core",     "lang": "Java",         "tier": "new-strong"},
    # Fintech
    {"repo": "juspay/hyperswitch",       "lang": "Rust",         "tier": "new-strong"},
    {"repo": "stripe/stripe-ios",        "lang": "Swift",        "tier": "new-strong"},
    # CLI / shell
    {"repo": "PowerShell/PowerShell",    "lang": "C#",           "tier": "new-strong"},
    # Compilers / languages
    {"repo": "elixir-lang/elixir",       "lang": "Elixir",       "tier": "new-strong"},
    # Gaming
    {"repo": "godotengine/godot",        "lang": "C++",          "tier": "new-strong"},

    # === WEAK / UNKNOWN ENFORCEMENT (expected) ===
    # AI-native
    {"repo": "vllm-project/vllm",        "lang": "Python/CUDA",  "tier": "new-weak"},
    {"repo": "vercel/ai",                "lang": "TypeScript",   "tier": "new-weak"},
    {"repo": "langflow-ai/langflow",     "lang": "Python/TS",    "tier": "new-weak"},
    {"repo": "open-webui/open-webui",    "lang": "TypeScript",   "tier": "new-weak"},
    {"repo": "ollama/ollama",            "lang": "Go",           "tier": "new-weak"},
    {"repo": "streamlit/streamlit",      "lang": "Python",       "tier": "new-weak"},
    # Web / frontend
    {"repo": "vitejs/vite",              "lang": "TypeScript",   "tier": "new-weak"},
    {"repo": "shadcn-ui/ui",             "lang": "TypeScript",   "tier": "new-weak"},
    {"repo": "remix-run/remix",          "lang": "TypeScript",   "tier": "new-weak"},
    {"repo": "excalidraw/excalidraw",    "lang": "TypeScript",   "tier": "new-weak"},
    {"repo": "refinedev/refine",         "lang": "TypeScript",   "tier": "new-weak"},
    # Backend / frameworks
    {"repo": "nestjs/nest",              "lang": "TypeScript",   "tier": "new-weak"},
    {"repo": "fastapi/fastapi",          "lang": "Python",       "tier": "new-weak"},
    {"repo": "strapi/strapi",            "lang": "TypeScript",   "tier": "new-weak"},
    {"repo": "nocodb/nocodb",            "lang": "TypeScript",   "tier": "new-weak"},
    # Databases
    {"repo": "qdrant/qdrant",            "lang": "Rust",         "tier": "new-weak"},
    {"repo": "redis/redis",              "lang": "C",            "tier": "new-weak"},
    # Gaming (weak enforcement)
    {"repo": "bevyengine/bevy",          "lang": "Rust",         "tier": "new-weak"},
    # CLI (weak enforcement)
    {"repo": "nushell/nushell",          "lang": "Rust",         "tier": "new-weak"},
    # Misc
    {"repo": "getmaxun/maxun",           "lang": "TypeScript",   "tier": "new-weak"},
    {"repo": "square/okhttp",            "lang": "Kotlin",       "tier": "new-weak"},
    {"repo": "haskell/cabal",            "lang": "Haskell",      "tier": "new-weak"},
    {"repo": "phoenixframework/phoenix", "lang": "Elixir",       "tier": "new-weak"},

    # === AI-HEAVY REPOS (added for attention signal analysis) ===
    # These repos have high AI adoption and substantial PR volumes.
    # Coding assistants / AI dev tools
    {"repo": "TabbyML/tabby",            "lang": "Rust",         "tier": "new-ai"},
    {"repo": "Aider-AI/aider",           "lang": "Python",       "tier": "new-ai"},
    {"repo": "cline/cline",              "lang": "TypeScript",   "tier": "new-ai"},
    {"repo": "e2b-dev/E2B",              "lang": "TypeScript",   "tier": "new-ai"},
    # LLM frameworks / inference
    {"repo": "ggerganov/llama.cpp",      "lang": "C++",          "tier": "new-ai"},
    {"repo": "lm-sys/FastChat",          "lang": "Python",       "tier": "new-ai"},
    {"repo": "BerriAI/litellm",          "lang": "Python",       "tier": "new-ai"},
    {"repo": "run-llama/llama_index",    "lang": "Python",       "tier": "new-ai"},
    {"repo": "stanfordnlp/dspy",          "lang": "Python",       "tier": "new-ai"},
    {"repo": "crewAIInc/crewAI",         "lang": "Python",       "tier": "new-ai"},
    # AI applications
    {"repo": "danny-avila/LibreChat",    "lang": "TypeScript",   "tier": "new-ai"},
    {"repo": "QuivrHQ/quivr",            "lang": "Python/TS",    "tier": "new-ai"},
    {"repo": "all-hands-ai/OpenHands",   "lang": "Python",       "tier": "new-ai"},
    {"repo": "Mintplex-Labs/anything-llm","lang": "JavaScript",  "tier": "new-ai"},
    # Vector DBs / RAG infra
    {"repo": "chroma-core/chroma",       "lang": "Python/Rust",  "tier": "new-ai"},
    {"repo": "milvus-io/milvus",         "lang": "Go",           "tier": "new-ai"},
    {"repo": "pinecone-io/pinecone-client","lang": "Python",     "tier": "new-ai"},
    # AI-heavy but traditional domain (good contrast)
    {"repo": "Lightning-AI/pytorch-lightning","lang": "Python",   "tier": "new-ai"},
    {"repo": "apache/spark",             "lang": "Scala/Python", "tier": "new-ai"},
    {"repo": "dmlc/xgboost",             "lang": "C++/Python",   "tier": "new-ai"},
]


def main():
    parser = argparse.ArgumentParser(
        description="Fetch PR data for 56 new repos"
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--repo", help="Fetch a single repo")
    parser.add_argument("--batch", choices=["strong", "weak", "ai"],
                        help="Only fetch one enforcement batch")
    parser.add_argument("--refetch", action="store_true",
                        help="Re-fetch repos that already have data (extends to full lookback window)")
    args = parser.parse_args()

    if args.repo:
        matching = [e for e in NEW_REPOS if e["repo"] == args.repo]
        if matching:
            repos = matching
        else:
            print(f"Repo {args.repo} not in new repo list. Running anyway.")
            repos = [{"repo": args.repo, "lang": "unknown", "tier": "new-?"}]
    elif args.batch == "strong":
        repos = [r for r in NEW_REPOS if r["tier"] == "new-strong"]
        print(f"Strong enforcement batch: {len(repos)} repos")
    elif args.batch == "weak":
        repos = [r for r in NEW_REPOS if r["tier"] == "new-weak"]
        print(f"Weak enforcement batch: {len(repos)} repos")
    elif args.batch == "ai":
        repos = [r for r in NEW_REPOS if r["tier"] == "new-ai"]
        print(f"AI-heavy batch: {len(repos)} repos")
    else:
        repos = NEW_REPOS

    # Skip repos we already have data for (unless --refetch)
    if args.refetch:
        to_fetch = repos
        print(f"--refetch: will extend all repos to full lookback window")
    else:
        already = set()
        for fp in DATA_DIR.glob("prs-*.json"):
            slug = fp.stem.replace("prs-", "")
            already.add(slug)

        to_fetch = []
        skipped = []
        for r in repos:
            slug = r["repo"].replace("/", "-")
            if slug in already:
                skipped.append(r["repo"])
            else:
                to_fetch.append(r)

        if skipped:
            print(f"Skipping {len(skipped)} repos with existing data: {', '.join(skipped[:5])}{'...' if len(skipped) > 5 else ''}")
            print(f"  (use --refetch to extend these to the full lookback window)")

    if not to_fetch:
        print("All repos already fetched!")
        return

    print(f"\nFetching {len(to_fetch)} repos (fetch + CatchRate, no LLM scoring)")
    print(f"Run 'python3 score_all.py' afterward to score specs/engagement\n")

    run_all(to_fetch, dry_run=args.dry_run, fetch_only=True)


if __name__ == "__main__":
    main()
