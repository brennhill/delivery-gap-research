# Study Session State — 2026-03-24

## What exists and where

### Data files (data/)
- `unified-prs.csv` — **START HERE.** 10,660 rows, 33 columns, one row per PR across 35 repos. Everything joined: repo, tier, size, spec coverage, catchrate classification, workflow tags, rework signals, rework type (alignment/implementation), LLM quality scores (7 dimensions). Rebuild with `python3 build-unified-csv.py`.
- `prs-{slug}.json` — Raw PR data per repo (reviews, files, body text)
- `upfront-{slug}.json` — Spec coverage + effectiveness + rework signals per repo
- `catchrate-{slug}.json` — Machine catch / human save / escape classification per PR
- `workflow-{slug}.json` — Workflow analysis (mechanism rates, transitions, bot detection)
- `spec-quality-{slug}.json` — **FULL LLM REVIEWS** per spec'd PR. Each entry has: 7 dimension scores, `missing` (list of what the spec lacks), `present` (list of what it does well), `reasoning` (1-2 sentence overall assessment), `change_type`, `spec_length_signal`. This is the complete AI review — the CSV only has the numeric scores.
- `aidev-repo-stats.csv` — AIDev dataset: 83K repos ranked by AI PR density
- `pr-features.csv` — 10,660 rows, 38 columns. Text-statistical features per PR (humanness signals, org context, reasoning quality, template/slop, text stats). No LLM calls needed — pure regex. Join with unified-prs.csv on (repo, pr_number).
- `engagement-{slug}.json` — **LLM formality scores** per PR (8 dimensions: lived_experience, organizational_memory, uncertainty, negative_scope, causal_reasoning, genuine_edge_cases, template_filler, overall_human_engagement + evidence quotes + classification). Columns written as `formality_*` and `fev_*` in master CSV. IN PROGRESS.

### Analysis files (study/)
- `study-findings.md` — Per-repo findings log (10 repos documented) + cross-repo patterns + 6 competing hypotheses
- `alignment-failure-analysis.md` — The "wrong thing, well-specified" finding with detection method and book implications
- `human-engagement-signals.md` — Feature design for detecting human vs AI engagement in specs. Validated signals, prompt history hypothesis, reasoning quality dimensions.
- `meta-observation.md` — This session itself as evidence: human corrections that prevented wrong conclusions, AI speed that accelerated testing.
- `score-formality.py` — LLM formality scorer (8 dimensions). Uses Haiku API. Validated on 6 known examples (3 human, 3 AI — all correctly classified). (Renamed from score-engagement.py.)
- `compute-features.py` — Statistical feature computer (38 features, no LLM). Validated against AI-tagged ground truth.
- `runner.py` — Study runner (38 repos: 30 original + 8 AI-tier)
- `score-specs.py` — LLM spec quality scorer (uses claude CLI, Haiku)
- `build-unified-csv.py` — Builds unified-prs.csv from all JSON sources
- `aggregate.py` — Original aggregation script (pre-quality-scoring)

### Key files in other repos
- `/Users/brenn/dev/delivery-gap-signals/` — Shared library (sources, workflow analyzer, bot detection)
- `/Users/brenn/dev/upfront/` — UPFRONT tool (coverage, quality, effectiveness)
- `/Users/brenn/dev/ai-augmented-dev/research/codex.md` — Master evidence compendium (A066-A070 = AI agent papers)

## Repos completed (10/38)

| # | Repo | Tier | PRs | Quality Scored | Status |
|---|------|------|-----|----------------|--------|
| 1 | cli/cli | B | 86 | 39 | Done |
| 2 | kubernetes/kubernetes | A | 200 | 56 | Done |
| 3 | cockroachdb/cockroach | A | 500 | — | PRs fetched, needs scoring |
| 4 | microsoft/vscode | A | 200 | — | PRs fetched, needs scoring |
| 5 | pingcap/tidb | A | 381 | — | PRs fetched, needs scoring |
| 6 | apache/arrow | A | 204 | — | PRs fetched, needs scoring |
| 7 | promptfoo/promptfoo | AI | 500 | 208 | Done |
| 8 | mendableai/firecrawl | AI | 285 | 56 | Done |
| 9 | calcom/cal.com | AI | 365 | 83 | Done |
| 10 | mlflow/mlflow | AI | 500 | 86 | Done |
| 11 | novuhq/novu | AI | 350 | 10 | PRs fetched, scoring partial (resume) |
| 12 | antiwork/gumroad | AI | 252 | — | PRs fetched, needs scoring |
| 13 | dotnet/aspire | AI | 500 | — | PRs fetched, needs scoring |
| 14 | liam-hq/liam | AI | 3 | 3 | Done (only 3 PRs, all Renovate bots — not useful) |

3 repos failed to fetch (cpython, uv, supabase — REST adapter JSON parse errors on large repos). 35 of 38 succeeded.

score-specs.py now has resume support + incremental saves + API support (ANTHROPIC_API_KEY). Scoring is running via API (~$2-3 total for all specs). Run `python3 score-specs.py` to resume, then `python3 build-unified-csv.py` to rebuild the CSV.

## Key findings so far

### Dataset size (as of 2026-03-24)
- 35 repos, 10,660 PRs, 3,033 spec'd (28%)
- 861 quality scored (of 3,746 scoreable), ~2,885 remaining (~24 min via API)
- 1,251 reworked PRs
- 3 repos failed to fetch: cpython, uv, supabase (REST adapter JSON parse bug)

### 1. Quality gradient is FLAT (n=472, 5 repos)
- HIGH quality specs: 16.1% rework (n=56)
- MEDIUM: 14.2% (n=288)
- LOW: 13.3% (n=128)
- NO SPEC: 9.6% (n=2153)
- ALL spec tiers rework MORE than no-spec. Quality gradient is slightly inverted.

### 2. Alignment failures dominate AI repos
- AI-tier repos: 63% of rework is alignment failures (wrong thing built)
- Traditional repos: 28% alignment failures
- Alignment failures have BETTER spec quality than implementation fixes (+7pp overall)
- This is the "wrong thing, well-specified" pattern — CONFIRMED at n=67

### 3. NO dimension predicts less rework
- error_states: REVERSE (-5.3pp) — more error detail → more rework
- acceptance_criteria: REVERSE (-5.6pp) — more AC → more rework
- behavioral_specificity: dropped to +1.4pp with more data (NO EFFECT)
- outcome_clarity, scope_boundaries: NO EFFECT
- The raised-bar hypothesis is the best explanation: better specs catch more problems pre-merge

### 4. Six competing hypotheses (see study-findings.md)
(a) Specs useless (null) — partially supported by no-spec outperforming
(b) Review friction — specs give reviewers something to reject against
(c) Raised bar — specs catch problems that would have escaped without them
(d) Specs raise HSR — testable via per-PR HSR split
(e) Yolo spec — AI writes spec, human doesn't read it, builds wrong thing anyway
(f) Wrong thing well-specified — CONFIRMED: alignment failures have higher quality specs

### 5. Bot detection expanded
Added to all 4 detection locations: copilot-pull-request-reviewer, copilot-swe-agent, pantheon-ai, promptfoo-scanner, cubic-dev-ai, devin-ai-integration. Prefix matching: copilot-, coderabbit-, sourcery-, pantheon-, devin-.

### 6. Tool fixes applied this session
- GraphQL `$since` variable removed (was declared but unused, GitHub started enforcing)
- `gh pr list --search "merged:>=DATE"` fails silently on some repos → added pure GraphQL fallback
- Bot detection expanded (6 new bots + prefix matching)

## To resume
1. Run `python3 build-unified-csv.py` to rebuild the CSV with any new quality scores
2. Check `ls data/spec-quality-*.json` to see which repos have quality scores
3. Run `python3 score-specs.py --repo {slug}` to score remaining repos
4. Run `python3 runner.py --repo {owner/repo}` to add more repos to the study
5. The 6 hypotheses in study-findings.md need more data to resolve — especially (c) vs (e)

## TODOs

1. **Run formality scorer** — `python3 score-formality.py` (can run parallel with quality scorer)
2. **Fetch review comment body text** — re-fetch all repos with `body` added to the reviews GraphQL query. Review text is where engagement signal lives ("this doesn't handle...", "LGTM", "per the spec..."). Currently we only have review state, not content. This enables comment-level engagement scoring.

2. **Fetch author self-comments on PRs** — author responding to review feedback = engagement signal. Not currently captured.

3. **Fix REST adapter JSON parse errors** — cpython, uv, supabase all fail with truncated JSON on large repos. Need chunked response handling.

## What to test next
- Run quality scoring on kubernetes, cockroach, vscode (large traditional repos) for comparison
- Test hypothesis (d): split HSR by spec'd vs unspec'd per PR
- Test hypothesis (c): do spec'd PRs have fewer POST-merge escapes?
- Finish remaining 28 repos in runner.py
- Consider: is behavioral_specificity the only dimension that matters? If so, the book's framing should emphasize concrete behavioral descriptions over formal spec structure
