# 30-Repo Study — Findings Log

Each repo run captures: workflow classification, notable anomalies, tool bugs discovered, and anything interesting for the book or future research.

---

## 1. cli/cli (Go, Tier B)

**Workflow:** comment-driven (57% comment→approve)
**Coverage:** 74% spec'd
**Rework:** spec'd 2.9% vs unspec'd 3.1% (delta -0.2%)
**Catchrate:** MCR 0%, HSR 96%

**Findings:**
- Uses `CHANGES_REQUESTED` → 0% MCR, 96% HSR. Clean GitHub-native-ish workflow but heavy on comment→approve.
- Straightforward repo, no surprises. Good baseline.

---

## 2. kubernetes/kubernetes (Go, Tier A)

**Workflow:** label-based (36% label + 36% no review)
**Coverage:** 51% spec'd
**Rework:** spec'd 2.4% vs unspec'd 1.8%
**Catchrate:** MCR 31%, HSR 68%

**Findings:**
- **Prow-based approval** — uses `/lgtm` labels and bot comments, not GitHub native review. Initially showed 73% MCR (wrong) and 100% MCR on large PRs.
- **Comment-based review detection bug discovered** — COMMENTED→commit patterns invisible to CATCHRATE. Led to `_had_comment_based_review()` fix.
- **Dependency bump inflation** — automated kubernetes/kubernetes bumps inflating large PR metrics. Led to shared `is_dependency_change()` filter.
- **Spec'd PRs rework MORE than unspec'd** — possible complexity bias (spec'd = harder tasks) or spec quality confound.

**Tool fixes triggered:**
- Comment-based review cycle counting (COMMENTED→commit, COMMENTED→commit→APPROVED)
- `is_dependency_change()` shared filter
- `--include-deps` CLI flag for both UPFRONT and CATCHRATE

---

## 3. cockroachdb/cockroach (Go, Tier A)

**Workflow:** approve-direct (71% approve-only, 16% rubber stamp)
**Coverage:** 56% spec'd
**Rework:** spec'd 3.2% vs unspec'd 2.1%
**Catchrate:** 0 review cycles initially (wrong)

**Findings:**
- **COMMENTED → APPROVED workflow** — uses `COMMENTED` then `APPROVED`, almost never `CHANGES_REQUESTED`. CATCHRATE showed 0 review cycles because it only counted CR-based cycles.
- **Real review friction hidden** — 6.9h TTM for comment→approve vs 2.4h for approve-only. The review friction is real, just invisible to tools looking for `CHANGES_REQUESTED`.
- **86% approve-only** initially reported — after comment→approve cycle fix, showed 71% approve-only, 13% comment→approve.
- **Spec'd PRs rework more** — same pattern as kubernetes. Could be complexity bias or spec quality.

**Tool fixes triggered:**
- COMMENTED→commit→APPROVED (same reviewer) cycle detection in CATCHRATE
- Workflow Analyzer spec written to systematically detect these patterns

---

## 4. microsoft/vscode (TypeScript, Tier A)

**Workflow:** (partial run, pre-workflow-analyzer)
**Coverage:** 42% spec'd
**Rework:** spec'd 30% vs unspec'd 17%

**Findings:**
- **Spec'd PRs rework MUCH more** — 30% vs 17%. Strongest reverse-delta in the study.
- **By complexity:** medium bucket equal (35% vs 35%) — weakens pure selection bias explanation.
- **Hypothesis:** specs give reviewers something concrete to reject against, increasing measured rework. This is actually specs WORKING (catching problems) but looking bad in the binary metric.
- **GraphQL timeouts** — large repo caused 502/504 errors. Led to auto-adjust page size (50→25→10) and REST fallback.

**Tool fixes triggered:**
- Auto-adjust GraphQL page size on gateway errors
- REST-only fetch adapter (`github_rest.py`)

---

## 5. pingcap/tidb (Go, Tier A)

**Workflow:** mixed (36% comment→approve, 52% approve-only)
**Coverage:** 59% spec'd
**Rework:** spec'd 0.4% vs unspec'd 0.7% (delta -0.2%)
**Catchrate:** MCR 0.4%, HSR 99.6%
**By complexity:** small spec'd 0.7% vs unspec'd 1.3%; medium/large both 0%

**Findings:**
- **Massive AI reviewer adoption** — 3 active AI review bots:
  - `pantheon-ai`: 97 reviews (COMMENTED-heavy, some APPROVED and CHANGES_REQUESTED)
  - `coderabbitai`: 96 reviews
  - `copilot-pull-request-reviewer`: 89 reviews
  - `copilot-swe-agent`: 3 reviews
  - Total: 285 bot reviews in 90 days
- **Bot misclassification bug** — `copilot-pull-request-reviewer` was classified as human (doesn't end in `[bot]`). `pantheon-ai` also missed. Led to bot detection fix.
- **Workflow reclassified after bot fix** — changed from "comment-driven" to "mixed" once pantheon-ai's 97 COMMENTED reviews were stripped from human counts.
- **Median reviewers dropped from 3 to 2** after bot fix — one of the "3 reviewers" was AI.
- **Rubber stamp rate climbing** — transition detected: 5% → 12% over the period.
- **Very low rework across the board** — both spec'd and unspec'd under 1%. Suggests strong review culture regardless of spec presence.

**Tool fixes triggered:**
- Added `copilot-pull-request-reviewer`, `copilot-swe-agent`, `pantheon-ai` to bot reviewer lists
- Added `_BOT_PREFIXES` tuple for prefix-based bot detection (`copilot-`, `coderabbit-`, `sourcery-`, `pantheon-`)
- Fixed bot detection in all 4 locations: `github_graphql.py`, `github_rest.py`, `github.py`, `workflow_detect.py`

---

## 6. apache/arrow (Multi, Tier A)

**Workflow:** approve-direct (60% approve-only, 22% comment→approve)
**Coverage:** 92% spec'd (188/204)
**Rework:** spec'd 2.1% vs unspec'd 0.0% (delta +2.1%, limited significance — only 16 unspec'd)
**Catchrate:** MCR 12%, HSR 88%
**By complexity:** small only (152 spec'd, 15 unspec'd)

**Findings:**
- **Highest spec coverage so far** — 92%. Tier A delivers on issue linking.
- **Single-reviewer culture** — median 1 review, 1 reviewer. 23% substantive review rate. Most PRs get a quick approval.
- **Extreme reviewer concentration** — `kou` has 99 reviews (~50% of all PRs). Major bus factor.
- **14% no-review PRs** — surprising for a Tier A repo. These may be maintainer self-merges.
- **Almost all small PRs** — no medium/large complexity buckets populated. Hard to test complexity confound.
- **Minimal AI reviewer adoption** — only 5 Copilot reviews total.
- **No tool fixes triggered** — clean run.

---

## 7. promptfoo/promptfoo (TypeScript, Tier AI)

**Workflow:** minimal-review (60% no-review in current window, transitioned from label-based in Feb 2026)
**Coverage:** 18% spec'd (51/287)
**Rework:** spec'd 19.6% vs unspec'd 10.2% (delta +9.4%)
**Catchrate:** MCR 23%, HSR 68%
**By complexity:** small spec'd 10.0% vs unspec'd 6.5%; medium spec'd 35.3% vs unspec'd 16.9%

**Findings:**
- **First Tier AI repo** — identified from AIDev dataset (932K agent-authored PRs). 4 different AI agents used (Codex, Cursor, Devin, Claude).
- **Workflow transition detected** — shifted from label-based (61% label) to minimal-review (60% no-review) in late Feb 2026. May indicate increased auto-merging.
- **`promptfoo-scanner`** — 274 COMMENTED reviews, classified as human. Clearly an automated scanner. Added to bot list.
- **OpenAI-adjacent project** — authors with `-oai` suffix (mldangelo-oai, jbeckwith-oai, jameshiester-oai) suggest OpenAI employees.
- **38% of PRs have zero reviews** — consistent with minimal-review classification.
- **Spec'd PRs rework MORE (19.6% vs 10.2%)** — strongest reverse-delta yet after vscode. Medium PRs: 35.3% spec'd vs 16.9% unspec'd. Consistent cross-repo pattern.
- **Very low spec coverage (18%)** — despite high AI agent usage.
- **23% MCR** — relatively high machine catch rate, likely from CI and the promptfoo-scanner bot.

**Tool fixes triggered:**
- Added `promptfoo-scanner` to bot reviewer lists

**Key insight for thesis:** High AI-agent usage + minimal human review + low spec coverage = the "outcome lottery" pattern. Agents submit PRs, many auto-merge with no review. The 19.6% rework rate on spec'd PRs suggests that when specs DO exist, they create review friction (which may be good — catching problems).

---

## 8. mendableai/firecrawl (TypeScript, Tier AI)

**Workflow:** minimal-review (71% rubber stamp, 20% comment→approve, 5% approve-only)
**Coverage:** 18% spec'd (50/272)
**Rework:** spec'd 30.0% vs unspec'd 23.9% (delta +6.1%)
**Catchrate:** MCR 3%, HSR 77%, escape ~20%
**By complexity:** small spec'd 30.3% vs unspec'd 19.7%; medium 30% vs 34%; large 28.6% vs 38.9%

**Findings:**
- **71% rubber stamp rate** — highest in the study. Most PRs approved in <5 min with zero comments. This is not review, it's auto-merge with a human click.
- **`cubic-dev-ai`** — 443 reviews (!!), classified as human. Obviously an AI reviewer bot. More reviews than total PRs because it reviews multiple times. Added to bot list.
- **`firecrawl-spring`** — 79 PRs authored by this bot. Automated PR generation.
- **`devin-ai-integration`** — 6 PRs from Devin. Confirms AIDev dataset.
- **~20% escape rate** — highest in the study. HSR only 77%. With 71% rubber stamps, defects are passing through unreviewed.
- **30% rework on spec'd PRs** — very high, but unspec'd also high at 24%. This repo has a quality problem across the board.
- **Large unspec'd PRs: 39% rework** — nearly 4 in 10 get reworked. But large spec'd: 28.6% — specs help on large changes.
- **`gh pr list --search merged:>=` returns empty** — GitHub search API inconsistency. Had to use GraphQL adapter directly. Need to add fallback to runner.

**Tool fixes triggered:**
- Added `cubic-dev-ai` to bot reviewer lists
- Discovered `gh pr list --search "merged:>=DATE"` doesn't work for all repos — needs fallback

**Key insight for thesis:** This is what "no verification infrastructure" looks like at scale. 71% rubber stamps + 18% spec coverage + AI-authored PRs + 20% escape rate = the delivery gap in action. Fast but not right.

---

## 9. calcom/cal.com (TypeScript, Tier AI)

**Workflow:** mixed (51% approve-only, 25% comment→approve, 15% rubber stamp, 0% no-review)
**Coverage:** 15% spec'd (55/363)
**Rework:** spec'd 12.7% vs unspec'd 14.9% (delta -2.2% — specs help slightly)
**Catchrate:** MCR 4%, HSR 81%
**By complexity:** small spec'd 9.5% vs unspec'd 12.7%; medium equal at 20%

**Findings:**
- **Devin as both author AND reviewer** — `devin-ai-integration` authored 4 PRs and submitted 92 COMMENTED reviews. Devin is reviewing human code. Added to bot list with `devin-` prefix.
- **`cubic-dev-ai`** — 427 reviews here too (same bot as firecrawl). Correctly flagged as bot this time.
- **Specs slightly help** — first AI-tier repo where spec'd PRs rework LESS (12.7% vs 14.9%). Small effect but consistent with small PRs (9.5% vs 12.7%).
- **15% spec coverage** — very low, typical for AI-tier repos.
- **0% no-review PRs** — despite heavy AI usage, every PR gets at least one review. Contrasts sharply with promptfoo (60% no-review) and firecrawl (71% rubber stamp).
- **15% rubber stamp rate** — much lower than firecrawl's 71%. Real review culture despite AI adoption.
- **HSR 81%** — better than firecrawl (77%) but lower than traditional repos.

**Tool fixes triggered:**
- Added `devin-ai-integration` to bot reviewer lists
- Added `devin-` to `_BOT_PREFIXES`

**Key insight for thesis:** cal.com has AI (Devin authoring + reviewing, cubic-dev-ai reviewing) but maintains review discipline — 0% no-review, 15% rubber stamp, 81% HSR. Compare to firecrawl: similar AI adoption, 71% rubber stamp, 20% escape rate. The difference is organizational permission to skip review, not the tools.

---

## 10. mlflow/mlflow (Python, Tier AI)

**Workflow:** mixed (54% approve-only, 25% comment→approve, 14% rubber stamp, 5% no-review)
**Coverage:** 24% spec'd (120/495)
**Rework:** spec'd 4.2% vs unspec'd 7.5% (delta -3.3% — specs help)
**Catchrate:** MCR 2%, HSR 91%
**By complexity:** small spec'd 2.8% vs unspec'd 6.5%; medium spec'd 16.7% vs unspec'd 8.7%

**Findings:**
- **MASSIVE Copilot adoption** — `copilot-pull-request-reviewer` submitted 408 reviews (more than any human). `copilot-swe-agent` submitted 117 reviews AND authored 268 PRs (54% of all PRs!).
- **54% of PRs authored by copilot-swe-agent** — the highest AI-authorship rate in the study. This is a genuinely AI-driven codebase.
- **Specs help here** — spec'd PRs rework at 4.2% vs unspec'd at 7.5%. The -3.3% delta is the strongest positive spec signal in the study so far (excluding arrow's limited sample).
- **Small PRs: spec'd 2.8% vs unspec'd 6.5%** — specs cut rework in half on small changes. This is within the same size bucket, controlling for complexity.
- **Medium PRs reverse** — spec'd 16.7% vs unspec'd 8.7%. But only 12 spec'd medium PRs — small sample.
- **`harupy`** — 539 reviews, clearly the primary maintainer. Single-reviewer concentration.
- **`mlflow-app`** — 27 PRs from an internal bot.
- **14% rubber stamp, 5% no-review** — moderate. Not as undisciplined as firecrawl.

**Tool fixes triggered:** None — clean run.

**Key insight for thesis:** mlflow is the clearest evidence yet: AI agents author 54% of PRs, Copilot reviews everything, AND specs reduce rework. This repo has the verification infrastructure (91% HSR, review discipline, spec linkage) that makes AI-driven development work. Compare to firecrawl: similar AI adoption, no infrastructure, 20% escape rate.

---

## Cross-Repo Patterns (so far)

1. **Spec'd PRs reworking more — three competing interpretations.** Seen in kubernetes, cockroach, vscode, promptfoo, firecrawl. Three explanations, not mutually exclusive:
   - **(a) Specs are useless** (null hypothesis) — spec presence has no causal effect, and the correlation is confounded by complexity (harder tasks get specs AND get reworked).
   - **(b) Specs create review friction** — specs give reviewers concrete criteria to reject against. A reviewer without a spec thinks "seems fine." A reviewer with a spec thinks "this doesn't match."
   - **(c) Specs raise the bar** — without a spec, "good enough" ships. With a spec, "doesn't match the spec" gets caught. The defect existed either way — the spec made it visible pre-merge instead of post-merge.

   If (b) or (c), we'd expect spec'd PRs to have higher rework but FEWER post-merge escapes. CATCHRATE escape rates + follow-on fix signals can test this. If (a), quality bucketing should show no gradient (high/medium/low quality specs all rework equally).

   **(d) Specs raise HSR** — if specs create higher review standards, spec'd PRs should show higher human save rates (more things caught during review). This is (b)/(c) expressed as a catchrate metric. Test: compare HSR for spec'd vs unspec'd PRs within the same repo.

   **(e) The "yolo spec" problem** — AI generates a high-quality spec, human skims it without really reading it, then builds something that doesn't match. The spec exists but wasn't internalized. This is an attention/process failure, not a spec quality failure. The spec is good, the engagement is bad. Fits the thesis about organizational permission — the infrastructure exists but nobody uses it. Analogous to having CI but ignoring red builds.

   This is particularly likely in AI-driven repos where AI writes both the spec AND the code. The human's role collapses from "author who specs then builds" to "approver who rubber-stamps both." The spec becomes a ritual artifact rather than a thinking tool.

   **How to detect:** If yolo-spec is happening, we'd see: (1) high spec quality scores but (2) no rework benefit from those specs, AND (3) low review depth / high rubber stamp rate on spec'd PRs specifically. The spec quality is high but the human engagement is low.

   **(f) The "wrong thing, well-specified" problem** — the spec is internally high quality (clear, testable, specific error states) but externally wrong (solving the wrong problem, wrong approach, wrong assumptions). Our LLM scorer can't detect this because it only evaluates the spec's internal quality, not whether the spec matches reality. This is **spec alignment**, distinct from spec quality. Particularly likely in AI-driven repos where AI writes the spec AND the code — the whole chain executes flawlessly on a bad premise.

   **How to detect:** If the follow-up rework PR changes the *approach* (different files, different API surface) rather than fixing the *implementation* (same files, bug fix), that's an alignment failure. UPFRONT's rework signals include `overlapping_files` — low file overlap between original and rework PR = alignment failure. High overlap = implementation failure. This is testable with existing data.

   **Preliminary cli-cli data (n=16, not conclusive):** error_states and behavioral_specificity dimensions show +20pp rework delta between above/below median. But sample too small. LLM quality scoring running on AI-tier repos for larger sample.

2. **Bot reviewer proliferation** — pingcap has 3 active AI reviewers, promptfoo has promptfoo-scanner. Every repo run discovers new bots. Bot detection is an ongoing challenge.

3. **Workflow diversity** — 7 repos, 5 different workflow types (comment-driven, label-based, approve-direct, mixed, minimal-review). Confirms the Workflow Analyzer was necessary.

4. **Very different review cultures** — kubernetes has 36% no-review PRs; pingcap has 3% no-review; promptfoo has 60% no-review. Same tools, wildly different practices.

5. **Tool reliability** — every repo has triggered at least one tool fix. The study is stress-testing the tools as much as it's measuring repos.

6. **AI-heavy repos have minimal review** — promptfoo (Tier AI, 4 agents) shows minimal-review workflow with 60% no-review PRs. Hypothesis: teams using AI agents auto-merge more, reducing the human review gate.

7. **LLM quality scores are non-deterministic** — same spec scored twice produces different results. Observed variance: ±10-15pp on individual dimensions, ±5-10pp on overall. Example: PR #48791 scored errors=0/AC=40/overall=51 on first run, then errors=40/AC=60/overall=62 on second. Individual PR scores are noisy; aggregate patterns across 100+ specs per repo should be stable. All findings based on averages and tier distributions, not individual scores. Future: could average 3 runs per spec for stability, but at 3x cost.

8. **AIDev dataset** — 932K agent-authored PRs across 116K repos. Agent distribution: OpenAI Codex 87%, Copilot 5%, Cursor 4%, Devin 3%, Claude Code 1%. Merge rates vary 2x by agent (Codex 83% vs Copilot 43%).
