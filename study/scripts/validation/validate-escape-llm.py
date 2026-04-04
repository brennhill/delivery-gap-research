#!/usr/bin/env python3
"""Test LLM judge with refined escape definitions on 126 human-labeled HIGH pairs.

Uses the precise definitions:
- ESCAPE: reached users, no automated system caught it
- MACHINE CATCH: CI/tests/build broke (system worked)
- NOT REWORK: ports, backports, enhancements, unrelated PRs

Usage:
    python validate-escape-llm.py           # score and compare
    python validate-escape-llm.py --analyze  # just analyze existing results
"""

import argparse
import json
import time
from pathlib import Path

from llm_utils import has_api_key, score_via_api, parse_llm_response

DATA_DIR = Path(__file__).resolve().parent / "data"
RESULTS_PATH = DATA_DIR / "escape-llm-validation.json"

JUDGE_PROMPT = """\
You are classifying whether a software change ESCAPED — meaning it reached users/production with a problem that no automated system caught.

I will show you two pull requests. PR A merged first. PR B came later and references PR A. Your job: classify PR B's relationship to PR A.

## Definitions

**ESCAPE** (label: "escape"): PR A had a problem that reached users. No CI, tests, linting, or build system caught it. A human had to discover it — by noticing broken behavior, getting a bug report, reviewing code after the fact, or users complaining. PR B fixes what PR A got wrong.

**MACHINE_CATCH** (label: "machine_catch"): PR A broke CI, tests, build, linting, or some other automated check. The infrastructure caught the problem before it affected users. PR B fixes the automated failure. Key signals: "fix CI", "fix build", "fix test", "fix lint", "tests failing", "build broke".

**NOT_RELATED** (label: "not_related"): PR B is NOT fixing PR A. It could be:
- A port/backport/cherry-pick of PR A to another branch
- A release PR that bundles PR A
- An enhancement/improvement to PR A (not fixing a bug)
- An unrelated PR that happens to reference PR A's number
- Planned follow-up work, not correcting a mistake

## PR A (the "original")
Title: {title_a}
Author: {author_a}
Date: {date_a}
Body:
{body_a}

## PR B (references PR A)
Title: {title_b}
Author: {author_b}
Date: {date_b}
Body:
{body_b}

## Return ONLY valid JSON:
{{
  "label": "escape" | "machine_catch" | "not_related",
  "confidence": "high" | "medium" | "low",
  "reason": "one sentence explanation"
}}
"""


def score_pairs():
    if not has_api_key():
        print("ERROR: ANTHROPIC_API_KEY not set")
        return

    with open(DATA_DIR / "human-validation-high-all.json") as f:
        pairs = json.load(f)

    existing = {}
    if RESULTS_PATH.exists():
        with open(RESULTS_PATH) as f:
            existing = json.load(f)

    # Load PR index for full bodies
    pr_index = {}
    for fp in sorted(DATA_DIR.glob("prs-*.json")):
        slug = fp.stem.replace("prs-", "")
        with open(fp) as f:
            prs = json.load(f)
        for pr in prs:
            repo = pr.get("repo", slug.replace("-", "/", 1))
            num = pr.get("pr_number")
            pr_index[f"{repo}#{num}"] = pr

    to_score = []
    for i, p in enumerate(pairs):
        key = f"{p['repo']}#{p['target_num']}->{p['source_num']}"
        if key not in existing:
            to_score.append((i, p, key))

    print(f"{len(existing)} already scored, {len(to_score)} to go")

    for idx, (i, pair, key) in enumerate(to_score):
        # Get full PR bodies from index
        target_pr = pr_index.get(f"{pair['repo']}#{pair['target_num']}")
        source_pr = pr_index.get(f"{pair['repo']}#{pair['source_num']}")

        body_a = (target_pr.get("body", "") if target_pr else pair.get("target_body", "")) or ""
        body_b = (source_pr.get("body", "") if source_pr else pair.get("source_body", "")) or ""

        prompt = JUDGE_PROMPT.format(
            title_a=pair["target_title"],
            author_a=pair["target_author"],
            date_a=pair["target_date"][:10] if pair["target_date"] else "?",
            body_a=body_a[:2000],
            title_b=pair["source_title"],
            author_b=pair["source_author"],
            date_b=pair["source_date"][:10] if pair["source_date"] else "?",
            body_b=body_b[:2000],
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

        label = result.get("label", "?")
        reason = result.get("reason", "?")[:80]
        print(f"  [{idx+1}/{len(to_score)}] {key}: {label} — {reason}", flush=True)

        if (idx + 1) % 10 == 0 or idx == len(to_score) - 1:
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

    # Human labels
    all_labels = [
        "no","yes","yes","no","yes","yes","yes","yes","yes","yes",
        "no","yes","yes","yes","no","no","yes","yes","no","yes",
        "yes","yes","yes","no","yes","yes","yes","yes","yes","yes",
        "yes","no","no","yes","yes","yes","yes","yes","yes","yes",
        "yes","no","yes","yes","yes","no","no","no","no","no",
        "no","no","yes","no","no","no","yes","no","no","yes",
        "yes","yes","yes","yes","no","no","yes","no","no","no",
        "no","no","yes","yes","no","no","yes","no","no","no",
        "yes","yes","no","yes","yes","no","yes","no","yes","yes",
        "yes","no","no","no","no","no","yes","yes","yes","yes",
        # holdout
        "no","no","no","no","yes","yes","no","no","yes","yes",
        "yes","yes","yes","yes","no","no","no","no","no","no",
        "no","no","no","no","no","no",
    ]

    with open(DATA_DIR / "human-validation-high-all.json") as f:
        pairs = json.load(f)

    comparisons = []
    for i, human_label in enumerate(all_labels):
        p = pairs[i]
        key = f"{p['repo']}#{p['target_num']}->{p['source_num']}"
        llm = llm_results.get(key)
        if not llm or "error" in llm:
            continue

        human_escape = human_label == "yes"
        llm_label = llm.get("label", "")
        llm_escape = llm_label == "escape"

        comparisons.append({
            "key": key,
            "human": human_escape,
            "llm_escape": llm_escape,
            "llm_label": llm_label,
            "llm_reason": llm.get("reason", ""),
        })

    N = len(comparisons)
    agree = sum(1 for c in comparisons if c["human"] == c["llm_escape"])
    tp = sum(1 for c in comparisons if c["human"] and c["llm_escape"])
    fp = sum(1 for c in comparisons if not c["human"] and c["llm_escape"])
    fn = sum(1 for c in comparisons if c["human"] and not c["llm_escape"])
    tn = sum(1 for c in comparisons if not c["human"] and not c["llm_escape"])

    prec = tp / (tp + fp) if (tp + fp) else 0
    rec = tp / (tp + fn) if (tp + fn) else 0

    po = agree / N if N else 0
    pe = ((tp+fp)*(tp+fn) + (tn+fn)*(tn+fp)) / (N*N) if N else 0
    kappa = (po - pe) / (1 - pe) if pe < 1 else 0

    print(f"\n=== HAIKU (escape definitions) vs HUMAN (N={N}) ===")
    print(f"Agreement: {agree}/{N} ({100*agree/N:.0f}%)")
    print(f"TP={tp} FP={fp} FN={fn} TN={tn}")
    print(f"Precision: {prec:.2f}  Recall: {rec:.2f}")
    print(f"Cohen's kappa: {kappa:.3f}")

    # LLM label distribution
    from collections import Counter
    labels = Counter(c["llm_label"] for c in comparisons)
    print(f"\nLLM label distribution: {dict(labels)}")

    # Disagreements
    disagreements = [c for c in comparisons if c["human"] != c["llm_escape"]]
    if disagreements:
        print(f"\nDISAGREEMENTS ({len(disagreements)}):")
        for c in disagreements[:15]:
            htype = "FP" if c["llm_escape"] else "FN"
            print(f"  {htype}: {c['key']} llm={c['llm_label']} — {c['llm_reason'][:80]}")


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
