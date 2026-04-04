#!/usr/bin/env python3
"""Validate all HIGH confidence rework pairs from CatchRate.

These are pairs where the fix PR explicitly references the target PR number.
Expected precision ~85%. This gives us clean training data for the classifier.

Usage:
    python validate-high-confidence.py           # score all HIGH pairs
    python validate-high-confidence.py --analyze  # analyze results
"""

import argparse
import json
import time
from pathlib import Path

from llm_utils import has_api_key, score_via_api, parse_llm_response

DATA_DIR = Path(__file__).resolve().parent / "data"
RESULTS_PATH = DATA_DIR / "high-confidence-validation.json"

JUDGE_PROMPT = """\
You are validating a software quality metric. I will show you two pull requests from the same repository. The metric claims that PR B is REWORK caused by PR A — meaning PR A didn't fully solve the problem, and PR B was needed to fix, complete, correct, or clean up after it.

Rework includes: bug fixes, missed edge cases, follow-up corrections, reverting broken changes, completing work that was incomplete, fixing regressions introduced by PR A. It does NOT need to be a "bug" — incomplete work that required a follow-up is rework.

Your job: Is PR B rework caused by PR A? Or are they independent PRs that just happen to touch similar files?

## PR A (the "original" — claimed to need rework)
Title: {title_a}
Author: {author_a}
Date: {date_a}
Body:
{body_a}

## PR B (the claimed "fix")
Title: {title_b}
Author: {author_b}
Date: {date_b}
Body:
{body_b}

## Judgment

Return ONLY valid JSON:
{{
  "is_fix": true/false,
  "confidence": "high"/"medium"/"low",
  "reason": "one sentence explanation"
}}

Rules:
- true = PR B fixes, corrects, completes, reverts, or cleans up after PR A
- true = PR B addresses something PR A missed, broke, or left incomplete
- true = same author, same feature area, shortly after = likely rework
- true = PR B title says "fix", "revert", "patch", "follow-up", "address" relating to PR A's area
- false = they touch similar files but are clearly independent features
- false = PR B is a new feature that happens to be in the same module
- false = PR B is a dependency update or routine maintenance unrelated to PR A
- "high" confidence = the relationship is obvious from titles/bodies/timing
- "low" confidence = you're guessing based on file overlap alone
"""


def load_high_confidence_pairs():
    """Load all HIGH confidence escape pairs from CatchRate output."""
    pairs = []

    for fp in sorted(DATA_DIR.glob("catchrate-*.json")):
        slug = fp.stem.replace("catchrate-", "")
        prs_fp = DATA_DIR / f"prs-{slug}.json"

        if not prs_fp.exists():
            continue

        with open(fp) as f:
            cr_data = json.load(f)
        with open(prs_fp) as f:
            raw_prs = json.load(f)

        # Index raw PRs by number for body/author
        pr_by_num = {p["pr_number"]: p for p in raw_prs}

        # Find HIGH confidence escapes
        for pr in cr_data.get("prs", []):
            if not pr.get("escaped"):
                continue
            if pr.get("escape_confidence") != "high":
                continue

            target_num = pr["number"]
            reason = pr.get("escape_reason", "")

            # Extract source PR number from reason like "fix: #123 (explicit PR ref)"
            import re
            m = re.search(r"#(\d+)", reason)
            if not m:
                continue
            source_num = int(m.group(1))

            target_pr = pr_by_num.get(target_num)
            source_pr = pr_by_num.get(source_num)

            if not target_pr or not source_pr:
                continue

            repo = target_pr.get("repo", slug.replace("-", "/", 1))
            pairs.append({
                "repo": repo,
                "target_num": target_num,
                "source_num": source_num,
                "target_title": target_pr.get("title", ""),
                "target_body": (target_pr.get("body", "") or "")[:2000],
                "target_author": target_pr.get("author", ""),
                "target_date": target_pr.get("merged_at", ""),
                "source_title": source_pr.get("title", ""),
                "source_body": (source_pr.get("body", "") or "")[:2000],
                "source_author": source_pr.get("author", ""),
                "source_date": source_pr.get("merged_at", ""),
                "escape_reason": reason,
            })

    return pairs


def score_pairs(pairs):
    """Score all pairs with LLM judge."""
    if not has_api_key():
        print("ERROR: ANTHROPIC_API_KEY not set")
        return

    existing = {}
    if RESULTS_PATH.exists():
        try:
            with open(RESULTS_PATH) as f:
                existing = json.load(f)
        except Exception:
            pass

    to_score = [p for p in pairs
                if f"{p['repo']}#{p['target_num']}->{p['source_num']}" not in existing]

    print(f"{len(existing)} already scored, {len(to_score)} to go")

    for i, pair in enumerate(to_score):
        prompt = JUDGE_PROMPT.format(
            title_a=pair["target_title"],
            author_a=pair["target_author"],
            date_a=pair["target_date"][:10] if pair["target_date"] else "?",
            body_a=pair["target_body"][:2000],
            title_b=pair["source_title"],
            author_b=pair["source_author"],
            date_b=pair["source_date"][:10] if pair["source_date"] else "?",
            body_b=pair["source_body"][:2000],
        )

        try:
            text = score_via_api(prompt, "claude-haiku-4-5-20251001")
            result = parse_llm_response(text)
        except Exception as e:
            result = {"error": str(e)}

        key = f"{pair['repo']}#{pair['target_num']}->{pair['source_num']}"
        verdict = "AGREE" if result.get("is_fix") else "CONFLICT"
        existing[key] = {
            "repo": pair["repo"],
            "target": pair["target_num"],
            "source": pair["source_num"],
            "target_title": pair["target_title"][:100],
            "source_title": pair["source_title"][:100],
            **result,
        }

        reason = result.get("reason", "?")[:80]
        print(f"  [{i+1}/{len(to_score)}] #{pair['target_num']}->{pair['source_num']}: "
              f"{verdict} ({result.get('confidence', '?')}) — {reason}", flush=True)

        # Save every 5
        if (i + 1) % 5 == 0 or i == len(to_score) - 1:
            tmp = RESULTS_PATH.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(existing, indent=2))
            tmp.replace(RESULTS_PATH)

        time.sleep(0.05)

    print(f"\nDone. {len(existing)} total scored.")


def analyze():
    """Analyze validation results."""
    if not RESULTS_PATH.exists():
        print(f"No results at {RESULTS_PATH}")
        return

    with open(RESULTS_PATH) as f:
        results = json.load(f)

    valid = {k: v for k, v in results.items() if "error" not in v}
    errors = len(results) - len(valid)

    true_fixes = sum(1 for r in valid.values() if r.get("is_fix") is True)
    false_fixes = sum(1 for r in valid.values() if r.get("is_fix") is False)

    print(f"=== HIGH CONFIDENCE VALIDATION ===")
    print(f"Total: {len(results)} ({errors} errors)")
    print(f"Valid: {len(valid)}")
    print()
    if len(valid) > 0:
        print(f"AGREE (real rework):  {true_fixes}/{len(valid)} ({100*true_fixes/len(valid):.0f}%)")
        print(f"CONFLICT (not rework): {false_fixes}/{len(valid)} ({100*false_fixes/len(valid):.0f}%)")
    print()

    from collections import Counter
    conf = Counter(r.get("confidence", "?") for r in valid.values())
    print(f"Judge confidence: {dict(conf)}")

    # Show conflicts
    conflicts = [(k, v) for k, v in valid.items() if v.get("is_fix") is False]
    if conflicts:
        print(f"\nCONFLICTS ({len(conflicts)}):")
        for k, v in conflicts[:10]:
            print(f"  {v['repo']} #{v['target']}->{v['source']}")
            print(f"    Target: {v['target_title']}")
            print(f"    Source: {v['source_title']}")
            print(f"    Reason: {v.get('reason', '?')}")
            print()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--analyze", action="store_true")
    args = parser.parse_args()

    if args.analyze:
        analyze()
        return

    pairs = load_high_confidence_pairs()
    print(f"HIGH confidence pairs to validate: {len(pairs)}")
    score_pairs(pairs)
    print()
    analyze()


if __name__ == "__main__":
    main()
