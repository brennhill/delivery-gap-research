#!/usr/bin/env python3
"""Check if real questions (not templates) collapsed between 2023 and now."""

import json
import re
from pathlib import Path

data_dir = Path(__file__).resolve().parent / "data"
hist_dir = Path(__file__).resolve().parent / "data-2023-H1"

TEMPLATE_PATTERNS = [
    r"###\s+what changed",
    r"###\s+why was the change",
    r"###\s+how to test",
    r"###\s+checklist",
    r"###\s+type of change",
    r"###\s+does this pr",
    r"###\s+screenshots",
    r"###\s+problem",
    r"###\s+changes",
    r"###\s+summary",
    r"###\s+description",
    r"\- \[ \]",  # checkbox items
]


def has_real_question(body):
    """Check for actual questions after stripping template boilerplate."""
    if not body:
        return False, ""
    lines = body.split("\n")
    clean_lines = []
    for line in lines:
        if any(re.search(p, line, re.IGNORECASE) for p in TEMPLATE_PATTERNS):
            continue
        if line.strip().startswith("```"):
            continue
        clean_lines.append(line)

    clean = "\n".join(clean_lines)

    # Find sentences ending in ?
    for match in re.finditer(r"[^.!?\n]{10,}\?", clean):
        text = match.group().strip()
        # Skip URLs, markdown links, code
        if text.startswith("http") or "`" in text:
            continue
        return True, text[:120]

    return False, ""


def analyze_repo(repo_slug, label=""):
    """Compare question rates for a repo between 2023 and now."""
    current_fp = data_dir / f"prs-{repo_slug}.json"
    hist_fp = hist_dir / f"prs-{repo_slug}.json"

    results = {}

    for period, fp in [("2023-H1", hist_fp), ("current", current_fp)]:
        if not fp.exists():
            continue
        with open(fp) as f:
            prs = json.load(f)
        if not prs:
            continue

        q_count = 0
        examples = []
        for p in prs:
            body = p.get("body", "") or ""
            has_q, example = has_real_question(body)
            if has_q:
                q_count += 1
                if len(examples) < 3:
                    examples.append((p.get("pr_number", "?"), example))

        results[period] = {
            "n": len(prs),
            "questions": q_count,
            "rate": 100 * q_count / len(prs),
            "examples": examples,
        }

    return results


def main():
    repos = [
        ("novuhq-novu", "AI-adopting"),
        ("PostHog-posthog", "AI-adopting"),
        ("oven-sh-bun", "AI-adopting"),
        ("denoland-deno", "AI-adopting"),
        ("grafana-grafana", "control"),
        ("sveltejs-svelte", "control"),
        ("astral-sh-ruff", "mixed"),
        ("pnpm-pnpm", "mixed"),
        ("cli-cli", "mixed"),
    ]

    print("=== REAL QUESTIONS (template-stripped) ===")
    print()

    for slug, label in repos:
        results = analyze_repo(slug, label)
        if not results:
            continue

        print(f"--- {slug} ({label}) ---")
        for period in ["2023-H1", "current"]:
            if period not in results:
                continue
            r = results[period]
            print(f"  {period}: {r['questions']}/{r['n']} ({r['rate']:.1f}%)")
            for pr_num, ex in r["examples"]:
                print(f"    #{pr_num}: {ex}")

        if "2023-H1" in results and "current" in results:
            delta = results["current"]["rate"] - results["2023-H1"]["rate"]
            print(f"  DELTA: {delta:+.1f}pp")
        print()


if __name__ == "__main__":
    main()
