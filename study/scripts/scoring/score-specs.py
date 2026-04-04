#!/usr/bin/env python3
"""Score spec quality using Claude Haiku — detailed inventory approach.

Rather than pre-deciding what matters, we capture detailed presence/absence
of every spec dimension and let the correlation with rework tell us which
ones actually predict outcomes.

Usage:
    python score-specs.py                  # score all repos
    python score-specs.py --repo cli-cli   # score one repo
    python score-specs.py --dry-run        # show what would be scored
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"

SCORING_PROMPT = """\
You are analyzing a software specification (GitHub issue, PR description, or ticket).
Your job is to inventory what this spec CONTAINS and what it's MISSING.
Do NOT judge format — judge content.

For each dimension below, score 0-100 AND note whether the information is present, \
partially present, or absent. We will correlate these with actual rework rates later, \
so accuracy matters more than generosity.

## Dimensions to inventory

### 1. outcome_clarity (0-100)
Is the desired end state clear? Could two developers read this and build the same thing?
Note what outcome IS described vs what's left ambiguous.

### 2. error_states (0-100)
Are error conditions, edge cases, and failure modes described?
- What happens when inputs are invalid?
- What happens on timeout/failure?
- Are boundary conditions addressed?
Score 0 if NO error handling is mentioned. Score 50 if "handle errors" is mentioned without specifics.

### 3. scope_boundaries (0-100)
Is it clear what's IN scope and what's NOT?
- Are there explicit exclusions?
- Could a developer accidentally build too much or too little?

### 4. acceptance_criteria (0-100)
Are there testable success conditions?
- Given/When/Then? Expected inputs/outputs? Pass/fail criteria?
- Score 0 if you'd have to invent every test case from scratch.

### 5. data_contracts (0-100)
Are data shapes, API contracts, or schema changes described?
- Field names, types, required vs optional?
- Request/response shapes?
- Score 0 if no data structures are mentioned. Score N/A for non-data-related changes.

### 6. dependency_context (0-100)
Does it reference what existing code/modules/APIs this touches?
- File paths, function names, module boundaries?
- What this integrates with?

### 7. behavioral_specificity (0-100)
Are specific behaviors described with concrete details?
- Numbers, thresholds, specific values?
- Or is it all vague ("should be fast", "handle gracefully")?

### 8. change_type
Classify: "feature", "bugfix", "refactor", "dependency", "docs", "config", "test", "other"

### 9. spec_length_signal
How much content is here? "empty" (<10 words), "minimal" (10-50), "short" (50-200), \
"medium" (200-500), "detailed" (500+)

## Output
Return ONLY valid JSON, no markdown:
{
  "outcome_clarity": N,
  "error_states": N,
  "scope_boundaries": N,
  "acceptance_criteria": N,
  "data_contracts": N,
  "dependency_context": N,
  "behavioral_specificity": N,
  "change_type": "...",
  "spec_length_signal": "...",
  "missing": ["list of important things NOT in this spec"],
  "present": ["list of concrete things this spec DOES describe well"],
  "reasoning": "1-2 sentences on overall quality"
}

## Spec text:
"""


def _ensure_prs_cached(repo_slug: str) -> Path:
    """Ensure PR data is cached locally. Fetches from GitHub if missing."""
    prs_path = DATA_DIR / f"prs-{repo_slug}.json"
    if prs_path.exists():
        return prs_path

    # Convert slug back to owner/repo
    parts = repo_slug.split("-", 1)
    if len(parts) == 2:
        # Handle cases like "calcom-cal.com" or "astral-sh-ruff"
        # Try the slug as-is first with / separator
        repo = repo_slug.replace("-", "/", 1)
    else:
        return prs_path  # can't determine repo name

    print(f"  Fetching PRs for {repo} (not cached)...")
    try:
        from delivery_gap_signals.sources import auto_fetch
        changes = auto_fetch(repo, lookback_days=90)
        data = [c.to_dict() for c in changes]
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        prs_path.write_text(json.dumps(data, indent=2, default=str))
        print(f"  -> {len(data)} PRs fetched and cached")
    except Exception as e:
        print(f"  -> FETCH FAILED: {e}")

    return prs_path


def extract_specs(repo_slug: str) -> list[dict]:
    """Extract spec'd PRs with body text from a repo's PR data."""
    prs_path = _ensure_prs_cached(repo_slug)
    if not prs_path.exists():
        return []

    prs = json.loads(prs_path.read_text())
    specs = []
    for pr in prs:
        if pr.get("ticket_ids") and pr.get("body") and len(pr.get("body", "")) > 20:
            specs.append({
                "pr_number": pr["pr_number"],
                "title": pr["title"],
                "body": pr["body"][:4000],
                "repo": pr.get("repo", repo_slug),
                "author": pr.get("author", ""),
                "additions": pr.get("additions", 0),
                "deletions": pr.get("deletions", 0),
            })
    return specs


from llm_utils import has_api_key as _has_api_key, score_via_api as _score_via_api, \
    score_via_cli as _score_via_cli, parse_llm_response as _parse_llm_response


_NUMERIC_DIMS = [
    "outcome_clarity", "error_states", "scope_boundaries",
    "acceptance_criteria", "data_contracts", "dependency_context",
    "behavioral_specificity",
]


def _single_score(title: str, body: str, model: str) -> dict:
    """One scoring run."""
    spec_text = f"Title: {title}\n\n{body}"
    prompt = SCORING_PROMPT + spec_text

    if _has_api_key():
        text = _score_via_api(prompt, model)
    else:
        text = _score_via_cli(prompt, model)

    return _parse_llm_response(text)


def score_spec(title: str, body: str, model: str = "claude-haiku-4-5-20251001", runs: int = 1) -> dict:
    """Score a single spec. Multiple runs are averaged for stability.

    With runs=1: returns raw scores (fast, cheap).
    With runs=3: scores 3 times, returns averaged numeric dims + individual runs.
    """
    try:
        first = _single_score(title, body, model)
    except Exception as e:
        return {"error": str(e)}

    if "error" in first or runs <= 1:
        return first

    # Multiple runs — collect all, average numeric dims
    all_runs = [first]
    for _ in range(runs - 1):
        try:
            r = _single_score(title, body, model)
            if "error" not in r:
                all_runs.append(r)
        except Exception:
            pass  # skip failed runs, use what we have

    if len(all_runs) == 1:
        return first

    # Average numeric dimensions
    averaged = {}
    for dim in _NUMERIC_DIMS:
        vals = [r[dim] for r in all_runs if isinstance(r.get(dim), (int, float))]
        if vals:
            averaged[dim] = round(sum(vals) / len(vals))

    # Take non-numeric fields from first run
    for key in first:
        if key not in averaged:
            averaged[key] = first[key]

    # Store individual run scores and variance for transparency
    averaged["_runs"] = len(all_runs)
    averaged["_run_scores"] = [
        {dim: r.get(dim) for dim in _NUMERIC_DIMS if dim in r}
        for r in all_runs
    ]
    # Compute max spread per dimension
    spreads = {}
    for dim in _NUMERIC_DIMS:
        vals = [r[dim] for r in all_runs if isinstance(r.get(dim), (int, float))]
        if len(vals) >= 2:
            spreads[dim] = max(vals) - min(vals)
    averaged["_max_spread"] = spreads

    return averaged


def score_repo(repo_slug: str, dry_run: bool = False, runs: int = 1) -> list[dict]:
    """Score all specs in a repo."""
    specs = extract_specs(repo_slug)
    if not specs:
        print(f"  No specs found for {repo_slug}")
        return []

    print(f"  {len(specs)} specs to score")

    # Resume support: load existing results
    repo_path = DATA_DIR / f"spec-quality-{repo_slug}.json"
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
            scores = score_spec(spec["title"], spec["body"], runs=runs)

            # Compute an overall from the numeric dimensions (for bucketing)
            dims = ["outcome_clarity", "error_states", "scope_boundaries",
                     "acceptance_criteria", "behavioral_specificity"]
            dim_scores = [scores.get(d, 0) for d in dims if isinstance(scores.get(d), (int, float))]
            overall = round(sum(dim_scores) / len(dim_scores)) if dim_scores else 0

            result = {
                "pr_number": spec["pr_number"],
                "title": spec["title"],
                "repo": spec["repo"],
                "author": spec["author"],
                "additions": spec["additions"],
                "deletions": spec["deletions"],
                **scores,
                "overall": overall,
            }
            results.append(result)

            print(f"    [{i+1}/{len(specs)}] #{spec['pr_number']}: "
                  f"outcome={scores.get('outcome_clarity','?')} "
                  f"errors={scores.get('error_states','?')} "
                  f"scope={scores.get('scope_boundaries','?')} "
                  f"AC={scores.get('acceptance_criteria','?')} "
                  f"type={scores.get('change_type','?')} "
                  f"overall={overall}", flush=True)

        except Exception as e:
            print(f"    [{i+1}/{len(specs)}] #{spec['pr_number']}: ERROR - {e}", flush=True)
            results.append({
                "pr_number": spec["pr_number"],
                "title": spec["title"],
                "repo": spec["repo"],
                "author": spec["author"],
                "error": str(e),
            })

        # Save incrementally every 10 items
        if not dry_run and len(results) % 10 == 0:
            repo_path.write_text(json.dumps(results, indent=2), encoding="utf-8")

        # Light rate limiting
        if not dry_run and i < len(specs) - 1:
            time.sleep(0.05)

    # Final save
    if not dry_run and results:
        repo_path.write_text(json.dumps(results, indent=2), encoding="utf-8")

    return results


def main():
    parser = argparse.ArgumentParser(description="Score spec quality via LLM")
    parser.add_argument("--repo", help="Score a single repo slug (e.g., cli-cli)")
    parser.add_argument("--dry-run", action="store_true", help="Show specs without scoring")
    parser.add_argument("--runs", type=int, default=1, help="Score each spec N times and average (default: 1)")
    args = parser.parse_args()

    if args.repo:
        slugs = [args.repo]
    else:
        slugs = sorted(
            p.stem.replace("prs-", "")
            for p in DATA_DIR.glob("prs-*.json")
        )

    all_results = []
    for slug in slugs:
        print(f"\n{slug}:")
        results = score_repo(slug, dry_run=args.dry_run, runs=args.runs)
        all_results.extend(results)

        # Save incrementally per repo
        if not args.dry_run and results:
            repo_path = DATA_DIR / f"spec-quality-{slug}.json"
            repo_path.write_text(json.dumps(results, indent=2), encoding="utf-8")

    if not args.dry_run and all_results:
        out_path = DATA_DIR / "spec-quality-all.json"
        out_path.write_text(json.dumps(all_results, indent=2), encoding="utf-8")
        print(f"\nSaved {len(all_results)} scores to {out_path}")

        # Summary
        valid = [r for r in all_results if "overall" in r and r.get("overall", -1) >= 0]
        if valid:
            avg = sum(r["overall"] for r in valid) / len(valid)
            tiers = {"high (70+)": 0, "medium (40-69)": 0, "low (<40)": 0}
            for r in valid:
                o = r["overall"]
                if o >= 70: tiers["high (70+)"] += 1
                elif o >= 40: tiers["medium (40-69)"] += 1
                else: tiers["low (<40)"] += 1
            print(f"Average overall: {avg:.0f}")
            print(f"Quality tiers: {tiers}")

            # Per-dimension averages
            for dim in ["outcome_clarity", "error_states", "scope_boundaries",
                        "acceptance_criteria", "data_contracts", "dependency_context",
                        "behavioral_specificity"]:
                vals = [r[dim] for r in valid if isinstance(r.get(dim), (int, float))]
                if vals:
                    print(f"  {dim}: avg={sum(vals)/len(vals):.0f}")


if __name__ == "__main__":
    main()
