# Spec Alignment Failures — Study Finding

**Date:** 2026-03-24
**Status:** Preliminary finding, needs more data

## Discovery

While running the 30-repo study, we found that spec'd PRs rework MORE than unspec'd in most repos. Investigating why, we discovered two distinct rework types based on file overlap between the original PR and its follow-up fix:

- **Implementation fix** (>=50% file overlap): Built the right thing wrong. Same files, fixing bugs or refining behavior.
- **Alignment failure** (<50% file overlap): Built the wrong thing. Different files, different approach entirely.

## Data

| Repo | Tier | Alignment Failures | Implementation Fixes | Alignment Rate |
|------|------|-------------------|---------------------|----------------|
| cli/cli | B | 6 | 13 | 32% |
| pingcap/tidb | A (AI reviewers) | 1 | 2 | 33% |
| mendableai/firecrawl | AI | 48 | 34 | **59%** |
| mlflow/mlflow | AI (54% AI-authored) | 23 | 14 | **62%** |
| calcom/cal.com | AI (Devin) | 48 | 13 | **79%** |

**Pattern:** AI-tier repos have 2-3x higher alignment failure rates than traditional repos.

## The "Wrong Thing, Well-Specified" Pattern

Crossing spec quality scores (LLM-scored) with rework type on firecrawl (n=15):

| | Alignment Failures (n=9) | Implementation Fixes (n=6) |
|---|---|---|
| Overall quality | 52 | 46 |
| Outcome clarity | **75** | 65 |
| Error states | 18 | 18 |
| Acceptance criteria | **41** | 33 |

Alignment failures have HIGHER quality specs. The specs are well-written — clear outcomes, specific criteria — but they're for the wrong thing. The quality of the spec didn't prevent building the wrong thing.

## Interpretation

### Why this happens in AI-driven repos

1. AI writes a spec that is internally coherent and detailed
2. Human skims it (or doesn't read it at all — "yolo spec")
3. AI implements it faithfully
4. The whole chain executes correctly on a wrong premise
5. A follow-up PR changes the approach entirely

The verification infrastructure catches implementation bugs (error states, edge cases) but NOT alignment bugs (wrong problem, wrong approach, wrong assumptions). This is a blind spot in the Verification Triangle — spec quality measures the spec's internal quality, not whether it matches reality.

## Spec Alignment as a Distinct Axis

Current Verification Triangle: spec quality × eval quality × cost

Proposed addition: **spec alignment** — does the spec match the actual need?

- **Spec quality**: Is the spec clear, testable, complete? (internal)
- **Spec alignment**: Is the spec describing the right thing? (external)

A spec can be high quality and low alignment (well-specified wrong thing) or low quality and high alignment (vague description of the right thing).

## How to Detect Alignment (future work)

### Post-merge (retrospective, what we're doing now)
- File overlap ratio between original PR and follow-up rework PR
- <50% overlap = alignment failure, >=50% = implementation fix

### Pre-merge (prospective, automation opportunity)
1. **Spec-to-diff semantic alignment** — embed spec text and code diff using CodeBERT/GraphCodeBERT, measure cosine similarity. Low similarity = code doesn't match what spec describes. (AIDev paper A070 measured this at 0.9356 for agent PRs.)
2. **Spec-to-issue alignment** — if PR "Closes #123", compare the issue description to the spec/PR description. Semantic drift = alignment risk.
3. **Review comment signals** — NLP on review comments for alignment language: "this doesn't match the issue", "wrong approach", "not what was asked for"

### The organizational signal
Alignment failure rate may be a proxy for **human engagement with specs**. Repos where humans write specs: 32-33% alignment failures. Repos where AI writes specs and humans rubber-stamp: 59-79% alignment failures. The spec exists but nobody internalized it.

## Implications for the Book

### Current framing (Chapter 6)
The Verification Triangle treats spec quality as a single dimension. The data suggests it's at least two:
- Quality (internal coherence, completeness, testability)
- Alignment (external correctness, matches actual need)

### Possible updates
1. Add alignment as a dimension or qualifier to spec quality
2. The "freed capacity" argument (Chapter 11) should note that freed capacity must include spec REVIEW, not just spec creation. AI can write specs; only humans can validate alignment.
3. The mandate section should distinguish: "having specs" (necessary) from "engaging with specs" (sufficient). Infrastructure without attention is ritual.

### The honest conclusion
Specs help — but only when humans actually engage with them. In AI-driven repos where AI writes the spec and the code, the spec can become a ceremonial artifact rather than a thinking tool. The Verification Triangle is necessary but not sufficient without human judgment at the alignment step.

This is not a weakness of the framework — it's a refinement. The triangle measures whether the infrastructure EXISTS. Alignment measures whether humans USE it.
