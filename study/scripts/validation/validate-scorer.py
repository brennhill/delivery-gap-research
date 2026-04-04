#!/usr/bin/env python3
"""Validate scorer consistency across model tiers.

Steelman test: maybe Haiku can't score engagement/quality well enough.
Take 50 medium-difficulty PRs and score them with Haiku, Sonnet, and
Opus.  Compare scores to see if stronger models produce materially
different classifications.

Usage:
    python validate-scorer.py                # score all 50 with all 3 models
    python validate-scorer.py --analyze      # compare existing scores
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from score_all import COMBINED_PROMPT
from llm_utils import has_api_key, score_via_api, parse_llm_response

DATA_DIR = Path(__file__).resolve().parent / "data"
SAMPLE_PATH = DATA_DIR / "scorer-validation-sample.json"
RESULTS_PATH = DATA_DIR / "scorer-validation-results.json"

MODELS = {
    "haiku": "claude-haiku-4-5-20251001",
    "sonnet": "claude-sonnet-4-5-20250929",
    "opus": "claude-opus-4-6",
}
# NOTE: If a model ID returns 404, check available models at
# https://docs.anthropic.com/en/docs/about-claude/models
# and update the IDs above. Common alternatives:
#   sonnet: claude-sonnet-4-5-20251022, claude-3-5-sonnet-20241022
#   opus: claude-opus-4-6-20260326, claude-3-5-opus-latest


def score_one(title: str, body: str, model_id: str) -> dict:
    """Score a single PR with the combined prompt."""
    spec_text = f"Title: {title}\n\n{body[:4000]}"
    prompt = COMBINED_PROMPT + spec_text
    try:
        text = score_via_api(prompt, model_id)
        return parse_llm_response(text)
    except Exception as e:
        return {"error": str(e)}


def run_scoring():
    """Score all 50 PRs with all 3 models."""
    if not has_api_key():
        print("ERROR: ANTHROPIC_API_KEY not set")
        return

    with open(SAMPLE_PATH) as f:
        sample = json.load(f)

    # Load existing results for resume
    results = {}
    if RESULTS_PATH.exists():
        try:
            with open(RESULTS_PATH) as f:
                results = json.load(f)
        except Exception:
            pass

    for model_name, model_id in MODELS.items():
        print(f"\n=== Scoring with {model_name} ({model_id}) ===")

        if model_name not in results:
            results[model_name] = {}

        scored = len(results[model_name])
        to_score = [s for s in sample
                    if str(s["pr_number"]) not in results[model_name]]
        print(f"  {scored} already scored, {len(to_score)} to go")

        for i, pr in enumerate(to_score):
            result = score_one(pr["title"], pr["body"], model_id)
            results[model_name][str(pr["pr_number"])] = {
                "repo": pr["repo"],
                "pr_number": pr["pr_number"],
                "ai_tagged": pr["ai_tagged"],
                "reworked": pr["reworked"],
                "escaped": pr["escaped"],
                **result,
            }

            cls = result.get("classification", "?")
            eng = result.get("overall_human_engagement", "?")
            print(f"  [{i+1}/{len(to_score)}] #{pr['pr_number']}: "
                  f"engagement={eng} [{cls}]", flush=True)

            # Save after every score
            tmp = RESULTS_PATH.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(results, indent=2))
            tmp.replace(RESULTS_PATH)

            if i < len(to_score) - 1:
                time.sleep(0.1)

    print(f"\nDone. Results in {RESULTS_PATH}")


def analyze():
    """Compare scores across models."""
    if not RESULTS_PATH.exists():
        print(f"ERROR: {RESULTS_PATH} not found. Run scoring first.")
        return

    with open(RESULTS_PATH) as f:
        results = json.load(f)

    with open(SAMPLE_PATH) as f:
        sample = json.load(f)

    models = [m for m in MODELS if m in results]
    if len(models) < 2:
        print(f"Need at least 2 models scored, have {len(models)}")
        return

    print(f"Models scored: {models}")
    print(f"PRs in sample: {len(sample)}")
    print()

    # Compare key scores
    fields = ["overall_human_engagement", "lived_experience",
              "organizational_memory", "uncertainty", "causal_reasoning",
              "template_filler", "precision_required", "testability"]

    from statistics import mean, stdev

    print(f"{'Field':<30}", end="")
    for m in models:
        print(f"  {m:>8}", end="")
    print(f"  {'Max Δ':>8}")
    print("-" * (30 + 10 * len(models) + 10))

    for field in fields:
        avgs = {}
        for m in models:
            vals = []
            for pr_key, r in results[m].items():
                v = r.get(field)
                if isinstance(v, (int, float)):
                    vals.append(v)
            avgs[m] = mean(vals) if vals else 0

        max_delta = max(avgs.values()) - min(avgs.values()) if avgs else 0

        print(f"{field:<30}", end="")
        for m in models:
            print(f"  {avgs[m]:>8.1f}", end="")
        flag = " ***" if max_delta > 15 else " *" if max_delta > 10 else ""
        print(f"  {max_delta:>8.1f}{flag}")

    # Classification agreement
    print(f"\n{'Classification':<30}", end="")
    for m in models:
        counts = {"human": 0, "mixed": 0, "ai_generated": 0}
        for r in results[m].values():
            cls = r.get("classification", "")
            if cls in counts:
                counts[cls] += 1
        print(f"  H={counts['human']:>2} M={counts['mixed']:>2} A={counts['ai_generated']:>2}", end="")
    print()

    # Per-PR agreement: how often do models agree on classification?
    agree_count = 0
    disagree_prs = []
    common_prs = set()
    for m in models:
        common_prs = common_prs | set(results[m].keys()) if not common_prs else common_prs & set(results[m].keys())

    for pr_key in common_prs:
        classes = [results[m][pr_key].get("classification", "") for m in models]
        if len(set(classes)) == 1:
            agree_count += 1
        else:
            repo = results[models[0]][pr_key].get("repo", "")
            pr_num = results[models[0]][pr_key].get("pr_number", "")
            disagree_prs.append((repo, pr_num, dict(zip(models, classes))))

    print(f"\nClassification agreement: {agree_count}/{len(common_prs)} "
          f"({100*agree_count/len(common_prs):.0f}%)")

    if disagree_prs:
        print(f"\nDisagreements ({len(disagree_prs)}):")
        for repo, pr, classes in disagree_prs[:10]:
            print(f"  {repo} #{pr}: {classes}")

    # Does model choice change the AI-tagged vs non-tagged delta?
    print(f"\n=== KEY TEST: Does model change the finding? ===")
    for m in models:
        ai_scores = []
        human_scores = []
        for r in results[m].values():
            eng = r.get("overall_human_engagement")
            if not isinstance(eng, (int, float)):
                continue
            if r.get("ai_tagged"):
                ai_scores.append(eng)
            else:
                human_scores.append(eng)

        if ai_scores and human_scores:
            print(f"  {m:>8}: AI-tagged avg={mean(ai_scores):.1f} "
                  f"non-AI avg={mean(human_scores):.1f} "
                  f"Δ={mean(human_scores)-mean(ai_scores):+.1f}")

    # Does model choice change rework prediction?
    print(f"\n=== Does engagement score predict rework? ===")
    for m in models:
        high_eng = [r for r in results[m].values()
                    if isinstance(r.get("overall_human_engagement"), (int, float))
                    and r["overall_human_engagement"] >= 50]
        low_eng = [r for r in results[m].values()
                   if isinstance(r.get("overall_human_engagement"), (int, float))
                   and r["overall_human_engagement"] < 50]

        if high_eng and low_eng:
            h_rwk = sum(1 for r in high_eng if r.get("reworked")) / len(high_eng) * 100
            l_rwk = sum(1 for r in low_eng if r.get("reworked")) / len(low_eng) * 100
            print(f"  {m:>8}: high-eng rwk={h_rwk:.0f}% (n={len(high_eng)}) "
                  f"low-eng rwk={l_rwk:.0f}% (n={len(low_eng)}) "
                  f"Δ={h_rwk-l_rwk:+.0f}pp")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--analyze", action="store_true",
                        help="Analyze existing scores (don't score)")
    args = parser.parse_args()

    if args.analyze:
        analyze()
    else:
        run_scoring()
        print("\n" + "=" * 60)
        analyze()


if __name__ == "__main__":
    main()
