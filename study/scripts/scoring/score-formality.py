#!/usr/bin/env python3
"""Score formality signals in spec text using Claude Haiku.

Unlike quality scoring (does the spec describe the work well?), this scores
whether a HUMAN was genuinely engaged in creating this spec vs whether it's
AI-generated boilerplate. Note: this measures formality more than engagement —
professional human writing scores identically to AI writing.

Usage:
    python3 score-formality.py --repo cli-cli     # score one repo
    python3 score-formality.py --test              # test on known examples
    python3 score-formality.py                     # score all repos
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"

FORMALITY_PROMPT = """\
You are analyzing a GitHub PR description or issue to detect whether a human was genuinely \
engaged in writing it, or whether it was AI-generated (possibly with minimal human oversight).

This is NOT about quality. An AI can write a high-quality, detailed, well-structured spec. \
We want to know if a HUMAN was thinking when this was written.

For each signal below, answer with a score 0-100 AND a brief evidence quote from the text \
(or "none found" if absent).

## Signals to detect

### 1. lived_experience (0-100)
Does the author describe something they personally encountered, debugged, or discovered?
- "I ran into this when..." / "After investigating, I found..." / "I noticed that..."
- NOT: "The issue is..." / "The root cause is..." (could be AI analyzing code)
- Key: Is someone narrating what happened TO THEM, or describing a system state?

### 2. organizational_memory (0-100)
Does it reference knowledge that only comes from being part of the organization?
- "This is left over from the Inertia migration" / "Per discussion with the auth team"
- "We chose X last quarter because of the deadline" / "@jane suggested this approach"
- NOT: "the Compliance module" (that's a code reference, not org knowledge)
- NOT: "the customer" generically — only specific references count
- Key: Would an AI with access to only the codebase know this?

### 3. uncertainty (0-100)
Does the author acknowledge what they DON'T know or ask genuine questions?
- "Should we also handle...?" / "I'm not sure if this breaks..."
- "Open question: does this affect the mobile app?"
- NOT: "This ensures..." / "This handles all edge cases" (AI never doubts itself)
- Key: AI almost never expresses uncertainty. This is the strongest human signal.

### 4. negative_scope (0-100)
Does it explicitly say what is NOT being done, with reasoning?
- "Not fixing Y in this PR because it needs a separate migration"
- "Out of scope: Z, because that requires API partner coordination"
- NOT: template checkboxes like "- [ ] Breaking backward compatibility"
- Key: Deliberate scoping requires judgment about what matters NOW vs LATER

### 5. causal_reasoning (0-100)
Does it explain WHY, grounded in specific system context?
- "because our payment provider throttles at 100 req/s"
- "this broke when we upgraded to Node 22 because the ESM loader changed"
- NOT: "in order to improve performance" (generic, no system-specific grounding)
- NOT: "because it's best practice" (no reasoning, just assertion)
- Key: Real causal chains reference specific systems, numbers, or events

### 6. genuine_edge_cases (0-100)
Are edge cases specific to this system, or generic CS concepts?
- SPECIFIC: "Cart with 0 items after last item removed during checkout race condition"
- GENERIC: "handle empty input" / "null check" / "error handling"
- Key: AI lists obvious edge cases. Humans describe edge cases they've actually seen or worried about.

### 7. template_filler (0-100, INVERTED: high = MORE template, bad)
Is this a template with sections filled in mechanically?
- "This PR introduces comprehensive improvements to the robust handling of..."
- "Key changes include:" followed by a bullet list restating the diff
- Section headers exist but content is just describing what the diff does
- Key: Does the text add information BEYOND what you'd get from reading the diff?

### 8. overall_human_engagement (0-100)
Your overall assessment: was a human genuinely thinking when this was written?
- 80-100: Clearly human — personal narrative, org context, uncertainty, specific reasoning
- 50-79: Mixed — some human signals but also template-y sections
- 20-49: Mostly generated — reads like an AI summary of the diff
- 0-19: Pure AI — no human signals at all

## Output
Return ONLY valid JSON, no markdown:
{
  "lived_experience": N,
  "organizational_memory": N,
  "uncertainty": N,
  "negative_scope": N,
  "causal_reasoning": N,
  "genuine_edge_cases": N,
  "template_filler": N,
  "overall_human_engagement": N,
  "evidence": {
    "lived_experience": "quote or none found",
    "organizational_memory": "quote or none found",
    "uncertainty": "quote or none found",
    "causal_reasoning": "quote or none found"
  },
  "classification": "human|ai_generated|mixed"
}

## Text to analyze:
"""


from llm_utils import has_api_key as _has_api_key, score_via_api as _score_via_api, \
    score_via_cli as _score_via_cli, parse_llm_response as _parse_response


def score_formality(title: str, body: str, model: str = "claude-haiku-4-5-20251001") -> dict:
    spec_text = f"Title: {title}\n\n{body[:4000]}"
    prompt = FORMALITY_PROMPT + spec_text
    try:
        if _has_api_key():
            text = _score_via_api(prompt, model)
        else:
            text = _score_via_cli(prompt, model)
    except Exception as e:
        return {"error": str(e)}
    return _parse_response(text)


# ── Test cases ──────────────────────────────────────────────────────────

KNOWN_HUMAN = [
    {
        "label": "pnpm debug narrative",
        "title": "ci: fix Windows CI job race condition",
        "body": """I've been running into a persistent issue on one of my PRs where only Windows CI job fails.
After debugging, I'm confident the problem is:
1. Verdaccio takes longer to start up on Windows (compared to Ubuntu).
3. My PR only touched a few packages, and one package that's particularly sensitive to Verdaccio being online was scheduled to run first.
Here is a repro of the failure above. I opened a PR that modifies the CI config to always run against Windows.""",
    },
    {
        "label": "biome LSP regression",
        "title": "fix(lsp): handle wrapped settings in didChangeConfiguration",
        "body": """This fixes a regression in the Biome LSP configuration update path.
When handling workspace/didChangeConfiguration, the server assumed that params.settings always contained the inner Biome settings object. However, some clients send a wrapped payload such as {"biome": {...}}. After #9323, this became user-visible because didChangeConfiguration started reloading workspace settings immediately, causing the misread settings to re-enable capabilities/diagnostics unexpectedly.
This change makes load_extension_settings(Some(settings)) accept both shapes.
Fixed biome-zed#59: require_config_file could be ignored in Zed when the client sent wrapped Biome settings.""",
    },
    {
        "label": "pnpm DS_Store bug",
        "title": "fix(store): return only directory names when clean expired cache",
        "body": """I ran into this error when executing pnpm store prune. After looking into the relevant code, I found that the command does not filter out files when traversing directories, which causes macOS Finder cache files like .DS_Store to unexpectedly break the command.
I understand that users normally wouldn't access this directory, so .DS_Store usually wouldn't be present. Still, I think it's important to add logic to ensure that filesystem traversal only considers directories.
This is a small and straightforward fix. Thanks in advance, and looking forward to your review.""",
    },
]

KNOWN_AI = [
    {
        "label": "dotnet copilot-swe-agent",
        "title": "Make required command validation generic via resource annotations",
        "body": """This pull request introduces a new, unified system for validating required commands/executables for resources using the RequiredCommandAnnotation and WithRequiredCommand extension methods. It removes legacy, resource-specific command validation classes and migrates all relevant code to use the new declarative approach. This results in a more flexible, reusable, and maintainable validation mechanism across the codebase. Additionally, documentation has been added to explain the new system.

Key changes:

Removal of Legacy Validators
- Removed the FuncCoreToolsInstallationManager and DevTunnelCliInstallationManager classes, along with their registrations and usages, in favor of the new annotation-based system.

New Annotation-Based Validation
- Introduced RequiredCommandAnnotation for declaratively specifying required commands on resources.
- Added WithRequiredCommand extension method for easy annotation registration.""",
    },
    {
        "label": "novu coderabbit-generated",
        "title": "feat(api-service): context aware subscription preferences admin API",
        "body": """This pull request adds support for context-aware topic subscriptions, allowing subscriptions to be scoped and filtered by context keys (such as tenant or project). This enables more granular management and querying of topic subscriptions based on contextual information. The changes include updates to DTOs, API request/response validation, filtering logic, and comprehensive end-to-end tests for context-aware behaviors.

The most important changes are:

Context-aware subscription support:
* Added contextKeys field to relevant DTOs to represent the context that scopes a subscription.
* Refactored all instances of contextKeys in filters from a single string to an array of strings, ensuring consistent handling.""",
    },
    {
        "label": "bun robobun fd caching",
        "title": "fix(router): don't cache file descriptors in Route.parse",
        "body": """## Summary
- FileSystemRouter.Route.parse() was caching file descriptors in the global entry cache (entry.cache.fd). When Bun.build() later closed these fds during ParseTask, the cache still referenced them. Subsequent Bun.build() calls would find these stale fds, pass them to readFileWithAllocator, and seekTo(0) would fail with EBADF (errno 9).
- The fix ensures Route.parse always closes the file it opens for getFdPath instead of caching it in the shared entry.

Closes #18242

## Test plan
- [x] Added regression test test/regression/issue/18242.test.ts
- [x] Test passes with bun bd test
- [x] Test fails with USE_SYSTEM_BUN=1 bun test (system bun v1.3.9)
- [x] Verified 5 sequential builds work correctly after the fix

🤖 Generated with Claude Code""",
    },
]


def run_test():
    print("=== TESTING ON KNOWN EXAMPLES ===\n")

    for group_label, examples in [("KNOWN HUMAN", KNOWN_HUMAN), ("KNOWN AI", KNOWN_AI)]:
        print(f"\n--- {group_label} ---\n")
        for ex in examples:
            result = score_formality(ex["title"], ex["body"])
            if "error" in result:
                print(f"  {ex['label']}: ERROR - {result['error']}")
                continue

            print(f"  {ex['label']}:")
            print(f"    lived_exp={result.get('lived_experience','?')} "
                  f"org_mem={result.get('organizational_memory','?')} "
                  f"uncertain={result.get('uncertainty','?')} "
                  f"neg_scope={result.get('negative_scope','?')} "
                  f"causal={result.get('causal_reasoning','?')} "
                  f"edges={result.get('genuine_edge_cases','?')} "
                  f"template={result.get('template_filler','?')} "
                  f"overall={result.get('overall_human_engagement','?')} "
                  f"class={result.get('classification','?')}")
            ev = result.get('evidence', {})
            if ev:
                for k, v in ev.items():
                    if v and v != "none found":
                        print(f"      {k}: \"{v[:100]}\"")
            print()


def extract_specs(repo_slug: str) -> list[dict]:
    prs_path = DATA_DIR / f"prs-{repo_slug}.json"
    if not prs_path.exists():
        return []
    prs = json.loads(prs_path.read_text())
    specs = []
    for pr in prs:
        body = pr.get("body", "") or ""
        if len(body) < 50:
            continue
        specs.append({
            "pr_number": pr["pr_number"],
            "title": pr["title"],
            "body": body[:4000],
            "repo": pr.get("repo", repo_slug),
            "author": pr.get("author", ""),
        })
    return specs


def score_repo(repo_slug: str, dry_run: bool = False) -> list[dict]:
    specs = extract_specs(repo_slug)
    if not specs:
        print(f"  No specs found for {repo_slug}")
        return []

    print(f"  {len(specs)} specs to score")

    repo_path = DATA_DIR / f"engagement-{repo_slug}.json"
    results = []
    scored_prs = set()
    if not dry_run and repo_path.exists():
        try:
            loaded = json.loads(repo_path.read_text())
            # Keep only successful results; retry errors
            results = [r for r in loaded if 'error' not in r]
            scored_prs = {r["pr_number"] for r in results}
            errors = len(loaded) - len(results)
            print(f"  Resuming: {len(scored_prs)} already scored" +
                  (f", {errors} errors will be retried" if errors else ""))
        except Exception:
            pass

    for i, spec in enumerate(specs):
        if dry_run:
            print(f"    [{i+1}/{len(specs)}] PR #{spec['pr_number']}: {spec['title'][:50]}")
            continue

        if spec["pr_number"] in scored_prs:
            continue

        try:
            scores = score_formality(spec["title"], spec["body"])

            result = {
                "pr_number": spec["pr_number"],
                "title": spec["title"],
                "repo": spec["repo"],
                "author": spec["author"],
                **scores,
            }
            results.append(result)

            overall = scores.get('overall_human_engagement', '?')
            cls = scores.get('classification', '?')
            print(f"    [{i+1}/{len(specs)}] #{spec['pr_number']}: "
                  f"lived={scores.get('lived_experience','?')} "
                  f"org={scores.get('organizational_memory','?')} "
                  f"uncertain={scores.get('uncertainty','?')} "
                  f"overall={overall} [{cls}]", flush=True)

        except Exception as e:
            print(f"    [{i+1}/{len(specs)}] #{spec['pr_number']}: ERROR - {e}", flush=True)
            results.append({
                "pr_number": spec["pr_number"],
                "title": spec["title"],
                "repo": spec["repo"],
                "author": spec["author"],
                "error": str(e),
            })

        if not dry_run and len(results) % 10 == 0:
            repo_path.write_text(json.dumps(results, indent=2), encoding="utf-8")

        if not dry_run and i < len(specs) - 1:
            time.sleep(0.05)

    if not dry_run and results:
        repo_path.write_text(json.dumps(results, indent=2), encoding="utf-8")

    return results


def main():
    parser = argparse.ArgumentParser(description="Score formality via LLM")
    parser.add_argument("--repo", help="Score a single repo slug")
    parser.add_argument("--test", action="store_true", help="Run on known examples only")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.test:
        run_test()
        return

    if args.repo:
        slugs = [args.repo]
    else:
        slugs = sorted(
            p.stem.replace("prs-", "")
            for p in DATA_DIR.glob("prs-*.json")
        )

    for slug in slugs:
        print(f"\n{slug}:")
        score_repo(slug, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
