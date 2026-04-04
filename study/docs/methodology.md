# Reproducible Methodology: Spec Quality and Software Outcomes

**Date:** 2026-03-25
**Dataset:** `data/master-prs.csv` — 10,660 PRs across 35 repos, 81 columns
**Reproduction:** Run the analysis in `reproduce-claims.py` against the master CSV

---

## Data Pipeline

```
prs-{slug}.json          ← GitHub GraphQL/REST (runner.py)
  ↓
upfront-{slug}.json      ← UPFRONT rework detection (runner.py)
catchrate-{slug}.json    ← CatchRate escape detection (runner.py)
workflow-{slug}.json     ← Workflow type classification (runner.py)
  ↓
spec-quality-{slug}.json ← LLM quality scoring, 7 dimensions (score-specs.py)
engagement-{slug}.json   ← LLM formality scoring, 8 dimensions (score-formality.py)
  ↓
unified-prs.csv          ← Join PR data + UPFRONT + CatchRate + workflow + quality (build-unified-csv.py)
  ↓
pr-features.csv          ← 44 regex features per PR (compute-features.py)
  ↓
master-prs.csv           ← Final join: unified + features + formality (build-master-csv.py)
```

## Key Definitions

### Outcome Variables
- **reworked** (`reworked=True`): PR was followed by another PR that fixes it, detected by UPFRONT's effectiveness signals (title/body references like "fix #N", "follow-up to #N", same-author patches within time window)
- **escaped** (`escaped=True`): Defect reached production. Detected by CatchRate classification of the follow-up PR (post-merge fix signal)
- **rework_type**: Classification based on file overlap between original PR and follow-up fix:
  - `alignment` = <50% file overlap (built the wrong thing — fix touches different files)
  - `implementation` = ≥50% file overlap (built it wrong — fix touches same files)

### Population Filters
- **Non-bot PRs** (n=9,016): `f_is_bot_author != True`. All rate calculations exclude bot-authored PRs.
- **Spec'd PRs**: `specd=True` — PR has a linked issue, detailed body, or other spec artifact
- **Size buckets**: XS (<10 lines), S (10-49), M (50-249), L (250-999), XL (1000+)

### Tier Classification
- **A**: High-governance traditional repos (kafka, biome, arrow, vscode, cockroach, svelte, kubernetes)
- **B**: Lower-governance traditional repos (cli, grafana, rust-lang)
- **AI**: Repos with significant AI-authored PRs (promptfoo, firecrawl, cal.com, mlflow, gumroad, novu, aspire)
- **?**: Unclassified repos

### Feature Prefixes
- `f_` — Regex-computed features (deterministic, no LLM)
- `q_` — LLM quality scores (7 dimensions, scored by Haiku)
- `formality_` — LLM formality scores (8 dimensions, scored by Haiku)
- `fev_` — Evidence quotes from formality scorer

---

## Claim 1: Casual Language is the Golden Signal

**Hypothesis:** PRs containing casual language (kinda, btw, WIP, nope, IIRC) predict better escape outcomes.

**Method:**
1. Filter to non-bot PRs (n=9,016)
2. Split by `f_casual > 0` (yes) vs `f_casual == 0` (no)
3. Compute rework rate and escape rate for each group

**Result (reproduced 2026-03-25):**

| Group | Rework | Escape | n |
|-------|--------|--------|---|
| casual=yes | 27.9% | 2.3% | 43 |
| casual=no | 11.9% | 5.0% | 8,973 |
| **Δ** | **+16.0pp** | **-2.7pp** | |

**Interpretation:** PRs with casual language have much higher rework (caught before merge) and lower escape (fewer defects reach production). This is the "golden signal" pattern: rework↑ escape↓ = the review process is working.

**Caveats:**
- **n=43** for casual=yes. Very small sample. Effect size is large but confidence interval is wide.
- No size-bucket stratification shown. Casual language may correlate with PR size or repo culture.
- Casual language is a proxy for human engagement, not a causal mechanism.

---

## Claim 2: Specs Shift Catches Earlier

**Hypothesis:** Spec'd PRs have higher rework rates (catches during review) but lower escape rates (fewer post-merge defects).

**Method:**
1. Filter to non-bot PRs (n=9,016)
2. Split by `specd=True` (n=2,654) vs `specd!=True` (n=6,362)
3. Compute rework and escape rates
4. Repeat per tier and per repo

**Result (reproduced 2026-03-25):**

| Group | Rework | Escape | n |
|-------|--------|--------|---|
| spec'd | 12.4% | 3.8% | 2,654 |
| unspec'd | 11.8% | 5.5% | 6,362 |
| **Δ** | **+0.6pp** | **-1.7pp** | |

**Per-tier breakdown:**

| Tier | Δ Rework | Δ Escape | Pattern | n_spec'd | n_unspec'd |
|------|----------|----------|---------|----------|------------|
| A | +2.0pp | -1.6pp | SHIFTED EARLIER | 1,046 | 1,070 |
| AI | +1.2pp | -2.0pp | SHIFTED EARLIER | 589 | 1,394 |
| B | -0.4pp | +0.5pp | (slight opposite) | 189 | 769 |
| ? | +1.6pp | -0.1pp | (rework up, escape flat) | 830 | 3,129 |

**Per-repo patterns (repos with ≥20 spec'd PRs):**
- SHIFTED EARLIER (rework↑ escape↓): 7 repos (kafka, ruff, biome, aspire, envoy, promptfoo, svelte)
- HELPS BOTH (both↓): 5 repos (cal.com, deno, mlflow, bun, rust-lang)
- HURTS BOTH (both↑): 6 repos (gumroad, cockroach, cli, elasticsearch, firecrawl, novu)
- SHIFTED LATER (rework↓ escape↑): 5 repos (grafana, transformers, langchain, pnpm, next.js)

**Interpretation:** Pooled effect supports the thesis (specs catch more in review, fewer escape). Effect is strongest in Tier A and AI repos. But repo-level variation is high — only ~43% show the ideal SHIFTED EARLIER pattern.

**Caveats:**
- Complexity confound: harder tasks get both specs AND more rework. Not controlled for.
- "spec'd" is binary — doesn't account for spec quality (see quality gradient analysis below).

---

## Claim 3: Alignment Failures (PARTIALLY RETRACTED)

**Original claim:** "AI-tier repos have 63% alignment failures vs 28% traditional."

**Reproduced result:**

| Tier | Alignment % | n_typed |
|------|-------------|---------|
| A | 76% | 185 |
| AI | 70% | 293 |
| B | 76% | 59 |
| ? | 67% | 540 |

**The original claim does NOT reproduce.** Alignment failures dominate all tiers equally (67-76%). The earlier "63% vs 28%" was likely from a smaller subset or different calculation method.

**What IS true:**
- The overlap ratio distribution is left-skewed and bimodal (peaks at 0-0.1 and 0.9-1.0)
- The 50% threshold is a reasonable cutpoint but alignment dominates everywhere
- Alignment failures with quality scores average 54.8 vs implementation fixes at 53.5 (Δ=+1.3pp, n=38 vs 21) — much smaller than the earlier reported +7pp

**Why the discrepancy:** The earlier analysis may have been on a subset of repos or used a different rework detection method. The file overlap calculation is sound (line 77-83 of `build-unified-csv.py`), but the claim about tier differences was not robust.

**Revised claim:** Alignment failures (building the wrong thing) account for ~70% of all rework across ALL tiers. This is NOT an AI-specific problem — it's the dominant failure mode everywhere.

---

## Claim 4: Mixed Formality = Worst Outcomes

**Hypothesis:** PRs classified as "mixed" formality (some human signals, some AI boilerplate) have worse outcomes than either pure-human or pure-AI specs.

**Method:**
1. Filter to non-bot PRs with formality classification (n=1,500)
2. Split by `formality_classification` (human / mixed / ai_generated)
3. Compute rework and escape rates

**Result (reproduced 2026-03-25):**

| Classification | Rework | Escape | n |
|----------------|--------|--------|---|
| human | 8.9% | 3.0% | 101 |
| mixed | 13.2% | 6.6% | 273 |
| ai_generated | 9.3% | 3.3% | 1,126 |

**Interpretation:** Mixed formality is clearly worst on both dimensions. Pure human and pure AI-generated have similar rates. The half-engaged state — where a human touched it but didn't deeply engage — produces the worst outcomes.

**Caveats:**
- "human" sample is small (n=101). Rates have wide confidence intervals.
- Classification is by a single LLM scorer (Haiku). No inter-rater reliability measured.
- Formality scoring still running — these numbers will change as more PRs are scored.

---

## Claim 5: Feature Scan — Signal Rankings

**Method:**
1. Filter to non-bot PRs (n=9,016)
2. For each of 44 regex features (`f_` columns), split by feature > 0 vs == 0
3. Compute Δ rework and Δ escape (feature_yes - feature_no)
4. Classify: GOLDEN (rework↑ escape↓), GOOD (both↓), DANGER (rework↓ escape↑)

**Top signals (reproduced 2026-03-25):**

### Golden Signals (rework↑, escape↓) — review catches more, fewer reach production
| Feature | Δ Rework | Δ Escape | n_yes |
|---------|----------|----------|-------|
| f_casual | +16.0pp | -2.7pp | 43 |
| f_human_signals | +0.3pp | -2.4pp | 221 |
| f_issue_refs | +2.5pp | -1.3pp | 910 |
| f_causal_chains | +0.2pp | -0.7pp | 1,047 |

### Good Signals (both↓) — engaged author catches problems pre-PR
| Feature | Δ Rework | Δ Escape | n_yes |
|---------|----------|----------|-------|
| f_fp_experience | -6.9pp | -4.0pp | 426 |
| f_typos | -4.5pp | -2.8pp | 133 |
| f_questions | -3.8pp | -2.6pp | 122 |
| f_incidents | -2.6pp | -2.2pp | 139 |

### Danger Signals (rework↓, escape↑) — looks good but problems slip through
| Feature | Δ Rework | Δ Escape | n_yes |
|---------|----------|----------|-------|
| f_negations | -2.5pp | +1.8pp | 642 |
| f_generic_edges | -3.1pp | +2.3pp | 179 |
| f_domain_grounding | -0.7pp | +0.5pp | 2,309 |

**Interpretation:**
- Human engagement proxies (casual, typos, questions, first-person experience) consistently predict better outcomes
- Formal quality signals (negations, generic edge cases, domain grounding) can be DANGER signals — they suppress rework (reviewers see thoroughness) but increase escapes (the thoroughness is performative)
- AI generates domain grounding, negation scoping, and generic edge cases at higher rates than humans — these are the signals AI can mimic

---

## Quality Gradient (spec quality vs outcomes)

**Method:** For PRs with LLM quality scores (q_overall), bucket into LOW (<40), MEDIUM (40-69), HIGH (≥70).

**Status:** Quality scoring still running (partial data). Not reproduced in this pass. Earlier finding: quality gradient is flat or slightly inverted — higher quality specs rework MORE, not less.

**Preliminary interpretation:** Spec quality measures the artifact, not the thinking behind it. A well-structured AI-generated spec scores high but may describe the wrong thing.

---

## Statistical Limitations

1. **No causal claims.** All findings are correlational. Spec'd PRs may be harder tasks. Casual language may reflect experienced developers who rework less for other reasons.

2. **Multiple comparisons.** 44 features × 2 outcomes = 88 comparisons. At p<0.05, expect ~4 false positives by chance. We have not applied Bonferroni or FDR correction.

3. **Small samples for key signals.** f_casual (n=43), f_typos (n=133), engagement:human (n=101). Effect sizes are large but confidence intervals are wide.

4. **LLM scorer non-determinism.** Quality and formality scores vary ±10-15pp per dimension across runs. Individual scores are noisy; only aggregate patterns are reliable.

5. **Selection bias.** Repos were chosen, not randomly sampled. Results may not generalize to all OSS or private repos.

6. **Measurement validity.** "reworked" is a proxy (follow-up PR detected by UPFRONT). Some follow-ups are enhancements, not fixes. "escaped" depends on CatchRate classification accuracy.

---

## Reproduction Steps

```bash
# 1. Ensure data files exist
ls data/master-prs.csv

# 2. Rebuild master CSV (if scorers have new data)
python3 build-master-csv.py

# 3. Run reproduction script
python3 reproduce-claims.py

# 4. Compare output against this document
```
