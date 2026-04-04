# Finding: Human Cognitive Presence Predicts Software Defect Rates

**Date:** 2026-03-25
**Dataset:** 11,376 PRs across 41 repos (master-prs.csv)
**Status:** Cycle 3 correctness review complete. See honest assessment below.

---

## Cycle 3 Honest Assessment

After three cycles of correctness review, here is what is real, what is not, and what needs more work.

### STATISTICALLY SIGNIFICANT (survives all robustness checks)

| Finding | Effect | p-value | Why it survives |
|---|---|---|---|
| Finding 1: AI deciles produce more defects | +11.1pp rework, +4.3pp escape | p=3.4e-16, p=2.1e-7 | Does not use attention signals at all |
| Finding 8: Polished spec paradox | Q4 vs Q1: +15.8pp rework, +6.4pp escape | p=0.0003, p=0.004 | Filters to NO attention signals; fp_experience contamination changes n from 538 to 545 |
| Pooled attention (strict 3-signal) | -5.2pp rework | p=0.029 | Uses only clean signals (typos, casual, questions) |

### DOES NOT SURVIVE ROBUSTNESS CHECKS

| Finding | Original claim | Why it fails |
|---|---|---|
| Finding 3: Attention in high-AI PRs | -13.7pp rework (p=0.00002), n=112 | 92% of attention triggers come from f_fp_experience, which is CONTAMINATED (AI generates "I tried/noticed" at 5.7x the rate of humans). Removing it: n=9, p=1.0. |
| Finding 5: The 2x2 (AI x Attention) | Best group is high-AI + attention | Same contamination. The "high AI + attention" cell is mostly AI-generated fp_experience text. |
| Finding 6: Attention gradient with AI | Effect scales from -2.7pp to -22.9pp | With strict signals: high-AI has n=6, very-high has n=3. Untestable. |

### SURVIVES DIRECTIONALLY (but attention proxy is weak)

| Finding | Core claim | Attention-dependent part |
|---|---|---|
| Finding 10: People don't learn | 23% rework-after-rework vs 12.9% baseline (1.8x) | Rework recurrence is independent of attention. Attention-rate comparison (0.9% vs 1.8% strict) is directionally consistent but rates are tiny. |
| Finding 11: Fix chains | 24% of fixes need re-fixing | Chain distribution is independent of attention. Attention on fixes (0.8% -> 0.4% strict) is directionally DOWN but sample is too small to test. |
| Finding 9: Size scaling | Unattended AI: 7.3% rework at Q1 to 31.3% at Q4 | Size gradient survives (independent of attention). Attention-by-size comparison uses contaminated 4-signal definition. |

### NEEDS MORE DATA

| What | Current state | What's needed |
|---|---|---|
| Pooled escape (strict) | -2.1pp, p=0.135 (NS) | More repos with strict attention PRs |
| High-AI strict attention | n=9 | Need ~100 strict-attention PRs in high-AI population |
| The 3 clean signals in high-AI PRs | 0.0-0.2% occurrence rate | These signals are genuinely rare in AI-written PRs — may need different detection approach |

---

## The Attention Hypothesis

The original hypothesis was that spec quality predicts software outcomes. It doesn't. What predicts outcomes is whether a human was cognitively present during the change -- and we can detect that through stylometric signals that AI won't produce.

**The contamination problem:** One of the four original attention signals (f_fp_experience: "I tried", "I noticed", "I ran into") is NOT a human marker. AI generates these first-person experience phrases at 5.7x the rate of humans. This signal was 92% of the attention triggers in high-AI PRs. The three clean signals (typos, casual language, questions) genuinely appear at lower rates in AI text:

| Signal | High-AI rate | Low-AI rate | Ratio | Status |
|---|---|---|---|---|
| f_casual | 0.2% | 0.7% | 0.3x | CLEAN |
| f_typos | 0.1% | 3.8% | 0.0x | CLEAN |
| f_questions | 0.0% | 3.5% | 0.0x | CLEAN |
| f_fp_experience | 4.4% | 0.8% | 5.7x | **CONTAMINATED** |

The clean signals are genuinely human markers but they are extremely rare in high-AI PRs (combined: 0.4% occurrence). This means we cannot currently test the attention hypothesis within the high-AI population -- we simply don't have enough data.

---

## Key Findings

### 1. AI-Authored PRs Produce More Defects (SURVIVES)

| Comparison | Rework | Escape | p-value |
|---|---|---|---|
| D10 (most AI) | 22.0% | 7.9% | |
| D01-D03 (most human) | 10.9% | 3.5% | |
| **Delta** | **+11.1pp** | **+4.3pp** | |
| Fisher's exact (rework) | | | **3.4x10^-16 *** |
| Fisher's exact (escape) | | | **2.1x10^-7 *** |
| Odds ratio | 2.30x | 2.33x | |

Method: Stylometric classifier (logistic regression, AUC 0.853) trained on 26 text features, labels from explicit AI tags (f_ai_tagged). Decile 10 = highest predicted AI probability (0.846-1.0, n=937). Deciles 1-3 = lowest (0-0.161, n=2,790).

This finding does not depend on attention signals at all.

### 2. Human Attention Signals Reduce Defects (Pooled -- marginal)

Using the strict 3-signal definition (typos, casual, questions only):

| Group | n | Rework | Escape |
|---|---|---|---|
| Has strict attention signal | 221 | 8.6% | 2.3% |
| No strict attention signal | 9,782 | 13.7% | 4.4% |
| **Delta** | | **-5.2pp** | **-2.1pp** |
| Fisher's exact (rework) | | | **p=0.029 *** |
| Fisher's exact (escape) | | | p=0.135 (NS) |

The rework effect is significant; the escape effect is not. This is a weaker finding than originally reported (which used the contaminated 4-signal definition: n=404, p=0.001).

### ~~3. Attention Matters MOST in High-AI PRs~~ (RETRACTED)

**This finding does not survive robustness checks.**

The original claim (OR=0.18 rework, OR=0.16 escape, p=0.00002) was driven by f_fp_experience contamination. 103 of 112 "attention" PRs in the high-AI group were triggered by fp_experience alone -- a signal AI generates at higher rates than humans.

With strict 3-signal attention: n_attn=9. Nothing is testable.

The effect direction may be real (the 3 clean signals do show lower defect rates in the pooled population), but we cannot currently claim it is strongest in high-AI PRs.

### 4. AI-Written Specs Make Things Worse

Within D10 (highest AI probability), spec'd PRs have WORSE outcomes than unspec'd:

| Group | n | Rework | Escape |
|---|---|---|---|
| D10 spec'd + no attention | 234 | 26.1% | 10.7% |
| D10 unspec'd | 693 | 20.9% | 7.1% |

The spec'd-but-unattended PRs are the worst group in the entire dataset.

**Why specs are worse in high-AI PRs:**
- 78.3% of D10 spec'd PRs have empty sections (AI fills template headers but leaves them thin)
- Formality score = 25 (identical to AI-generated baseline)
- Average body length 2,681 chars -- long, polished, and lifeless

### ~~5. The 2x2: AI Level x Attention~~ (CONTAMINATED)

The original 2x2 is contaminated by fp_experience. The "high AI + attention" cell (n=112, 3.6% rework) is overwhelmingly fp_experience-triggered, not genuine human attention. Cannot be reported as-is.

---

## What Does NOT Hold Up

| Claim | Status | Evidence |
|---|---|---|
| Spec quality predicts outcomes | **Dead** | Quality gradient is flat/inverted |
| Specs help high-AI PRs | **Dead** | Spec'd PRs in D10 are worse (+3.2pp escape) |
| Alignment failures are more common in AI repos | **Retracted** | 67-76% across all tiers |
| Formality scorer detects AI | **Dead** | Measures formality, not engagement (AUC ~0.5) |
| Attention in high-AI PRs (Finding 3) | **Retracted** | fp_experience contamination; n=9 without it |
| 2x2 AI x Attention (Finding 5) | **Retracted** | Same contamination |
| Attention gradient with AI level (Finding 6) | **Untestable** | n=3-6 in high-AI buckets with strict signals |

---

## What Survives, and What It Means

The honest story from this data is:

1. **AI-authored PRs produce more defects.** (Strong, p < 10^-15)
2. **Polished AI specs are a trap.** Within unattended high-AI PRs, higher spec quality predicts WORSE outcomes. (Strong, p=0.0003)
3. **Attention signals correlate with fewer defects pooled across all PRs.** (Marginal, p=0.029 for rework only)
4. **Rework doesn't trigger learning.** 23% of post-rework PRs also get reworked. (No attention dependency)
5. **Fix chains exist.** 24% of fixes need re-fixing. (No attention dependency)

What we CANNOT say: that attention specifically helps high-AI PRs more than low-AI PRs. The data is consistent with this (the direction is right), but the clean signals are too rare in AI-written text to reach significance. This is the central question of the paper and it remains unanswered by the current dataset.

---

## What We Can't Measure (Yet)

1. **Prompt history** -- the real engagement signal is in the AI chat, not the PR description. We're measuring residue of thinking, not thinking itself.
2. **Untagged AI usage** -- 88% of PRs have no AI tag and no human signal. They're in the unknown middle.
3. **Causal direction** -- do attention signals cause better outcomes, or do skilled developers both write casually AND produce better code?

---

## Implications

### For the book (The Delivery Gap):
The core narrative holds: AI increases defect rates and polished specs create false confidence. The attention hypothesis is promising but underpowered -- present it as a direction, not a proven finding.

### For the Infrastructure Multiplier paper:
Finding 1 (AI defect rate) and Finding 8 (spec paradox) are solid. The attention-in-high-AI interaction effect needs more data before it can be published as a primary finding.

### For practitioners:
- AI-authored PRs need more scrutiny, not less.
- An AI-generated spec with empty sections is a warning sign, not a green flag.
- A polished-looking AI spec may suppress reviewer vigilance -- the Q4 spec paradox.
- The clean attention signals (typos, casual language, questions) DO correlate with fewer defects in the pooled population, but the within-high-AI claim is unproven.

---

## Statistical Methods

- **AI detection:** Logistic regression on 26 text features, AUC 0.853 (5-fold CV)
- **Significance tests:** Fisher's exact test (two-tailed) for all comparisons
- **Escape definition:** strict_escaped (requires follow-up PR with fix/revert in title)
- **Attention definition:** Strict 3-signal (typos, casual, questions). The original 4-signal definition including f_fp_experience is DEPRECATED due to AI contamination.
- **Confounds acknowledged:** Complexity, author skill, repo culture, fp_experience contamination, repo concentration (pingcap/tidb and astral-sh/ruff account for 69% of high-AI attention PRs with original definition).

---

## Finding 7: Broadening Attention Signals Destroys the Effect (SURVIVES)

This finding is actually STRENGTHENED by the contamination discovery.

| Composite | n_attn | Δ Rework | p-value |
|---|---|---|---|
| Strict (typos, casual, questions) | 221 | -5.2pp | **p=0.029** |
| Narrow (+ fp_experience, CONTAMINATED) | 404 | -5.4pp | **p=0.001** |
| Broad (+mentions, incidents, history, refs) | 2,851 | -0.4pp | p=0.58 (nothing) |

The fp_experience contamination discovery is itself evidence FOR Finding 7's thesis: only signals that AI cannot produce are valid attention markers. fp_experience looked good in pooled analysis but was contaminated within high-AI PRs -- exactly what broadening would do.

**The 3 signals that genuinely work are artifacts of human imperfection:**
1. **Typos** -- AI doesn't misspell
2. **Casual language** -- AI doesn't write "kinda", "btw", "WIP"
3. **Questions** -- AI doesn't express uncertainty

---

## Finding 8: The Polished Spec Paradox (SURVIVES -- strongest novel finding)

Within high-AI PRs with no attention signals, spec quality INVERSELY predicts outcomes:

| Quality tier | n | Rework | Escape | avg quality |
|---|---|---|---|---|
| Q1 (worst specs) | 130 | 6.9% | **0.0%** | 25 |
| Q2 | 138 | 10.1% | 1.4% | 43 |
| Q3 | 136 | 21.3% | 8.1% | 55 |
| Q4 (best specs) | 141 | **22.7%** | **6.4%** | 71 |

Fisher's exact Q4 vs Q1: rework **p=0.0003***, escape **p=0.004**. OR=3.95 for rework.

This finding is UNAFFECTED by fp_experience contamination because it filters to PRs with NO attention signals. Whether fp_experience is included or excluded in the attention filter barely changes the population (538 vs 545 PRs).

**Why this happens:** A sloppy AI spec ("fix the thing") is obviously incomplete -- reviewers scrutinize it. A polished AI spec with detailed sections and listed edge cases LOOKS thorough -- reviewers trust it and rubber-stamp. The polish is a trap that suppresses reviewer vigilance.

---

## Finding 9: AI Failure Scales With Size (size scaling SURVIVES)

Within unattended high-AI PRs, defect rate scales linearly with PR size:

| PR size (unattended AI) | Rework | Escape | n |
|---|---|---|---|
| Q1 (<20 lines) | 7.3% | 1.4% | 1,037 |
| Q2 (20-91 lines) | 16.0% | 5.0% | 457 |
| Q3 (91-350 lines) | 24.1% | 7.3% | 453 |
| Q4 (350+ lines) | **31.3%** | **12.1%** | 453 |

The size-scaling finding does not depend on attention signals.

The original "attention fixes every size" comparison used the contaminated 4-signal definition and is not reliable.

---

## The Confusion Log: What We Got Wrong Along The Way

1. **"Specs reduce rework" (Act 1)** -- Starting hypothesis. Wrong.
2. **"Better specs reduce rework" (Act 2)** -- Quality gradient is flat/inverted.
3. **"Alignment failures are AI-specific" (Claim 3)** -- RETRACTED.
4. **"The engagement scorer detects AI" (Act 5)** -- Measures formality, not engagement.
5. **"Specs help high-AI PRs" (Claim 2 refinement)** -- Spec'd high-AI PRs are worse.
6. **"Broadening attention signals will increase sample size"** -- Kills the signal.
7. **"Size = precision"** -- Size correlates but is not causal.
8. **Escape definition was inflated** -- Introduced strict_escaped.
9. **Data quality issues** -- 29 repos capped at 100 PRs.
10. **"fp_experience is a human signal" (Cycle 2)** -- AI generates "I tried/noticed" at 5.7x the rate of humans. 92% of high-AI attention triggers were from this contaminated signal. The "strongest finding" (Finding 3) was built on it.

Each correction was driven by a human asking "but is this actually true?" -- which is itself evidence for the attention hypothesis.

---

## Finding 10: People Don't Learn From Getting Caught (rework recurrence SURVIVES)

After a PR gets reworked, what does the author do on their next PR?

| After a... | n | Next PR also reworked |
|---|---|---|
| Reworked PR | 1,233 | **23.0%** |
| Clean PR | 6,997 | 12.9% |

Getting reworked makes you **1.8x more likely** to get reworked again. This finding does NOT depend on attention signals.

**Serial reworkers exist:** 41 authors had 3+ consecutive reworks (30 with exactly 3, 6 with 4, 2 with 5, 3 with 6 in a row).

Attention rates after rework (strict 3-signal): 0.9% after rework vs 1.8% after clean. Directionally consistent (attention drops after rework) but absolute rates are tiny.

---

## Finding 11: Fix Chains -- Fixes Need Fixing (SURVIVES)

| Fix attempts | Count | % |
|---|---|---|
| Fixed in 1 attempt | 1,205 | 76% |
| Needed 2 attempts | 267 | 17% |
| Needed 3 attempts | 71 | 4% |
| Needed 4+ attempts | 35 | 2% |
| **Total needing 2+ fixes** | **373** | **24%** |

The chain-length distribution does not depend on attention signals.

---

## Finding 12: Historical Baseline — Attention Signals Vanished With AI Adoption

Pre/post comparison using 2023-H1 (pre-AI) vs current (2025-2026) data from the same repos.

**Novu (0% AI in 2023 → 18.1% now):**

| Signal | 2023-H1 (n=861) | Current (n=867) | Change | Fisher p |
|---|---|---|---|---|
| Questions | **74.0%** | **0.3%** | -73.7pp | **p=8.1×10⁻²⁷³** |
| Strict 3-signal | **74.0%** | **0.3%** | -73.7pp | **p=8.1×10⁻²⁷³** |
| AI-tagged | 0.0% | 18.1% | +18.1pp | **p=5.3×10⁻⁵¹** |
| Casual | 0.7% | 0.1% | -0.6pp | |

**Deno (0% AI in 2023 → 14.0% now):**

| Signal | 2023-H1 (n=1,182) | Current (n=500) | Change | Fisher p |
|---|---|---|---|---|
| Questions | **2.5%** | **0.2%** | -2.3pp | **p=4.6×10⁻⁴** |
| Strict 3-signal | **3.0%** | **0.4%** | -2.6pp | **p=4.0×10⁻⁴** |
| AI-tagged | 0.0% | 14.0% | +14.0pp | **p=3.6×10⁻³⁹** |

**Interpretation:** As AI adoption rose from 0% to 14-18%, human attention signals collapsed. Novu's question rate dropped from 74% to 0.3% — an odds ratio of 819. This is not a gradual decline; it's a cliff. Developers stopped asking questions in PR descriptions when AI started writing them.

This is the strongest evidence for the attention hypothesis: the same repos, same teams, same codebases — but AI adoption eliminated the cognitive engagement signals that predict quality outcomes.

**Caveat:** We cannot prove AI CAUSED the attention drop. Other factors (team changes, process changes, repo maturity) could contribute. But the timing and magnitude (0% AI → 18% AI coinciding with 74% questions → 0.3% questions) are highly suggestive.

---

## Reproduction

```bash
cd ~/dev/ai-augmented-dev/research/study
source .venv/bin/activate
python3 build-unified-csv.py && python3 compute-features.py && python3 build-master-csv.py
python3 reproduce-claims.py
```
