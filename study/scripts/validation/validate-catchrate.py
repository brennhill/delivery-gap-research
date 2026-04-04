#!/usr/bin/env python3
"""Validate CatchRate rework/escape detection accuracy.

Pulls 100 "reworked=True" and 100 "reworked=False" PR pairs,
shows the target PR and its supposed "fix" PR side by side,
and uses an LLM to judge whether the fix is actually a fix.

This is the BLOCKING validation — every finding depends on
rework/escape rates being accurate.

Usage:
    python validate-catchrate.py              # build sample + score with LLM
    python validate-catchrate.py --manual     # just show pairs for manual review
    python validate-catchrate.py --analyze    # analyze existing scores
"""

import argparse
import csv
import json
import random
import time
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"

JUDGE_PROMPT = """\
You are validating a software quality metric. I will show you two pull requests from the same repository. The metric claims that PR B is REWORK caused by PR A — meaning PR A didn't fully solve the problem, and PR B was needed to fix, complete, correct, or clean up after it.

Rework includes: bug fixes, missed edge cases, follow-up corrections, reverting broken changes, completing work that was incomplete, fixing regressions introduced by PR A. It does NOT need to be a "bug" — incomplete work that required a follow-up is rework.

Your job: Is PR B rework caused by PR A? Or are they independent PRs that just happen to touch similar files?

## PR A (the "original" — claimed to have a defect)
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

## Files both PRs touch
{overlapping_files}

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


def load_rework_pairs():
    """Load rework pairs from CatchRate upfront data."""
    pairs = []

    # Load all upfront files to find target->source mappings
    for fp in sorted(DATA_DIR.glob("upfront-*.json")):
        slug = fp.stem.replace("upfront-", "")
        prs_fp = DATA_DIR / f"prs-{slug}.json"

        if not prs_fp.exists():
            continue

        with open(fp) as f:
            upfront = json.load(f)
        with open(prs_fp) as f:
            prs = json.load(f)

        # Index PRs by number
        pr_by_num = {p["pr_number"]: p for p in prs}

        signals = upfront.get("effectiveness", {}).get("signals", [])
        for s in signals:
            target_num = int(s["target"])
            source_num = int(s["source"])

            target_pr = pr_by_num.get(target_num)
            source_pr = pr_by_num.get(source_num)

            if target_pr and source_pr:
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
                    "overlapping_files": s.get("overlapping_files", []),
                })

    return pairs


def build_sample():
    """Build a stratified sample for validation."""
    pairs = load_rework_pairs()
    print(f"Total rework pairs in data: {len(pairs)}")

    # Also need non-rework PRs as negative control
    with open(DATA_DIR / "master-prs.csv") as f:
        rows = list(csv.DictReader(f))

    non_rework = [r for r in rows
                  if r.get("f_is_bot_author") != "True"
                  and r.get("reworked") != "True"]

    random.seed(42)

    # Stratified sample: up to 5 pairs per repo, then fill remaining randomly
    from collections import defaultdict
    by_repo = defaultdict(list)
    for p in pairs:
        by_repo[p["repo"]].append(p)

    sample_rework = []
    for repo in sorted(by_repo.keys()):
        repo_pairs = by_repo[repo]
        sample_rework.extend(random.sample(repo_pairs, min(5, len(repo_pairs))))

    # Fill to 100 from remaining
    remaining = [p for p in pairs if p not in sample_rework]
    if len(sample_rework) < 100 and remaining:
        sample_rework.extend(random.sample(remaining, min(100 - len(sample_rework), len(remaining))))

    sample_rework = sample_rework[:100]

    # Sample 100 non-rework PRs (as negative control)
    sample_non_rework = random.sample(non_rework, min(100, len(non_rework)))

    sample = {
        "rework_pairs": sample_rework,
        "non_rework_prs": [
            {"repo": r["repo"], "pr_number": int(r["pr_number"]),
             "title": r.get("title", "")}
            for r in sample_non_rework
        ],
    }

    out_path = DATA_DIR / "catchrate-validation-sample.json"
    with open(out_path, "w") as f:
        json.dump(sample, f, indent=2)

    print(f"Sampled {len(sample_rework)} rework pairs")
    print(f"Sampled {len(sample['non_rework_prs'])} non-rework PRs")
    print(f"Saved to {out_path}")

    return sample


def score_with_llm(sample):
    """Score rework pairs with LLM judge."""
    from llm_utils import has_api_key, score_via_api, parse_llm_response

    if not has_api_key():
        print("ERROR: ANTHROPIC_API_KEY not set")
        return

    results_path = DATA_DIR / "catchrate-validation-results.json"

    # Load existing
    existing = {}
    if results_path.exists():
        try:
            with open(results_path) as f:
                existing = json.load(f)
        except Exception:
            pass

    pairs = sample["rework_pairs"]
    to_score = [p for p in pairs
                if f"{p['repo']}#{p['target_num']}->{p['source_num']}" not in existing]

    print(f"{len(existing)} already scored, {len(to_score)} to go")

    for i, pair in enumerate(to_score):
        overlap_files = pair.get("overlapping_files", [])
        overlap_str = "\n".join(overlap_files[:20]) if overlap_files else "(no file overlap data)"

        prompt = JUDGE_PROMPT.format(
            title_a=pair["target_title"],
            author_a=pair["target_author"],
            date_a=pair["target_date"][:10] if pair["target_date"] else "?",
            body_a=pair["target_body"][:2000],
            title_b=pair["source_title"],
            author_b=pair["source_author"],
            date_b=pair["source_date"][:10] if pair["source_date"] else "?",
            body_b=pair["source_body"][:2000],
            overlapping_files=overlap_str,
        )

        try:
            text = score_via_api(prompt, "claude-haiku-4-5-20251001")
            result = parse_llm_response(text)
        except Exception as e:
            result = {"error": str(e)}

        key = f"{pair['repo']}#{pair['target_num']}->{pair['source_num']}"
        existing[key] = {
            "repo": pair["repo"],
            "target": pair["target_num"],
            "source": pair["source_num"],
            "target_title": pair["target_title"][:100],
            "source_title": pair["source_title"][:100],
            "overlap_files": len(pair.get("overlapping_files", [])),
            **result,
        }

        is_fix = result.get("is_fix", "?")
        conf = result.get("confidence", "?")
        verdict = "AGREE" if is_fix else "CONFLICT"
        print(f"  [{i+1}/{len(to_score)}] #{pair['target_num']}->{pair['source_num']}: "
              f"{verdict} ({conf}) — {result.get('reason', '?')[:80]}", flush=True)

        # Save after every score
        if (i + 1) % 5 == 0 or i == len(to_score) - 1:
            tmp = results_path.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(existing, indent=2))
            tmp.replace(results_path)

        time.sleep(0.05)

    print(f"\nDone. {len(existing)} total scored.")


def analyze():
    """Analyze validation results."""
    results_path = DATA_DIR / "catchrate-validation-results.json"
    if not results_path.exists():
        print(f"No results at {results_path}")
        return

    with open(results_path) as f:
        results = json.load(f)

    total = len(results)
    errors = sum(1 for r in results.values() if "error" in r)
    valid = {k: v for k, v in results.items() if "error" not in v}

    true_fixes = sum(1 for r in valid.values() if r.get("is_fix") is True)
    false_fixes = sum(1 for r in valid.values() if r.get("is_fix") is False)

    print(f"=== CATCHRATE VALIDATION RESULTS ===")
    print(f"Total scored: {total} ({errors} errors)")
    print(f"Valid judgments: {len(valid)}")
    print()
    print(f"PRECISION (are CatchRate's rework flags correct?):")
    if len(valid) > 0:
        print(f"  AGREE (CatchRate=rework, LLM=rework):     {true_fixes}/{len(valid)} ({100*true_fixes/len(valid):.0f}%)")
        print(f"  CONFLICT (CatchRate=rework, LLM=not):     {false_fixes}/{len(valid)} ({100*false_fixes/len(valid):.0f}%)")
        print()
        if true_fixes / len(valid) >= 0.8:
            print(f"  VERDICT: CatchRate precision >= 80%. Rework rates are trustworthy.")
        elif true_fixes / len(valid) >= 0.6:
            print(f"  VERDICT: CatchRate precision 60-80%. Rework rates are directionally correct but inflated.")
        else:
            print(f"  VERDICT: CatchRate precision < 60%. Rework rates are unreliable. Findings at risk.")
    else:
        print(f"  No valid judgments yet.")
    print()

    # By confidence
    from collections import Counter
    conf_dist = Counter(r.get("confidence", "?") for r in valid.values())
    print(f"Confidence distribution: {dict(conf_dist)}")

    for conf in ["high", "medium", "low"]:
        subset = {k: v for k, v in valid.items() if v.get("confidence") == conf}
        if subset:
            fixes = sum(1 for r in subset.values() if r.get("is_fix") is True)
            print(f"  {conf}: {fixes}/{len(subset)} true fixes ({100*fixes/len(subset):.0f}%)")

    # By repo
    print(f"\nBy repo:")
    repo_results = {}
    for r in valid.values():
        repo = r.get("repo", "?")
        if repo not in repo_results:
            repo_results[repo] = {"true": 0, "false": 0}
        if r.get("is_fix"):
            repo_results[repo]["true"] += 1
        else:
            repo_results[repo]["false"] += 1

    for repo in sorted(repo_results.keys()):
        d = repo_results[repo]
        total_r = d["true"] + d["false"]
        print(f"  {repo:<30} {d['true']}/{total_r} true ({100*d['true']/total_r:.0f}%)")

    # Show false positives (flagged as rework but LLM says not a fix)
    print(f"\nFALSE POSITIVES (sample):")
    fps = [(k, v) for k, v in valid.items() if v.get("is_fix") is False]
    for k, v in fps[:10]:
        print(f"  {v['repo']} #{v['target']}->{v['source']}")
        print(f"    Target: {v['target_title']}")
        print(f"    Source: {v['source_title']}")
        print(f"    Reason: {v.get('reason', '?')}")
        print()


def show_manual(sample):
    """Show pairs for manual review."""
    for i, pair in enumerate(sample["rework_pairs"][:20]):
        print(f"=== PAIR {i+1} ===")
        print(f"Repo: {pair['repo']}")
        print(f"TARGET #{pair['target_num']}: {pair['target_title']}")
        print(f"  Author: {pair['target_author']}, Date: {pair['target_date'][:10] if pair['target_date'] else '?'}")
        print(f"FIX #{pair['source_num']}: {pair['source_title']}")
        print(f"  Author: {pair['source_author']}, Date: {pair['source_date'][:10] if pair['source_date'] else '?'}")
        print(f"  Overlapping files: {len(pair.get('overlapping_files', []))}")
        print()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manual", action="store_true")
    parser.add_argument("--analyze", action="store_true")
    args = parser.parse_args()

    if args.analyze:
        analyze()
        return

    # Build or load sample
    sample_path = DATA_DIR / "catchrate-validation-sample.json"
    if sample_path.exists():
        with open(sample_path) as f:
            sample = json.load(f)
        print(f"Loaded existing sample: {len(sample['rework_pairs'])} pairs")
    else:
        sample = build_sample()

    if args.manual:
        show_manual(sample)
    else:
        score_with_llm(sample)
        print()
        analyze()


if __name__ == "__main__":
    main()
