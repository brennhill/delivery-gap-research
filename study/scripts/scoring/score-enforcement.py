#!/usr/bin/env python3
"""Score enforcement depth for each repo by parsing hook configs.

Maps to the Quality Gate Tiers from Chapter 7:
  Tier 0: Static analysis (formatting, linting, type checking)
  Tier 1: Contract gates (schema validation, API contracts)
  Tier 2: Invariant gates (tests, business rules)
  Tier 3: Policy gates (security scanning, secret detection, permissions)
  Tier 4: Behavioral gates (not detectable from config files)

Detects enforcement from:
  - .pre-commit-config.yaml (Python ecosystem)
  - .husky/ hooks (JS/TS ecosystem)
  - .github/workflows/ CI configs (all ecosystems)

Output: data/enforcement-scores.json

Usage:
    python score-enforcement.py
    python score-enforcement.py --repo django/django
"""

import base64
import json
import re
import subprocess
import sys
import time
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"

# All repos (existing 43 + new candidates)
REPOS = [
    # Existing 43
    "PostHog/posthog", "anthropics/anthropic-cookbook", "antiwork/gumroad",
    "apache/arrow", "apache/kafka", "astral-sh/ruff", "biomejs/biome",
    "calcom/cal.com", "clerkinc/javascript", "cli/cli",
    "cockroachdb/cockroach", "continuedev/continue", "denoland/deno",
    "django/django", "dotnet/aspire", "elastic/elasticsearch",
    "envoyproxy/envoy", "facebook/react", "grafana/grafana",
    "huggingface/transformers", "kubernetes/kubernetes",
    "langchain-ai/langchain", "liam-hq/liam", "lobehub/lobe-chat",
    "mendableai/firecrawl", "microsoft/vscode", "mlflow/mlflow",
    "n8n-io/n8n", "nats-io/nats-server", "novuhq/novu",
    "oven-sh/bun", "pingcap/tidb", "pnpm/pnpm",
    "prometheus/prometheus", "promptfoo/promptfoo", "python/cpython",
    "rust-lang/rust", "supabase/supabase", "sveltejs/svelte",
    "tailwindlabs/tailwindcss", "temporalio/temporal",
    "traefik/traefik", "vercel/next.js",
    # New candidates with pre-commit
    "pallets/flask", "fastapi/fastapi", "pydantic/pydantic",
    "celery/celery", "pytest-dev/pytest", "apache/airflow",
    "dagster-io/dagster", "prefecthq/prefect", "dbt-labs/dbt-core",
    "sqlalchemy/sqlalchemy", "open-webui/open-webui",
    "langflow-ai/langflow", "chroma-core/chroma", "weaviate/weaviate",
    "vllm-project/vllm", "ray-project/ray",
    # New candidates without pre-commit
    "redis/redis", "clickhouse/clickhouse", "vitessio/vitess",
    "etcd-io/etcd", "tikv/tikv", "rails/rails",
    "nestjs/nest", "vitejs/vite", "hashicorp/terraform",
    "hashicorp/vault", "ollama/ollama", "flutter/flutter",
    "strapi/strapi", "nocodb/nocodb", "minio/minio",
]

# === TIER 0: Static Analysis (formatting, linting, type checking) ===
TIER0_PATTERNS = {
    # Formatters
    "black": "formatter",
    "prettier": "formatter",
    "gofmt": "formatter",
    "rustfmt": "formatter",
    "isort": "formatter",
    "autopep8": "formatter",
    "yapf": "formatter",
    "dart_format": "formatter",
    "clang-format": "formatter",
    "biome": "formatter",
    # Linters
    "flake8": "linter",
    "pylint": "linter",
    "ruff": "linter",
    "eslint": "linter",
    "golangci-lint": "linter",
    "clippy": "linter",
    "rubocop": "linter",
    "stylelint": "linter",
    "shellcheck": "linter",
    "hadolint": "linter",
    "markdownlint": "linter",
    "yamllint": "linter",
    "actionlint": "linter",
    "biome.*lint": "linter",
    "oxlint": "linter",
    "lint-staged": "linter",
    "lint": "linter",
    # Type checkers
    "mypy": "type_checker",
    "pyright": "type_checker",
    "tsc": "type_checker",
    "typescript": "type_checker",
    "typecheck": "type_checker",
    "type-check": "type_checker",
}

# === TIER 1: Contract Gates (schema, API contracts) ===
TIER1_PATTERNS = {
    "openapi": "api_contract",
    "swagger": "api_contract",
    "graphql.*schema": "api_contract",
    "protobuf": "api_contract",
    "proto.*lint": "api_contract",
    "buf": "api_contract",
    "json.*schema": "schema_validation",
    "avro": "schema_validation",
    "pact": "contract_test",
}

# === TIER 2: Invariant Gates (tests, business rules) ===
TIER2_PATTERNS = {
    "pytest": "test",
    "jest": "test",
    "vitest": "test",
    "mocha": "test",
    "go test": "test",
    "cargo test": "test",
    "unittest": "test",
    "test": "test",
    "spec": "test",
    "check": "test",
    "verify": "test",
    "coverage": "coverage",
    "codecov": "coverage",
    "coveralls": "coverage",
    "nyc": "coverage",
    "istanbul": "coverage",
    "c8": "coverage",
}

# === TIER 3: Policy Gates (security, secrets, compliance) ===
TIER3_PATTERNS = {
    "detect-secrets": "secret_detection",
    "gitleaks": "secret_detection",
    "trufflehog": "secret_detection",
    "secret": "secret_detection",
    "bandit": "security_scan",
    "safety": "security_scan",
    "snyk": "security_scan",
    "dependabot": "dependency_audit",
    "renovate": "dependency_audit",
    "audit": "security_scan",
    "codeql": "security_scan",
    "semgrep": "security_scan",
    "trivy": "security_scan",
    "owasp": "security_scan",
    "license": "compliance",
    "sbom": "compliance",
}


def gh_api_content(repo, path):
    """Fetch file content from GitHub API."""
    r = subprocess.run(
        ["gh", "api", f"repos/{repo}/contents/{path}", "--jq", ".content"],
        capture_output=True, text=True, timeout=15,
    )
    if r.returncode != 0:
        return None
    try:
        return base64.b64decode(r.stdout.strip()).decode("utf-8", errors="replace")
    except Exception:
        return None


def gh_api_list(repo, path):
    """List directory contents from GitHub API."""
    r = subprocess.run(
        ["gh", "api", f"repos/{repo}/contents/{path}", "--jq", ".[].name"],
        capture_output=True, text=True, timeout=15,
    )
    if r.returncode != 0:
        return []
    return [name.strip() for name in r.stdout.strip().split("\n") if name.strip()]


def score_text(text, patterns):
    """Score text against tier patterns. Returns set of matched categories."""
    text_lower = text.lower()
    matches = set()
    for pattern, category in patterns.items():
        if re.search(pattern, text_lower):
            matches.add(category)
    return matches


def score_repo(repo):
    """Score enforcement depth for a single repo."""
    print(f"  Scanning {repo}...", flush=True)

    result = {
        "repo": repo,
        "hooks": {},
        "enforcement_sources": [],
    }

    all_text = ""

    # 1. Check .pre-commit-config.yaml
    content = gh_api_content(repo, ".pre-commit-config.yaml")
    if content:
        result["hooks"]["pre_commit"] = True
        result["enforcement_sources"].append("pre-commit")
        all_text += content + "\n"
    else:
        result["hooks"]["pre_commit"] = False

    # 2. Check .husky/ directory
    husky_hooks = gh_api_list(repo, ".husky")
    if husky_hooks:
        result["hooks"]["husky"] = True
        result["enforcement_sources"].append("husky")
        for hook in husky_hooks:
            if hook.startswith("."):
                continue
            content = gh_api_content(repo, f".husky/{hook}")
            if content:
                all_text += content + "\n"
    else:
        result["hooks"]["husky"] = False

    # 3. Check CI workflows (sample first 10)
    workflows = gh_api_list(repo, ".github/workflows")
    result["hooks"]["ci_workflow_count"] = len(workflows)
    ci_text = ""
    for wf in workflows[:10]:
        content = gh_api_content(repo, f".github/workflows/{wf}")
        if content:
            ci_text += content + "\n"

    # 4. Check for Makefile / justfile (often contains check targets)
    for build_file in ["Makefile", "justfile", "Taskfile.yml"]:
        content = gh_api_content(repo, build_file)
        if content:
            all_text += content + "\n"

    # Score enforcement hooks (pre-commit + husky)
    hook_tier0 = score_text(all_text, TIER0_PATTERNS)
    hook_tier1 = score_text(all_text, TIER1_PATTERNS)
    hook_tier2 = score_text(all_text, TIER2_PATTERNS)
    hook_tier3 = score_text(all_text, TIER3_PATTERNS)

    # Score CI (separate — CI is not enforcement in the same way)
    ci_tier0 = score_text(ci_text, TIER0_PATTERNS)
    ci_tier1 = score_text(ci_text, TIER1_PATTERNS)
    ci_tier2 = score_text(ci_text, TIER2_PATTERNS)
    ci_tier3 = score_text(ci_text, TIER3_PATTERNS)

    # Enforcement = hooks (runs before commit, can't skip)
    # CI = verification (runs after push, can be advisory)
    result["enforcement"] = {
        "tier0": sorted(hook_tier0),
        "tier1": sorted(hook_tier1),
        "tier2": sorted(hook_tier2),
        "tier3": sorted(hook_tier3),
    }
    result["ci"] = {
        "tier0": sorted(ci_tier0),
        "tier1": sorted(ci_tier1),
        "tier2": sorted(ci_tier2),
        "tier3": sorted(ci_tier3),
    }

    # Compute scores
    result["enforcement_depth"] = (
        len(hook_tier0) + len(hook_tier1) * 2 + len(hook_tier2) * 3 + len(hook_tier3) * 4
    )
    result["enforcement_tier_count"] = sum(1 for t in [hook_tier0, hook_tier1, hook_tier2, hook_tier3] if t)
    result["ci_depth"] = (
        len(ci_tier0) + len(ci_tier1) * 2 + len(ci_tier2) * 3 + len(ci_tier3) * 4
    )
    result["ci_tier_count"] = sum(1 for t in [ci_tier0, ci_tier1, ci_tier2, ci_tier3] if t)
    result["total_depth"] = result["enforcement_depth"] + result["ci_depth"]
    result["total_tier_count"] = len(
        set(
            (["t0"] if (hook_tier0 or ci_tier0) else [])
            + (["t1"] if (hook_tier1 or ci_tier1) else [])
            + (["t2"] if (hook_tier2 or ci_tier2) else [])
            + (["t3"] if (hook_tier3 or ci_tier3) else [])
        )
    )

    # Convert sets to lists for JSON
    for tier_dict in [result["enforcement"], result["ci"]]:
        for k in tier_dict:
            tier_dict[k] = sorted(tier_dict[k]) if isinstance(tier_dict[k], set) else tier_dict[k]

    time.sleep(0.3)
    return result


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", help="Score a single repo")
    args = parser.parse_args()

    repos = [args.repo] if args.repo else REPOS
    out_path = DATA_DIR / "enforcement-scores.json"

    # Load existing
    existing = {}
    if out_path.exists():
        try:
            with open(out_path) as f:
                for item in json.load(f):
                    existing[item["repo"]] = item
        except Exception:
            pass

    for i, repo in enumerate(repos):
        if repo in existing and not args.repo:
            continue
        print(f"[{i+1}/{len(repos)}] {repo}:", flush=True)
        try:
            result = score_repo(repo)
            existing[repo] = result
            print(f"  enforcement_depth={result['enforcement_depth']} "
                  f"ci_depth={result['ci_depth']} "
                  f"tiers={result['total_tier_count']}/4 "
                  f"sources={result['enforcement_sources']}", flush=True)
        except Exception as e:
            print(f"  ERROR: {e}", flush=True)

        # Save after every repo
        tmp = out_path.with_suffix(".json.tmp")
        all_results = sorted(existing.values(), key=lambda x: x["repo"])
        tmp.write_text(json.dumps(all_results, indent=2))
        tmp.replace(out_path)

    # Summary
    print(f"\n{'='*70}")
    print(f"ENFORCEMENT SCORING SUMMARY ({len(existing)} repos)")
    print(f"{'='*70}\n")

    print(f"{'Repo':<40} {'Enf':>4} {'CI':>4} {'Tiers':>5} {'Sources':<20}")
    print("-" * 80)
    for r in sorted(existing.values(), key=lambda x: x["enforcement_depth"], reverse=True):
        print(f"{r['repo']:<40} {r['enforcement_depth']:>4} {r['ci_depth']:>4} "
              f"{r['total_tier_count']:>5}/4 {','.join(r['enforcement_sources']):<20}")


if __name__ == "__main__":
    main()
