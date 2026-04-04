# Data Fixes TODO

Status as of 2026-03-26. Nothing below is optional — all must be done before publishing.

## Running Now

- [ ] **Enforcement scoring** (`score-enforcement.py`) — 20/74 repos done, hit GitHub rate limit. Resume when limit resets. Scores enforcement depth (Tier 0-3) from pre-commit configs, husky hooks, and CI workflows.
- [ ] **PR re-fetch** (`refetch-incomplete.py`) — 11/15 repos done, hit rate limit. cockroachdb, django, elastic (504), envoyproxy, facebook/react, grafana (504), kubernetes, n8n, prometheus done. Remaining: python/cpython, rust-lang/rust, calcom, oven-sh/bun, PostHog.
- [ ] **Scorer validation** (`validate-scorer.py`) — haiku + sonnet + opus all scored. Results show 36% classification agreement. Engagement score does NOT predict rework (direction flips by model).

## BLOCKING: CatchRate Validation

Every finding depends on rework/escape rates being accurate. CatchRate links "fix" PRs to "target" PRs based on file overlap and timing. False positives: two PRs touching the same files that aren't actually a fix relationship. In a repo with 500 PRs all touching `src/auth.ts`, many will have coincidental file overlap.

**We have zero precision/recall data.** This must be validated before publishing anything.

Validation plan:
- [ ] Pull 100 random "reworked=True" PR pairs (target + source)
- [ ] Pull 100 random "reworked=False" PRs
- [ ] For each pair: manually check on GitHub — is the source actually a fix for the target?
- [ ] Could use LLM for first pass: show target PR title/body + source PR title/body, ask "is this a fix?"
- [ ] Report precision (% of flagged pairs that are real fixes) and recall (% of real fixes caught)
- [ ] If precision < 80%, rework rates are inflated and findings weaken
- [ ] Check if false positive rate varies by repo (high-velocity repos may have more coincidental overlap)

## Must Run (in order, after rate limit resets)

1. [ ] **Finish enforcement scoring** — resume `score-enforcement.py` (54 repos remaining)
2. [ ] **Finish PR re-fetch** — resume `refetch-incomplete.py` (4 repos remaining)
3. [ ] **Recompute features** — `python3 compute-features.py` (adds 12 StyloAI features + fixes bot list: renovate, github-actions, clerk-cookie, cursor, devin now classified as bots)
4. [ ] **Rebuild master CSV** — `python3 build-master-csv.py`
5. [ ] **Retrain classifier** — `python3 train-classifier.py` (proper holdout, noise filter, 20 StyloAI features)
6. [ ] **Score cognitive questions** — `python3 score-questions.py` (LLM-scored questions on 2023 + current data, same method both periods). Needs ANTHROPIC_API_KEY.
7. [ ] **Test enforcement depth vs outcomes** — correlate enforcement scores with rework/escape at repo level
8. [ ] **Expand to 85+ repos** — fetch PRs for the 31 new candidate repos to get statistical power

## Findings That Survived Red-Teaming

1. **Two-bucket classification works.** Human (99% accurate) / Augmented (tagged OR classifier). No claim about HOW AI was involved.
2. **Augmented PRs have more defects.** +2.6pp rework, +1.1pp escape. Direction holds in 28/39 repos.
3. **Within-author is a coin flip.** 63 authors, 49% worse with AI, 41% better, median delta 0.0pp. Effect is NOT individual.
4. **Specs don't help within outcome quartiles.** No within-tier effect. Low tier: specs +4.5pp WORSE. Cultural indicator, not causal.

## Findings That Were Killed

- **Tier classification** — circular (defined by outcome, "predicted" outcome)
- **Pooled PR p-values** — fake (real N≈42, not 24K). ALL chi-squared p-values are invalid
- **Historical attention collapse** — artifact of different detection methods + template confound
- **Comment density predicts outcomes** — only on 33/42 repos (9 missing data). Waiting on re-fetch.
- **LLM engagement score predicts rework** — direction flips by model. Not a real signal.
- **Pre-commit predicts outcomes** — N=5 treatment group, maturity confound. calcom/pnpm have husky but high rework. Enforcement PRESENCE doesn't predict — enforcement DEPTH might.
- **Infra breadth predicts outcomes** — flat (ρ=-0.089, p=0.58). File presence ≠ enforcement.

## Key Methodological Lessons

- **Don't define tiers by outcomes then predict outcomes.** Use process as IV, outcomes as DV.
- **Pooled PR tests violate independence.** Real N = number of repos. Use repo-level Spearman.
- **LLM scores are model-dependent.** 36% classification agreement across haiku/sonnet/opus.
- **File presence ≠ enforcement.** calcom has 5 infra signals and 23% rework. Only enforcement DEPTH matters.
- **Two buckets: Human/Augmented.** Classifier detects human text (99%). Can't distinguish "human used AI for code" from "human did everything."
- **Proper holdout.** Controls never in training. Report contaminated AND uncontaminated AUC.
- **Noise is 14.4% of data.** Filter dep bumps, releases, reverts, automation bots, empty bodies.

## Critical Next Test: Triangle as Three-Legged Stool

The book claims all three vertices are load-bearing. We tested each alone — none reliably predicts. But the thesis is you need ALL THREE. This matches DORA 2025: AI is a "mirror and multiplier" — amplifies whatever exists. Teams with all foundations saw gains, teams missing any foundation saw -7.2% delivery stability.

**Test design:**
1. Score each vertex independently per repo:
   - **Spec vertex:** spec rate (have this)
   - **Eval vertex:** enforcement depth across tiers (scoring now)
   - **Cost vertex:** proxy TBD — maybe review iteration rate, CI-blocks-merge, comment density (someone is watching the numbers)
2. Test: does the COMBINATION predict outcomes when no single vertex does?
3. Specifically: repos missing ANY vertex should have high rework regardless of the other two
4. If this holds: the triangle is a three-legged stool, not three independent variables. Removing any leg collapses it.

**Why this matters:** Single-variable tests failing doesn't disprove the thesis — it SUPPORTS the stool model. Specs alone don't help (one leg). Infra alone doesn't help (one leg). Culture alone barely helps (one leg). But all three together might be the load-bearing combination. That would also explain the DORA finding — their seven "foundational capabilities" are the same stool from a different angle.

**Prediction to falsify:** If repos scoring high on all three vertices DON'T have lower rework than repos scoring high on only one or two, the stool model fails and the vertices are not synergistic.

## Key Finding: Enforcement vs Advisory (2026-03-26)

**Enforcement depth predicts rework: ρ=-0.306, p=0.049, N=42.**
**CI depth does NOT predict: ρ=+0.006, p=0.97.**

Same checks, different enforcement model. Checks you can skip are being skipped.
PR size distribution also flat — small batches don't differentiate.

The finding isn't "what checks do you have" — it's "which checks do you ENFORCE."
Advisory verification is decoration. Enforcement verification is infrastructure.

## Open Questions

- Does enforcement DEPTH (Tier 0-3 coverage) predict outcomes? Scoring in progress.
- Does the two-bucket finding hold after noise filtering + bot reclassification? Need to recompute.
- Are there enforcement patterns in elite repos that DON'T fit Tier 0-4? Look for unknown categories in CI configs.
- Can we get branch protection API data? Most repos returned "unknown" — may need collaborator access.
- Is 85 repos achievable? 31 new candidates identified. Need to fetch PRs + score enforcement.
- Does cognitive_questions (LLM-scored) show a real historical change? Need to run score-questions.py.

## New Repo Candidates (for expansion to 85+)

### With enforcement hooks (pre-commit)
pallets/flask, fastapi/fastapi, pydantic/pydantic, celery/celery, pytest-dev/pytest, apache/airflow, dagster-io/dagster, prefecthq/prefect, dbt-labs/dbt-core, sqlalchemy/sqlalchemy, open-webui/open-webui, langflow-ai/langflow, chroma-core/chroma, weaviate/weaviate, vllm-project/vllm, ray-project/ray

### Without enforcement hooks
redis/redis, clickhouse/clickhouse, vitessio/vitess, etcd-io/etcd, tikv/tikv, rails/rails, nestjs/nest, vitejs/vite, hashicorp/terraform, hashicorp/vault, ollama/ollama, flutter/flutter, strapi/strapi, nocodb/nocodb, minio/minio

### With husky (JS enforcement — but depth varies)
calcom, clerk, lobehub, next.js, pnpm, PostHog, continuedev, promptfoo, nestjs, webpack, strapi, nocodb, chakra-ui
