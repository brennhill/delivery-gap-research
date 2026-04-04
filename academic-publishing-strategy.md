# Academic Publishing Strategy for The Delivery Gap

The Verification Triangle is in a similar position to where DORA was in 2015-2016. Forsgren had the practitioner reports (State of DevOps) and then published the academic backing. We have the book and the tooling. Here's what's publishable and when.

## DORA Precedent

Forsgren's timeline:
- **2016**: Two SSRN working papers (WDSI) — formally grounded the four metrics in the EOQ model
- **2017**: DESRIST/Springer design-science paper — validated the DORA platform as a research artifact
- **2018**: *Accelerate* book published
- **2020**: AMCIS paper — 7,522-respondent cluster analysis validating that throughput and stability move in tandem
- **2021**: SPACE framework (ACM Queue) — extended beyond the four metrics

Key insight: the SSRN papers came *before* the book and established academic priority. The large-N validation came *after*.

---

## Before the Book Ships (Strengthens Credibility)

### 1. SSRN Working Paper

**"The Verification Triangle: A Measurement Framework for AI-Assisted Software Delivery"**

Define the three vertices, the six core metrics, the manufacturing quality lineage (first pass yield = machine catch rate, rework rate = human save rate, scrap rate = escape rate). SSRN is where Forsgren published her early DORA papers. No peer review required, establishes priority, citable immediately.

This is the highest-leverage move — a reviewer or blurb-writer can point to it. A publisher evaluating the proposal sees an academic citation, not just a manuscript.

**Effort**: A weekend. The content already exists in Chapter 6 and the Verification Metrics appendix.

### 2. Blog Post With Open Data

Run the companion repo scripts against 2-3 public repos (or anonymized data from teams you've worked with). Publish the size-bucketed spec effectiveness numbers. "Here's what the Verification Triangle looks like on real codebases."

This is the equivalent of the early State of DevOps reports — practitioner-facing, data-backed, shareable.

**Effort**: A few days. Scripts exist; need real data.

---

## After the Book Ships (Builds the Research Program)

### 3. Conference Paper: Complexity-Controlled Spec Effectiveness

**Target venue**: AMCIS, ESEM, or CHASE (Cooperative and Human Aspects of Software Engineering)

**Study design**: Bucket PRs by size (lines changed), compare spec'd vs unspec'd rework rate, review cycle count, and time-to-merge within each bucket. This controls for complexity and proves specs actually help rather than just correlating with easier tasks.

**Data source**: Open-source repos using `gh pr view --json` scripts. N can be large with minimal effort.

**Why it matters**: This is a clean empirical study with a clear finding. If specs help within size buckets, it's causal evidence. If they don't, the book's thesis needs qualifying.

### 4. Design-Science Paper: The Tool Suite

**Target venue**: DESRIST or equivalent

**Subject**: UPFRONT (spec quality) + CATCHRATE (eval quality) + CHANGELEDGER (cost) as a research artifact. Design rationale, architecture, initial validation.

This is exactly Forsgren's DORA Platform paper (DESRIST 2017, Springer LNCS) transplanted to the Verification Triangle.

### 5. Industry Survey: Verification Triangle Maturity

**Target venue**: AMCIS or ICSE-SEIP (Software Engineering in Practice)

**Study design**: Survey engineering teams, cluster-analyze their Verification Triangle maturity (spec quality practices, gate coverage, cost measurement), correlate with delivery outcomes.

This is the AMCIS 2020 paper (Forsgren's 7,522-respondent cluster analysis) transplanted to the AI era. Need 500+ respondents to be taken seriously.

---

## Priority Order

1. **SSRN working paper** — before book ships, costs nothing, establishes priority
2. **Blog post with open data** — before or at book launch, drives awareness
3. **Conference paper on spec effectiveness** — after book ships, strongest empirical contribution
4. **Design-science paper on tools** — after tools are mature (v1.0+)
5. **Industry survey** — longest lead time, highest impact, needs distribution channel

---

## Academic References (DORA Lineage)

These are cataloged in `codex.md` as A036-A042:
- A036: Forsgren & Humble, "DevOps: Profiles in ITSM Performance" (WDSI 2016, SSRN)
- A037: Forsgren & Humble, "The Role of Continuous Delivery" (WDSI 2016, SSRN)
- A038: Forsgren et al., "DORA Platform" (DESRIST 2017, Springer LNCS)
- A039: Forsgren et al., "Taxonomy of Software Delivery Performance Profiles" (AMCIS 2020)
- A040: Forsgren et al., "The SPACE of Developer Productivity" (ACM Queue 2021)
- A041: Forsgren et al., "DevEx: What Actually Drives Productivity" (ACM Queue 2023)
- A042: Forsgren et al., "DevEx in Action" (ACM Queue 2024)
