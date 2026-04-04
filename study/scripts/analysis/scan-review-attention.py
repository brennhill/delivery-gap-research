#!/usr/bin/env python3
"""
scan-review-attention.py — Scan PR review comments for attention signals.

Expands the attention signals dataset beyond PR descriptions (n=221) by
mining the much larger corpus of PR review comments. Scans for:
  - Questions (genuine vs rhetorical)
  - Uncertainty/hedging language
  - Challenge language (pushback, alternatives, edge cases)
  - Review depth signals (length, unique reviewers, rounds)

Data source: research/study/data/prs-*.json
Output: research/study/data/review-attention-signals.csv

Research note: This is exploratory. The heuristics for genuine vs rhetorical
questions are rough. Hedging/challenge phrase lists are hand-curated and
incomplete. Treat counts as lower bounds, not precise measurements.
"""

import csv
import glob
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
INPUT_PATTERN = os.path.join(DATA_DIR, "prs-*.json")
OUTPUT_PATH = os.path.join(DATA_DIR, "review-attention-signals.csv")

# Phrases that suggest genuine uncertainty or information-seeking.
# Matched case-insensitively against the sentence containing each '?'.
GENUINE_QUESTION_PATTERNS = [
    r"\bshould\s+we\b",
    r"\bwhat\s+if\b",
    r"\bhave\s+you\s+considered\b",
    r"\bis\s+this\b",
    r"\bis\s+there\b",
    r"\bare\s+we\b",
    r"\bare\s+there\b",
    r"\bdo\s+we\b",
    r"\bdo\s+you\b",
    r"\bdoes\s+this\b",
    r"\bwhy\s+(do|does|did|is|are|was|were|would|should|can|could)\b",
    r"\bhow\s+(do|does|did|is|are|was|were|would|should|can|could)\b",
    r"\bwhat\s+(do|does|did|is|are|was|were|would|should|can|could)\b",
    r"\bwhat\s+happens\b",
    r"\bwhat\s+about\b",
    r"\bcould\s+we\b",
    r"\bcould\s+you\b",
    r"\bcan\s+we\b",
    r"\bcan\s+you\b",
    r"\bwould\s+it\b",
    r"\bwouldn't\s+it\b",
    r"\bshouldn't\s+(this|we|it)\b",
    r"\bmight\s+(this|we|it)\b",
    r"\bis\s+it\s+possible\b",
    r"\bany\s+reason\b",
]

# Short trailing patterns that are almost always rhetorical.
# If a question sentence matches ONLY these and no genuine patterns, skip it.
RHETORICAL_PATTERNS = [
    r"\bright\s*\?$",
    r"\bno\s*\?$",
    r"\byes\s*\?$",
    r"\beh\s*\?$",
    r"\bhuh\s*\?$",
    r"\bokay\s*\?$",
    r"\bok\s*\?$",
]

# Uncertainty / hedging phrases. Matched case-insensitively as whole phrases
# within review body text. Each match increments the hedging counter by 1.
HEDGING_PHRASES = [
    r"\bi\s+think\b",
    r"\bprobably\b",
    r"\bnot\s+sure\b",
    r"\bmight\b",
    r"\bmaybe\b",
    r"\bcould\s+be\b",
    r"\bi\s+wonder\b",
    r"\bseems?\s+like\b",
    r"\bi\s+believe\b",
    r"\bpossibly\b",
    r"\barguably\b",
    r"\biirc\b",
    r"\bif\s+i'm\s+not\s+mistaken\b",
    r"\bcorrect\s+me\s+if\b",
    r"\bi\s+suspect\b",
    r"\bnot\s+entirely\s+sure\b",
    r"\bif\s+i\s+recall\b",
    r"\bif\s+i\s+remember\b",
    r"\bi\s+guess\b",
    r"\bafaik\b",
    r"\bas\s+far\s+as\s+i\s+know\b",
]

# Challenge / pushback phrases. These suggest the reviewer is actively
# questioning design decisions or raising concerns.
CHALLENGE_PHRASES = [
    r"\bwhy\s+not\b",
    r"\bhave\s+you\s+considered\b",
    r"\bwhat\s+about\b",
    r"\bshouldn't\s+this\b",
    r"\bwouldn't\s+it\s+be\s+better\b",
    r"\bconcern(ed|s)?\b",
    r"\bworried\s+about\b",
    r"\bedge\s+case\b",
    r"\bwhat\s+happens\s+when\b",
    r"\bwhat\s+if\b",
    r"\binstead\s+of\b",
    r"\balternative(ly)?\b",
    r"\brather\s+than\b",
    r"\bpotential(ly)?\s+(issue|problem|bug)\b",
    r"\bnit(pick)?\b",
    r"\brace\s+condition\b",
    r"\bthread\s+safe(ty)?\b",
    r"\boff[- ]by[- ]one\b",
    r"\bbreaking\s+change\b",
]

# Pre-compile all regex patterns for performance.
GENUINE_RE = [re.compile(p, re.IGNORECASE) for p in GENUINE_QUESTION_PATTERNS]
RHETORICAL_RE = [re.compile(p, re.IGNORECASE) for p in RHETORICAL_PATTERNS]
HEDGING_RE = [re.compile(p, re.IGNORECASE) for p in HEDGING_PHRASES]
CHALLENGE_RE = [re.compile(p, re.IGNORECASE) for p in CHALLENGE_PHRASES]


# ---------------------------------------------------------------------------
# Analysis helpers
# ---------------------------------------------------------------------------

def count_questions(text: str) -> tuple[int, int]:
    """
    Count total question marks and genuine (non-rhetorical) questions.

    Splits text into sentences by '?', then classifies each as genuine
    or rhetorical. A question is "genuine" if it matches any genuine
    pattern. It's "rhetorical" if it ONLY matches rhetorical patterns
    (or no patterns at all but is very short — e.g., "right?").

    Returns (total_questions, genuine_questions).
    """
    if not text:
        return 0, 0

    total = text.count("?")
    if total == 0:
        return 0, 0

    # Split on '?' to get the sentence fragment preceding each question mark.
    # The last element after splitting won't have a '?' so we skip it.
    fragments = text.split("?")[:-1]
    genuine = 0

    for frag in fragments:
        # Take the last ~200 chars as the "sentence" context.
        sentence = frag[-200:].strip()
        if not sentence:
            continue

        # Check if it matches any genuine question pattern.
        is_genuine = any(r.search(sentence) for r in GENUINE_RE)

        # If not flagged as genuine, check if it's rhetorical (skip it).
        # Very short fragments (< 15 chars) without genuine markers are
        # likely rhetorical ("right?", "no?", "ok?").
        if is_genuine:
            genuine += 1

    return total, genuine


def count_phrase_matches(text: str, patterns: list[re.Pattern]) -> int:
    """Count total matches of a list of compiled regex patterns in text."""
    if not text:
        return 0
    return sum(len(p.findall(text)) for p in patterns)


def extract_review_signals(reviews: list[dict]) -> dict:
    """
    Extract attention signals from a PR's review comments.

    Filters out bot reviewers. Aggregates signals across all non-bot
    review comments for the PR.

    Returns a dict of signal values.
    """
    # Accumulate non-bot review text and metadata.
    total_text = []
    unique_reviewers = set()
    unique_dates = set()

    for review in reviews:
        # Skip bot reviewers — their comments are templated noise.
        if review.get("is_bot", False):
            continue

        body = review.get("body") or ""
        # Some reviews have empty bodies (e.g., bare "approved" clicks).
        # We still count the reviewer and date even if body is empty,
        # because showing up to approve is itself a signal of attention.
        reviewer = review.get("reviewer", "")
        if reviewer:
            unique_reviewers.add(reviewer)

        submitted = review.get("submitted_at", "")
        if submitted:
            # Extract just the date portion for counting review "rounds".
            # Multiple reviews on the same day = same round.
            date_part = submitted[:10]  # "2026-03-25"
            unique_dates.add(date_part)

        if body.strip():
            total_text.append(body)

    # Combine all non-bot review text for analysis.
    combined = "\n".join(total_text)

    total_q, genuine_q = count_questions(combined)
    hedging = count_phrase_matches(combined, HEDGING_RE)
    challenges = count_phrase_matches(combined, CHALLENGE_RE)
    total_len = len(combined)

    has_attention = (genuine_q > 0) or (hedging > 0) or (challenges > 0)

    return {
        "review_questions": total_q,
        "review_genuine_questions": genuine_q,
        "review_hedging_count": hedging,
        "review_challenge_count": challenges,
        "review_total_length": total_len,
        "review_unique_reviewers": len(unique_reviewers),
        "review_rounds": len(unique_dates),
        "has_review_attention": has_attention,
    }


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def main():
    files = sorted(glob.glob(INPUT_PATTERN))
    if not files:
        print(f"ERROR: No files matching {INPUT_PATTERN}", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(files)} PR data files to scan.")
    print()

    # Accumulators for summary stats.
    rows = []
    total_prs = 0
    prs_with_reviews = 0
    prs_with_nonbot_reviews = 0
    prs_with_attention = 0
    signal_totals = Counter()

    for filepath in files:
        filename = os.path.basename(filepath)
        # Extract repo slug from filename: prs-owner-repo.json -> owner/repo
        # But the filename format is prs-{owner}-{repo}.json which is ambiguous
        # if owner or repo contain hyphens. We'll use the repo field from the
        # data itself instead.
        print(f"  Scanning {filename}...", end="", flush=True)

        with open(filepath, "r") as f:
            try:
                prs = json.load(f)
            except json.JSONDecodeError as e:
                print(f" ERROR: {e}")
                continue

        file_count = 0
        for pr in prs:
            total_prs += 1
            reviews = pr.get("reviews") or []

            if reviews:
                prs_with_reviews += 1

            # Get the repo name from the PR data itself — more reliable
            # than parsing the filename.
            repo = pr.get("repo", "")
            pr_number = pr.get("pr_number", "")

            signals = extract_review_signals(reviews)

            # Track whether this PR had any non-bot review text.
            if signals["review_total_length"] > 0:
                prs_with_nonbot_reviews += 1

            if signals["has_review_attention"]:
                prs_with_attention += 1

            # Accumulate signal totals for summary.
            for key in ["review_questions", "review_genuine_questions",
                        "review_hedging_count", "review_challenge_count"]:
                signal_totals[key] += signals[key]

            rows.append({
                "repo": repo,
                "pr_number": pr_number,
                **signals,
            })
            file_count += 1

        print(f" {file_count} PRs")

    # Sort by repo, then pr_number for deterministic output.
    rows.sort(key=lambda r: (r["repo"], int(r["pr_number"]) if str(r["pr_number"]).isdigit() else 0))

    # Write CSV.
    fieldnames = [
        "repo", "pr_number",
        "review_questions", "review_genuine_questions",
        "review_hedging_count", "review_challenge_count",
        "review_total_length", "review_unique_reviewers",
        "review_rounds", "has_review_attention",
    ]

    with open(OUTPUT_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    # -----------------------------------------------------------------------
    # Summary statistics
    # -----------------------------------------------------------------------
    print()
    print("=" * 65)
    print("SUMMARY")
    print("=" * 65)
    print(f"Total PRs scanned:                  {total_prs:,}")
    print(f"PRs with any reviews:               {prs_with_reviews:,} ({100*prs_with_reviews/max(total_prs,1):.1f}%)")
    print(f"PRs with non-bot review text:        {prs_with_nonbot_reviews:,} ({100*prs_with_nonbot_reviews/max(total_prs,1):.1f}%)")
    print(f"PRs with review attention signals:   {prs_with_attention:,} ({100*prs_with_attention/max(total_prs,1):.1f}%)")
    print()
    print("Signal totals across all PRs:")
    print(f"  Total question marks:              {signal_totals['review_questions']:,}")
    print(f"  Genuine questions:                 {signal_totals['review_genuine_questions']:,}")
    print(f"  Hedging phrases:                   {signal_totals['review_hedging_count']:,}")
    print(f"  Challenge phrases:                 {signal_totals['review_challenge_count']:,}")
    print()

    # Distribution of attention signals (how many PRs have 0, 1, 2, ... signals).
    genuine_q_dist = Counter()
    hedging_dist = Counter()
    challenge_dist = Counter()
    for row in rows:
        genuine_q_dist[row["review_genuine_questions"]] += 1
        hedging_dist[row["review_hedging_count"]] += 1
        challenge_dist[row["review_challenge_count"]] += 1

    print("Distribution of genuine questions per PR:")
    for k in sorted(genuine_q_dist.keys())[:10]:
        bar = "#" * min(genuine_q_dist[k] // 50, 40)
        print(f"  {k:3d}: {genuine_q_dist[k]:6,}  {bar}")
    if genuine_q_dist and max(genuine_q_dist.keys()) >= 10:
        rest = sum(v for k, v in genuine_q_dist.items() if k >= 10)
        print(f"  10+: {rest:6,}")
    print()

    print("Distribution of hedging count per PR:")
    for k in sorted(hedging_dist.keys())[:10]:
        bar = "#" * min(hedging_dist[k] // 50, 40)
        print(f"  {k:3d}: {hedging_dist[k]:6,}  {bar}")
    if hedging_dist and max(hedging_dist.keys()) >= 10:
        rest = sum(v for k, v in hedging_dist.items() if k >= 10)
        print(f"  10+: {rest:6,}")
    print()

    print("Distribution of challenge count per PR:")
    for k in sorted(challenge_dist.keys())[:10]:
        bar = "#" * min(challenge_dist[k] // 50, 40)
        print(f"  {k:3d}: {challenge_dist[k]:6,}  {bar}")
    if challenge_dist and max(challenge_dist.keys()) >= 10:
        rest = sum(v for k, v in challenge_dist.items() if k >= 10)
        print(f"  10+: {rest:6,}")
    print()

    # Compare to the 221-PR description-based attention signals.
    print("-" * 65)
    print("COMPARISON TO DESCRIPTION-BASED ATTENTION SIGNALS")
    print("-" * 65)
    print(f"  Description-based (prior):         221 PRs with signals")
    print(f"  Review-based (this scan):           {prs_with_attention:,} PRs with signals")
    if prs_with_attention > 0:
        ratio = prs_with_attention / 221
        print(f"  Expansion factor:                  {ratio:.1f}x")
    print()

    print(f"Output written to: {OUTPUT_PATH}")
    print(f"Total rows: {len(rows):,}")


if __name__ == "__main__":
    main()
