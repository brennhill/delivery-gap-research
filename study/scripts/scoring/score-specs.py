#!/usr/bin/env python3
"""Score specification quality using Claude Haiku.

Reads spec'd PRs from prs-*.json (identified via spec-signals-*.json),
scores each on 7 quality dimensions via LLM, and saves results to
spec-quality-*.json. Has resume support — re-run safely to continue
where it left off.

To reproduce from scratch: delete data/spec-quality-*.json, then run:
    python3 scripts/scoring/score-specs.py

Requires: ANTHROPIC_API_KEY environment variable, anthropic package.

Usage:
    python3 score-specs.py                      # score all repos (20 workers)
    python3 score-specs.py --repo cli-cli       # score one repo
    python3 score-specs.py --workers 5          # fewer concurrent workers
    python3 score-specs.py --dry-run            # show what would be scored
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import time
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

# ── LLM utilities ───────────────────────────────────────────────────

def _has_api_key() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


async def _call_llm_async(client, prompt: str, model: str, max_tokens: int = 2048) -> str:
    """Call Anthropic API asynchronously."""
    message = await client.messages.create(
        model=model,
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text


def _parse_response(text: str) -> dict:
    """Parse JSON from LLM response, stripping markdown fences.

    Handles truncated responses by extracting numeric scores via regex
    when full JSON parsing fails.
    """
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass

    # Truncated JSON — extract what we can via regex
    extracted = {}
    for dim in NUMERIC_DIMS:
        m = re.search(rf'"{dim}"\s*:\s*(\d+)', text)
        if m:
            extracted[dim] = int(m.group(1))
    # Also try change_type and spec_length_signal
    ct = re.search(r'"change_type"\s*:\s*"(\w+)"', text)
    if ct:
        extracted["change_type"] = ct.group(1)
    sl = re.search(r'"spec_length_signal"\s*:\s*"(\w+)"', text)
    if sl:
        extracted["spec_length_signal"] = sl.group(1)

    if len(extracted) >= 5:  # got at least 5 of 7 numeric dims
        return extracted

    return {"_parse_error": f"Parse error: {text[:200]}"}


# ── Scoring prompt ──────────────────────────────────────────────────

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
- Score 0 if no data structures are mentioned or if the change is not data-related.

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
  "spec_length_signal": "..."
}

## Spec text:
"""

NUMERIC_DIMS = [
    "outcome_clarity", "error_states", "scope_boundaries",
    "acceptance_criteria", "data_contracts", "dependency_context",
    "behavioral_specificity",
]

MODEL = "claude-haiku-4-5-20251001"
MIN_BODY_LENGTH = 50  # characters
MAX_RETRIES = 3
RETRY_BACKOFF = [2, 5, 15]  # seconds
DEFAULT_WORKERS = 20


# ── Spec extraction ────────────────────────────────────────────────

def _get_specd_pr_numbers(repo_slug: str) -> set[int]:
    """Get spec'd PR numbers from spec-signals classification."""
    ss_path = DATA_DIR / f"spec-signals-{repo_slug}.json"
    if not ss_path.exists():
        return set()
    with open(ss_path) as f:
        data = json.load(f)
    prs = data.get("coverage", {}).get("prs", [])
    return {int(p["number"]) for p in prs if p.get("specd")}


def _load_issue_bodies(repo_slug: str) -> dict[str, str]:
    """Load fetched issue bodies for a repo. Returns {issue_key: body_text}."""
    path = DATA_DIR / f"issue-bodies-{repo_slug}.json"
    if not path.exists():
        return {}
    with open(path) as f:
        data = json.load(f)
    # Map issue keys to body text, skip not-found
    bodies = {}
    for key, val in data.items():
        if val.get("_not_found") or not val.get("body"):
            continue
        bodies[key] = val["body"]
    return bodies


def _get_spec_sources(repo_slug: str) -> dict[int, str]:
    """Get spec_source for each spec'd PR number."""
    ss_path = DATA_DIR / f"spec-signals-{repo_slug}.json"
    if not ss_path.exists():
        return {}
    with open(ss_path) as f:
        data = json.load(f)
    sources = {}
    for p in data.get("coverage", {}).get("prs", []):
        if p.get("specd") and p.get("spec_source"):
            sources[int(p["number"])] = p["spec_source"]
    return sources


def _resolve_issue_key(spec_source: str, repo: str) -> str | None:
    """Convert a spec_source to an issue-bodies key (owner/repo#NNN)."""
    if not spec_source:
        return None
    if spec_source in ("#000", "#0"):
        return None
    m = re.match(r"https?://github\.com/([^/]+/[^/]+)/issues/(\d+)", spec_source)
    if m:
        return f"{m.group(1)}#{m.group(2)}"
    m = re.match(r"#(\d+)$", spec_source)
    if m and int(m.group(1)) > 0:
        return f"{repo}#{m.group(1)}"
    return None


def extract_specs(repo_slug: str) -> list[dict]:
    """Extract spec'd PRs with body text from a repo's PR data.

    When issue bodies are available (from fetch-issue-bodies.py),
    concatenates the issue body with the PR body to give the scorer
    the full specification context.
    """
    prs_path = DATA_DIR / f"prs-{repo_slug}.json"
    if not prs_path.exists():
        return []

    specd_numbers = _get_specd_pr_numbers(repo_slug)
    if not specd_numbers:
        return []

    with open(prs_path) as f:
        prs = json.load(f)

    # Load issue bodies and spec sources
    issue_bodies = _load_issue_bodies(repo_slug)
    spec_sources = _get_spec_sources(repo_slug)
    # Get canonical repo name from spec-signals (not from slug — hyphen splitting is ambiguous)
    ss_path = DATA_DIR / f"spec-signals-{repo_slug}.json"
    if ss_path.exists():
        with open(ss_path) as f:
            repo_name = json.load(f).get("repo", repo_slug.replace("-", "/", 1))
    else:
        repo_name = repo_slug.replace("-", "/", 1)

    enriched_count = 0
    specs = []
    for pr in prs:
        pr_num = pr.get("pr_number") or pr.get("number")
        if pr_num is None:
            continue
        pr_num = int(pr_num)
        if pr_num not in specd_numbers:
            continue

        pr_body = pr.get("body") or ""

        # Try to enrich with issue body
        issue_body = ""
        spec_source = spec_sources.get(pr_num, "")
        issue_key = _resolve_issue_key(spec_source, repo_name)
        if issue_key and issue_key in issue_bodies:
            issue_body = issue_bodies[issue_key]
            enriched_count += 1

        # Combine: issue body first (the spec), then PR body (implementation notes)
        if issue_body:
            combined = f"=== LINKED ISSUE ===\n{issue_body[:3000]}\n\n=== PR DESCRIPTION ===\n{pr_body[:1000]}"
        else:
            combined = pr_body

        if len(combined) <= MIN_BODY_LENGTH:
            continue

        specs.append({
            "pr_number": pr_num,
            "title": pr.get("title", ""),
            "body": combined[:4000],
            "repo": pr.get("repo", repo_slug),
            "author": pr.get("author", ""),
            "has_issue_body": bool(issue_body),
        })

    if enriched_count > 0:
        print(f"  {enriched_count} PRs enriched with issue body", flush=True)

    return specs


# ── Scoring ─────────────────────────────────────────────────────────

def _save_atomic(path: Path, data: list[dict]) -> None:
    """Atomic write via temp file + rename."""
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    os.replace(str(tmp), str(path))


def _validate_scores(scores: dict) -> dict:
    """Clamp numeric dimensions to 0-100, default missing to 0."""
    for dim in NUMERIC_DIMS:
        val = scores.get(dim)
        if isinstance(val, (int, float)):
            scores[dim] = max(0, min(100, int(round(val))))
        elif isinstance(val, str) and val.lower() in ("n/a", "na"):
            scores[dim] = 0
        else:
            scores[dim] = 0  # missing or wrong type
    return scores


async def _score_one(client, spec: dict, sem: asyncio.Semaphore) -> dict:
    """Score a single spec with retry and concurrency limiting."""
    prompt = SCORING_PROMPT + f"Title: {spec['title']}\n\n{spec['body']}"
    last_err = None

    for attempt in range(MAX_RETRIES):
        try:
            async with sem:
                text = await _call_llm_async(client, prompt, MODEL)
            result = _parse_response(text)
            if "_parse_error" in result:
                last_err = result["_parse_error"]
                if attempt < MAX_RETRIES - 1:
                    wait = RETRY_BACKOFF[min(attempt, len(RETRY_BACKOFF) - 1)]
                    await asyncio.sleep(wait)
                continue
            return _validate_scores(result)
        except Exception as e:
            last_err = str(e)
            if attempt < MAX_RETRIES - 1:
                wait = RETRY_BACKOFF[min(attempt, len(RETRY_BACKOFF) - 1)]
                await asyncio.sleep(wait)

    return {"_script_error": last_err or "unknown"}


async def score_repo_async(repo_slug: str, workers: int, dry_run: bool = False) -> list[dict]:
    """Score all specs in a repo with async concurrency. Resume-safe."""
    specs = extract_specs(repo_slug)
    if not specs:
        print(f"  No scoreable specs for {repo_slug}")
        return []

    # Resume: load existing results
    out_path = DATA_DIR / f"spec-quality-{repo_slug}.json"
    results = []
    scored_prs: set[int] = set()
    if not dry_run and out_path.exists():
        try:
            loaded = json.loads(out_path.read_text())
            results = [r for r in loaded if "_script_error" not in r]
            scored_prs = {r["pr_number"] for r in results}
            errors = len(loaded) - len(results)
            remaining = len(specs) - len(scored_prs)
            print(f"  {len(specs)} specs, {len(scored_prs)} done, {remaining} remaining" +
                  (f", {errors} errors retrying" if errors else ""))
        except Exception as e:
            print(f"  Warning: could not load existing results: {e}")
    else:
        print(f"  {len(specs)} specs to score")

    # Filter to unscored
    to_score = [s for s in specs if s["pr_number"] not in scored_prs]

    if dry_run:
        for i, spec in enumerate(to_score):
            print(f"    [{i+1}/{len(to_score)}] PR #{spec['pr_number']}: {spec['title'][:60]}")
        return results

    if not to_score:
        return results

    import anthropic
    import traceback as tb

    print(f"  Starting async scoring: {len(to_score)} PRs, {workers} workers, "
          f"batch size {workers * 2}", flush=True)

    client = anthropic.AsyncAnthropic()
    sem = asyncio.Semaphore(workers)
    BATCH_SIZE = workers * 2
    total_batches = (len(to_score) + BATCH_SIZE - 1) // BATCH_SIZE

    try:
        for batch_idx, batch_start in enumerate(range(0, len(to_score), BATCH_SIZE)):
            batch = to_score[batch_start:batch_start + BATCH_SIZE]
            print(f"\n  Batch {batch_idx + 1}/{total_batches} "
                  f"({len(batch)} PRs, #{batch[0]['pr_number']}..#{batch[-1]['pr_number']})",
                  flush=True)

            tasks = [_score_one(client, spec, sem) for spec in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            print(f"  Batch {batch_idx + 1} gather returned {len(batch_results)} results", flush=True)

            ok_count = 0
            err_count = 0
            for spec, scores in zip(batch, batch_results):
                if isinstance(scores, BaseException):
                    scores = {"_script_error": f"{type(scores).__name__}: {scores}"}

                dim_scores = [scores.get(d) for d in NUMERIC_DIMS
                              if isinstance(scores.get(d), (int, float))]
                overall = round(sum(dim_scores) / len(dim_scores)) if dim_scores else 0

                result = {**scores}
                result["pr_number"] = spec["pr_number"]
                result["title"] = spec["title"]
                result["repo"] = spec["repo"]
                result["author"] = spec["author"]
                result["overall"] = overall
                result["has_issue_body"] = spec.get("has_issue_body", False)
                results.append(result)

                if "_script_error" in scores:
                    print(f"    #{spec['pr_number']}: FAILED - {scores['_script_error']}", flush=True)
                    err_count += 1
                else:
                    print(f"    #{spec['pr_number']}: overall={overall} "
                          f"type={scores.get('change_type', '?')}", flush=True)
                    ok_count += 1

            print(f"  Processing {ok_count + err_count}/{len(batch)} results complete",
                  file=sys.stderr, flush=True)
            _save_atomic(out_path, results)
            total_done = batch_start + len(batch)
            total_ok = sum(1 for r in results if "_script_error" not in r)
            msg = (f"  Batch {batch_idx + 1} done: {ok_count} ok, {err_count} failed | "
                   f"Progress: {total_done}/{len(to_score)} | "
                   f"Total scored: {total_ok}")
            print(msg, flush=True)
            print(msg, file=sys.stderr, flush=True)

    except BaseException as e:
        print(f"\n  CRASH in {repo_slug}: {type(e).__name__}: {e}", flush=True)
        tb.print_exc()
        if results:
            _save_atomic(out_path, results)
            print(f"  Saved {len(results)} results before crash", flush=True)
        raise
    finally:
        try:
            await client.close()
        except Exception:
            pass  # don't mask the real error

    print(f"  Repo complete: {sum(1 for r in results if '_script_error' not in r)} scored, "
          f"{sum(1 for r in results if '_script_error' in r)} failed", flush=True)
    return results


# ── Main ────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Score specification quality via Claude Haiku. "
                    "Resume-safe: re-run to continue where you left off. "
                    "Delete spec-quality-*.json to rescore from scratch."
    )
    parser.add_argument("--repo", help="Score a single repo slug (e.g., cli-cli)")
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS,
                        help=f"Concurrent API calls (default: {DEFAULT_WORKERS})")
    parser.add_argument("--dry-run", action="store_true", help="Show specs without scoring")
    args = parser.parse_args()

    if not args.dry_run and not _has_api_key():
        print("Error: ANTHROPIC_API_KEY not set. Set it or use --dry-run.")
        sys.exit(1)

    if args.repo:
        slugs = [args.repo]
    else:
        slugs = sorted(
            p.stem.replace("prs-", "")
            for p in DATA_DIR.glob("prs-*.json")
        )

    async def run_all():
        total_scored = 0
        total_repos = 0
        print(f"Scoring {len(slugs)} repos with {args.workers} workers\n", flush=True)
        for i, slug in enumerate(slugs):
            print(f"\n{'='*60}", flush=True)
            print(f"[{i+1}/{len(slugs)}] {slug}:", flush=True)
            try:
                results = await score_repo_async(slug, workers=args.workers, dry_run=args.dry_run)
                scored = sum(1 for r in results if "_script_error" not in r)
                total_scored += scored
                if results:
                    total_repos += 1
            except BaseException as e:
                import traceback
                print(f"\n  ERROR on {slug}: {type(e).__name__}: {e}", flush=True)
                traceback.print_exc()
                if isinstance(e, (KeyboardInterrupt, SystemExit)):
                    raise
                print(f"  Skipping — will retry on next run", flush=True)

        print(f"\n{'='*60}", flush=True)
        print(f"Done. {total_scored} PRs scored across {total_repos} repos.", flush=True)

    try:
        asyncio.run(run_all())
        print("\n*** SCRIPT COMPLETED NORMALLY ***", file=sys.stderr, flush=True)
    except KeyboardInterrupt:
        print("\nInterrupted — progress saved to last completed batch.",
              file=sys.stderr, flush=True)
    except BaseException as e:
        import traceback
        print(f"\nFATAL: {type(e).__name__}: {e}", file=sys.stderr, flush=True)
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
