#!/usr/bin/env python3
"""Score spec quality AND formality in a single LLM call per PR.

Combines score-specs.py and score-formality.py into one pass.
Saves to both spec-quality-{slug}.json and engagement-{slug}.json
for backward compatibility with the build pipeline.

Usage:
    python score-all.py                  # score all repos
    python score-all.py --repo cli-cli   # score one repo
    python score-all.py --dry-run        # show what would be scored
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from llm_utils import has_api_key, score_via_api, score_via_cli, parse_llm_response

DATA_DIR = Path(__file__).resolve().parent / "data"

COMBINED_PROMPT = """\
You are analyzing a GitHub PR description or issue. Score it on TWO axes:
(A) SPEC QUALITY — how well does it describe what to build?
(B) HUMAN ENGAGEMENT — was a human genuinely thinking, or is this AI-generated boilerplate?

For every numeric field, score 0-100.

## A. Spec Quality Dimensions

1. outcome_clarity: Is the desired end state clear? Could two devs build the same thing?
2. error_states: Are error conditions, edge cases, failure modes described? 0 if none mentioned.
3. scope_boundaries: Clear what's IN and NOT in scope?
4. acceptance_criteria: Testable success conditions? Given/When/Then?
5. data_contracts: Data shapes, API contracts, schema changes? N/A if not data-related.
6. dependency_context: References to existing code, modules, APIs this touches?
7. behavioral_specificity: Concrete details (numbers, thresholds) vs vague ("should be fast")?
8. change_type: "feature"|"bugfix"|"refactor"|"dependency"|"docs"|"config"|"test"|"other"
9. spec_length_signal: "empty"|"minimal"|"short"|"medium"|"detailed"

## B. Human Engagement Signals

10. lived_experience: Author narrates what happened TO THEM? ("I ran into..." vs "The issue is...")
11. organizational_memory: References org knowledge an AI couldn't know? ("Per discussion with auth team")
12. uncertainty: Acknowledges unknowns? ("Should we also handle...?") AI never doubts itself.
13. negative_scope: Explicitly says what's NOT being done, with reasoning?
14. causal_reasoning: Explains WHY grounded in specific system context? (not "best practice")
15. genuine_edge_cases: System-specific edge cases, or generic CS concepts?
16. template_filler: (INVERTED: high = MORE template = bad) Is this just restating the diff?
17. overall_human_engagement: Overall: 80-100 clearly human, 50-79 mixed, 20-49 mostly AI, 0-19 pure AI.

## C. Task Precision

18. precision_required (0-100): How narrow is the correctness window for this task?
- HIGH (80-100): One correct implementation, many wrong ones. Payment logic, crypto, auth, race conditions, data migrations, protocol compliance, correctness-critical algorithms. Getting it 95% right means it's wrong.
- MEDIUM (40-79): Several valid approaches but meaningful constraints. API design, database schema, error handling strategy, performance optimization with specific targets.
- LOW (0-39): Many acceptable outputs. UI styling, documentation, boilerplate scaffolding, config changes, dependency bumps, adding a standard CRUD endpoint. "Good enough" is the bar.
- Key question: If you gave this task to 10 competent developers independently, how similar would their implementations be? High similarity = high precision required.

## D. Cognitive Questions

19. cognitive_questions (0-100): Does the author ask GENUINE questions showing they are thinking?
NOT template headers ("### What changed?"). NOT rhetorical. NOT checklists.
Look for: "Should we also handle X?", "I'm not sure if this affects Y", "Does anyone know if Z is still used?", "Would it be better to...?", "What happens when...?"
These signal the author is cognitively engaged — they're thinking about edge cases, seeking feedback, or expressing uncertainty about their own work.
- 80-100: Multiple genuine questions showing deep engagement with the problem
- 40-79: One or two real questions mixed with template
- 10-39: Template questions only, or questions that are really statements
- 0-9: No questions at all, or only boilerplate

## E. Testability of Success Criteria

20. testability (0-100): Could you write a FAILING test from this description alone, without reading the code?
This is NOT the same as acceptance_criteria. acceptance_criteria measures whether criteria exist. Testability measures whether you could AUTOMATE verification without reading the implementation.

Score by asking: "If I handed this to a QA engineer who has never seen the codebase, could they write a test that fails before the change and passes after?"

Examples to calibrate:

TESTABILITY 90, acceptance_criteria 85:
"POST /webhooks/stripe with valid HMAC-SHA256 signature returns 200. Invalid signature returns 401. Missing signature header returns 400."
→ QA engineer writes 3 HTTP tests immediately. No code reading needed.

TESTABILITY 20, acceptance_criteria 75:
"Given a user, when they log in, then they should be authenticated. Given invalid credentials, then login should fail gracefully."
→ Sounds testable but ISN'T. What endpoint? What response code? What does "gracefully" mean? 400? 401? 403? Redirect? QA engineer has to read the code or ask questions.

TESTABILITY 10, acceptance_criteria 60:
"This PR improves error handling across the auth module. Errors are now caught and reported consistently."
→ What errors? What does "consistently" mean? What's the observable difference? Cannot write any test.

TESTABILITY 5, acceptance_criteria 10:
"Refactors the middleware to use the new pattern. No functional changes."
→ Only testable assertion is "it still compiles." No behavioral test possible.

TESTABILITY 85, acceptance_criteria 40:
"Requests exceeding 100/minute per API key get 429 with Retry-After header set to seconds until reset."
→ Low acceptance_criteria (only one criterion) but HIGH testability (exact numbers, exact header, exact response code). One test, but it's completely automatable.

## Output
Return ONLY valid JSON, no markdown:
{
  "outcome_clarity": N, "error_states": N, "scope_boundaries": N,
  "acceptance_criteria": N, "data_contracts": N, "dependency_context": N,
  "behavioral_specificity": N,
  "change_type": "...", "spec_length_signal": "...",
  "lived_experience": N, "organizational_memory": N, "uncertainty": N,
  "negative_scope": N, "causal_reasoning": N, "genuine_edge_cases": N,
  "template_filler": N, "overall_human_engagement": N,
  "precision_required": N, "cognitive_questions": N, "testability": N,
  "evidence": {
    "lived_experience": "quote or none found",
    "organizational_memory": "quote or none found",
    "uncertainty": "quote or none found",
    "causal_reasoning": "quote or none found",
    "cognitive_questions": "quote the question or none found"
  },
  "classification": "human|ai_generated|mixed"
}

## Text to analyze:
"""


def score_pr(title: str, body: str, model: str = "claude-haiku-4-5-20251001") -> dict:
    """Score a single PR on both quality and engagement dimensions."""
    spec_text = f"Title: {title}\n\n{body[:4000]}"
    prompt = COMBINED_PROMPT + spec_text
    try:
        if has_api_key():
            text = score_via_api(prompt, model)
        else:
            text = score_via_cli(prompt, model)
    except Exception as e:
        return {"error": str(e)}
    return parse_llm_response(text)


def extract_specs(repo_slug: str) -> list[dict]:
    """Extract PRs with body text from a repo's PR data."""
    prs_path = DATA_DIR / f"prs-{repo_slug}.json"
    if not prs_path.exists():
        return []
    with open(prs_path) as f:
        prs = json.load(f)
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


def _split_result(result: dict, spec: dict) -> tuple[dict, dict]:
    """Split a combined score into quality and engagement dicts."""
    quality_fields = [
        "outcome_clarity", "error_states", "scope_boundaries",
        "acceptance_criteria", "data_contracts", "dependency_context",
        "behavioral_specificity", "change_type", "spec_length_signal",
        "precision_required", "testability",
    ]
    engagement_fields = [
        "lived_experience", "organizational_memory", "uncertainty",
        "negative_scope", "causal_reasoning", "genuine_edge_cases",
        "template_filler", "overall_human_engagement",
        "precision_required", "testability", "cognitive_questions",
        "evidence", "classification",
    ]

    base = {
        "pr_number": spec["pr_number"],
        "title": spec["title"],
        "repo": spec["repo"],
        "author": spec["author"],
    }

    quality = dict(base)
    for f in quality_fields:
        quality[f] = result.get(f)

    # Compute overall quality score
    dims = ["outcome_clarity", "error_states", "scope_boundaries",
            "acceptance_criteria", "behavioral_specificity"]
    dim_scores = [result[d] for d in dims
                  if isinstance(result.get(d), (int, float))]
    quality["overall"] = round(sum(dim_scores) / len(dim_scores)) if dim_scores else 0

    engagement = dict(base)
    for f in engagement_fields:
        engagement[f] = result.get(f)

    if "error" in result:
        quality["error"] = result["error"]
        engagement["error"] = result["error"]

    return quality, engagement


def score_repo(repo_slug: str, dry_run: bool = False) -> None:
    """Score all PRs in a repo, writing to both output files."""
    specs = extract_specs(repo_slug)
    if not specs:
        print(f"  No specs found for {repo_slug}")
        return

    quality_path = DATA_DIR / f"spec-quality-{repo_slug}.json"
    engagement_path = DATA_DIR / f"engagement-{repo_slug}.json"

    # Load existing results (resume support)
    quality_results = []
    engagement_results = []
    scored_prs = set()

    if not dry_run:
        # Load existing results — only consider a PR "scored" if it appears
        # without error in BOTH files, so a crash between writes doesn't
        # permanently skip a PR from the incomplete file.
        quality_existing = {}
        engagement_existing = {}
        for path, existing_dict in [(quality_path, quality_existing),
                                     (engagement_path, engagement_existing)]:
            if path.exists():
                try:
                    with open(path) as f:
                        loaded = json.load(f)
                    for r in loaded:
                        if "error" not in r:
                            existing_dict[r["pr_number"]] = r
                except Exception:
                    pass
        # Only mark as scored if present in BOTH files
        scored_prs = set(quality_existing.keys()) & set(engagement_existing.keys())
        quality_results.extend(quality_existing[pr] for pr in scored_prs)
        engagement_results.extend(engagement_existing[pr] for pr in scored_prs)

    to_score = [s for s in specs if s["pr_number"] not in scored_prs]
    print(f"  {len(specs)} specs total, {len(scored_prs)} already scored, "
          f"{len(to_score)} to score", flush=True)

    if dry_run:
        for s in to_score[:5]:
            print(f"    PR #{s['pr_number']}: {s['title'][:50]}")
        return

    for i, spec in enumerate(to_score):
        try:
            result = score_pr(spec["title"], spec["body"])
            quality, engagement = _split_result(result, spec)

            quality_results.append(quality)
            engagement_results.append(engagement)

            overall_q = quality.get("overall", "?")
            overall_e = result.get("overall_human_engagement", "?")
            cls = result.get("classification", "?")
            print(f"    [{i+1}/{len(to_score)}] #{spec['pr_number']}: "
                  f"quality={overall_q} engagement={overall_e} [{cls}]", flush=True)

        except Exception as e:
            print(f"    [{i+1}/{len(to_score)}] #{spec['pr_number']}: ERROR - {e}", flush=True)
            err = {"pr_number": spec["pr_number"], "title": spec["title"],
                   "repo": spec["repo"], "author": spec["author"], "error": str(e)}
            quality_results.append(err)
            engagement_results.append(err)

        # Save after every score — never lose progress (atomic via temp files)
        for out_path, results_list in [(quality_path, quality_results),
                                        (engagement_path, engagement_results)]:
            tmp = out_path.with_suffix('.json.tmp')
            tmp.write_text(json.dumps(results_list, indent=2), encoding="utf-8")
            tmp.replace(out_path)

        if i < len(to_score) - 1:
            time.sleep(0.05)

    # Final save (atomic)
    for out_path, results_list in [(quality_path, quality_results),
                                    (engagement_path, engagement_results)]:
        if results_list:
            tmp = out_path.with_suffix('.json.tmp')
            tmp.write_text(json.dumps(results_list, indent=2), encoding="utf-8")
            tmp.replace(out_path)

    print(f"  Done: {len(quality_results)} quality + {len(engagement_results)} engagement scores")


def main():
    parser = argparse.ArgumentParser(description="Score spec quality + formality in one LLM call")
    parser.add_argument("--repo", help="Score a single repo slug")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

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
