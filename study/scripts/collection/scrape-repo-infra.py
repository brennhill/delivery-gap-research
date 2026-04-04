#!/usr/bin/env python3
"""Scrape repo-level infrastructure signals from GitHub API.

Detects CODEOWNERS, workflow files, branch protection, linter configs,
test frameworks, contributing guides, and AI context files for all 43 repos.

Output: data/repo-infra.json

Usage:
    python scrape-repo-infra.py
    python scrape-repo-infra.py --repo pingcap/tidb
"""

import json
import subprocess
import time
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"

# All repos from the study
REPOS = [
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
]


def gh_api(endpoint: str, jq: str = ".") -> tuple[bool, str]:
    """Call GitHub API via gh CLI. Returns (success, output)."""
    try:
        result = subprocess.run(
            ["gh", "api", endpoint, "--jq", jq],
            capture_output=True, text=True, timeout=15,
        )
        return result.returncode == 0, result.stdout.strip()
    except Exception as e:
        return False, str(e)


def check_file_exists(repo: str, path: str) -> bool:
    """Check if a file exists in the repo."""
    ok, _ = gh_api(f"repos/{repo}/contents/{path}", ".name")
    return ok


def scrape_repo(repo: str) -> dict:
    """Scrape all detectable infrastructure signals for a repo."""
    print(f"  Scanning {repo}...", flush=True)
    signals = {"repo": repo}

    # CODEOWNERS
    signals["has_codeowners"] = (
        check_file_exists(repo, "CODEOWNERS")
        or check_file_exists(repo, ".github/CODEOWNERS")
        or check_file_exists(repo, "docs/CODEOWNERS")
    )

    # Workflow count
    ok, out = gh_api(f"repos/{repo}/contents/.github/workflows", "length")
    signals["workflow_count"] = int(out) if ok and out.isdigit() else 0

    # Branch protection
    ok, out = gh_api(
        f"repos/{repo}/branches/main/protection",
        ".required_pull_request_reviews.required_approving_review_count // 0",
    )
    if not ok:
        # Try 'master' branch
        ok, out = gh_api(
            f"repos/{repo}/branches/master/protection",
            ".required_pull_request_reviews.required_approving_review_count // 0",
        )
    signals["required_reviewers"] = int(out) if ok and out.isdigit() else -1
    # -1 = unknown (API denied/no branch protection)

    # Dismiss stale reviews
    ok, out = gh_api(
        f"repos/{repo}/branches/main/protection",
        ".required_pull_request_reviews.dismiss_stale_reviews // false",
    )
    signals["dismiss_stale_reviews"] = out == "true" if ok else None

    # Config files (Tier 0: static analysis)
    tier0_configs = {
        ".pre-commit-config.yaml": "pre_commit",
        ".eslintrc": "eslint",
        ".eslintrc.json": "eslint",
        "eslint.config.js": "eslint",
        "eslint.config.mjs": "eslint",
        "ruff.toml": "ruff",
        "biome.json": "biome",
        "biome.jsonc": "biome",
        ".prettierrc": "prettier",
        ".prettierrc.json": "prettier",
    }
    found_linters = set()
    for path, name in tier0_configs.items():
        if check_file_exists(repo, path):
            found_linters.add(name)
    signals["linters"] = sorted(found_linters)
    signals["linter_count"] = len(found_linters)
    signals["has_pre_commit"] = "pre_commit" in found_linters

    # Test framework configs
    test_configs = {
        "jest.config.js": "jest",
        "jest.config.ts": "jest",
        "jest.config.mjs": "jest",
        "vitest.config.ts": "vitest",
        "vitest.config.js": "vitest",
        "pytest.ini": "pytest",
        "conftest.py": "pytest",
        "Cargo.toml": "cargo_test",
        "go.mod": "go_test",
        "phpunit.xml": "phpunit",
        ".nycrc": "nyc_coverage",
        "codecov.yml": "codecov",
        ".codecov.yml": "codecov",
    }
    found_tests = set()
    for path, name in test_configs.items():
        if check_file_exists(repo, path):
            found_tests.add(name)
    signals["test_frameworks"] = sorted(found_tests)
    signals["test_framework_count"] = len(found_tests)

    # pyproject.toml check (may contain linter + test config)
    if check_file_exists(repo, "pyproject.toml"):
        signals["has_pyproject"] = True
        if "ruff" not in found_linters:
            found_linters.add("pyproject_possible_ruff")
    else:
        signals["has_pyproject"] = False

    # Context files (AI-specific)
    signals["has_claude_md"] = check_file_exists(repo, "CLAUDE.md") or check_file_exists(repo, ".claude/CLAUDE.md")
    signals["has_agents_md"] = check_file_exists(repo, "AGENTS.md")
    signals["has_contributing"] = (
        check_file_exists(repo, "CONTRIBUTING.md")
        or check_file_exists(repo, ".github/CONTRIBUTING.md")
    )

    # Dependabot / Renovate (automated dependency management)
    signals["has_dependabot"] = check_file_exists(repo, ".github/dependabot.yml")
    signals["has_renovate"] = (
        check_file_exists(repo, "renovate.json")
        or check_file_exists(repo, ".github/renovate.json")
    )

    # Docker (sandbox/containerization)
    signals["has_dockerfile"] = (
        check_file_exists(repo, "Dockerfile")
        or check_file_exists(repo, "docker-compose.yml")
        or check_file_exists(repo, "docker-compose.yaml")
    )

    # Mergify / merge queue
    signals["has_mergify"] = check_file_exists(repo, ".mergify.yml")
    signals["has_merge_queue"] = check_file_exists(repo, ".github/merge-queue.yml")

    time.sleep(0.5)  # Rate limit courtesy
    return signals


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", help="Scrape a single repo")
    args = parser.parse_args()

    repos = [args.repo] if args.repo else REPOS
    out_path = DATA_DIR / "repo-infra.json"

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
        print(f"[{i+1}/{len(repos)}] {repo}:", flush=True)
        try:
            signals = scrape_repo(repo)
            existing[repo] = signals
            print(f"  CODEOWNERS={signals['has_codeowners']} workflows={signals['workflow_count']} "
                  f"linters={signals['linters']} tests={signals['test_frameworks']}", flush=True)
        except Exception as e:
            print(f"  ERROR: {e}", flush=True)

        # Save after every repo
        tmp = out_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(sorted(existing.values(), key=lambda x: x["repo"]), indent=2))
        tmp.replace(out_path)

    print(f"\nWrote {len(existing)} repos to {out_path}")


if __name__ == "__main__":
    main()
