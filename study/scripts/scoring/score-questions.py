#!/usr/bin/env python3
"""Score PRs for genuine cognitive questions using LLM.

Scores both current and historical (2023-H1) PRs so we can compare
using the SAME detection method across time periods.

Usage:
    python score-questions.py                    # score all repos (current + historical)
    python score-questions.py --repo novuhq/novu # score one repo
    python score-questions.py --historical-only  # only score 2023-H1 data
    python score-questions.py --analyze          # compare 2023 vs current scores
"""

import argparse
import json
import time
from pathlib import Path

from llm_utils import has_api_key, score_via_api, parse_llm_response

DATA_DIR = Path(__file__).resolve().parent / "data"
HIST_DIR = Path(__file__).resolve().parent / "data-2023-H1"
RESULTS_DIR = DATA_DIR / "question-scores"

PROMPT = """\
You are analyzing a GitHub PR description. Score ONE thing:

**cognitive_questions** (0-100): Does the author ask GENUINE questions?

NOT template headers ("### What changed?", "## Summary").
NOT checklists ("- [ ] Does this PR...").
NOT rhetorical questions restating the problem.
NOT questions in code blocks or URLs.

YES: "Should we also handle the case where X?", "I'm not sure if this affects Y",
"Does anyone know if Z is still used?", "Would it be better to...?",
"What happens when the user does X while Y is loading?"

These signal cognitive engagement — the author is thinking about edge cases,
seeking feedback, or expressing uncertainty about their own work.

Score:
- 80-100: Multiple genuine questions showing deep thinking about the problem
- 40-79: One or two real questions
- 10-39: Template questions only, or questions that are really statements
- 0-9: No questions at all

Return ONLY valid JSON:
{"cognitive_questions": N, "question_text": "quote the best genuine question, or 'none'"}

## PR to analyze:
"""


def score_one(title, body, model="claude-haiku-4-5-20251001"):
    text = f"Title: {title}\n\n{(body or '')[:3000]}"
    try:
        resp = score_via_api(PROMPT + text, model)
        return parse_llm_response(resp)
    except Exception as e:
        return {"error": str(e)}


def score_dataset(prs, out_path, label=""):
    """Score a list of PRs, saving incrementally."""
    existing = {}
    if out_path.exists():
        try:
            with open(out_path) as f:
                existing = json.load(f)
        except Exception:
            pass

    to_score = [p for p in prs if str(p.get("pr_number", "")) not in existing]
    print(f"  {label}: {len(existing)} done, {len(to_score)} to score", flush=True)

    for i, p in enumerate(to_score):
        result = score_one(p.get("title", ""), p.get("body", ""))
        key = str(p.get("pr_number", i))
        existing[key] = {
            "pr_number": p.get("pr_number"),
            "title": p.get("title", "")[:100],
            "author": p.get("author", ""),
            **result,
        }

        if (i + 1) % 10 == 0 or i == len(to_score) - 1:
            tmp = out_path.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(existing, indent=2))
            tmp.replace(out_path)

        if (i + 1) % 50 == 0:
            print(f"    [{i+1}/{len(to_score)}]", flush=True)

        time.sleep(0.05)

    return existing


def analyze():
    """Compare question scores between 2023 and current."""
    print("=== COGNITIVE QUESTIONS: 2023-H1 vs CURRENT ===")
    print()

    repos_with_both = []

    for hist_fp in sorted(HIST_DIR.glob("prs-*.json")):
        slug = hist_fp.stem.replace("prs-", "")
        current_fp = DATA_DIR / f"prs-{slug}.json"
        hist_scores_fp = RESULTS_DIR / f"questions-2023-{slug}.json"
        current_scores_fp = RESULTS_DIR / f"questions-current-{slug}.json"

        if not all(fp.exists() for fp in [hist_scores_fp, current_scores_fp]):
            continue

        with open(hist_scores_fp) as f:
            hist_scores = json.load(f)
        with open(current_scores_fp) as f:
            curr_scores = json.load(f)

        def avg_score(scores):
            vals = [v.get("cognitive_questions", 0) for v in scores.values()
                    if isinstance(v.get("cognitive_questions"), (int, float))]
            return sum(vals) / len(vals) if vals else 0, len(vals)

        h_avg, h_n = avg_score(hist_scores)
        c_avg, c_n = avg_score(curr_scores)

        # % with score > 30 (has real questions)
        h_real = sum(1 for v in hist_scores.values()
                     if isinstance(v.get("cognitive_questions"), (int, float))
                     and v["cognitive_questions"] > 30)
        c_real = sum(1 for v in curr_scores.values()
                     if isinstance(v.get("cognitive_questions"), (int, float))
                     and v["cognitive_questions"] > 30)

        h_pct = 100 * h_real / h_n if h_n else 0
        c_pct = 100 * c_real / c_n if c_n else 0

        repo_name = slug.replace("-", "/", 1)
        repos_with_both.append((repo_name, h_n, h_avg, h_pct, c_n, c_avg, c_pct))

    if not repos_with_both:
        print("No repos with both historical and current question scores.")
        return

    print(f"{'Repo':<28} {'2023 N':>6} {'2023 Avg':>8} {'2023 Q%':>7} "
          f"{'Now N':>5} {'Now Avg':>7} {'Now Q%':>6} {'Delta':>7}")
    print("-" * 80)
    for repo, h_n, h_avg, h_pct, c_n, c_avg, c_pct in sorted(
            repos_with_both, key=lambda x: x[3], reverse=True):
        delta = c_pct - h_pct
        print(f"{repo:<28} {h_n:>6} {h_avg:>8.1f} {h_pct:>7.1f} "
              f"{c_n:>5} {c_avg:>7.1f} {c_pct:>6.1f} {delta:>+7.1f}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", help="Score a single repo (owner/name)")
    parser.add_argument("--historical-only", action="store_true")
    parser.add_argument("--analyze", action="store_true")
    args = parser.parse_args()

    if args.analyze:
        analyze()
        return

    if not has_api_key():
        print("ERROR: ANTHROPIC_API_KEY not set")
        return

    RESULTS_DIR.mkdir(exist_ok=True)

    # Score historical data
    if not args.repo or args.historical_only:
        print("=== Scoring 2023-H1 data ===")
        for fp in sorted(HIST_DIR.glob("prs-*.json")):
            slug = fp.stem.replace("prs-", "")
            with open(fp) as f:
                prs = json.load(f)
            if not prs:
                continue
            out = RESULTS_DIR / f"questions-2023-{slug}.json"
            score_dataset(prs, out, label=f"2023 {slug}")

    # Score current data
    if not args.historical_only:
        repos_to_score = []
        if args.repo:
            slug = args.repo.replace("/", "-")
            repos_to_score = [(slug, DATA_DIR / f"prs-{slug}.json")]
        else:
            for fp in sorted(DATA_DIR.glob("prs-*.json")):
                slug = fp.stem.replace("prs-", "")
                repos_to_score.append((slug, fp))

        print("=== Scoring current data ===")
        for slug, fp in repos_to_score:
            with open(fp) as f:
                prs = json.load(f)
            out = RESULTS_DIR / f"questions-current-{slug}.json"
            score_dataset(prs, out, label=f"current {slug}")

    print("\nDone. Run with --analyze to compare periods.")


if __name__ == "__main__":
    main()
