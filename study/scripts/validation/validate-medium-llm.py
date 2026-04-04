#!/usr/bin/env python3
"""Score 30 MEDIUM pairs with haiku LLM judge, compare to human labels.

Usage:
    python validate-medium-llm.py           # score and compare
    python validate-medium-llm.py --analyze  # just analyze existing results
"""

import argparse
import json
import time
from pathlib import Path

from llm_utils import has_api_key, score_via_api, parse_llm_response

DATA_DIR = Path(__file__).resolve().parent / "data"
RESULTS_PATH = DATA_DIR / "medium-llm-validation.json"

JUDGE_PROMPT = """\
You are validating a software quality metric. I will show you two pull requests from the same repository. The metric claims that PR B is REWORK caused by PR A — meaning PR A didn't fully solve the problem, and PR B was needed to fix, complete, correct, or clean up after it.

Rework includes: bug fixes, missed edge cases, follow-up corrections, reverting broken changes, completing work that was incomplete, fixing regressions introduced by PR A. It does NOT need to be a "bug" — incomplete work that required a follow-up is rework.

NOT rework: cherry-picks/backports to other branches, release automation PRs that bundle changes, independent features in the same module, planned incremental work, scope expansion (discovering a bigger problem after fixing a small one).

Your job: Is PR B rework caused by PR A? Or are they independent PRs that just happen to touch similar files or share an author?

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
- false = they touch similar files but are clearly independent features
- false = PR B is a cherry-pick/backport/port of PR A to another branch
- false = PR B is a release PR that bundles PR A
- false = PR B is planned next-step work, not fixing something wrong with PR A
- false = PR B is scope expansion (realized bigger problem exists), not PR A being wrong
"""


def score_pairs():
    if not has_api_key():
        print("ERROR: ANTHROPIC_API_KEY not set")
        return

    with open(DATA_DIR / "human-validation-medium.json") as f:
        pairs = json.load(f)

    existing = {}
    if RESULTS_PATH.exists():
        with open(RESULTS_PATH) as f:
            existing = json.load(f)

    to_score = []
    for i, p in enumerate(pairs):
        key = f"{p['repo']}#{p['target_num']}->{p['source_num']}"
        if key not in existing:
            to_score.append((i, p, key))

    print(f"{len(existing)} already scored, {len(to_score)} to go")

    for idx, (i, pair, key) in enumerate(to_score):
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

        existing[key] = {
            "pair_index": i,
            "repo": pair["repo"],
            "target": pair["target_num"],
            "source": pair["source_num"],
            **result,
        }

        verdict = "YES" if result.get("is_fix") else "NO"
        reason = result.get("reason", "?")[:80]
        print(f"  [{idx+1}/{len(to_score)}] {key}: {verdict} — {reason}", flush=True)

        # Save every 5
        if (idx + 1) % 5 == 0 or idx == len(to_score) - 1:
            tmp = RESULTS_PATH.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(existing, indent=2))
            tmp.replace(RESULTS_PATH)

        time.sleep(0.05)

    print(f"\nDone. {len(existing)} scored.")
    analyze()


def analyze():
    if not RESULTS_PATH.exists():
        print("No results yet")
        return

    with open(RESULTS_PATH) as f:
        llm_results = json.load(f)
    with open(DATA_DIR / "human-validation-medium-labels.json") as f:
        human_data = json.load(f)
    with open(DATA_DIR / "human-validation-medium.json") as f:
        pairs = json.load(f)

    # Build comparison
    comparisons = []
    for label_entry in human_data["labels"]:
        idx = label_entry["pair"]
        human_label = label_entry["label"]
        if human_label == "unsure":
            continue

        p = pairs[idx]
        key = f"{p['repo']}#{p['target_num']}->{p['source_num']}"
        llm = llm_results.get(key)
        if not llm or "error" in llm:
            continue

        human_bool = human_label == "yes"
        llm_bool = llm.get("is_fix", False)
        comparisons.append({
            "key": key,
            "human": human_bool,
            "llm": llm_bool,
            "llm_confidence": llm.get("confidence", "?"),
            "llm_reason": llm.get("reason", "?"),
        })

    N = len(comparisons)
    agree = sum(1 for c in comparisons if c["human"] == c["llm"])
    tp = sum(1 for c in comparisons if c["human"] and c["llm"])
    fp = sum(1 for c in comparisons if not c["human"] and c["llm"])
    fn = sum(1 for c in comparisons if c["human"] and not c["llm"])
    tn = sum(1 for c in comparisons if not c["human"] and not c["llm"])

    prec = tp / (tp + fp) if (tp + fp) else 0
    rec = tp / (tp + fn) if (tp + fn) else 0

    po = agree / N if N else 0
    pe = ((tp+fp)*(tp+fn) + (tn+fn)*(tn+fp)) / (N*N) if N else 0
    kappa = (po - pe) / (1 - pe) if pe < 1 else 0

    print(f"\n=== HAIKU vs HUMAN on MEDIUM pairs (N={N}) ===")
    print(f"Agreement: {agree}/{N} ({100*agree/N:.0f}%)")
    print(f"TP={tp} FP={fp} FN={fn} TN={tn}")
    print(f"Precision: {prec:.2f}  Recall: {rec:.2f}")
    print(f"Cohen's kappa: {kappa:.3f}")

    # Disagreements
    disagreements = [c for c in comparisons if c["human"] != c["llm"]]
    if disagreements:
        print(f"\nDISAGREEMENTS ({len(disagreements)}):")
        for c in disagreements:
            label = "FP" if c["llm"] else "FN"
            print(f"  {label}: {c['key']} human={'yes' if c['human'] else 'no'} llm={'yes' if c['llm'] else 'no'}")
            print(f"       {c['llm_reason'][:100]}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--analyze", action="store_true")
    args = parser.parse_args()

    if args.analyze:
        analyze()
    else:
        score_pairs()


if __name__ == "__main__":
    main()
