# The Polished Spec Paradox: Why Better Documentation Doesn't Predict Better Software

*Specs constrain AI. They don't guarantee quality. And the one signal that does predict quality is something nobody measures.*

---

Everyone in software engineering agrees: write it down before you build it. The better the spec, the better the code. We tested this assumption against 23,967 pull requests across 43 open-source repositories using three independent scoring methods and three independent outcome detectors. The results:

1. **Specs don't reduce defects.** After controlling for change size, specs have no significant effect on production escapes (p=0.53).
2. **Better specs predict worse outcomes.** This holds across an LLM-based scorer (p=0.001), a deterministic structural scorer (p=0.0002), and persists after controlling for change size. The most likely explanation is confounding — harder work gets better specs AND more defects.
3. **Specs constrain AI, not humans.** AI-generated PRs without specs are nearly 2x larger than AI PRs with specs (median 99 vs 51 lines). Human PRs show no difference (~51 lines regardless). Specs act as a boundary on AI generation.
4. **Questions predict quality.** Among 44 textual features scanned, questions in the spec ("Should this handle the nil case?") are the only signal that predicts fewer production escapes. Every other measure of spec thoroughness — length, structure, specificity, acceptance criteria — predicts more defects, not fewer.

## The setup

We measured PR descriptions three ways:

**LLM scorer:** Seven dimensions (outcome clarity, error states, scope boundaries, acceptance criteria, data contracts, dependency context, behavioral specificity), each 0-100. Evaluated 6,203 PRs across 10 repositories.

**Structural scorer:** Deterministic text analysis — word count, markdown structure, specificity markers (file paths, function names, numbers), error awareness keywords, scope signals, acceptance criteria patterns, questions, and cross-references. No LLM involved. Scored all 23,967 PRs.

**JIT risk features:** Lines added/deleted, files changed, churn ratio — standard commit-level defect prediction features from Kamei et al. (2016). These measure the *change itself*, not the spec.

We measured outcomes three ways:

**Primary detector:** Follow-up PR matching — did a subsequent PR fix, revert, or correct this one?

**Conservative detector (`strict_escaped`):** Only counts follow-up PRs with explicit "fix" or "revert" in the title.

**Approximate SZZ:** Traces from fix PRs back to the most recent prior PR in the same repo — an approximation of the Śliwerski-Zimmermann-Zeller algorithm.

## Finding 1: Specs don't reduce defects

The raw numbers look promising:

| Group | Escape rate | Rework rate | n |
|---|---|---|---|
| Has spec | 3.8% | 12.2% | 6,203 |
| No spec | 4.2% | 15.5% | 17,764 |

But spec'd PRs are systematically smaller (median 51 vs 63 lines). Logistic regression controlling for change size:

| Outcome | has_spec effect | p-value |
|---|---|---|
| Production escapes | Not significant | p=0.53 |
| Rework | Modest reduction (OR=0.82) | p=0.007 |

Specs may reduce rework slightly, but the effect on production escapes disappears after controlling for change size.

## Finding 2: Better specs predict worse outcomes

This is the paradox, and it holds across both scorers.

**LLM scorer (6,203 PRs, 10 repos):**

| Quality tier | Rework | Escape | n |
|---|---|---|---|
| Low (<40) | 9.7% | 2.7% | 1,699 |
| Medium (40-69) | 12.4% | 4.5% | 3,325 |
| High (>=70) | 17.9% | 6.9% | 1,179 |

Fisher's exact HIGH vs LOW: OR=2.04 (rework, p<0.0001), OR=2.65 (escape, p<0.0001).

**Structural scorer (23,967 PRs, all 43 repos, no LLM):**

Higher structural scores predict more production escapes (OR=1.39, p=0.0002). Every dimension — length, structure, specificity, error awareness, acceptance criteria, references — goes in the wrong direction.

**After controlling for change size (logistic regression):**

The LLM quality score remains significant: each 1-point increase in q_overall increases escape odds by ~3% (p=0.001) and rework odds by ~2% (p=0.0002), even after controlling for log(additions), log(deletions), and log(files changed).

### Why?

Two explanations compete:

**Confounding by indication.** Complex, risky changes attract thorough specs AND have more defects. The spec doesn't cause the defects; the difficulty causes both. This is the most likely explanation and we cannot rule it out with observational data.

**Vigilance suppression.** A polished spec looks like someone thought deeply. Reviewers trust it and review less carefully. A sloppy spec is obviously incomplete, so reviewers scrutinize harder. This mechanism is supported by a sub-analysis of AI-assisted PRs where no human attention signals are present — the gradient intensifies in that context (Q4 rework: 22.7% vs Q1: 6.9%, p=0.0003).

Both may be partially true. What we can say definitively: **better-looking specs do not produce better outcomes in any analysis we ran.**

## Finding 3: Specs constrain AI, not humans

This emerged from the JIT risk profile analysis and is the most actionable finding.

| Group | Median lines | Median files | n |
|---|---|---|---|
| AI + spec | 51 | 2 | — |
| AI + no spec | 99 | 4 | — |
| Human + spec | 51 | 2 | — |
| Human + no spec | 52 | 3 | — |

AI-generated PRs without specs are nearly 2x larger. Human PRs are the same size regardless.

Humans already self-constrain. AI without a spec sprawls — touching twice as many files and writing twice as many lines. The spec acts as a boundary on AI generation, preventing the worst sprawl. This is a constraint mechanism, not a quality mechanism.

Spec quality (q_overall) has zero correlation with PR risk profile (r=0.011, not significant). The spec constrains scope but doesn't improve the code within that scope.

## Finding 4: Questions predict quality

Among 44 textual features scanned in PR descriptions, one stands out:

**Questions in the spec correlate with fewer production escapes.**

The structural scorer's `s_questions` dimension (count of question marks) is the only dimension that goes in the "right" direction — more questions, fewer escapes (r=-0.014, p<0.05). Every other dimension (length, structure, specificity, error awareness, acceptance criteria, references) correlates positively with defects.

When we pool questions with two other attention signals — typos (a marker of human typing, not AI generation) and casual/hedging language ("I think," "probably should," "not sure if") — the combined effect is clear:

| Group | n | Rework | Escape |
|---|---|---|---|
| Has attention signals | 221 | 8.6% | 2.3% |
| No attention signals | 9,782 | 13.7% | 4.4% |

That's -5.2pp rework and -2.1pp escape (p=0.029).

Questions are hard to confound with change complexity. Complex changes don't naturally have more question marks. Questions are a behavioral signal — the author was thinking about what they didn't know. This is fundamentally different from documenting what they did know, and it correlates with better outcomes while documentation quality does not.

## What this means

### For spec-driven development

The spec-driven development movement measures the wrong thing. Template completeness, section count, acceptance criteria presence — none of these predict quality in our data. The one signal that does predict quality (questions) is something no template requires and no scoring system measures.

This doesn't mean specs are useless. Specs constrain AI sprawl — a real and measurable benefit. And specs may reduce rework slightly (p=0.007). But the belief that better documentation produces better software is not supported by our data.

### For AI-assisted development

AI makes specs easy to produce. It can fill out any template perfectly. The result scores high on every quality metric — and correlates with worse outcomes, because the human never had to think.

When the spec was hard to write, the difficulty was the value. The spec was evidence of thinking. When AI generates the spec, the evidence disappears. The document looks identical. But the thinking didn't happen.

**The spec is not the point. The thinking the spec forces is the point.** And nobody measures the thinking.

### For tooling

If you're building spec processes or tools:

- **Stop measuring spec completeness.** It's noise at best and a false signal at worst.
- **Start measuring attention signals.** Questions, uncertainty, and human imperfection are better predictors than structural quality.
- **Use specs as AI constraints, not quality guarantees.** Specs prevent AI sprawl. They don't prevent AI mistakes.
- **Force the thinking, not the template.** Challenge-first processes (where humans must articulate their reasoning before AI generates code) may be more valuable than spec templates (where AI can fill in the blanks).

## Caveats

**Sample:** 43 open-source repositories, convenience sample. Cannot generalize to proprietary codebases.

**LLM spec scorer:** ±10-15pp variability per dimension. Produced minimal variance across repos (99% scored HIGH on a 0-100 scale). Cross-repo quality comparisons are unreliable. Within-repo variance is the usable signal.

**Structural scorer:** Deterministic and reproducible, but word count dominates the overall score. The finding that longer descriptions correlate with more defects likely reflects complexity confounding, not a causal relationship.

**Rework detector:** Unvalidated precision/recall. Cross-validated with conservative (strict_escaped) and approximate SZZ detectors. Direction consistent across all three.

**Confounding:** We control for change size but cannot control for change difficulty or risk. Confounding by indication — hard work gets better specs AND more defects — is the most parsimonious explanation for the paradox and cannot be eliminated with observational data.

**Attention signals:** Marginally significant (p≈0.06 individually, p=0.029 pooled) with small sample (n=221). Suggestive, not definitive.

**Questions signal:** Significant under the structural scorer (p<0.05) but effect size is small (r=-0.014). Replication needed.

## Related work

- **Montgomery et al. (2022):** Systematic mapping of 105 requirements quality studies. Most quality metrics measure textual properties, not cognitive properties. The gap between what's measurable and what matters remains open.
- **Nagappan & Ball (2005):** Code churn predicts defects with 89% accuracy — a downstream behavioral signal, not an upstream quality metric.
- **Kamei et al. (2016):** JIT defect prediction using 14 commit-level features. Change size and developer experience are the strongest predictors. We use these as controls.
- **Dell'Acqua et al. (2023):** Harvard/BCG — AI improved quality 40% inside the frontier, degraded it 19pp outside. The variable was judgment, not documentation.
- **Anthropic (2026):** Own RCT — AI assistance reduced comprehension by 17%. The interaction pattern (conceptual inquiry vs delegation) determines outcomes. Directly relevant: thinking quality, not artifact quality, drives results.
- **METR (2025):** AI increased completion time 19% for experienced developers. AI may hurt experts executing as well as novices learning.
- **Perry et al. (2024):** Microsoft — "false sense of confidence" with AI assistants. AI code reviewed less carefully despite comparable vulnerability rates. Supports the vigilance suppression mechanism.
- **SmartBear/Cisco:** Review effectiveness collapses above 400 LOC. Complementary: even a perfect spec can't fix a broken review.
- **Śliwerski, Zimmermann, Zeller (2005):** The SZZ algorithm for tracing bug-introducing commits. We use an approximation for cross-validation.

---

*This study analyzes 23,967 pull requests across 43 open-source repositories. Spec quality measured by LLM scorer (7 dimensions, 6,203 PRs) and deterministic structural scorer (8 dimensions, all PRs). Outcomes measured by primary rework detector, conservative strict_escaped variant, and approximate SZZ. Statistical tests: Fisher's exact, Mann-Whitney U, logistic regression (statsmodels), Spearman correlation. Analysis scripts in the [research repository](https://github.com/brennhill/ai-augmented-dev).*

*Part of ["The Delivery Gap"](https://thedeliverygap.com) by Brenn Hill — a book and empirical study on AI-assisted software delivery.*
