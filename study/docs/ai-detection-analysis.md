# AI Detection Analysis: What We Can and Can't Detect

**Date:** 2026-03-25
**Dataset:** master-prs.csv — 10,660 PRs, 9,016 non-bot

---

## The Detection Gap

We can confidently classify only 11.6% of PRs:

| Group | Method | n | % | Rework | Escape |
|-------|--------|---|---|--------|--------|
| Confirmed AI | f_ai_tagged + no human signals | 533 | 5.9% | 17.6% | 6.4% |
| Confirmed human | human signals (typos/casual/questions/fp_exp) + not tagged | 516 | 5.7% | 8.1% | 1.9% |
| Unknown | neither signal | 7,967 | 88.4% | 11.8% | 3.5% |

AI-confirmed PRs have **2.2x the rework** and **3.4x the escape rate** of human-confirmed PRs.

The 88% "unknown" group is contaminated — it contains both untagged AI and formal-but-human PRs that we can't separate with current signals.

---

## Formality Scorer

**The LLM formality scorer (formality_ columns) measures formality, not engagement.**

Evidence:
- Overall score is identical for AI-tagged (median=25) and not-tagged (median=25)
- 81% of Tier A (traditional, high-governance) PRs are classified as "ai_generated" — because professional human writing looks like AI
- 4 of 8 dimensions go the wrong direction: AI scores HIGHER on negative_scope (+5.9), causal_reasoning (+6.4), genuine_edge_cases (+5.5), organizational_memory (+2.1)
- These are "performative thoroughness" signals — AI is better at sounding thoughtful than humans

**The "mixed" classification still predicts worst outcomes** (13.2% rework, 5.5% escape), which makes sense reframed: "mixed formality" = half-polished work where someone started but didn't finish thinking.

**Recommendation:** Treat `formality_` columns as formality scores. Do NOT use `formality_classification` as AI detection. Use stylometric classifier or f_ai_tagged instead.

---

## Stylometric Classifier (regex features → AI prediction)

### Method
- Features: 26 regex-computed text statistics (body_len, word_count, type_token_ratio, etc.)
- Labels: f_ai_tagged as positive class (643 AI, 7,588 not-tagged)
- Trained on PRs with body > 50 chars (n=8,231)
- 5-fold stratified cross-validation

### Results

| Model | AUC | Precision (AI) | Recall (AI) |
|-------|-----|----------------|-------------|
| Logistic Regression | 0.839 | 0.237 | 0.733 |
| Random Forest | 0.880 | 0.704 | 0.325 |

Logistic regression catches more AI (73% recall) but has many false positives (24% precision). Random forest is more conservative (33% recall) but more precise (70%).

### Top Discriminating Features

**Predicts AI:**
| Feature | Coef | Meaning |
|---------|------|---------|
| empty_sections | +0.660 | AI fills template headers but leaves sections thin |
| sent_len_mean | +0.326 | AI writes longer, more uniform sentences |
| word_count | +0.312 | AI writes more text |
| avg_word_len | +0.297 | AI uses longer/more formal words |
| external_context | +0.243 | AI references external systems (from diff, not knowledge) |

**Predicts human:**
| Feature | Coef | Meaning |
|---------|------|---------|
| type_token_ratio | -0.743 | **Strongest signal.** Humans use more diverse vocabulary. AI repeats. |
| negations | -0.463 | Humans say "don't", "not", "won't" naturally |
| sent_len_std | -0.353 | Humans vary sentence length. AI is uniform. |
| human_mentions | -0.341 | Humans reference other people by name |
| typos | -0.164 | Humans misspell |

### Classifier Predictions vs Outcomes

| Predicted class | n | % tagged | Rework | Escape |
|----------------|---|----------|--------|--------|
| Very likely human (0-0.1) | 1,088 | 0.7% | 11.1% | 3.4% |
| Probably human (0.1-0.3) | 3,492 | 1.7% | 10.6% | 3.1% |
| Uncertain (0.3-0.5) | 1,663 | 5.6% | 11.3% | 3.8% |
| Probably AI (0.5-0.7) | 791 | 12.9% | 11.8% | 3.3% |
| Very likely AI (0.7-1.0) | 1,197 | 31.7% | 16.3% | 4.3% |

Escape rate climbs from 3.1% (probably human) to 4.3% (very likely AI). Rework jumps to 16.3% for very likely AI.

---

## Repo-Level AI Signal

Repos with higher AI% tend to have higher escape rates (r=0.262). Not strong, but consistent.

Top AI-usage repos:
| Repo | AI% | Rework | Escape |
|------|-----|--------|--------|
| promptfoo | 43.5% | 16.1% | 7.0% |
| pingcap/tidb | 34.3% | 0.9% | 0.0% |
| denoland/deno | 20.6% | 31.7% | 11.4% |
| pnpm/pnpm | 19.0% | 21.8% | 6.9% |
| antiwork/gumroad | 18.1% | 14.9% | 7.7% |

Notable: pingcap/tidb has 34% AI tagging but near-zero rework/escape — suggests strong governance can compensate for AI usage.

---

## Author-Level Analysis

### Casual language is not driven by a few prolific authors
- 43 casual PRs from 30 unique authors (1.4 PRs/author avg)

### Within-author controls

**Casual vs formal (same author, n=24 authors):**
- Casual PRs: 27.8% rework, 2.8% escape
- Formal PRs: 12.0% rework, 3.2% escape
- Δ: +15.8pp rework, -0.4pp escape
- Rework signal survives within-author. Escape effect is much weaker within-author.

**fp_experience does NOT survive within-author (n=17 authors):**
- fp_exp PRs: 15.2% rework, 3.0% escape
- No-fp PRs: 16.1% rework, 2.7% escape
- Δ: -1.0pp rework, +0.4pp escape — flat
- The pooled -6.9pp rework signal was author skill confound, not a causal effect.

**Within-author AI vs non-AI (n=49 authors):**
- AI-tagged PRs: 17.5% rework, 5.4% escape
- Non-AI PRs: 16.1% rework, 4.5% escape
- Δ: +1.4pp rework, +0.9pp escape — small but in "AI is worse" direction

### Author volume confounds outcomes
| Volume | Rework | Escape | Authors | PRs |
|--------|--------|--------|---------|-----|
| 1-2 PRs | 6.2% | 1.5% | 1,009 | 1,235 |
| 3-9 PRs | 10.3% | 2.7% | 386 | 1,915 |
| 10-49 PRs | 11.6% | 4.2% | 184 | 3,723 |
| 50+ PRs | 17.3% | 4.5% | 27 | 2,143 |

Prolific authors have 3x the rework rate of low-volume authors. This is a major confound — prolific authors touch harder, more visible work.

---

## Composite AI Confidence Score

Simple additive score combining multiple signals:

| Component | Weight | Rationale |
|-----------|--------|-----------|
| f_ai_tagged | +3 | Explicit declaration |
| f_slop | +1 | AI writing patterns |
| f_templates | +1 | Template filling |
| f_empty_sections | +1 | Thin template sections |
| f_body_len > 2000 | +1 | AI writes long |
| f_casual | -3 | AI won't write "kinda" |
| f_typos | -2 | AI won't misspell |
| f_questions | -2 | AI won't ask |
| f_fp_experience | -2 | AI won't narrate personal experience |

| Score range | n | Rework | Escape |
|-------------|---|--------|--------|
| [-10,-3) most human | 38 | 18.4% | 0.0% |
| [-3,-1) human | 355 | 7.0% | 2.5% |
| [-1,1) unknown | 6,098 | 11.6% | 3.3% |
| [1,3) AI-leaning | 1,947 | 12.4% | 4.0% |
| [3,10) most AI | 578 | 17.0% | 5.9% |

Escape rate climbs monotonically 0% → 2.5% → 3.3% → 4.0% → 5.9%.

Most-human has high rework (18.4%) with zero escapes — the golden pattern. These people catch everything in review.

---

## What We Still Can't Detect

1. **AI-assisted but untagged** — someone used Copilot but didn't add a tag
2. **AI-drafted then edited** — human cleaned up AI output, no trace
3. **AI for code, human for spec** — we only analyze the spec text, not the code
4. **Prompt history** — the real engagement signal is in the chat, not the PR

The stylometric classifier helps (AUC 0.88) but the fundamental problem remains: we're analyzing the artifact (PR description) when the real signal is in the process (was a human thinking?).

---

## Statistical Significance Tests

Tests run 2026-03-25 using Fisher's exact test and chi-squared on the master dataset (n=9,016 non-bot PRs).

### AI vs Human: Rework and Escape Rates

**Decile comparison (stylometric classifier):**

| Comparison | Outcome | Rate (AI) | Rate (Human) | Delta | Odds Ratio | Fisher p | Chi² p | Verdict |
|---|---|---|---|---|---|---|---|---|
| D10 vs D01-D03 | Rework | 19.7% (162/824) | 9.9% (244/2,469) | +9.8pp | 2.23x | 1.7×10⁻¹² | 2.3×10⁻¹³ | *** p<0.001 |
| D10 vs D01-D03 | Escape | 4.9% (40/824) | 2.8% (68/2,469) | +2.1pp | 1.80x | 4.6×10⁻³ | 4.8×10⁻³ | ** p<0.01 |

**Confirmed groups (tagged + human signals):**

| Comparison | Outcome | Rate (AI) | Rate (Human) | Delta | Odds Ratio | Fisher p | Chi² p | Verdict |
|---|---|---|---|---|---|---|---|---|
| Confirmed AI vs Human | Rework | 17.6% (94/533) | 8.1% (42/516) | +9.5pp | 2.42x | 5.5×10⁻⁶ | 7.3×10⁻⁶ | *** p<0.001 |
| Confirmed AI vs Human | Escape | 6.4% (34/533) | 1.9% (10/516) | +4.4pp | 3.45x | 3.2×10⁻⁴ | 6.0×10⁻⁴ | *** p<0.001 |

**Interpretation:** AI-authored PRs have significantly higher rework (2.2-2.4x odds) and escape rates (1.8-3.5x odds). The confirmed-groups comparison is the cleanest because it uses ground truth labels (explicit AI tags vs regex human signals like typos/casual/questions).

### Spec Effect Within High-AI PRs

| Comparison | Outcome | Spec'd | Unspec'd | Delta | Fisher p | Verdict |
|---|---|---|---|---|---|---|
| D10 only | Rework | 17.6% (65/369) | 21.3% (97/455) | -3.7pp | 0.19 | NOT SIGNIFICANT |
| D10 only | Escape | 3.5% (13/369) | 5.9% (27/455) | -2.4pp | 0.14 | NOT SIGNIFICANT |

**Interpretation:** The spec effect within high-AI PRs goes in the right direction (specs reduce both rework and escape) but does not reach significance. Sample sizes are too small (369 spec'd in D10). The pooled analysis across all AI levels shows a significant spec effect (-1.5pp escape, p not computed here), suggesting the effect is real but needs more data to confirm within the high-AI subgroup specifically.

### Summary of What Is and Isn't Significant

**Highly significant (p < 0.001):**
- AI PRs have higher rework rates than human PRs
- AI PRs have higher escape rates than human PRs (confirmed groups)
- The stylometric classifier predicts AI authorship (AUC 0.839-0.880)

**Significant (p < 0.01):**
- AI PRs have higher escape rates (decile comparison)
- ai_probability correlates with rework (point-biserial r=0.06, p < 10⁻⁸)

**Marginally significant (p < 0.05):**
- ai_probability correlates with escape (point-biserial r=0.02, p=0.038)

**Not significant:**
- Spec effect within high-AI subgroup alone (direction correct but n too small)
- formality_classification as a predictor of anything (r ≈ 0)

### Caveats
- All tests are two-tailed
- No Bonferroni correction applied across the full set of comparisons
- Confirmed AI uses self-reported tags (f_ai_tagged) which may not be representative of all AI usage
- Confirmed human uses proxy signals (typos, casual language) which may miss formal human writers
