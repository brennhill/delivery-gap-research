# Rework Definition and Measurement Proxies

## The Definition

Rework is work that must be redone because you built the wrong thing, or because what you built was incomplete or buggy enough to require significant correction. AI-assisted development increases all forms of rework because generation speed outpaces verification capacity.

Four signals, each caught at a different point:

1. **Pre-merge rework** — long review cycles with many patches. The review process caught problems before they shipped.
2. **Post-merge rework** — reverts, follow-up fix PRs, reopened tickets. You shipped something that did not hold up.
3. **Code churn** — lines rewritten within 14-30 days of being authored. You replaced recently written code.
4. **Abandoned work** — changes that were started but never shipped, or shipped and later fully killed. The entire investment produced zero value.

## The Measurement Thesis

Don't measure the spec. Measure the downstream signals.

- **Rework rate** tells you whether the thinking happened.
- **Change failure rate** tells you whether the gates caught what the thinking missed.
- High rework + specs exist = specs are paperwork, thinking didn't happen.
- High rework + no specs = nobody thought about it, predictable.
- Low rework + specs exist = the forcing function is working.
- Low rework + no specs = either trivial work or natural discipline (rare).

## Proxies Extractable from Public GitHub

### High confidence (counting API events, no classification)

| Signal | GitHub Source | Precision | Status |
|--------|-------------|-----------|--------|
| Review rounds | Review events with state CHANGES_REQUESTED, count per PR | ~100% | Need to fetch |
| Review response time | Time between author push and reviewer response | ~100% | Need to fetch |
| Review iteration time | Time between reviewer feedback and author's next push | ~100% | Need to fetch |
| Total review calendar time | PR created_at to final approval timestamp | ~100% | Likely derivable from existing data |
| Revert rate | Git commit messages matching revert patterns | 100% | Already validated in CatchRate |
| CI failure rate | GitHub status checks API, pass/fail per PR | ~100% | Need to fetch |
| PR size | additions + deletions from GitHub API | 100% | Already have |
| Abandonment rate | PRs closed without merge, open >7 days, >50 lines changed | ~95% | Likely have the fields |

### Medium confidence (requires classification)

| Signal | GitHub Source | Precision | Status |
|--------|-------------|-----------|--------|
| Fix-follow-up rate | PR body text referencing prior PRs ("fixes #N", "follow-up to #N") | 67% | Already validated in CatchRate (HIGH tier) |

### Not extractable from public GitHub

| Signal | Why not | Alternative |
|--------|---------|-------------|
| Ticket reopens | No Jira/Linear access for OSS repos | Only available for internal/private repos |
| Code churn (line-level) | Requires cloning every repo + git diff analysis over time windows | Heavy but feasible; GitClear/LinearB do this commercially |
| True change failure rate | Requires deployment data, not just merge data | Use revert rate as proxy |
| Abandoned work (post-ship) | "Feature flagged off" or "feature killed" not visible in git | Only PRs closed without merge are visible |

## Review Time Decomposition

Review round count alone misses the time dimension:

- **2 rounds in 30 minutes** = quick feedback loop, healthy
- **2 rounds over 5 days** = either hard review (large diff, complex domain) or queue pressure (reviewer overload)
- **4 rounds in 2 hours** = active iteration, probably good
- **4 rounds over 2 weeks** = something fundamentally wrong with the change

Decompose into:
- **Response time** (push → review): queue pressure signal. Long response time = reviewer overload.
- **Iteration time** (review → next push): complexity signal. Long iteration time = author struggling with feedback, change was likely underspecified.
- **Total calendar time** (open → approved): overall friction.

If response time is long but iteration time is short, the problem is reviewer capacity, not change quality. If iteration time is long, the change was probably underspecified or the wrong approach.

Edge case: PR takes 2 rounds over 5 days and the diff is 40 lines. Nobody cares about this change — it's sitting in a queue because it's not important enough to prioritize. That's a different kind of waste: effort that shouldn't have been started. Connects to intent clarity — was this worth building at all?

## Existing Tools That Track Subsets

| Layer | Tools | What they measure |
|-------|-------|-------------------|
| Pre-merge rework | Graphite (review cycles), Jellyfish (rework time) | Review rounds, time in iteration |
| Code-level rework | LinearB (21d window), GitClear (14d), Pluralsight Flow (30d) | Lines rewritten after commit |
| Post-deploy rework | DORA 5th metric (2024), Faros, Swarmia | Unplanned deployments to fix bugs |
| Ticket-level rework | Jira plugins (Reopening Counter) | Issues reopened after resolution |

No tool currently tracks all four signals together.

## What We Already Have (43-repo study)

- 23,967 PRs across 43 open-source repositories
- PR metadata: created_at, merged_at, closed_at, additions, deletions, body text
- Revert detection (100% precision)
- Fix-follow-up detection via PR body references (67% precision, HIGH tier only)
- AI detection (co-author tags + classifier)
- Spec detection (upfront scores)

## What We'd Need to Fetch

For the 43 existing repos (~24K PRs):

1. **Review events** — `GET /repos/{owner}/{repo}/pulls/{number}/reviews`
   - Gives: reviewer, state (APPROVED, CHANGES_REQUESTED, COMMENTED), submitted_at
   - ~24K API calls, rate-limited at 5K/hour with auth = ~5 hours

2. **PR commit timestamps** — `GET /repos/{owner}/{repo}/pulls/{number}/commits`
   - Gives: commit SHA, timestamp (for computing iteration time between review and next push)
   - ~24K API calls, another ~5 hours

3. **CI status checks** — `GET /repos/{owner}/{repo}/commits/{sha}/check-runs`
   - Gives: conclusion (success, failure, etc.) per commit
   - Would need for merge commit or last PR commit
   - ~24K API calls, another ~5 hours

Total: ~15 hours of API fetching. Could parallelize across repos.

## Research Questions

1. Does pre-merge rework (review rounds) correlate with post-merge rework (reverts/fixes)?
   - If yes: review friction is a leading indicator of escape risk.
   - If no: they measure different things (review catches problems vs. review creates friction).

2. Does review response time predict rework?
   - If long response times correlate with more rework: reviewer overload causes quality degradation.
   - If not: queue time is annoying but not dangerous.

3. Does abandonment rate correlate with AI adoption?
   - Are AI-generated PRs more likely to be closed without merge?
   - If yes: AI generates more speculative work that doesn't survive review.

4. Do repos with higher CI failure rates have lower post-merge rework?
   - Stricter gates should catch more pre-merge, reducing post-merge rework.
   - This is the machine-catch-rate-reduces-human-save-rate thesis.

5. Does PR size predict review round count?
   - Expected: yes. Larger PRs = more rounds. But is there a threshold effect?
   - The SmartBear 400-line finding should be visible in review round data.

## First Run Results (2026-03-28)

Ran `analyze-rework-proxies.py` on 23,750 human-authored PRs across 43 repos. Full output in `data/rework-proxy-results.txt`.

### What worked

**PR size predicts review friction (PR-level, N=23,750).** ρ = 0.115, p = 5.76e-71.
- Small PRs (<100 lines): 2.3% get CHANGES_REQUESTED, median 1.2h to first review
- Medium (100-400): 5.6% CR rate, 3.2h to first review
- Large (400-1000): 8.0% CR rate, 4.5h to first review
- XL (1000+): 7.2% CR rate, 8.4h to first review
- Replicates the SmartBear finding with different data and a different signal.

**AI adoption is a coin flip for rework.** AI-tagged PRs: 3.9% CR rate, 0.4% revert rate. Non-AI: 4.1% CR rate, 0.7% revert rate. No meaningful difference. Confirms within-author coin flip from earlier study.

**Two significant repo-level correlations:**
- CR rate ↔ median open hours (ρ = +0.44, p < 0.01) — review friction lengthens PR lifetime
- CI fail rate ↔ AI rate (ρ = +0.50, p < 0.01) — AI-heavy repos have higher CI failure rates

### What didn't work

**Repo-level correlations with revert rate: nothing significant.** N=43 is too small.
- CI strictness vs reverts: ρ = -0.18, p = 0.24 (right direction, no power)
- Review depth vs reverts: ρ = -0.14, p = 0.38 (right direction, no power)
- AI adoption vs reverts: ρ = -0.12, p = 0.45 (no signal)
- PR size vs reverts: ρ = -0.14, p = 0.38 (no signal)

### Interpretation

The repo-level sample (N=43) cannot detect moderate effects. The PR-level sample (N=23,750) CAN detect effects but only for signals that vary at the PR level (size, review rounds). The clean findings are about mechanical relationships (bigger PRs → more friction → longer lifetimes) not about the Triangle's vertices predicting outcomes.

The revert rate is too sparse (~0.6% overall) and too noisy at the repo level to correlate with anything at N=43. We'd need either more repos (100+) or a different outcome metric.

### Next steps

1. **Fetch abandoned PRs** (closed without merge) — this is a much higher-frequency signal than reverts and may show effects that reverts are too sparse to detect.
2. **Within-repo before/after** — for repos where process infrastructure appeared (PR templates, CLAUDE.md), compare rework metrics before and after.
3. **Larger sample** — the 56 additional repos identified in `fetch-new-repos.py` were never fetched. Adding them would roughly double N.
