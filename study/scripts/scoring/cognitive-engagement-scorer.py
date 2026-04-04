#!/usr/bin/env python3
"""
Cognitive engagement scorer for PR descriptions.

Measures evidence of human THINKING in PR descriptions — NOT documentation
thoroughness or structural completeness. The existing structural spec scorer
(structural-spec-scorer.py) is 99.4% correlated with word count; it measures
documentation effort. This scorer targets cognitive engagement markers that
are independent of description length.

Five dimensions, each normalized per-100-words to remove length bias:
  1. Questions — genuine uncertainty probing (not rhetorical)
  2. Error/edge case thinking — failure mode awareness
  3. Uncertainty/hedging — honest admission of unknowns
  4. Scope awareness — explicit boundary-setting
  5. Tradeoff reasoning — explaining WHY an approach was chosen

Composite score: 0-5 binary (how many dimensions are present), NOT a sum
of raw counts. This prevents long descriptions from automatically scoring
higher.
"""

import re
import json
import glob
import os
import shutil
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import pearsonr, spearmanr

DATA_DIR = Path(__file__).parent / "data"
MASTER_CSV = DATA_DIR / "master-prs.csv"
OUTPUT_CSV = DATA_DIR / "cognitive-engagement-scores.csv"


# ── Code block stripping ────────────────────────────────────────────────
# Matches fenced code blocks (``` ... ```) including the content inside.
# We strip these BEFORE scoring because code contains error keywords,
# variable names, etc. that reflect implementation, not thinking.
# Match both backtick (```) and tilde (~~~) fenced code blocks per CommonMark spec.
CODE_BLOCK_PATTERN = re.compile(r'(?:```|~~~).*?(?:```|~~~)', re.DOTALL)

# Also strip inline code (`...`) — same rationale
INLINE_CODE_PATTERN = re.compile(r'`[^`]+`')

# Strip quoted text (lines starting with >) — these are someone else's words
QUOTE_LINE_PATTERN = re.compile(r'^>.*$', re.MULTILINE)


def strip_code_and_quotes(text: str) -> str:
    """Remove code blocks, inline code, and quoted text from PR body.

    We score the author's prose, not their code snippets or quoted text.
    """
    if not text:
        return ""
    text = CODE_BLOCK_PATTERN.sub('', text)
    text = INLINE_CODE_PATTERN.sub('', text)
    text = QUOTE_LINE_PATTERN.sub('', text)
    return text


# ── Dimension 1: Questions (genuine uncertainty probing) ────────────────
#
# We want questions that show the author is THINKING about design decisions,
# edge cases, or soliciting feedback. We exclude:
#   - Tag questions: "right?", "no?", "yeah?", "eh?" (not real questions)
#   - Rhetorical/filler at end of sentence after a statement
#   - Questions inside code blocks (already stripped above)
#
# Strategy: find all sentences ending in '?', then filter out non-genuine ones.

# Tag questions — these are conversational fillers, not genuine uncertainty.
# Pattern: a word like "right", "no", "yes", "yeah", "correct", "huh", "eh"
# immediately before the question mark, possibly with punctuation.
TAG_QUESTION_RE = re.compile(
    r'\b(?:right|no|yes|yeah|correct|huh|eh|ok|okay)\s*\?',
    re.IGNORECASE
)

# Genuine question indicators — phrases that strongly suggest real inquiry.
# These help us identify questions that show actual thinking.
GENUINE_QUESTION_INDICATORS = re.compile(
    r'(?:'
    r'should\s+(?:we|this|I|it)'          # "should we handle..."
    r'|what\s+if'                          # "what if the connection drops?"
    r'|what\s+happens'                     # "what happens when..."
    r'|is\s+(?:this|it|there)\s+(?:the|a)' # "is this the right approach?"
    r'|have\s+(?:we|you)\s+considered'     # "have we considered..."
    r'|do\s+(?:we|you)\s+(?:need|want)'   # "do we need to..."
    r'|how\s+(?:should|do|does|would|will)' # "how should we handle..."
    r'|can\s+(?:we|this|it)'              # "can we avoid..."
    r'|would\s+(?:it|this)'              # "would it be better..."
    r'|could\s+(?:we|this)'              # "could we use..."
    r'|why\s+(?:not|do|does|is|are)'     # "why not use X?"
    r'|any\s+(?:thoughts|ideas|concerns)' # "any thoughts?"
    r'|thoughts\s*\?'                     # standalone "thoughts?"
    r'|wdyt\s*\?'                         # "wdyt?" (what do you think)
    r')',
    re.IGNORECASE
)


def count_genuine_questions(text: str) -> int:
    """Count genuine questions in text (code blocks already stripped).

    A question is genuine if it:
    - Contains a question mark
    - Is NOT a tag question (right?, no?)
    - Shows actual inquiry about design, approach, or edge cases

    We split on '?' and check each segment. A question counts as genuine if:
    1. It matches GENUINE_QUESTION_INDICATORS (strong signal), OR
    2. It has 5+ words and is NOT a tag question (weaker but still real)

    Short fragments (<2 words) and tag questions (right? no?) are excluded.
    Template headers (## What does this PR do?) are excluded.
    """
    if not text:
        return 0

    # Common markdown template headers to exclude
    template_re = re.compile(
        r'^\s*#+\s+', re.MULTILINE  # lines starting with ## are headers
    )

    segments = text.split('?')
    count = 0

    for segment in segments[:-1]:  # last segment has no '?' after it
        segment = segment.strip()
        if not segment:
            continue

        # Get the last sentence/clause before the '?'
        lines = segment.split('\n')
        last_part = lines[-1].strip() if lines else segment

        # Skip markdown headers (template boilerplate like "## What does this PR do?")
        if template_re.match(last_part):
            continue

        # Skip tag questions (right?, no?) — only if the whole thing is short
        if TAG_QUESTION_RE.search(last_part + '?'):
            words = last_part.split()
            if len(words) <= 3:
                continue

        # Skip very short fragments (likely not real questions)
        words = last_part.split()
        if len(words) < 2:
            continue

        # Strong signal: matches genuine question indicator patterns
        if GENUINE_QUESTION_INDICATORS.search(last_part):
            count += 1
        # Weaker signal: longer question (5+ words) that passed all filters
        elif len(words) >= 5:
            count += 1
        # Otherwise skip — too short to be meaningful without an indicator

    return count


# ── Dimension 2: Error/Edge Case Thinking ───────────────────────────────
#
# Detects mentions of failure modes and boundary conditions in the author's
# prose. These indicate the author is thinking about what could go wrong,
# not just what the happy path does.
#
# We use word-boundary matching (\b) to avoid partial matches like
# "timeout" matching inside "setTimeout" (though that's stripped as code).

ERROR_THINKING_PATTERNS = [
    # Explicit edge/corner case language
    re.compile(r'\bedge\s+case', re.IGNORECASE),
    re.compile(r'\bcorner\s+case', re.IGNORECASE),
    re.compile(r'\bboundary\s+(?:condition|case|value)', re.IGNORECASE),

    # Failure mode language
    re.compile(r'\b(?:error|errors)\b', re.IGNORECASE),
    re.compile(r'\bfail(?:s|ed|ure|ures|ing)?\b', re.IGNORECASE),
    re.compile(r'\bcrash(?:es|ed|ing)?\b', re.IGNORECASE),
    re.compile(r'\bexception(?:s)?\b', re.IGNORECASE),
    re.compile(r'\bpanic(?:s|ked)?\b', re.IGNORECASE),

    # Null/empty/missing state
    re.compile(r'\bnull\b', re.IGNORECASE),
    re.compile(r'\bnil\b', re.IGNORECASE),
    re.compile(r'\bempty\b', re.IGNORECASE),
    re.compile(r'\bundefined\b', re.IGNORECASE),

    # Timing/concurrency issues
    re.compile(r'\btimeout(?:s)?\b', re.IGNORECASE),
    re.compile(r'\brace\s+condition', re.IGNORECASE),
    re.compile(r'\bdeadlock', re.IGNORECASE),

    # Numeric boundaries
    re.compile(r'\boverflow\b', re.IGNORECASE),
    re.compile(r'\bunderflow\b', re.IGNORECASE),

    # Resilience language
    re.compile(r'\bfallback\b', re.IGNORECASE),
    re.compile(r'\bretry\b', re.IGNORECASE),
    re.compile(r'\bretries\b', re.IGNORECASE),
    re.compile(r'\bgraceful(?:ly)?\b', re.IGNORECASE),
    re.compile(r'\bdegrade(?:s|d)?\b', re.IGNORECASE),

    # Conditional failure thinking
    re.compile(r'\bwhat\s+happens?\s+(?:when|if)\b', re.IGNORECASE),
    re.compile(r'\bif\s+\w+\s+fails?\b', re.IGNORECASE),
]


def count_error_thinking(text: str) -> int:
    """Count distinct error/edge-case thinking phrases in text.

    Each pattern is counted at most once per PR to avoid inflating the
    score when someone mentions "error" five times in one paragraph.
    We want to measure breadth of error thinking, not repetition.
    """
    if not text:
        return 0

    count = 0
    for pattern in ERROR_THINKING_PATTERNS:
        if pattern.search(text):
            count += 1
    return count


# ── Dimension 3: Uncertainty/Hedging ────────────────────────────────────
#
# Detects honest uncertainty — the author admitting they don't know
# something or expressing tentativeness. This is a strong signal of
# human engagement because:
#   1. AI-generated text rarely hedges (it states things confidently)
#   2. Uncertainty shows the author is THINKING about limits of knowledge
#   3. Templates never include hedging language

UNCERTAINTY_PATTERNS = [
    re.compile(r'\bI\s+think\b', re.IGNORECASE),
    re.compile(r'\bprobably\b', re.IGNORECASE),
    re.compile(r'\bnot\s+sure\b', re.IGNORECASE),
    re.compile(r'\bmight\b', re.IGNORECASE),
    re.compile(r'\bmaybe\b', re.IGNORECASE),
    re.compile(r'\bcould\s+be\b', re.IGNORECASE),
    re.compile(r'\bI\s+believe\b', re.IGNORECASE),
    re.compile(r'\bpossibly\b', re.IGNORECASE),
    re.compile(r'\barguably\b', re.IGNORECASE),
    re.compile(r'\bIIRC\b'),                         # case-sensitive: it's an acronym
    re.compile(r"\bif\s+I[''`]m\s+not\s+mistaken\b", re.IGNORECASE),
    re.compile(r'\bcorrect\s+me\s+if\b', re.IGNORECASE),
    re.compile(r'\bI\s+wonder\b', re.IGNORECASE),
    re.compile(r'\bunsure\b', re.IGNORECASE),
    re.compile(r'\bopen\s+question\b', re.IGNORECASE),
    re.compile(r'\bTBD\b'),                           # case-sensitive: it's an acronym
    re.compile(r'\bneeds?\s+discussion\b', re.IGNORECASE),
    re.compile(r'\bthoughts\s*\?', re.IGNORECASE),    # "thoughts?" as uncertainty solicitation
]


def count_uncertainty(text: str) -> int:
    """Count distinct uncertainty/hedging phrases.

    Like error thinking, we count each pattern at most once to measure
    breadth of hedging, not repetition.
    """
    if not text:
        return 0

    count = 0
    for pattern in UNCERTAINTY_PATTERNS:
        if pattern.search(text):
            count += 1
    return count


# ── Dimension 4: Scope Awareness ───────────────────────────────────────
#
# Detects explicit boundary-setting — the author thinking about what is
# NOT in this PR. This is a high-value cognitive signal because:
#   1. It requires understanding the larger system context
#   2. It shows deliberate prioritization
#   3. AI-generated PRs rarely set scope boundaries

SCOPE_PATTERNS = [
    re.compile(r'\bout\s+of\s+scope\b', re.IGNORECASE),
    re.compile(r'\bnot\s+in\s+this\s+(?:PR|pull\s+request|MR|merge\s+request|change|patch)\b', re.IGNORECASE),
    re.compile(r'\bfollow[\s-]*up\b', re.IGNORECASE),
    re.compile(r'\bfuture\s+(?:work|PR|change|improvement)\b', re.IGNORECASE),
    re.compile(r'\bseparate\s+(?:PR|pull\s+request|MR|merge\s+request|issue|ticket|change)\b', re.IGNORECASE),
    re.compile(r'\bdefer(?:red)?\b', re.IGNORECASE),
    re.compile(r"\bwon[''`]t\s+address\b", re.IGNORECASE),
    re.compile(r'\bbeyond\s+(?:the\s+)?scope\b', re.IGNORECASE),
    re.compile(r'\btracked\s+in\b', re.IGNORECASE),
    re.compile(r'\bTODO\b'),                          # case-sensitive: convention
    re.compile(r'\bknown\s+limitation', re.IGNORECASE),
    re.compile(r'\bdeliberately\s+not\b', re.IGNORECASE),
    re.compile(r'\bintentionally\s+(?:skip|omit|exclude|ignore)', re.IGNORECASE),
]


def count_scope_awareness(text: str) -> int:
    """Count distinct scope-awareness phrases."""
    if not text:
        return 0

    count = 0
    for pattern in SCOPE_PATTERNS:
        if pattern.search(text):
            count += 1
    return count


# ── Dimension 5: Tradeoff Reasoning ────────────────────────────────────
#
# Detects the author explaining WHY they chose an approach. This is the
# hardest dimension to detect without false positives because words like
# "because" and "option" are extremely common in normal prose.
#
# Strategy: use multi-word patterns that specifically indicate comparative
# or explanatory reasoning, not single common words.

TRADEOFF_PATTERNS = [
    # Explicit comparison language
    re.compile(r'\bchose\b.*\b(?:because|over|instead)\b', re.IGNORECASE),
    re.compile(r'\bdecided\s+to\b', re.IGNORECASE),
    re.compile(r'\bwent\s+with\b', re.IGNORECASE),
    re.compile(r'\binstead\s+of\b', re.IGNORECASE),
    re.compile(r'\balternative(?:s|ly)?\b', re.IGNORECASE),

    # Tradeoff vocabulary
    re.compile(r'\btrade[\s-]*off', re.IGNORECASE),
    re.compile(r'\bpro(?:s)?\s*/\s*con(?:s)?\b', re.IGNORECASE),
    re.compile(r'\bdownside', re.IGNORECASE),
    re.compile(r'\bupside', re.IGNORECASE),

    # Comparative reasoning
    re.compile(r'\bcompared\s+to\b', re.IGNORECASE),
    re.compile(r'\b(?:option|approach)\s+(?:A|B|1|2|was)\b', re.IGNORECASE),
    re.compile(r'\bconsidered\s+(?:using|doing|making|adding|the)\b', re.IGNORECASE),

    # Rationale language (multi-word to reduce false positives)
    re.compile(r'\brationale\b', re.IGNORECASE),
    re.compile(r'\bthe\s+reasoning\b', re.IGNORECASE),

    # "vs" as comparison marker (but not in code-like contexts)
    re.compile(r'\b\w+\s+vs\.?\s+\w+', re.IGNORECASE),
]


def count_tradeoff_reasoning(text: str) -> int:
    """Count distinct tradeoff reasoning phrases.

    Uses multi-word patterns to reduce false positives. Single words like
    "because" or "option" alone are too common to be meaningful.
    """
    if not text:
        return 0

    count = 0
    for pattern in TRADEOFF_PATTERNS:
        if pattern.search(text):
            count += 1
    return count


# ── Scoring pipeline ───────────────────────────────────────────────────

def score_pr(body: str) -> dict:
    """Score a single PR body on all 5 cognitive engagement dimensions.

    Returns raw counts, per-100-word rates, and composite score.
    """
    if not body or not isinstance(body, str):
        body = ""

    # Strip code blocks and quotes — we score thinking, not implementation
    clean_text = strip_code_and_quotes(body)

    # Word count on cleaned text (for normalization)
    words = clean_text.split()
    word_count = len(words)

    # Raw counts for each dimension
    raw_questions = count_genuine_questions(clean_text)
    raw_error = count_error_thinking(clean_text)
    raw_uncertainty = count_uncertainty(clean_text)
    raw_scope = count_scope_awareness(clean_text)
    raw_tradeoff = count_tradeoff_reasoning(clean_text)

    # Per-100-words normalization to remove length bias.
    # For PRs with very short bodies (< 10 words), rates would be unstable,
    # so we use 0 — there's not enough text to meaningfully score.
    if word_count >= 10:
        rate_questions = (raw_questions / word_count) * 100
        rate_error = (raw_error / word_count) * 100
        rate_uncertainty = (raw_uncertainty / word_count) * 100
        rate_scope = (raw_scope / word_count) * 100
        rate_tradeoff = (raw_tradeoff / word_count) * 100
    else:
        rate_questions = 0.0
        rate_error = 0.0
        rate_uncertainty = 0.0
        rate_scope = 0.0
        rate_tradeoff = 0.0

    # Composite: how many dimensions are present (0-5 binary)
    # Measures BREADTH of engagement, not depth/volume.
    # For very short bodies (< 10 words), composite is also 0 —
    # a 3-word body with "error maybe TODO" is not real engagement.
    if word_count < 10:
        raw_questions = 0
        raw_error = 0
        raw_uncertainty = 0
        raw_scope = 0
        raw_tradeoff = 0

    composite = sum([
        1 if raw_questions > 0 else 0,
        1 if raw_error > 0 else 0,
        1 if raw_uncertainty > 0 else 0,
        1 if raw_scope > 0 else 0,
        1 if raw_tradeoff > 0 else 0,
    ])

    return {
        "ce_questions": raw_questions,
        "ce_questions_rate": round(rate_questions, 4),
        "ce_error_thinking": raw_error,
        "ce_error_thinking_rate": round(rate_error, 4),
        "ce_uncertainty": raw_uncertainty,
        "ce_uncertainty_rate": round(rate_uncertainty, 4),
        "ce_scope_awareness": raw_scope,
        "ce_scope_awareness_rate": round(rate_scope, 4),
        "ce_tradeoff_reasoning": raw_tradeoff,
        "ce_tradeoff_reasoning_rate": round(rate_tradeoff, 4),
        "ce_composite": composite,
        "ce_body_words": word_count,
    }


def load_bodies() -> pd.DataFrame:
    """Load PR bodies from all prs-*.json files.

    Returns DataFrame with columns: repo, pr_number, body.
    """
    json_files = sorted(glob.glob(str(DATA_DIR / "prs-*.json")))
    print(f"Loading bodies from {len(json_files)} prs-*.json files...")

    rows = []
    for jf in json_files:
        with open(jf) as f:
            prs = json.load(f)
        repo_name = Path(jf).stem.replace("prs-", "")
        n_prs = len(prs)
        for pr in prs:
            rows.append({
                "repo": pr.get("repo", repo_name),
                "pr_number": pr["pr_number"],
                "body": pr.get("body", "") or "",
            })
        print(f"  {repo_name}: {n_prs} PRs")

    df = pd.DataFrame(rows)
    print(f"  Total: {len(df)} PR bodies across {df['repo'].nunique()} repos")
    return df


def main():
    print("=" * 70)
    print("COGNITIVE ENGAGEMENT SCORER")
    print("Measuring evidence of human thinking, not documentation thoroughness")
    print("=" * 70)

    # ── Load master CSV ─────────────────────────────────────────────────
    if not MASTER_CSV.exists():
        print(f"ERROR: {MASTER_CSV} not found")
        sys.exit(1)

    master = pd.read_csv(MASTER_CSV, low_memory=False)
    print(f"\nMaster CSV: {len(master)} rows, {master['repo'].nunique()} repos")

    # ── Load bodies and score ───────────────────────────────────────────
    bodies = load_bodies()

    print(f"\nScoring {len(bodies)} PR descriptions on 5 cognitive engagement dimensions...")
    scores = bodies["body"].apply(score_pr).apply(pd.Series)
    scored = pd.concat([bodies[["repo", "pr_number"]], scores], axis=1)

    # ── Save standalone CSV ─────────────────────────────────────────────
    scored.to_csv(OUTPUT_CSV, index=False)
    print(f"\nSaved {len(scored)} rows to {OUTPUT_CSV}")

    # ── Merge into master CSV ───────────────────────────────────────────
    # Backup first
    bak = MASTER_CSV.with_suffix(".csv.bak")
    if bak.exists():
        bak2 = MASTER_CSV.with_suffix(".csv.bak2")
        if bak2.exists():
            bak_target = MASTER_CSV.with_suffix(".csv.bak3")
        else:
            bak_target = bak2
    else:
        bak_target = bak

    print(f"Backing up master-prs.csv -> {bak_target.name}")
    shutil.copy2(MASTER_CSV, bak_target)

    # Drop existing ce_ columns if re-running
    existing_ce_cols = [c for c in master.columns if c.startswith("ce_")]
    if existing_ce_cols:
        print(f"  Dropping {len(existing_ce_cols)} existing ce_ columns (re-run)")
        master = master.drop(columns=existing_ce_cols)

    # Deduplicate scored data before merge to prevent row multiplication
    score_cols = ["repo", "pr_number"] + [c for c in scored.columns if c.startswith("ce_")]
    scored_deduped = scored[score_cols].drop_duplicates(subset=["repo", "pr_number"], keep="first")

    merged = master.merge(
        scored_deduped,
        on=["repo", "pr_number"],
        how="left",
    )

    # Fill NaN for PRs that had no matching body
    ce_cols = [c for c in merged.columns if c.startswith("ce_")]
    unmatched = merged["ce_composite"].isna().sum()
    if unmatched > 0:
        print(f"  WARNING: {unmatched} PRs had no matching body (filling with 0)")
        for col in ce_cols:
            merged[col] = merged[col].fillna(0)

    # Ensure integer types for count columns
    int_cols = ["ce_questions", "ce_error_thinking", "ce_uncertainty",
                "ce_scope_awareness", "ce_tradeoff_reasoning", "ce_composite",
                "ce_body_words"]
    for col in int_cols:
        if col in merged.columns:
            merged[col] = merged[col].astype(int)

    merged.to_csv(MASTER_CSV, index=False)
    print(f"  Saved {len(merged)} rows to {MASTER_CSV}")

    # ── Validation output ───────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("VALIDATION")
    print("=" * 70)

    # Filter out bots for validation
    if "f_is_bot_author" in merged.columns:
        merged["f_is_bot_author"] = merged["f_is_bot_author"].fillna(False).astype(bool)
        non_bot = merged[~merged["f_is_bot_author"]].copy()
        print(f"\nExcluding bots: {len(merged)} total -> {len(non_bot)} non-bot PRs")
    else:
        non_bot = merged.copy()
        print(f"\nNo bot column found, using all {len(non_bot)} PRs")

    # ── Distribution of composite scores ────────────────────────────────
    print(f"\n{'─' * 50}")
    print("COMPOSITE SCORE DISTRIBUTION (0-5)")
    print(f"{'─' * 50}")
    dist = non_bot["ce_composite"].value_counts().sort_index()
    total = len(non_bot)
    for score_val in range(6):
        n = dist.get(score_val, 0)
        pct = n / total * 100
        bar = "#" * int(pct / 2)
        print(f"  {score_val}: {n:>6} ({pct:>5.1f}%)  {bar}")

    # ── Correlation with word count ─────────────────────────────────────
    # This is the KEY validation — we WANT these to be LOW.
    # If they're high, we've just recreated the structural scorer.
    print(f"\n{'─' * 50}")
    print("CORRELATION WITH BODY WORD COUNT (want LOW)")
    print(f"{'─' * 50}")
    print("  If these are high (>0.8), we've failed — the score is just")
    print("  measuring description length, not thinking quality.\n")

    # Use ce_body_words for word count since it's the cleaned version
    wc = non_bot["ce_body_words"]
    has_words = non_bot[wc > 0].copy()  # exclude empty bodies
    print(f"  N = {len(has_words)} PRs with non-empty bodies\n")

    dimensions = [
        ("ce_questions", "Questions (count)"),
        ("ce_questions_rate", "Questions (rate/100w)"),
        ("ce_error_thinking", "Error thinking (count)"),
        ("ce_error_thinking_rate", "Error thinking (rate/100w)"),
        ("ce_uncertainty", "Uncertainty (count)"),
        ("ce_uncertainty_rate", "Uncertainty (rate/100w)"),
        ("ce_scope_awareness", "Scope awareness (count)"),
        ("ce_scope_awareness_rate", "Scope awareness (rate/100w)"),
        ("ce_tradeoff_reasoning", "Tradeoff reasoning (count)"),
        ("ce_tradeoff_reasoning_rate", "Tradeoff reasoning (rate/100w)"),
        ("ce_composite", "COMPOSITE (0-5)"),
    ]

    for col, label in dimensions:
        if col not in has_words.columns:
            continue
        vals = has_words[col]
        if vals.std() == 0:
            print(f"  {label:35s}  r=N/A (zero variance)")
            continue
        r, p = pearsonr(has_words["ce_body_words"], vals)
        print(f"  {label:35s}  r={r:+.3f}  p={p:.4f}")

    # ── Correlation with s_overall ──────────────────────────────────────
    # Should be moderate, NOT 0.99
    print(f"\n{'─' * 50}")
    print("CORRELATION WITH s_overall (want MODERATE, not 0.99)")
    print(f"{'─' * 50}")

    if "s_overall" in non_bot.columns:
        valid = non_bot.dropna(subset=["s_overall", "ce_composite"])
        if len(valid) > 10:
            r, p = pearsonr(valid["s_overall"], valid["ce_composite"])
            rho, p_rho = spearmanr(valid["s_overall"], valid["ce_composite"])
            print(f"  Pearson  r={r:+.3f}  p={p:.4f}")
            print(f"  Spearman rho={rho:+.3f}  p={p_rho:.4f}")
            print(f"  N = {len(valid)}")
        else:
            print("  Not enough valid data for correlation")
    else:
        print("  s_overall column not found in master CSV")

    # ── Correlation with outcomes ───────────────────────────────────────
    print(f"\n{'─' * 50}")
    print("CORRELATION WITH OUTCOMES")
    print(f"{'─' * 50}")

    outcome_cols = ["reworked", "escaped", "strict_escaped"]
    for outcome in outcome_cols:
        if outcome not in non_bot.columns:
            print(f"\n  {outcome}: column not found")
            continue

        oc = non_bot[outcome].fillna(False).astype(bool)
        n_true = oc.sum()
        n_false = (~oc).sum()
        print(f"\n  {outcome} (N_true={n_true}, N_false={n_false}):")

        for col, label in dimensions:
            if col not in non_bot.columns:
                continue
            vals = non_bot[col]
            if vals.std() == 0:
                print(f"    {label:35s}  r=N/A (zero variance)")
                continue

            # Point-biserial correlation (Pearson with binary variable)
            r, p = pearsonr(oc.astype(float), vals)
            sig = "*" if p < 0.05 else ""
            print(f"    {label:35s}  r={r:+.3f}  p={p:.4f} {sig}")

    # ── Top 5 PRs by composite score ────────────────────────────────────
    print(f"\n{'─' * 50}")
    print("TOP 5 PRs BY COMPOSITE SCORE (sanity check)")
    print(f"{'─' * 50}")

    top5 = non_bot.nlargest(5, "ce_composite")
    for _, row in top5.iterrows():
        title = row.get("title", "N/A")
        # Truncate long titles
        if isinstance(title, str) and len(title) > 80:
            title = title[:77] + "..."
        print(f"  [{row['ce_composite']}] {row['repo']}#{int(row['pr_number'])}")
        print(f"      {title}")
        print(f"      words={row['ce_body_words']}  q={row['ce_questions']}  "
              f"err={row['ce_error_thinking']}  unc={row['ce_uncertainty']}  "
              f"scope={row['ce_scope_awareness']}  trade={row['ce_tradeoff_reasoning']}")

    # ── Dimension prevalence ────────────────────────────────────────────
    print(f"\n{'─' * 50}")
    print("DIMENSION PREVALENCE (% of non-bot PRs with dimension > 0)")
    print(f"{'─' * 50}")

    dim_cols = ["ce_questions", "ce_error_thinking", "ce_uncertainty",
                "ce_scope_awareness", "ce_tradeoff_reasoning"]
    dim_labels = ["Questions", "Error thinking", "Uncertainty",
                  "Scope awareness", "Tradeoff reasoning"]

    for col, label in zip(dim_cols, dim_labels):
        present = (non_bot[col] > 0).sum()
        pct = present / len(non_bot) * 100
        print(f"  {label:25s}  {present:>6} ({pct:>5.1f}%)")

    print(f"\nDone. Scores saved to:")
    print(f"  {OUTPUT_CSV}")
    print(f"  {MASTER_CSV} (merged)")


if __name__ == "__main__":
    main()
