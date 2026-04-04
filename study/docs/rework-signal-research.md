# Rework Signal Research: What's Validated and What's Not

**Date:** 2026-03-28

## Summary

| Signal | Validated as defect predictor? | Key paper | Strength |
|--------|-------------------------------|-----------|----------|
| Code churn (relative) | **Yes** | Nagappan & Ball, ICSE 2005 | **Strong** — 89% accuracy, Microsoft Research |
| DORA rework rate | Correlated with CFR | DORA 2024-2025 reports | **Strong** — large survey, credible source |
| PR size | Practitioner consensus | SmartBear/Cisco 2006 | Moderate — one study, unreplicated at scale |
| Review rounds | Process metric only | Fan et al. 2021 | Weak — no defect link established |
| Ticket reopens | Studied, not as leading indicator | Zimmermann et al., ICSE 2012 | Moderate — predicts which bugs reopen |
| Abandoned PRs | Studied as waste | Jiang et al., TOSEM 2022 | Moderate for waste — no defect link |

## Key Finding for the Book

**DORA 2025 Report:** AI adoption improves throughput but increases delivery instability — specifically increased rework and failed deployments. The report states this is because acceleration without robust control systems (automated testing, fast feedback loops) leads to instability downstream. This IS the delivery gap stated by DORA with survey data.

Only 7.3% of teams report rework rates below 2%. 26.1% experience rework rates between 8-16%.

## Detail per Signal

### Code Churn (Relative) — VALIDATED
- Nagappan & Ball (2005), Microsoft Research, ICSE: relative churn measures discriminated fault-prone from non-fault-prone binaries at 89% accuracy on Windows Server 2003
- Key insight: absolute churn is poor predictor; RELATIVE churn (normalized by component size, temporal extent) is the signal
- GitClear (2024-2025): AI-generated code has 41% higher churn rate than human-written code
- Citation: https://www.microsoft.com/en-us/research/publication/use-of-relative-code-churn-measures-to-predict-system-defect-density/

### DORA Rework Rate — VALIDATED (as stability signal)
- Added as 5th DORA metric in 2024
- Definition: unplanned deployments to fix user-facing bugs / total deployments
- Highly correlated with change failure rate
- 2025 finding: AI adoption increases instability/rework
- Self-reported survey data (methodological caveat)
- Citations: dora.dev/research/, DORA 2025 report

### PR Size — MODERATE
- SmartBear/Cisco (2006): 2,500 reviews, 3.2M lines. 200-400 LOC optimal. Collapses after 400.
- Graphite (7M PRs): confirmed pattern. Large PRs get fewer review cycles (rubber-stamping).
- Our data (23,750 PRs): ρ = 0.115, p = 5.76e-71 for size→review friction. Replicates.
- No newer large-scale peer-reviewed replication.

### Review Rounds — NOT VALIDATED as defect predictor
- Fan et al. (2021): predicted how many rounds a patch will need. Not whether rounds predict defects.
- Mantyla & Lassenius (2009): 75% of review-found defects are evolvability (not functional bugs)
- Industry: widely tracked as process metric by Graphite, Jellyfish, software.com
- Gap: no study validates "more rounds → fewer post-merge defects"

### Ticket Reopens — NOT VALIDATED as leading indicator
- Zimmermann et al. (2012), Microsoft, ICSE: characterized why bugs reopen (6 causes)
- Lo et al. (2017): not all reopens are negative (some are scope changes)
- Industry: tracked as KPI in ITSM. MetricNet: <5% reopen → >85% customer satisfaction.
- Gap: studied to predict which bugs will reopen, not whether reopen rate predicts future defects

### Abandoned PRs — NOT VALIDATED as defect predictor (waste signal only)
- Jiang et al. (2022), ACM TOSEM: 265,325 PRs, 4,450 abandoned. Complex PRs, novice contributors, lengthy reviews increase abandonment.
- Fan et al. (2022), ICSE: 12 main reasons for abandonment
- Code Climate: average 8% abandonment, ~$24K/year/developer wasted
- Gap: no link from abandonment rate to downstream quality

## Implications

The honest framing: we have two validated signals (relative code churn and DORA rework rate) and four useful-but-unvalidated process metrics. The book should:
1. Lead with the validated signals
2. Present the process metrics as "useful indicators" not "proven predictors"
3. Cite Nagappan & Ball and DORA 2025 as the evidence base
4. Note that nobody has connected all six signals together — that's the contribution
