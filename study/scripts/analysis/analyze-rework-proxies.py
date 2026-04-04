#!/usr/bin/env python3
"""Analyze rework proxy signals from existing PR data.

Tests four hypotheses from rework-definition-proxy.md:
1. Does CI strictness trade off against post-merge rework (reverts)?
2. Does review depth (rounds) trade off against post-merge rework?
3. Does PR size predict review rounds AND reverts?
4. Does AI adoption predict review friction or abandonment patterns?

Plus descriptive stats on rework signals by repo.

Usage:
    python3 analyze-rework-proxies.py
"""

import json
import re
from pathlib import Path
from collections import defaultdict
from datetime import datetime, timezone

import numpy as np
from scipy import stats

DATA_DIR = Path(__file__).resolve().parent / "data"

# ═══════════════════════════════════════════════════════════════════════
# LOAD DATA
# ═══════════════════════════════════════════════════════════════════════

REVERT_RE = re.compile(r'^Revert\s+"', re.IGNORECASE)
AI_TAG_RE = re.compile(
    r'(?:co-authored-by:.*(?:copilot|claude|cursor|devin|coderabbit)|'
    r'Generated with|🤖|CURSOR_AGENT|auto-generated)',
    re.IGNORECASE,
)

BOT_AUTHORS = {
    'robobun', 'denobot', 'nextjs-bot', 'vercel-release-bot', 'ti-chi-bot',
    'dotnet-bot', 'renovate', 'dependabot', 'github-actions', 'clerk-cookie',
    'copilot-swe-agent', 'devin-ai-integration', 'cursor',
}


def is_ai_tagged(pr):
    """Check if PR has AI co-author tags."""
    body = pr.get("body") or ""
    title = pr.get("title") or ""
    return bool(AI_TAG_RE.search(body) or AI_TAG_RE.search(title))


def is_revert(pr):
    """Check if this PR is a revert."""
    title = pr.get("title") or ""
    return bool(REVERT_RE.match(title)) or title.lower().startswith("revert ")


def parse_ts(s):
    """Parse ISO timestamp."""
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def human_reviews(pr):
    """Get non-bot reviews."""
    return [r for r in pr.get("reviews", []) if not r.get("is_bot", False)]


def changes_requested_count(pr):
    """Count CHANGES_REQUESTED events from human reviewers."""
    return sum(1 for r in human_reviews(pr) if r.get("state") == "changes_requested")


def review_round_count(pr):
    """Count review rounds: each CHANGES_REQUESTED or approval is a round."""
    reviews = human_reviews(pr)
    return sum(1 for r in reviews if r.get("state") in ("changes_requested", "approved"))


def time_to_first_review_hours(pr):
    """Hours from PR creation to first human review."""
    created = parse_ts(pr.get("created_at"))
    if not created:
        return None
    reviews = human_reviews(pr)
    if not reviews:
        return None
    first = min(parse_ts(r["submitted_at"]) for r in reviews if parse_ts(r.get("submitted_at")))
    if not first:
        return None
    return (first - created).total_seconds() / 3600


def pr_open_hours(pr):
    """Hours from creation to merge."""
    created = parse_ts(pr.get("created_at"))
    merged = parse_ts(pr.get("merged_at"))
    if not created or not merged:
        return None
    return (merged - created).total_seconds() / 3600


def pr_size(pr):
    """Total lines changed."""
    return (pr.get("additions") or 0) + (pr.get("deletions") or 0)


# ═══════════════════════════════════════════════════════════════════════
# LOAD AND PROCESS
# ═══════════════════════════════════════════════════════════════════════

print("Loading PR data...")

repos = {}
all_prs = []

for f in sorted(DATA_DIR.glob("prs-*.json")):
    repo_name = f.stem.replace("prs-", "").replace("-", "/", 1)
    data = json.loads(f.read_text())
    # Filter out bot-authored PRs
    data = [pr for pr in data if pr.get("author", "").lower() not in BOT_AUTHORS]
    repos[repo_name] = data
    all_prs.extend(data)

print(f"Loaded {len(all_prs)} human-authored PRs across {len(repos)} repos\n")

# ═══════════════════════════════════════════════════════════════════════
# PER-REPO STATS
# ═══════════════════════════════════════════════════════════════════════

print("=" * 80)
print("PER-REPO REWORK PROXY SIGNALS")
print("=" * 80)

repo_stats = {}

for repo_name, prs in sorted(repos.items()):
    n = len(prs)
    if n < 30:
        continue

    n_reverts = sum(1 for pr in prs if is_revert(pr))
    n_cr = sum(1 for pr in prs if changes_requested_count(pr) > 0)
    n_multi_cr = sum(1 for pr in prs if changes_requested_count(pr) >= 2)
    n_ci_fail = sum(1 for pr in prs if pr.get("ci_status") == "failed")
    n_ci_present = sum(1 for pr in prs if pr.get("ci_status") and pr["ci_status"] != "no_checks")
    n_ai = sum(1 for pr in prs if is_ai_tagged(pr))

    sizes = [pr_size(pr) for pr in prs]
    median_size = np.median(sizes)
    open_hours = [pr_open_hours(pr) for pr in prs if pr_open_hours(pr) is not None]
    median_open = np.median(open_hours) if open_hours else 0

    review_rounds = [review_round_count(pr) for pr in prs]
    median_rounds = np.median(review_rounds)

    revert_rate = n_reverts / n * 100
    cr_rate = n_cr / n * 100
    ci_fail_rate = n_ci_fail / max(n_ci_present, 1) * 100
    ai_rate = n_ai / n * 100

    repo_stats[repo_name] = {
        "n": n,
        "revert_rate": revert_rate,
        "cr_rate": cr_rate,
        "multi_cr_rate": n_multi_cr / n * 100,
        "ci_fail_rate": ci_fail_rate,
        "ai_rate": ai_rate,
        "median_size": median_size,
        "median_open_hours": median_open,
        "median_review_rounds": median_rounds,
    }

# Print summary table
print(f"\n{'Repo':<40s} {'PRs':>5s} {'Revert%':>8s} {'CR%':>6s} {'CI Fail%':>9s} {'AI%':>6s} {'Med Size':>9s} {'Med Open h':>11s} {'Med Rnds':>9s}")
print("-" * 115)
for repo, s in sorted(repo_stats.items(), key=lambda x: x[1]["revert_rate"]):
    print(f"{repo:<40s} {s['n']:>5d} {s['revert_rate']:>7.1f}% {s['cr_rate']:>5.1f}% {s['ci_fail_rate']:>8.1f}% {s['ai_rate']:>5.1f}% {s['median_size']:>9.0f} {s['median_open_hours']:>10.1f} {s['median_review_rounds']:>9.1f}")

# ═══════════════════════════════════════════════════════════════════════
# HYPOTHESIS 1: CI strictness vs revert rate
# ═══════════════════════════════════════════════════════════════════════

print("\n" + "=" * 80)
print("HYPOTHESIS 1: Does CI strictness reduce post-merge rework (reverts)?")
print("=" * 80)

ci_rates = [s["ci_fail_rate"] for s in repo_stats.values()]
revert_rates = [s["revert_rate"] for s in repo_stats.values()]

rho, p = stats.spearmanr(ci_rates, revert_rates)
print(f"\nSpearman correlation: ρ = {rho:.3f}, p = {p:.4f}")
print(f"N = {len(ci_rates)} repos")
if p < 0.05:
    direction = "NEGATIVE (stricter CI → less rework)" if rho < 0 else "POSITIVE (stricter CI → more rework — unexpected)"
    print(f"SIGNIFICANT: {direction}")
else:
    print("NOT SIGNIFICANT at p < 0.05")

# ═══════════════════════════════════════════════════════════════════════
# HYPOTHESIS 2: Review depth vs revert rate
# ═══════════════════════════════════════════════════════════════════════

print("\n" + "=" * 80)
print("HYPOTHESIS 2: Does review depth (CR rate) reduce post-merge rework?")
print("=" * 80)

cr_rates = [s["cr_rate"] for s in repo_stats.values()]
rho, p = stats.spearmanr(cr_rates, revert_rates)
print(f"\nSpearman correlation: ρ = {rho:.3f}, p = {p:.4f}")
print(f"N = {len(cr_rates)} repos")
if p < 0.05:
    direction = "NEGATIVE (more review friction → fewer reverts)" if rho < 0 else "POSITIVE (more review friction → more reverts)"
    print(f"SIGNIFICANT: {direction}")
else:
    print("NOT SIGNIFICANT at p < 0.05")

# ═══════════════════════════════════════════════════════════════════════
# HYPOTHESIS 3: PR size predicts review rounds AND reverts
# ═══════════════════════════════════════════════════════════════════════

print("\n" + "=" * 80)
print("HYPOTHESIS 3: Does PR size predict review friction and reverts?")
print("=" * 80)

# Bucket PRs by size
size_buckets = {
    "small (<100)": [],
    "medium (100-400)": [],
    "large (400-1000)": [],
    "xlarge (1000+)": [],
}

for pr in all_prs:
    s = pr_size(pr)
    if s < 100:
        size_buckets["small (<100)"].append(pr)
    elif s < 400:
        size_buckets["medium (100-400)"].append(pr)
    elif s < 1000:
        size_buckets["large (400-1000)"].append(pr)
    else:
        size_buckets["xlarge (1000+)"].append(pr)

print(f"\n{'Size Bucket':<20s} {'N':>6s} {'Avg CR':>7s} {'CR Rate':>8s} {'Revert%':>8s} {'Med Open h':>11s}")
print("-" * 65)
for bucket, prs in size_buckets.items():
    n = len(prs)
    avg_cr = np.mean([changes_requested_count(pr) for pr in prs])
    cr_rate = sum(1 for pr in prs if changes_requested_count(pr) > 0) / max(n, 1) * 100
    rev_rate = sum(1 for pr in prs if is_revert(pr)) / max(n, 1) * 100
    opens = [pr_open_hours(pr) for pr in prs if pr_open_hours(pr) is not None]
    med_open = np.median(opens) if opens else 0
    print(f"{bucket:<20s} {n:>6d} {avg_cr:>7.3f} {cr_rate:>7.1f}% {rev_rate:>7.1f}% {med_open:>10.1f}")

# Correlation at PR level
all_sizes = [pr_size(pr) for pr in all_prs]
all_cr_counts = [changes_requested_count(pr) for pr in all_prs]
rho_size_cr, p_size_cr = stats.spearmanr(all_sizes, all_cr_counts)
print(f"\nPR size vs CR count (PR-level): ρ = {rho_size_cr:.3f}, p = {p_size_cr:.2e}")

# ═══════════════════════════════════════════════════════════════════════
# HYPOTHESIS 4: AI adoption vs review friction
# ═══════════════════════════════════════════════════════════════════════

print("\n" + "=" * 80)
print("HYPOTHESIS 4: Does AI adoption predict review friction?")
print("=" * 80)

ai_prs = [pr for pr in all_prs if is_ai_tagged(pr)]
non_ai_prs = [pr for pr in all_prs if not is_ai_tagged(pr)]

print(f"\nAI-tagged PRs: {len(ai_prs)}")
print(f"Non-AI PRs: {len(non_ai_prs)}")

if len(ai_prs) > 10:
    ai_cr_rate = sum(1 for pr in ai_prs if changes_requested_count(pr) > 0) / len(ai_prs) * 100
    non_ai_cr_rate = sum(1 for pr in non_ai_prs if changes_requested_count(pr) > 0) / len(non_ai_prs) * 100

    ai_rev_rate = sum(1 for pr in ai_prs if is_revert(pr)) / len(ai_prs) * 100
    non_ai_rev_rate = sum(1 for pr in non_ai_prs if is_revert(pr)) / len(non_ai_prs) * 100

    ai_sizes = [pr_size(pr) for pr in ai_prs]
    non_ai_sizes = [pr_size(pr) for pr in non_ai_prs]

    ai_opens = [pr_open_hours(pr) for pr in ai_prs if pr_open_hours(pr) is not None]
    non_ai_opens = [pr_open_hours(pr) for pr in non_ai_prs if pr_open_hours(pr) is not None]

    print(f"\n{'Metric':<30s} {'AI-tagged':>12s} {'Non-AI':>12s} {'Delta':>12s}")
    print("-" * 70)
    print(f"{'CR rate':<30s} {ai_cr_rate:>11.1f}% {non_ai_cr_rate:>11.1f}% {ai_cr_rate - non_ai_cr_rate:>+11.1f}pp")
    print(f"{'Revert rate':<30s} {ai_rev_rate:>11.1f}% {non_ai_rev_rate:>11.1f}% {ai_rev_rate - non_ai_rev_rate:>+11.1f}pp")
    print(f"{'Median PR size':<30s} {np.median(ai_sizes):>12.0f} {np.median(non_ai_sizes):>12.0f} {np.median(ai_sizes) - np.median(non_ai_sizes):>+12.0f}")
    print(f"{'Median open hours':<30s} {np.median(ai_opens):>12.1f} {np.median(non_ai_opens):>12.1f} {np.median(ai_opens) - np.median(non_ai_opens):>+12.1f}")
else:
    print("Too few AI-tagged PRs for comparison")

# ═══════════════════════════════════════════════════════════════════════
# REPO-LEVEL CORRELATION MATRIX
# ═══════════════════════════════════════════════════════════════════════

print("\n" + "=" * 80)
print("REPO-LEVEL CORRELATION MATRIX (Spearman)")
print("=" * 80)

metrics = {
    "revert_rate": [s["revert_rate"] for s in repo_stats.values()],
    "cr_rate": [s["cr_rate"] for s in repo_stats.values()],
    "ci_fail_rate": [s["ci_fail_rate"] for s in repo_stats.values()],
    "ai_rate": [s["ai_rate"] for s in repo_stats.values()],
    "median_size": [s["median_size"] for s in repo_stats.values()],
    "median_open_hours": [s["median_open_hours"] for s in repo_stats.values()],
}

metric_names = list(metrics.keys())
print(f"\n{'':>20s}", end="")
for name in metric_names:
    print(f"{name:>16s}", end="")
print()

for name1 in metric_names:
    print(f"{name1:>20s}", end="")
    for name2 in metric_names:
        if name1 == name2:
            print(f"{'---':>16s}", end="")
        else:
            rho, p = stats.spearmanr(metrics[name1], metrics[name2])
            sig = "*" if p < 0.05 else " "
            print(f"{rho:>+.2f} (p={p:.2f}){sig:>1s}".rjust(16), end="")
    print()

print(f"\nN = {len(repo_stats)} repos. * = p < 0.05")

# ═══════════════════════════════════════════════════════════════════════
# REVIEW TIME ANALYSIS
# ═══════════════════════════════════════════════════════════════════════

print("\n" + "=" * 80)
print("REVIEW TIME DECOMPOSITION")
print("=" * 80)

# For PRs with reviews, compute time to first review by size bucket
for bucket, prs in size_buckets.items():
    ttfr = [time_to_first_review_hours(pr) for pr in prs if time_to_first_review_hours(pr) is not None]
    if ttfr:
        print(f"{bucket:<20s}  median time to first review: {np.median(ttfr):.1f}h  (N={len(ttfr)})")

# Long-lived PRs: open > 72 hours
long_prs = [pr for pr in all_prs if (pr_open_hours(pr) or 0) > 72]
short_prs = [pr for pr in all_prs if 0 < (pr_open_hours(pr) or 0) <= 24]

if long_prs and short_prs:
    long_cr = sum(1 for pr in long_prs if changes_requested_count(pr) > 0) / len(long_prs) * 100
    short_cr = sum(1 for pr in short_prs if changes_requested_count(pr) > 0) / len(short_prs) * 100
    long_rev = sum(1 for pr in long_prs if is_revert(pr)) / len(long_prs) * 100
    short_rev = sum(1 for pr in short_prs if is_revert(pr)) / len(short_prs) * 100

    print(f"\nPRs open >72h: {len(long_prs)} ({long_cr:.1f}% CR rate, {long_rev:.1f}% revert rate)")
    print(f"PRs open ≤24h: {len(short_prs)} ({short_cr:.1f}% CR rate, {short_rev:.1f}% revert rate)")

print("\n" + "=" * 80)
print("DONE")
print("=" * 80)
