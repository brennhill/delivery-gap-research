// SSRN Working Paper — Spec-Driven Development Null Result
// Compile: typst compile ssrn-sdd-null-result.typ ssrn-sdd-null-result.pdf

#set document(
  title: "Does Spec-Driven Development Reduce Defects? An Empirical Test of Industry Claims Across 119 Open-Source Repositories",
  author: "Brenn Hill",
)

#set page(
  paper: "us-letter",
  margin: (top: 1in, bottom: 1in, left: 1in, right: 1in),
  numbering: "1",
  number-align: center,
)

#set text(
  font: "New Computer Modern",
  size: 11pt,
  lang: "en",
)

#set par(
  justify: true,
  leading: 0.7em,
  first-line-indent: 0.5in,
)

#set heading(numbering: "1.1")

#show heading.where(level: 1): it => {
  set text(size: 14pt, weight: "bold")
  set par(first-line-indent: 0pt)
  v(1.5em)
  it
  v(0.8em)
}

#show heading.where(level: 2): it => {
  set text(size: 12pt, weight: "bold")
  set par(first-line-indent: 0pt)
  v(1.2em)
  it
  v(0.6em)
}

#show heading.where(level: 3): it => {
  set text(size: 11pt, weight: "bold", style: "italic")
  set par(first-line-indent: 0pt)
  v(1em)
  it
  v(0.4em)
}

#set table(
  stroke: 0.5pt + luma(180),
  inset: 6pt,
)

#show table.cell.where(y: 0): set text(weight: "bold", size: 10pt)

#show raw.where(block: true): it => {
  set text(size: 9.5pt)
  block(
    fill: luma(245),
    inset: 10pt,
    radius: 2pt,
    width: 100%,
    it,
  )
}

#show raw.where(block: false): it => {
  set text(size: 10pt)
  box(fill: luma(240), inset: (x: 3pt, y: 1pt), radius: 1pt, it)
}

#set list(indent: 0.3in)
#set enum(indent: 0.3in)

// === TITLE PAGE ===

#v(2in)

#align(center)[
  #text(size: 18pt, weight: "bold")[
    Does Spec-Driven Development Reduce Defects?\ An Empirical Test of Industry Claims\ Across 119 Open-Source Repositories
  ]

  #v(1.5em)

  #text(size: 13pt)[Brenn Hill]

  #v(0.5em)

  #text(size: 11pt, fill: luma(100))[Independent Researcher]

  #v(2em)

  #text(size: 11pt, fill: luma(100))[Working Paper --- April 2026]

  #v(1em)

  #text(size: 10pt, fill: luma(120))[
    Suggested citation: Hill, B. (2026). Does Spec-Driven Development Reduce Defects? An Empirical Test of Industry Claims Across 119 Open-Source Repositories. SSRN Working Paper.
  ]
]

#v(2em)

#par(first-line-indent: 0pt)[
  #text(weight: "bold", size: 11pt)[Abstract]
]

#par(first-line-indent: 0pt)[
  #text(size: 10.5pt)[
Spec-driven development (SDD) tools --- GitHub's Spec Kit, Amazon's Kiro, and others --- claim that writing specifications before implementation reduces defects, prevents rework, and improves code quality. These claims lack empirical evidence. We provide the first large-scale test: 88,052 pull requests (after bot exclusion) across 119 open-source repositories (103 with SZZ defect tracing coverage), using within-author fixed-effects estimation. We test specification _artifacts_ in open-source pull requests --- the closest available proxy for SDD workflows, scored on the same quality dimensions SDD tools prescribe --- not the tools' integrated workflows directly. Five hypotheses derived from vendor claims are tested. None are supported at a level that would justify the vendor claims. The naive association between specifications and defects is _reversed_ (specifications accompany more bugs, not fewer); after within-author controls, the most likely interpretation is confounding by indication: harder tasks receive specifications and independently produce more defects. Specification quality has no meaningful effect on rework (_p_ = 0.827). Specifications do not constrain AI-generated code scope (_p_ = 0.997). One hypothesis (specification quality reduces defects) shows a small signal (_p_ = 0.016) that does not survive robustness checks, and even at face value predicts only 8 fewer bugs per 1,000 pull requests per 10-point quality improvement --- unlikely to justify the specification effort required. Ten robustness checks confirm the overall null. Specification artifacts proxy for task complexity, not quality improvement.
  ]
]

#pagebreak()

// === BODY ===

= Introduction

#par(first-line-indent: 0pt)[
The rise of AI-assisted software development has produced a new category of developer tooling: specification-driven development (SDD) frameworks. These tools --- including GitHub's Spec Kit #cite(<speckit2025>) and Amazon's Kiro #cite(<kiro2025>) --- claim that writing formal specifications before implementation leads to fewer defects, less rework, and higher-quality code, particularly when AI agents perform the implementation.
]

Böckeler #cite(<fowler2025>) defines spec-driven development as "writing a 'spec' before writing code with AI" where "[t]he spec becomes the source of truth for the human and the AI." The GitHub Copilot Academy frames it more strongly: "Specifications don't serve code --- code serves specifications" #cite(<copilotacademy2025>). The movement gained momentum in 2025 with the release of GitHub's Spec Kit (open-source, v0.0.72 as of this writing) and Amazon's Kiro IDE. Böckeler examined three tools pursuing the approach #cite(<fowler2025>). SDD is positioned as an antidote to "vibe coding" --- iteratively prompting AI without formal requirements --- which practitioners associate with scope creep, rework, and defects.

The core premise is intuitive: if developers articulate what software should do before writing it, AI systems will produce more reliable output. The GitHub Copilot Academy lists "reduced rework, living documentation, systematic quality" among SDD's benefits #cite(<copilotacademy2025>). Kiro claims that specifications enable "fewer iterations and higher accuracy" and "prevent costly rewrites" #cite(<kiro2025b>). GitHub's Spec Kit blog post promises "less guesswork, fewer surprises, and higher-quality code" #cite(<speckit2025>).

These claims rest on a plausible causal chain: clearer requirements → less ambiguity → fewer defects. However, none of the marketing materials, documentation, or blog posts accompanying these tools cite empirical evidence for the claimed outcomes. The assertions are presented as self-evident truths rather than testable hypotheses. No study has tested SDD's quality claims on production-scale data prior to this paper.

This paper provides the first large-scale empirical test. We analyze 88,052 merged pull requests (after excluding 12,195 bot-authored PRs) across 119 open-source repositories, using the SZZ algorithm to trace defects back to their introducing commits and within-author fixed-effects estimation to control for developer-level confounding. We derive five hypotheses directly from vendor claims and test each with the most conservative methodology available for observational data.

= Related Work

== Requirements Engineering and Defect Prevention

The claim that upfront specification prevents defects has deep roots in software engineering. Boehm's cost-of-change curve #cite(<boehm1981>) argued that requirements defects are exponentially cheaper to fix early. However, subsequent work has challenged the universality of this finding. Shull et al. #cite(<shull2002>) found that the cost multiplier depends heavily on project context, and agile methodologies have demonstrated that iterative refinement can be more effective than upfront specification for certain project types #cite(<beck2001>).

The question of whether requirements quality predicts software defects has been studied directly. Mund et al. #cite(<mund2015>) combined two empirical studies and found only weak evidence that requirements specification quality predicts implementation defects, with effect sizes that varied substantially across projects. Femmer et al. #cite(<femmer2017>) developed automated detection of "requirements smells" (ambiguity, incompleteness, inconsistency) and found that while smells were prevalent, their relationship to downstream defects was context-dependent. These findings suggest that the relationship between specification quality and code quality is not as straightforward as SDD vendors assume --- a pattern our study confirms at larger scale.

== SDD Literature

The academic literature on SDD perpetuates the pattern of unsubstantiated claims. Piskala #cite(<piskala2026>) claims "controlled studies showing error reductions of up to 50%," citing a Red Hat Developer blog post #cite(<naszcyniec2025>) and an InfoQ article #cite(<griffin2026>) as evidence. Neither source contains any controlled study, any experiment, or any quantitative data. The "50%" figure traces through a citation chain that terminates in practitioner opinion pieces with no empirical backing. Guo et al. #cite(<sedeve2025>) claim SDD "guarantees software quality" without empirical validation. Marri #cite(<marri2026>) reports a 73% security defect reduction from constitutional specs, but on a single project (_n_ = 1), with the same developer implementing both conditions sequentially --- the author acknowledges "small sample size limits statistical power." Roy #cite(<roy2026>) proposes iterative spec-code co-evolution but reports no independently validated quality outcomes. Zietsman #cite(<zietsman2026>) runs small planted-bug experiments and is honest about their limitations ("directional, not statistically significant"), while contributing the useful observation that AI reviewers without specs suffer circular reasoning --- but does not test whether specs reduce defects at scale.

Practitioner evaluations have been more skeptical. Eberhardt, writing for Scott Logic, found Spec Kit roughly ten times slower than iterative development, producing thousands of lines of specification markdown that still resulted in buggy code #cite(<scottlogic2025>). Zaninotto argued that "SDD shines when starting a new project from scratch, but as the application grows, the specs miss the point more often and slow development," and proposed iterative natural-language development as a faster alternative #cite(<zaninotto2025>).

No study has tested SDD's quality claims on production-scale data prior to this paper.

= Hypotheses

We identified five empirical claims made by SDD tool vendors in their public documentation, blog posts, and marketing materials. Each claim is stated verbatim and mapped to a testable hypothesis.

#par(first-line-indent: 0pt)[
  #text(weight: "bold")[Claim 1: Specifications reduce defects.]
]

GitHub's Spec Kit blog post promises "less guesswork, fewer surprises, and higher-quality code" #cite(<speckit2025>). Kiro claims specifications lead to "fewer iterations and higher accuracy" #cite(<kiro2025b>).

#par(first-line-indent: 0pt)[
  *H1: Pull requests with specification artifacts have lower defect-introduction rates than pull requests without them, controlling for author and PR size.*
]

#par(first-line-indent: 0pt)[
  #text(weight: "bold")[Claim 2: Specifications reduce rework.]
]

The GitHub Copilot Academy lists "reduced rework" among SDD's benefits #cite(<copilotacademy2025>). Kiro claims to "prevent costly rewrites" #cite(<kiro2025b>). GitHub's blog states that SDD enables "iterative development without expensive rewrites" #cite(<speckit2025>).

#par(first-line-indent: 0pt)[
  *H2: Pull requests with specification artifacts have lower rework rates than pull requests without them, controlling for author and PR size.*
]

#par(first-line-indent: 0pt)[
  #text(weight: "bold")[Claim 3: Clearer specifications produce more reliable code.]
]

GitHub's Spec Kit blog states that "providing a clear specification up front, along with a technical plan and focused tasks, gives the coding agent more clarity, improving its overall efficacy" #cite(<speckit2025>). Kiro claims specifications enable "fewer iterations and higher accuracy" #cite(<kiro2025b>). This implies a dose--response relationship: higher specification quality should predict fewer defects.

#par(first-line-indent: 0pt)[
  *H3: Among pull requests with specifications, higher specification quality predicts lower defect-introduction rates, controlling for author and PR size.*
]

#par(first-line-indent: 0pt)[
  *H4: Among pull requests with specifications, higher specification quality predicts lower rework rates, controlling for author and PR size.*
]

#par(first-line-indent: 0pt)[
  #text(weight: "bold")[Claim 4: Specifications constrain AI-generated code scope.]
]

GitHub's Spec Kit blog describes tasks that give "the coding agent a way to validate its work and stay on track" #cite(<speckit2025>). Kiro claims specs provide "a North Star to guide the work of the agent, allowing it to take on larger tasks without getting lost" #cite(<kiro2025>).

#par(first-line-indent: 0pt)[
  *H5: Specifications reduce code churn (additions + deletions) for AI-tagged pull requests more than for human-authored pull requests, controlling for author.*
]

= Methods

== Dataset

We collected pull request data from 119 open-source repositories spanning 17 programming languages. Repositories were selected to represent large, active projects with diverse contribution patterns. We collected data between March 28 and April 3, 2026, with a 365-day lookback window per repository. The resulting dataset spans April 2025 through early April 2026 (p1--p99: April 8, 2025 to April 1, 2026), totaling 100,247 PRs. We excluded 12,195 bot-authored PRs (dependabot, renovate, and other automated accounts identified by username pattern and bot flags), leaving 88,052 PRs from human and AI-assisted authors.

For each pull request, we extracted: author, merge date, additions, deletions, files changed, linked issues, PR description, review comments, and co-author tags (used to identify AI-assisted contributions).

#figure(
  table(
    columns: (auto, auto, auto),
    align: (left, right, left),
    table.header([*Metric*], [*Value*], [*Notes*]),
    [Repositories], [119], [convenience sample, 17 languages],
    [PRs (post-bot exclusion)], [88,052], [12,195 bots removed],
    [Median PRs per repo], [517], [range 9--4,803],
    [Median spec rate (per repo)], [26.2%], [IQR 16.0--41.1%],
    [Median AI tag rate (per repo)], [1.2%], [IQR 0.4--8.1%],
    [SZZ-covered repos], [103], [16 had unreachable merge SHAs],
    [SZZ bug-introducing PRs], [9,754], [12.5% of SZZ-covered PRs],
    [Quality-scored PRs], [5,192], [5.9% of total; non-random subsample],
  ),
  caption: [Study dataset overview.],
) <tab:dataset-overview>

The sample spans 17 programming languages, with Python (31 repos, 26%), TypeScript (26, 22%), Go (17, 14%), and Rust (13, 11%) predominating. The median repository has a 26.2% specification rate (IQR 16.0--41.1%). AI tagging is present in most repositories: the median AI tag rate is 1.2% (IQR 0.4--8.1%). The 5,989 AI-tagged PRs provide sufficient statistical power for the primary AI analyses, though we recognize that the AI-specific results would benefit from a larger AI-tagged sample as agentic workflows become more prevalent.

== Variables

=== Specification Presence (`specd`)

A pull request is classified as "specified" if it meets any of the following criteria: (a) it links to a GitHub issue or external tracking ticket, (b) its description references a specification document, RFC, or design doc, or (c) its description contains structured requirements content (acceptance criteria, behavioral descriptions, scope boundaries). Classification is performed programmatically by parsing PR metadata: issue references (`#123`, `fixes #456`), cross-reference URLs, and description structure (presence of headings, checklists, or requirement-style language). 24,298 of 88,052 PRs (27.6%) are classified as specified.

This operationalization is deliberately generous: it captures any form of upfront specification artifact, from a linked Jira ticket to a detailed RFC. SDD tools claim benefits from _any_ form of specification, so we test the broadest reasonable definition. Specification _presence_ and specification _quality_ are tested separately: H1 and H2 test whether having any specification artifact predicts fewer defects or less rework; H3 and H4 test whether, among the subset of PRs that have specifications, higher-quality specifications predict better outcomes. This two-level design addresses the objection that our binary `specd` measure is too coarse by also testing whether the content of the specification matters.

=== Specification Quality (`q_overall`)

For the subset of specified PRs with substantial descriptions (body length > 50 characters), we scored specification quality by prompting Claude Haiku (Anthropic) with the PR title and body and a structured rubric. The LLM scored each PR across seven dimensions: outcome clarity, error states, scope boundaries, acceptance criteria, data contracts, dependency context, and behavioral specificity. Each dimension is scored 0--100, and the overall quality score is the mean across dimensions.

These seven dimensions were chosen to align with the quality criteria recommended by SDD tools themselves. Spec Kit's template prescribes "core requirements" (outcome clarity), "acceptance criteria" (our acceptance criteria dimension), "edge cases" (error states), "data models" and "API contracts" (data contracts), and "user stories" (behavioral specificity) #cite(<speckit2025>). Kiro prescribes "clear requirements," "acceptance criteria," "system architecture," and "technology choices" #cite(<kiro2025b>). Six of our seven dimensions have direct equivalents in Spec Kit's recommended structure; all seven are covered across both tools. This alignment is deliberate: we measure specification quality on the dimensions that SDD vendors themselves say matter.

We validated the LLM scoring against independent human ratings on a stratified random sample of 30 PRs. The human rater scored each dimension on the same rubric, blind to the LLM scores. Overall rank-order agreement was moderate: Spearman _ρ_ = 0.37 (_p_ = 0.04), Pearson _r_ = 0.44 (_p_ = 0.02). The LLM scores systematically higher than the human rater (mean bias: +7 points on the 0--100 scale, mean absolute difference: 16 points). Per-dimension agreement varies: scope boundaries (_ρ_ = 0.45, _p_ = 0.01), dependency context (_ρ_ = 0.37, _p_ = 0.04), and behavioral specificity (_ρ_ = 0.39, _p_ = 0.03) show significant agreement, while acceptance criteria (_ρ_ = 0.02) and error states (_ρ_ = 0.18) show near-zero correlation. The LLM reliably detects whether specification content is _present_ but cannot judge whether it is _correct_ for the domain --- a distinction between formal completeness and functional quality. Since even this completeness-oriented measure shows no defect benefit, the null finding is conservative: a more precise quality measure would sharpen the estimate, not reverse it.

5,192 PRs (5.9% of total) received quality scores. This subsample is non-random --- only spec'd PRs with sufficient description text were scored --- and results from this subsample carry a selection bias caveat.

A further limitation: we cannot distinguish specifications written before implementation from descriptions written after. Many PR descriptions in our dataset are likely post-hoc --- the developer wrote the code, then described what it does. We compared quality scores for PRs with linked issues (more likely pre-implementation intent; median quality 57, _N_ = 975) to PRs classified by description content alone (more likely post-hoc; median quality 51, _N_ = 978). The difference is statistically significant (_p_ < 0.001) but substantively small (6 points on the 0--100 scale), and the direction varies by dimension. Neither group shows meaningfully different defect rates. The pre/post distinction does not appear to matter for our quality measure, and the null finding holds across both subgroups.

Furthermore, many effective AI instructions are inherently underspecified by our rubric's standards. A prompt like "improve the error handling, it looks ugly" scores low on outcome clarity, acceptance criteria, and behavioral specificity --- yet it is a perfectly successful instruction for an AI agent that can read the surrounding code. The agent does not need the spec to enumerate every error case; it can infer them from context. This class of task --- where the codebase itself provides sufficient specification --- is invisible to our quality measure but may represent a large share of productive AI-assisted work. If detailed specifications add no value for tasks where the code context is sufficient, the marginal benefit of specification effort is even smaller than our results suggest.

=== Defect Introduction (`szz_buggy`)

We applied the SZZ algorithm #cite(<szz2005>) to 103 of 119 repositories, tracing 64,805 blame links from fix commits to bug-introducing commits. The remaining 16 repositories produced zero traceable blame links: their merge commit SHAs (recorded by the GitHub API) are not reachable in single-branch clones, typically because the repository uses squash-merge workflows where GitHub's synthetic merge commits are garbage-collected after merging. The SZZ algorithm traces defect-fixing commits back to the commits that introduced the defect using `git blame`. We use the basic SZZ variant, which da Costa et al. #cite(<dacosta2017>) found misattributes 46--71% of bug-introducing changes depending on the project. This noise is substantial, but it is non-differential with respect to specification presence: there is no reason to expect SZZ to systematically misattribute more for spec'd PRs than unspec'd PRs. Non-differential measurement error attenuates associations toward the null, which works against finding a protective effect but does not create spurious reversed associations. We acknowledge the implications for statistical power in Section~7. Each bug-introducing commit was mapped to its originating pull request. A PR is marked `szz_buggy = True` if any of its commits were identified as introducing a defect that was later fixed. 9,754 PRs (12.5% of those in SZZ-covered repos) are marked as bug-introducing.

=== Rework (`reworked`)

A pull request is classified as reworked if a subsequent PR within 30 days by any author modifies overlapping files and has a title or description indicating correction (matching patterns such as "fix," "revert," "bugfix," "hotfix," "regression," "broke," or "broken"). File overlap is computed by comparing the set of files changed in each PR pair; high-frequency files (touched by >30% of PRs in the repository) are excluded to avoid spurious attribution. 11,820 PRs (13.4%) are classified as reworked. The 30-day window was chosen based on sensitivity analysis: rework detection increases from 14 to 30 days but shows diminishing returns beyond 30 days (the spec--rework association is directionally consistent across 14-, 30-, 60-, and 90-day windows).

=== AI-Tagged (`ai_tagged`)

A pull request is classified as AI-assisted through two detection layers. First, a regex matches co-author tags (e.g., `Co-authored-by: Copilot`), generation attribution strings (`Generated with`, `Claude Code`, `written with/by` followed by a tool name), AI agent markers (`CURSOR_AGENT`, `coderabbit.ai`, `AI-generated`), and the robot emoji (🤖). Second, we parse structured "AI Disclosure" and "AI Usage" sections that some repositories include in their PR templates, classifying the disclosure content as AI-used or no-AI-used. We validated the combined classifier against 537 PRs with clear self-reported AI disclosures: precision is 98.8% (1 false positive) and recall is 24.2% (75.8% false negatives). The low recall reflects that many developers describe AI use in natural language that our patterns do not capture. 5,989 PRs (6.8%) carry AI tags after bot exclusion. This remains a lower bound.

=== Code Churn (`total_churn`)

Total code churn is defined as additions + deletions. We use `log(1 + churn)` in regressions to normalize the heavily right-skewed distribution (median: 55, mean: 698).

== Statistical Approach

For each hypothesis, we report three levels of analysis:

#par(first-line-indent: 0pt)[
  *Pooled:* Raw rates and Fisher's exact test. This is the analysis that naive claims would cite.
]

#par(first-line-indent: 0pt)[
  *Controlled:* Logistic regression with size controls (log additions, log deletions, log files changed) and repository fixed effects (dummy variables). This addresses between-repository confounding.
]

#par(first-line-indent: 0pt)[
  *Within-author:* Linear probability model (LPM) with full author demeaning and clustered standard errors. All variables --- treatment, controls, and outcome --- are demeaned by author, equivalent to author fixed effects via the Frisch--Waugh--Lovell theorem. Standard errors are clustered at the author level to account for within-author residual correlation. We use LPM rather than logistic regression because demeaning is exact for OLS but produces biased estimates in logit due to the incidental parameters problem #cite(<neyman1948>). Chamberlain's conditional logit avoids this problem but requires discarding groups without outcome variation, reducing power. We follow Angrist and Pischke's recommendation of LPM for fixed-effects estimation with binary outcomes #cite(<angrist2009>). Primary models use size controls (log additions, log deletions, log files changed); we verify that results hold when adding JIT defect prediction features #cite(<kamei2013>) as additional controls (Section~5.6).
]

The within-author estimate is the most credible. Observational studies of developer practices face severe confounding: developers who write specifications may differ systematically from those who do not in skill, experience, task selection, and organizational context. The within-author design addresses this by comparing the same developer's specified PRs to their own unspecified PRs, eliminating all time-invariant author-level confounding. The treatment effect is identified only from authors who have _both_ specified and unspecified PRs in the dataset.

We restrict within-author analysis to authors with ≥2 PRs and report the number of authors with treatment variation (those who have both spec'd and unspec'd PRs), as these are the observations that identify the effect. For within-author estimates, we report 95% confidence intervals based on clustered standard errors to allow readers to assess what effect sizes are compatible with the data.

We do not apply multiple-comparison corrections across the five hypotheses. At α = 0.05, approximately 0.25 false positives are expected by chance. We interpret all results with this in mind.

Sample sizes vary across hypotheses because of SZZ coverage, quality scoring, and within-author filtering:

#align(center)[
  #table(
    columns: (auto, auto, auto, auto),
    align: (left, right, right, right),
    table.header[Hypothesis][PRs (pre-filter)][Within-author _N_][Identifying authors],
    [H1: specs → bugs], [77,814 (103 SZZ repos)], [72,046], [2,181],
    [H2: specs → rework], [88,052 (all 119 repos)], [81,647], [2,524],
    [H3: quality → bugs], [5,192 (scored subset)], [4,901], [357],
    [H4: quality → rework], [5,192 (scored subset)], [4,901], [357],
    [H5: spec × AI → churn], [88,052 (all 119 repos)], [71,932], [366],
  )
]

#text(size: 9pt)[Within-author _N_ is after restricting to authors with ≥2 PRs and dropping rows with missing controls. Identifying authors are those with variation in both treatment and control conditions.]

= Results

== H1: Specifications Reduce Defects

#par(first-line-indent: 0pt)[
  Analysis restricted to 77,814 PRs in the 103 repositories with SZZ coverage.
]

#align(center)[
  #table(
    columns: 4,
    table.header[Method][Coefficient][_p_-value][Interpretation],
    [Pooled (Fisher's exact)], [OR = 1.202], [< 0.001], [Spec'd PRs have _higher_ bug rate],
    [Controlled (logit, no repo FE#super[†])], [0.067], [0.006], [Effect persists with size controls],
    [Within-author (LPM)], [+0.014 \[+0.005, +0.024\]], [0.003], [+1.4pp _increase_ in bug rate],
  )
]

#text(size: 9pt)[#super[†] Repository fixed effects caused a singular matrix; controlled estimate uses size controls only. Within-author 95% CI in brackets.]

Identified from 2,181 authors with treatment variation (out of 4,328 authors with ≥2 PRs).

*H1 is not supported.* The pooled comparison (top row) is the naive analysis: spec'd PRs have a 20.2% higher odds of introducing a bug than unspec'd PRs. But this comparison is confounded --- developers who write specs are different from those who don't, and the repos that encourage specs are different from those that don't. The controlled logistic regression (middle row) adds size controls (repository fixed effects caused a singular matrix and were dropped). The effect persists.

The within-author estimate (bottom row) is the most credible. It compares the _same developer's_ spec'd PRs to their own unspec'd PRs, eliminating all time-invariant author-level confounding --- skill, experience, coding style, and organizational context are held constant because both the "treatment" and "control" come from the same person. The result: within-author, spec'd PRs are associated with a 1.4 percentage-point _increase_ in defect-introduction rates (_p_ = 0.003, OR = 1.13, Cohen's _d_ = 0.07). The direction is opposite to the vendor claim at every level of analysis.

This is consistent with confounding by indication: harder, riskier tasks receive specifications _and_ introduce more defects. A developer rationally invests specification effort in proportion to task complexity. The spec does not cause the bugs --- the task difficulty that motivates the spec also produces the bugs. When JIT risk features are added as controls (Section~5.6), the within-author spec coefficient drops 55% and loses significance (_p_ = 0.229), confirming that measurable task complexity explains most of the association.

A plausible alternative explanation is detection bias: if spec'd PRs have better test coverage and more granular QA, their bugs may be detected and fixed individually, making them more visible to SZZ tracing. Unspec'd PRs might have bugs that go undetected longer or get fixed in bulk refactoring commits that SZZ cannot trace, producing artificially low bug rates. We cannot rule this out entirely. However, two observations weigh against it. First, the rework measure (H2) does not depend on SZZ tracing and shows the same directional pattern. Second, propensity score matching (Section~5.6) eliminates the defect association entirely by matching on observable risk features. This suggests task complexity --- not detection asymmetry --- is the primary driver.

== H2: Specifications Reduce Rework

#par(first-line-indent: 0pt)[
  Analysis includes all 88,052 PRs.
]

#align(center)[
  #table(
    columns: 4,
    table.header[Method][Coefficient][_p_-value][Interpretation],
    [Pooled (Fisher's exact)], [OR = 1.179], [< 0.001], [Spec'd PRs have higher rework],
    [Controlled (logit + repo FE)], [0.178], [< 0.001], [Effect persists],
    [Within-author (LPM)], [+0.012 \[+0.005, +0.019\]], [0.001], [+1.2pp _increase_ in rework rate],
  )
]

Identified from 2,524 authors with treatment variation (out of 4,892 with ≥2 PRs).

*H2 is not supported.* The within-author effect is in the wrong direction: the same author's spec'd PRs have a 1.2 percentage-point higher rework rate than their unspec'd PRs (_p_ = 0.001, OR = 1.10, Cohen's _d_ = 0.05). The pooled odds ratio (1.18×) is modest, and within-author the effect is small but significant. Specifications are associated with more rework, not less.

== H3: Specification Quality Reduces Defects

#par(first-line-indent: 0pt)[
  H1 and H2 tested specification _presence_ --- whether having any specification artifact matters. H3 and H4 test specification _quality_ --- whether, among PRs that already have specifications, better-written specifications predict better outcomes. This is the stronger version of the SDD claim: not just "write a spec" but "write a _good_ spec." We consider H3 and H4 _exploratory_ rather than confirmatory: the quality measure has limited construct validity (human--LLM agreement _ρ_ = 0.37 on _N_ = 30) and is tested on a non-random 5.9% subsample.
]

Quality is the mean of seven rubric dimensions (described in Section~4.2), each scored 0--100. The overall quality score is the mean across dimensions. These dimensions were chosen to align with the quality criteria that SDD tools themselves prescribe (Section~4.2). The scoring is automated with limited human validation (_ρ_ = 0.37 on 30 PRs; Section~4.2) --- a limitation we acknowledge (Section~7). The quality score measures _formal_ specification completeness (are error states described? are acceptance criteria present?) rather than _functional_ correctness (are the right error states described? are the acceptance criteria valid for this domain?). A specification can score highly on every dimension and still specify the wrong behavior.

#par(first-line-indent: 0pt)[
  Analysis restricted to 5,192 PRs with LLM-scored specification quality (6.7% of SZZ-covered PRs). Selection bias caveat: only specified PRs with substantial descriptions were scored.
]

#align(center)[
  #table(
    columns: 4,
    table.header[Method][Coefficient][_p_-value][Interpretation],
    [Controlled (logit + repo FE)], [−0.005], [0.042], [Quality predicts fewer bugs],
    [Within-author (LPM)], [−0.0008 \[−0.0014, −0.0001\]], [0.016], [−0.08pp per quality point],
  )
]

Identified from 357 authors with treatment variation.

*H3 is weakly supported on a biased subsample.* The within-author coefficient is statistically significant (_p_ = 0.016) but substantively small: a 10-point improvement in specification quality (on the 0--100 scale) predicts a 0.8 percentage-point reduction in defect rate. This is the one result in the SDD-predicted direction. However, three caveats limit its interpretation. First, it is identified from 357 authors on 5.9% of the data, in a subsample non-randomly selected for having substantial specification content. Second, when restricted to the three quality dimensions with validated human--LLM agreement (Section~5.6), the effect weakens (_p_ = 0.072) while the unvalidated dimensions strengthen --- suggesting the signal may reflect description length or task complexity rather than specification quality (Section~5.6). Third, the effect size is small enough that even if causal, it would not justify the specification effort required to achieve it.

== H4: Specification Quality Reduces Rework

#align(center)[
  #table(
    columns: 4,
    table.header[Method][Coefficient][_p_-value][Interpretation],
    [Controlled (logit + repo FE)], [0.003], [0.195], [Quality does not predict rework],
    [Within-author (LPM)], [−0.000 \[−0.001, +0.001\]], [0.827], [Effectively zero],
  )
]

Identified from 357 authors with treatment variation (same scored subsample as H3).

*H4 is not supported.* Specification quality has no meaningful relationship with rework rates within-author. The coefficient is effectively zero, with _p_ = 0.827. The controlled logistic regression is also non-significant (_p_ = 0.195), consistent with the within-author finding (thorough specifications accompany difficult tasks that are more likely to be reworked).

== H5: Specifications Constrain AI Scope

#par(first-line-indent: 0pt)[
  Analysis uses log code churn (additions + deletions) as outcome. PRs with zero churn excluded (missing data artifact). AI detection combines regex pattern matching with structured AI disclosure parsing (Section~4.2), identifying 5,989 AI-tagged PRs --- 2.3× more than co-author tags alone.
]

#align(center)[
  #table(
    columns: 4,
    table.header[Group][Within-author coef][_p_-value][Interpretation],
    [AI-tagged PRs], [+0.120], [0.030], [Spec'd AI PRs are _larger_],
    [Human PRs], [+0.140], [< 0.001], [Spec'd human PRs are _larger_],
    [Interaction (spec × AI)], [+0.000 \[−0.101, +0.102\]], [0.997], [No differential scope constraint],
  )
]

AI analysis identified from 224 authors with treatment variation; interaction from 366.

*H5 is not supported.* The interaction term is effectively zero (_p_ = 0.997): specifications have the same effect on code churn for AI-tagged PRs as for human PRs. Within-author, both spec'd AI PRs (+12.0%) and spec'd human PRs (+14.0%) are larger than their unspec'd counterparts --- the same confounding-by-indication pattern as H1 and H2 (harder tasks get specs and produce more code). There is no evidence that specifications constrain AI-generated code scope.

== Robustness Checks

Ten additional analyses test whether the null result is an artifact of our primary measures or insufficient controls.

=== Alternative Outcome Measures

In addition to SZZ-traced defects and rework, we test specification effects on two additional outcome measures: _escaped defects_ (PRs whose CI passed but were subsequently followed by a fix or revert) and _strict escaped_ (escaped PRs where the follow-up PR's title explicitly indicates a fix or regression).

#align(center)[
  #table(
    columns: 4,
    table.header[Outcome][Within-author coef][_p_-value][N],
    [SZZ bugs], [+0.014], [0.003], [72,046],
    [Rework], [+0.012], [0.001], [81,647],
    [Escaped], [+0.001], [0.333], [81,647],
    [Strict escaped], [+0.001], [0.108], [81,647],
  )
]

N reflects within-author estimation restricted to authors with ≥2 PRs; the smaller samples compared to H1 (77,814) and H2 (88,052) reflect this filtering. The SZZ bugs and rework rows reproduce the H1 and H2 findings (included here for comparison). Both show significant positive associations --- specs accompany more bugs and more rework, not less --- which we attribute to confounding by indication. The escaped and strict escaped measures, which capture a different class of defect (CI-passing code that subsequently required a fix), are also directionally positive but not significant. No outcome measure shows specifications reducing defects at _p_ < 0.05.

=== Incremental Validity Beyond JIT Features

The JIT defect prediction framework #cite(<kamei2013>) uses 14 code-change features (subsystems touched, file entropy, developer experience, etc.) to predict defect-introducing commits. We test whether specification information adds predictive power beyond JIT features on the 62,126 PRs with both complete JIT features and SZZ outcomes.

#align(center)[
  #table(
    columns: 4,
    table.header[Model][Pseudo~_R_#super[2]][AIC][Spec variable _p_],
    [JIT features only], [0.078], [44,793], [---],
    [JIT + spec presence], [0.078], [44,786], [0.003],
    [JIT + spec quality#super[†]], [0.096], [---], [0.059],
  )
]

#text(size: 9pt)[#super[†] Scored subset only (5,192 PRs). JIT-only Pseudo~_R_#super[2] on same subset = 0.093.]

Spec presence is statistically significant when added to the JIT model (_p_ = 0.003) but the increment is substantively negligible: Δ Pseudo~_R_#super[2] = 0.0002, and AIC improves by only 7 points. Spec quality adds a marginally significant increment (_p_ = 0.059) on a biased subsample. In both cases, the incremental predictive power is too small to matter in practice --- JIT features account for nearly all the predictive power.

=== Individual Quality Dimensions

We test each of the seven specification quality dimensions independently against SZZ bugs and rework (within-author LPM, 4,901 PRs):

#align(center)[
  #table(
    columns: 5,
    table.header[Dimension][→ bugs coef][_p_][→ rework coef][_p_],
    [Outcome clarity], [−0.001], [0.119], [−0.000], [0.812],
    [Error states], [−0.000], [0.100], [+0.000], [0.308],
    [Scope boundaries], [−0.001], [0.027], [−0.000], [0.239],
    [Acceptance criteria], [−0.001], [0.063], [−0.000], [0.469],
    [Data contracts], [−0.001], [0.037], [+0.000], [0.927],
    [Dependency context], [−0.000], [0.536], [+0.000], [0.411],
    [Behavioral specificity], [−0.001], [0.020], [−0.000], [0.676],
  )
]

All coefficients in the bugs column are negative (directionally protective) but extremely small. To put the magnitudes in plain language: the largest coefficient is −0.001 (scope boundaries). This means that scoring the maximum possible improvement on scope boundaries --- moving from 0 to 100 on the rubric --- would predict 0.1 fewer percentage points of bugs. In a codebase with a 12% base bug rate, that is a reduction from 12.0% to 11.9%. No individual quality dimension produces a practically meaningful reduction in defects. The rework column is even starker: every coefficient rounds to zero.

Three dimensions show marginal statistical significance for bugs (scope boundaries _p_ = 0.027, data contracts _p_ = 0.037, behavioral specificity _p_ = 0.020), but none survive Bonferroni correction#footnote[Bonferroni correction adjusts the significance threshold for multiple comparisons. When testing 7 dimensions simultaneously, the probability of at least one false positive at α = 0.05 is approximately 30%. Dividing the threshold by the number of tests (0.05 / 7 = 0.007) controls the family-wise error rate.] (threshold: _p_ < 0.007 for 7 tests). Statistical significance at these magnitudes reflects the large sample size, not a meaningful effect. Even if these tiny coefficients reflected real causal relationships, they would be too small to justify the specification effort required to achieve them.

=== Validated Quality Dimensions Only

Our LLM quality rubric was validated against human ratings on 30 PRs (Section~4.2). Three of seven dimensions showed significant human--LLM agreement: scope boundaries (_ρ_ = 0.45), dependency context (_ρ_ = 0.37), and behavioral specificity (_ρ_ = 0.39). Two dimensions showed near-zero agreement: acceptance criteria (_ρ_ = 0.02) and error states (_ρ_ = 0.18). If measurement noise in the unvalidated dimensions attenuates the quality coefficient toward zero (classical errors-in-variables bias), restricting to validated dimensions should recover a larger effect.

#align(center)[
  #table(
    columns: 5,
    table.header[Quality composite][→ bugs coef][_p_][→ rework coef][_p_],
    [All 7 dimensions], [−0.0008], [0.016], [−0.0001], [0.827],
    [3 validated dimensions only], [−0.0006], [0.072], [−0.0001], [0.744],
    [4 unvalidated dimensions only], [−0.0009], [0.004], [+0.0000], [0.926],
  )
]

The pattern is not what measurement-error attenuation would predict. The validated-only composite weakens (_p_ = 0.072), while the unvalidated composite --- the dimensions where LLM and human disagree --- strengthens (_p_ = 0.004). If the quality score were capturing a real protective effect attenuated by noise, removing the noisy dimensions should sharpen the estimate, not weaken it. One caveat: the validated composite has slightly less variance (SD 21.7 vs. 20.5), which reduces statistical power, so the weakening could partly reflect a power loss rather than a substantive change. Still, the strongest signal comes from the dimensions our instrument measures least reliably, which is not the pattern a true quality effect would produce. The unvalidated dimensions likely correlate with description length rather than specification quality: longer descriptions give the LLM more text in which to detect keywords for each dimension, and longer descriptions accompany more complex tasks, which produce more defects. This is confounding by indication operating through the quality measure itself. For rework (H4), all three composites produce coefficients indistinguishable from zero.

=== Repo-Level Analysis

We also aggregate to the repository level (_N_ = 98 repos with ≥50 PRs) and test whether repos with higher specification rates have lower defect or rework rates.

#align(center)[
  #table(
    columns: 3,
    table.header[Comparison][Spearman _ρ_][_p_-value],
    [Spec rate vs. bug rate], [−0.110], [0.283],
    [Spec rate vs. rework rate], [−0.047], [0.643],
  )
]

At the repository level, specification rate has no relationship with either bug rate (_ρ_ = −0.11, _p_ = 0.28) or rework rate (_ρ_ = −0.05, _p_ = 0.64). Neither correlation is significant. An OLS regression controlling for mean PR size shows the spec rate coefficient at −0.060 (_p_ = 0.13) --- not significant.

=== Subgroup Analysis

SDD tools are marketed primarily for AI-assisted workflows. We test whether the null result holds across human-only PRs, AI-tagged PRs, and repos stratified by AI adoption rate. As in all analyses, bot PRs are excluded.

#align(center)[
  #table(
    columns: 5,
    table.header[Subgroup][→ bugs coef][_p_][→ rework coef][_p_],
    [All non-bot PRs (88,052)], [+0.014], [0.003], [+0.012], [0.001],
    [Human-only, no AI (82,063)], [+0.015], [0.003], [+0.011], [0.004],
    [AI-tagged, non-bot (5,989)], [+0.011], [0.424], [+0.010], [0.399],
    [Zero-AI repos (3,562)], [−0.016], [0.377], [−0.033], [0.014],
    [Low-AI repos (51,877)], [+0.019], [0.001], [+0.009], [0.061],
    [High-AI repos (32,613)], [+0.010], [0.185], [+0.018], [0.003],
  )
]

The pattern is consistent across subgroups. For human-authored PRs, specs are associated with _more_ bugs and _more_ rework --- the confounding-by-indication pattern. For AI-tagged PRs, the coefficients are positive but not significant (_p_ = 0.42 for bugs, _p_ = 0.40 for rework). The null holds whether a repo has zero AI adoption, moderate adoption, or high adoption.

=== High-Quality Specs Only

A likely reviewer objection is that our `specd` measure is too loose --- that linked Jira tickets are not "real" specifications in the SDD sense, and only high-quality structured specs should show the benefit. We test this directly by restricting to top-quartile (quality score ≥ 67) and top-decile (≥ 77) specs. Quality thresholds are computed from the scored subset's distribution (median = 55, p75 = 67, p90 = 77).

#align(center)[
  #table(
    columns: 4,
    table.header[Test][→ bugs coef][_p_][Identifying authors],
    [Top-quartile specs vs. all others], [−0.025], [0.036], [225],
    [Top-decile specs vs. all others], [−0.015], [0.370], [113],
    [High-quality vs. NO spec (low-quality excluded)], [−0.027], [0.052], [184],
    [AI-tagged + high-quality spec], [−0.044], [0.070], [52],
  )
]

The top-quartile result is marginally significant (−2.5pp, _p_ = 0.036) but does not survive scrutiny. First, when we perform the cleanest comparison --- high-quality specs vs. PRs with _no spec at all_, excluding low-quality specs entirely --- the effect is borderline (_p_ = 0.052). Second, if there were a real dose-response relationship, top-decile specs should show a _stronger_ effect than top-quartile. Instead the effect weakens (_p_ = 0.370) --- the opposite of what a causal relationship predicts. Third, the top-quartile result would not survive Bonferroni correction across the four tests shown. Fourth, even top-quartile specs do not reduce rework (+0.9pp, _p_ = 0.578).

The AI + high-quality spec result (_p_ = 0.070, −4.4pp) is the closest test to the agentic SDD workflow vendors are selling. However, it is identified from only 52 authors --- far too few for a stable estimate --- and the effect vanishes when comparing AI specs broadly (_p_ = 0.424). We note it as suggestive but not robust.

The objection that our measure is "too loose" does not rescue the SDD claims. Even restricting to the best-quality specs, the protective effect is fragile, does not follow a dose-response pattern, and does not reduce rework.

=== JIT Features as Primary Controls

A reviewer concern is that size controls (log additions, deletions, files) are insufficient --- the JIT defect prediction framework #cite(<kamei2013>) captures task complexity dimensions (entropy, file age, developer experience) that may confound the specification–defect association. We re-run H1 and H2 with 13 JIT features as additional controls alongside size controls (sexp excluded for zero variance).

#align(center)[
  #table(
    columns: 4,
    table.header[Test][Size controls only][+ JIT controls][Change],
    [H1: specs → bugs (coef)], [+0.014 (_p_ = 0.003)], [+0.006 (_p_ = 0.229)], [−55%],
    [H2: specs → rework (coef)], [+0.012 (_p_ = 0.001)], [+0.009 (_p_ = 0.024)], [−23%],
  )
]

For H1, the spec coefficient drops 55% and loses significance when JIT features are added, indicating that much of the apparent spec--defect association is explained by task complexity dimensions that size alone does not capture. For H2, the coefficient drops 23% but remains significant: specifications remain associated with more rework even after controlling for JIT risk features. The within-author spec coefficient in the JIT-controlled model (+0.006, _p_ = 0.229) is not significant for defects.

=== Propensity Score Matching

As an alternative to regression-based controls, we match each spec'd PR to an unspec'd PR with a similar JIT risk profile using nearest-neighbor propensity score matching (caliper = 0.05 SD of the logit propensity score). This directly addresses confounding by indication by comparing spec'd PRs to observationally similar unspec'd PRs.

#align(center)[
  #table(
    columns: 4,
    table.header[Outcome][Spec'd (matched)][Unspec'd (matched)][Difference],
    [Bug rate (17,375 pairs)], [14.7%], [15.2%], [−0.6pp (_p_ = 0.133)],
    [Rework rate (19,648 pairs)], [15.2%], [14.7%], [+0.5pp (_p_ = 0.146)],
  )
]

All 16 covariates are well-balanced after matching (all standardized mean differences < 0.1). For defects, the matched spec'd and unspec'd bug rates are indistinguishable --- propensity score matching eliminates the raw association entirely. For rework, the result is the same: after matching on observable risk features, the rework difference is +0.5 percentage points and not significant (_p_ = 0.146). Both the defect and rework associations are explained by the JIT risk profile of the tasks that receive specifications.

=== Temporal Analysis: The SDD Era

Specification adoption in our dataset is not uniform over time. Monthly specification rates rose from near zero before September 2025 to 14.6% by March 2026, coinciding with the release of Spec Kit (September 2025) and Kiro (July 2025). AI-tagged PR rates rose from 0.9% to 5.6% over the same period. If SDD tools are driving specification adoption and those specifications improve outcomes, the effect should be visible in the most recent data --- the period closest to production SDD usage.

We restrict the within-author analysis to the most recent three months of the observation window (January--March 2026), when specification rates are highest (13.5%) and AI adoption is most prevalent (4.4%):

#align(center)[
  #table(
    columns: 5,
    table.header[Test][Recent 3 months coef][_p_][Full dataset coef][_p_],
    [Specs → SZZ bugs], [+0.004], [0.435], [+0.014], [0.003],
    [Specs → rework], [+0.016], [0.001], [+0.012], [0.001],
    [AI + specs → bugs], [+0.003], [0.822], [---], [---],
    [AI + specs → rework], [+0.016], [0.212], [---], [---],
    [Spec × AI interaction (H5)], [+0.011], [0.861], [+0.000], [0.997],
  )
]

The pattern is consistent. In the period of highest SDD adoption, specifications are associated with more rework (+1.6pp, _p_ = 0.001) and directionally more bugs (+0.4pp, _p_ = 0.435, not significant). For AI-tagged PRs, specs have no effect in either direction. The H5 scope-constraint interaction is null in both the full dataset and the recent window. The null result is not a historical artifact --- it persists in the data most representative of the SDD era.

A caveat on the temporal data: SZZ-traced bug rates for the most recent months are likely underestimates, because defects introduced recently may not yet have been fixed (and therefore cannot be traced back to their introducing commits). This right-censoring affects absolute bug rates but not the _relative_ comparison between spec'd and unspec'd PRs within the same time window, which is the quantity of interest.

The null result holds across every angle: four outcome measures, two predictive frameworks (LPM and JIT), propensity score matching on JIT risk profiles, seven quality dimensions, two units of analysis (PR-level and repo-level), six subgroup cuts, multiple quality thresholds, and temporal restriction to the period of highest SDD adoption. When JIT features are added as controls, the H1 spec coefficient drops 55% and loses significance; propensity score matching eliminates the association entirely. No specification measure robustly predicts fewer defects or less rework under any operationalization.

= Discussion

== Confounding by Indication

The pattern across all five hypotheses is identical: naive analysis suggests specifications accompany worse outcomes, but within-author analysis reduces but does not eliminate the reversed association; propensity score matching on JIT features eliminates it entirely, confirming confounding by indication #cite(<salas1999>). Developers rationally invest specification effort in proportion to task complexity. Harder tasks receive specifications _and_ produce more defects --- the specification does not cause the bugs.

JIT risk feature profiles confirm this directly. Spec'd PRs have significantly higher change entropy (1.3×), more lines added (1.6×), touch older files (1.8×), and involve more prior developers (1.2×) than unspec'd PRs (all _p_ < 0.001). Notably, spec'd PR authors have _less_ experience than unspec'd PR authors (median 62 vs. 121 prior commits, _p_ < 0.001) --- less experienced developers spec more, not less, consistent with specifications being a support mechanism for harder tasks.

This confounding cuts both ways. The within-author null is consistent with both "specifications have zero effect" and "specifications have a small positive effect masked by residual task selection." We cannot distinguish these interpretations with observational data. However, the within-author estimates are not merely insignificant but _directionally reversed_ across most tests, and propensity score matching eliminates both the defect and rework associations entirely. If a protective effect exists, it is smaller than our study can detect.

Spec'd PRs receive more review (56% longer to merge, more review cycles), but this additional review does not translate into fewer defects --- the same confounding pattern. AI-tagged PRs receive _less_ review scrutiny despite a higher base defect rate (16.7% vs. 12.2%), a finding concerning independent of the specification question.

== Why Specifications May Not Prevent Defects

One explanation for the null is the chain of conditions required for a specification to prevent defects. The spec must be accurate in every assertion. It must have no substantial omissions. The AI must interpret it exactly as intended. The AI must make no implementation mistakes. And the spec itself must describe the correct solution. Each condition is individually difficult; together they represent a high bar. Defects arise precisely where human understanding is incomplete --- and specifications are written by the same humans whose incomplete understanding produces the defects. This does not prove specifications _cannot_ work, but it suggests why the marginal benefit may be smaller than vendors assume.

SDD vendors conflate _directing_ the AI (telling it what to build) with _ensuring quality_ (fewer bugs, less rework). Specifications may be effective at direction --- a structured task description is better than a vague prompt. But direction is not quality. An agent faithfully executing a spec will reproduce every gap, ambiguity, and wrong assumption in that spec. The specification tells the AI _what_ to build. It does not tell the AI _what it forgot to specify_.

== Vendor Evidence

No SDD tool vendor has published empirical evidence for the quality claims tested here. The evidence base consists of first-principles reasoning and developer testimonials. GitHub describes Spec Kit as "an experiment" #cite(<speckit2025>) and publishes no effectiveness data. Third-party evaluations are negative: Böckeler found Spec Kit's overhead "overkill for the size of the problem" #cite(<fowler2025>); Eberhardt found it roughly ten times slower than iterative development #cite(<scottlogic2025>). Notably, no SDD tool appears in the 100,247 PRs in our dataset --- a text search for `.specify/`, `.speckit/`, `.kiro/`, and `spec-kit` returns zero matches. The vendors' own repositories do not use the tools they sell. GitHub, Amazon, and other SDD vendors have the data and engineering resources to conduct controlled evaluations of their products. That they have not done so, while making specific quality claims in marketing materials, is itself informative.

We measure the _kind_ of specification content that SDD tools claim to improve upon, scored on the same quality dimensions those tools prescribe. If the tool's format itself is the active ingredient --- something beyond the seven quality dimensions we measure --- that would be a testable claim that vendors have not tested.

SDD tooling imposes real costs: specification-writing time, process overhead, organizational change. Teams adopting SDD on the basis of vendor claims are making investment decisions on unsubstantiated assertions. We do not argue that thinking about requirements is wasted effort. We argue that the _products_ claiming to reduce defects through specification artifacts have not demonstrated that they do.

= Limitations

== Construct Validity: Organic Artifacts vs. SDD Tool Output

Three gaps separate what we measure from what SDD vendors claim.

*We detect specification artifacts, not specification processes.* Our classifier flags linked issues, structured descriptions, and referenced design documents. A linked Jira ticket created to satisfy a process requirement counts the same as a detailed design document written after iterative refinement. If the benefit comes from the _thinking_ rather than the _artifact_, our measure is too coarse. Two observations partially address this concern. First, the within-author design compares the same developer's spec'd and unspec'd work, controlling for that person's consistent habits. Second, H3 and H4 test quality _within_ spec'd PRs on seven SDD-aligned dimensions. If deeper thinking produced better artifacts, those artifacts should predict better outcomes. They do not. The remaining objection --- that process depth helps through a mechanism invisible in the artifact itself --- is difficult to test with any observational design.

*We test organic specifications, not SDD tool output.* Spec Kit generates structured documents through a guided workflow and feeds them to a coding agent. A linked GitHub issue is not the same thing. Our operationalization is the broadest reasonable proxy available, but it may miss whatever specific mechanism the tools provide. The high-quality spec subsample (top-quartile, scored on the dimensions SDD tools prescribe) is the closest approximation. It too shows no robust effect.

*We cannot observe agentic workflows directly.* Even for AI-tagged PRs with specifications, we do not know whether the spec was actually used as input to an agent or just written for human consumption. True agentic SDD --- where the agent reads the spec, generates code from it, and validates against it --- is not observable in our data. The 52-author AI + high-quality spec subsample is the closest proxy we have.

== Measurement Noise in Defect Tracing, Quality Scoring, and AI Detection

*Defect detection is noisy.* The SZZ algorithm traces fix commits back to their introducing commits via `git blame`. da Costa et al. #cite(<dacosta2017>) found that basic SZZ misattributes 46--71% of bug-introducing changes. We use the basic variant for implementation simplicity across 103 repositories. This noise is substantial. We initially assumed it to be non-differential with respect to specification status, but this assumption deserves scrutiny: spec'd PRs are 1.6× larger and touch files with more prior changes, creating more `git blame` targets per commit. If SZZ misattributes more for larger changesets, the measurement error could be differential --- inflating the apparent bug rate for spec'd PRs. Two observations partially mitigate this concern: the rework measure (H2) does not depend on SZZ and shows the same directional pattern, and propensity score matching on size and complexity features eliminates the defect association entirely. Nonetheless, the reversed H1 association (specs predict _more_ bugs) should be interpreted cautiously --- confounding by indication and differential SZZ noise are difficult to disentangle.

*Quality scoring is automated and unvalidated.* Our LLM-based rubric (Claude Haiku) measures _formal_ quality --- whether the text contains outcome descriptions, error states, and acceptance criteria --- not _functional_ quality. A spec can score highly and still describe the wrong behavior. The rubric's seven dimensions align with what SDD tools prescribe, which means our scoring shares whatever blind spots those templates have. The scoring was applied only to PRs with substantial description text, creating a non-random subsample.

*AI detection relies on voluntary tagging.* We identify AI-assisted PRs via self-reported markers in the PR body. Developers who use AI without attribution are invisible. The false-negative rate is unknown. If many untagged PRs involved AI, the H5 comparison would be diluted toward the null.

*The control group may be contaminated.* Some "unspec'd" PRs may have had specifications shared verbally, in Slack, or in external tools. This would attenuate any treatment effect. However, if informal specification produces equivalent outcomes to formal artifacts, the SDD value proposition is undermined: vendors claim the _tooling and artifact_ add value, not that thinking about requirements helps in general.

== Residual Confounding and Task Selection

*Confounding by indication* is the primary threat. Developers spec hard tasks. Hard tasks produce bugs. The within-author design addresses this by comparing each developer to themselves, but within-author task selection remains possible: if an author consistently specs their hardest work and skips specs on easy tasks, the comparison is biased. The JIT-controlled models and propensity score matching (both in Section~5.6) address this further, and both confirm the null for defects.

*Time-varying confounding.* An author's skill, tooling, and project context may change over the observation period. The within-author estimator assumes these are stable.

== External Validity: Open-Source Convenience Sample

*Open-source only.* All 119 repositories are open-source. SDD tools target commercial teams with product managers, QA processes, and sprint planning. The specification practices and defect economics may differ.

*Convenience sample.* Repositories were not randomly selected. Results cannot be generalized beyond the sample.

*Pre-agentic era.* Most PRs predate widespread agentic AI coding tools. The dataset contains 5,989 AI-tagged PRs (after bot exclusion), the closest available proxy for agentic workflows. Within this subsample, specs show no effect on bugs (_p_ = 0.424) or rework (_p_ = 0.399). We cannot rule out that true agentic workflows would produce different results --- but that is itself an untested claim.

== Statistical Caveats

*Multiple comparisons.* We test five hypotheses without correction. At α = 0.05, approximately 0.25 false positives are expected by chance.

*Power for AI interaction.* The scope-constraint interaction (H5) is identified from 366 authors with variation in both specification and AI use. The null result (_p_ = 0.997) is not a power issue --- the coefficient is effectively zero.

*No pre-registration.* The five hypotheses, operationalizations, quality thresholds, and robustness checks were not pre-registered. All analyses are post-hoc. We cannot rule out that alternative analyst choices (different quality thresholds, different rework definitions, different control sets) would produce different results. The ten robustness checks are intended to address this concern by showing stability across specifications, but a pre-registered confirmatory study would provide stronger evidence.

= Conclusion

Spec-driven development tools make five specific, testable claims: specifications reduce defects (H1), prevent rework (H2), improve outcomes through higher-quality requirements (H3, H4), and constrain AI-generated code scope (H5). Production-scale data from purpose-built SDD tools is not yet publicly available. We test the claims using the best available proxy: 88,052 pull requests across 119 open-source repositories, where specification artifacts are scored on the same quality dimensions that SDD tools prescribe, using within-author fixed-effects estimation.

None of the five hypotheses are supported at a level that would justify the vendor claims. The naive association between specifications and defects is reversed (specifications accompany _more_ defects); after within-author controls, the most parsimonious interpretation is confounding by indication. Specification quality has no meaningful effect on rework (_p_ = 0.827). Specifications do not constrain AI-generated code scope (_p_ = 0.997). Ten robustness checks confirm the null. Specification presence proxies for task complexity, not for quality improvement.

Three important caveats bound these findings. First, we test organic specification artifacts, not SDD tool-generated specifications --- the construct gap is real (Section~7). Second, SZZ defect tracing has substantial measurement noise (46--71% misattribution), which attenuates true effects. Third, our open-source convenience sample may not generalize to commercial teams. Whether purpose-built SDD tooling would produce different results on commercial codebases remains an open question. The best available proxy evidence offers no support for the quality claims being made.

Specifications may still have value --- but not the value being claimed. A specification is an auditable record of what the code was _meant_ to do, which is valuable for compliance, debugging, and onboarding regardless of whether it prevents defects. Specifications may improve developer efficiency by enabling task batching: a developer can queue structured work for an AI agent and shift attention elsewhere, reclaiming time without improving code quality. Specifications create accountability, making it harder for defects to pass unchallenged through review. These are real benefits. They are not "fewer bugs" or "reduced rework." SDD vendors would do well to make claims they can substantiate.

The dataset and analysis code are available at: `github.com/brennhill/delivery-gap-research`.

#pagebreak()

= References

#set par(first-line-indent: 0pt, hanging-indent: 0.5in)

#bibliography(style: "apa", title: none,
  "ssrn-sdd-refs.yml",
)
