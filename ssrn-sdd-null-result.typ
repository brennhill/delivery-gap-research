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
Spec-driven development (SDD) tools --- GitHub's Spec Kit, Amazon's Kiro, and others --- claim that writing specifications before implementation reduces defects, prevents rework, and improves code quality. These claims lack empirical evidence. We provide the first large-scale test: 89,599 pull requests (after bot exclusion) across 119 open-source repositories, using SZZ defect tracing and within-author fixed-effects estimation. We test specification _artifacts_ in open-source pull requests --- the closest available proxy for SDD workflows, scored on the same quality dimensions SDD tools prescribe --- not the tools' integrated workflows directly. Five hypotheses derived from vendor claims are tested. None are supported. The naive association between specifications and defects is _reversed_ (specifications accompany more bugs, not fewer); after within-author controls, the most likely interpretation is confounding by indication: harder tasks receive specifications and independently produce more defects. Specification quality has no meaningful effect on rework (_p_ = 0.767). The AI scope-constraint claim is null (_p_ = 0.505). Nine robustness checks --- alternative outcomes, JIT defect features, propensity score matching, individual quality dimensions, repo-level aggregation, subgroup analysis, high-quality spec subsample, JIT-controlled primary models, and temporal restriction to the period of highest SDD adoption --- all confirm. Specification artifacts proxy for task complexity, not quality improvement.
  ]
]

#pagebreak()

// === BODY ===

= Introduction

#par(first-line-indent: 0pt)[
The rise of AI-assisted software development has produced a new category of developer tooling: specification-driven development (SDD) frameworks. These tools --- including GitHub's Spec Kit #cite(<speckit2025>), Amazon's Kiro #cite(<kiro2025>), and Tessl --- claim that writing formal specifications before implementation leads to fewer defects, less rework, and higher-quality code, particularly when AI agents perform the implementation.
]

Böckeler #cite(<fowler2025>) defines spec-driven development as "writing a 'spec' before writing code with AI" where "[t]he spec becomes the source of truth for the human and the AI." The GitHub Copilot Academy frames it more strongly: "Specifications don't serve code --- code serves specifications" #cite(<copilotacademy2025>). The movement gained momentum in 2025 with the release of GitHub's Spec Kit (open-source, v0.0.72 as of this writing) and Amazon's Kiro IDE. Böckeler examined three tools pursuing the approach #cite(<fowler2025>). SDD is positioned as an antidote to "vibe coding" --- iteratively prompting AI without formal requirements --- which practitioners associate with scope creep, rework, and defects.

The core premise is intuitive: if developers articulate what software should do before writing it, AI systems will produce more reliable output. The GitHub Copilot Academy lists "reduced rework, living documentation, systematic quality" among SDD's benefits #cite(<copilotacademy2025>). Kiro claims that specifications enable "fewer iterations and higher accuracy" and "prevent costly rewrites" #cite(<kiro2025b>). GitHub's Spec Kit blog post promises "less guesswork, fewer surprises, and higher-quality code" #cite(<speckit2025>).

These claims rest on a plausible causal chain: clearer requirements → less ambiguity → fewer defects. However, none of the marketing materials, documentation, or blog posts accompanying these tools cite empirical evidence for the claimed outcomes. The assertions are presented as self-evident truths rather than testable hypotheses. No study has tested SDD's quality claims on production-scale data prior to this paper.

This paper provides the first large-scale empirical test. We analyze 89,599 merged pull requests (after excluding 10,648 bot-authored PRs) across 119 open-source repositories, using the SZZ algorithm to trace defects back to their introducing commits and within-author fixed-effects estimation to control for developer-level confounding. We derive five hypotheses directly from vendor claims and test each with the most conservative methodology available for observational data.

= Related Work

== Requirements Engineering and Defect Prevention

The claim that upfront specification prevents defects has deep roots in software engineering. Boehm's cost-of-change curve #cite(<boehm1981>) argued that requirements defects are exponentially cheaper to fix early. However, subsequent work has challenged the universality of this finding. Shull et al. #cite(<shull2002>) found that the cost multiplier depends heavily on project context, and agile methodologies have demonstrated that iterative refinement can be more effective than upfront specification for certain project types #cite(<beck2001>).

The question of whether requirements quality predicts software defects has been studied directly. Mund et al. #cite(<mund2015>) combined two empirical studies and found only weak evidence that requirements specification quality predicts implementation defects, with effect sizes that varied substantially across projects. Femmer et al. #cite(<femmer2017>) developed automated detection of "requirements smells" (ambiguity, incompleteness, inconsistency) and found that while smells were prevalent, their relationship to downstream defects was context-dependent. These findings suggest that the relationship between specification quality and code quality is not as straightforward as SDD vendors assume --- a pattern our study confirms at larger scale.

== SDD Literature

The academic literature on SDD perpetuates the pattern of unsubstantiated claims. Piskala #cite(<piskala2026>) claims "controlled studies showing error reductions of up to 50%," citing a Red Hat Developer blog post #cite(<naszcyniec2025>) and an InfoQ article #cite(<griffin2026>) as evidence. Neither source contains any controlled study, any experiment, or any quantitative data. The "50%" figure traces through a citation chain that terminates in practitioner opinion pieces with no empirical backing. Guo et al. #cite(<sedeve2025>) claim SDD "guarantees software quality" without empirical validation. Marri #cite(<marri2026>) reports a 73% security defect reduction from constitutional specs, but on a single project (_n_ = 1), with the same developer implementing both conditions sequentially --- the author acknowledges "small sample size limits statistical power." Roy #cite(<roy2026>) proposes iterative spec-code co-evolution but reports no independently validated quality outcomes. Zietsman #cite(<zietsman2026>) runs small planted-bug experiments and is honest about their limitations ("directional, not statistically significant"), while contributing the useful observation that AI reviewers without specs suffer circular reasoning --- but does not test whether specs reduce defects at scale.

Practitioner evaluations have been more skeptical. Eberhardt, writing for Scott Logic, found Spec Kit roughly ten times slower than iterative development, producing thousands of lines of specification markdown that still resulted in buggy code #cite(<scottlogic2025>). Zaninotto argued that "SDD shines when starting a new project from scratch, but as the application grows, the specs miss the point more often and slow development," and proposed iterative natural-language development as a faster alternative #cite(<zaninotto2025>).

No study has tested SDD's quality claims on production-scale data prior to this paper.

= Study Design

== Hypotheses

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

== Dataset

We collected pull request data from 119 open-source repositories spanning 14 programming languages. Repositories were selected to represent large, active projects with diverse contribution patterns. We collected data between March 28 and April 3, 2026, with a 365-day lookback window per repository. The resulting dataset spans April 2025 through early April 2026 (p1--p99: April 8, 2025 to April 1, 2026), totaling 100,247 PRs. We excluded 10,648 bot-authored PRs (dependabot, renovate, and 22 other automated accounts identified by username pattern and bot flags), leaving 89,599 PRs from human and AI-assisted authors.

For each pull request, we extracted: author, merge date, additions, deletions, files changed, linked issues, PR description, review comments, and co-author tags (used to identify AI-assisted contributions).

#figure(
  table(
    columns: (auto, auto, auto),
    align: (left, right, left),
    table.header([*Metric*], [*Value*], [*Notes*]),
    [Repositories], [119], [convenience sample, 14 languages],
    [PRs (post-bot exclusion)], [89,599], [10,648 bots removed],
    [Median PRs per repo], [517], [range 9--4,803],
    [Median spec rate (per repo)], [0.0%], [IQR 0.0--15.3%],
    [Median AI tag rate (per repo)], [0.0%], [IQR 0.0--0.9%],
    [SZZ-covered repos], [103], [16 had unreachable merge SHAs],
    [SZZ bug-introducing PRs], [9,983], [12.6% of SZZ-covered PRs],
    [Quality-scored PRs], [5,246], [5.9% of total; non-random subsample],
  ),
  caption: [Study dataset overview.],
) <tab:dataset-overview>

The sample spans 17 programming languages, with Python (31 repos, 26%), TypeScript (26, 22%), Go (17, 14%), and Rust (13, 11%) predominating. Specification rates are highly skewed: the median repository has 0% spec'd PRs, while the 75th percentile is 15.3%. AI tagging is concentrated: 76 of 119 repositories have zero AI-tagged PRs, and the median AI tag rate is 0% (75th percentile: 0.9%). However, the within-author and within-repo designs compare AI and non-AI work within the same contexts, and the 2,650 AI-tagged PRs provide sufficient statistical power for the primary AI analyses. We recognize that the AI-specific results (H5, AI subgroups) would benefit from a larger AI-tagged sample as agentic workflows become more prevalent.

== Operationalization

=== Specification Presence (`specd`)

A pull request is classified as "specified" if it meets any of the following criteria: (a) it links to a GitHub issue or external tracking ticket, (b) its description references a specification document, RFC, or design doc, or (c) its description contains structured requirements content (acceptance criteria, behavioral descriptions, scope boundaries). Classification is performed programmatically by parsing PR metadata: issue references (`#123`, `fixes #456`), cross-reference URLs, and description structure (presence of headings, checklists, or requirement-style language). 7,926 of 89,599 PRs (8.8%) are classified as specified.

This operationalization is deliberately generous: it captures any form of upfront specification artifact, from a linked Jira ticket to a detailed RFC. SDD tools claim benefits from _any_ form of specification, so we test the broadest reasonable definition. Specification _presence_ and specification _quality_ are tested separately: H1 and H2 test whether having any specification artifact predicts fewer defects or less rework; H3 and H4 test whether, among the subset of PRs that have specifications, higher-quality specifications predict better outcomes. This two-level design addresses the objection that our binary `specd` measure is too coarse by also testing whether the content of the specification matters.

=== Specification Quality (`q_overall`)

For the subset of specified PRs with substantial descriptions (body length > 50 characters), we scored specification quality by prompting Claude Haiku (Anthropic) with the PR title and body and a structured rubric. The LLM scored each PR across seven dimensions: outcome clarity, error states, scope boundaries, acceptance criteria, data contracts, dependency context, and behavioral specificity. Each dimension is scored 0--100, and the overall quality score is the mean across dimensions.

These seven dimensions were chosen to align with the quality criteria recommended by SDD tools themselves. Spec Kit's template prescribes "core requirements" (outcome clarity), "acceptance criteria" (our acceptance criteria dimension), "edge cases" (error states), "data models" and "API contracts" (data contracts), and "user stories" (behavioral specificity) #cite(<speckit2025>). Kiro prescribes "clear requirements," "acceptance criteria," "system architecture," and "technology choices" #cite(<kiro2025b>). Six of our seven dimensions have direct equivalents in Spec Kit's recommended structure; all seven are covered across both tools. This alignment is deliberate: we measure specification quality on the dimensions that SDD vendors themselves say matter.

We validated the LLM scoring against independent human ratings on a stratified random sample of 30 PRs. The human rater scored each dimension on the same rubric, blind to the LLM scores. Overall rank-order agreement was moderate: Spearman _ρ_ = 0.37 (_p_ = 0.04), Pearson _r_ = 0.44 (_p_ = 0.02). The LLM scores systematically higher than the human rater (mean bias: +7 points on the 0--100 scale, mean absolute difference: 16 points). Per-dimension agreement varies: scope boundaries (_ρ_ = 0.45, _p_ = 0.01), dependency context (_ρ_ = 0.37, _p_ = 0.04), and behavioral specificity (_ρ_ = 0.39, _p_ = 0.03) show significant agreement, while acceptance criteria (_ρ_ = 0.02) and error states (_ρ_ = 0.18) show near-zero correlation. The LLM reliably detects whether specification content is _present_ but cannot judge whether it is _correct_ for the domain --- a distinction between formal completeness and functional quality. Since even this completeness-oriented measure shows no defect benefit, the null finding is conservative: a more precise quality measure would sharpen the estimate, not reverse it.

5,246 PRs (5.9% of total) received quality scores. This subsample is non-random --- only spec'd PRs with sufficient description text were scored --- and results from this subsample carry a selection bias caveat.

A further limitation: we cannot distinguish specifications written before implementation from descriptions written after. Many PR descriptions in our dataset are post-hoc --- the developer wrote the code, validated it, possibly iterated through review, and then described what it does. These post-hoc descriptions should score _higher_ on our quality rubric than pre-implementation specifications, because the developer is describing validated behavior rather than predicting it. The fact that even this generous measure --- which includes descriptions written with full knowledge of what the code actually does --- shows no defect-prevention benefit makes the SDD claim harder to sustain, not easier. If describing what code _does_ after building it does not predict fewer defects, describing what code _should do_ before building it is unlikely to fare better.

Furthermore, many effective AI instructions are inherently underspecified by our rubric's standards. A prompt like "improve the error handling, it looks ugly" scores low on outcome clarity, acceptance criteria, and behavioral specificity --- yet it is a perfectly successful instruction for an AI agent that can read the surrounding code. The agent does not need the spec to enumerate every error case; it can infer them from context. This class of task --- where the codebase itself provides sufficient specification --- is invisible to our quality measure but may represent a large share of productive AI-assisted work. If detailed specifications add no value for tasks where the code context is sufficient, the marginal benefit of specification effort is even smaller than our results suggest.

=== Defect Introduction (`szz_buggy`)

We applied the SZZ algorithm #cite(<szz2005>) to 103 of 119 repositories, tracing 64,805 blame links from fix commits to bug-introducing commits. The remaining 16 repositories produced zero traceable blame links: their merge commit SHAs (recorded by the GitHub API) are not reachable in single-branch clones, typically because the repository uses squash-merge workflows where GitHub's synthetic merge commits are garbage-collected after merging. The SZZ algorithm traces defect-fixing commits back to the commits that introduced the defect using `git blame`. We use the basic SZZ variant, which da Costa et al. #cite(<dacosta2017>) found misattributes 46--71% of bug-introducing changes depending on the project. This noise is substantial, but it is non-differential with respect to specification presence: there is no reason to expect SZZ to systematically misattribute more for spec'd PRs than unspec'd PRs. Non-differential measurement error attenuates associations toward the null, which works against finding a protective effect but does not create spurious reversed associations. We acknowledge the implications for statistical power in Section~6. Each bug-introducing commit was mapped to its originating pull request. A PR is marked `szz_buggy = True` if any of its commits were identified as introducing a defect that was later fixed. 9,983 PRs (12.6% of those in SZZ-covered repos) are marked as bug-introducing.

=== Rework (`reworked`)

A pull request is classified as reworked if a subsequent PR by any author modifies overlapping files and has a title or description indicating correction (matching patterns such as "fix," "revert," "bugfix," "hotfix," "regression," "broke," or "broken"). File overlap is computed by comparing the set of files changed in each PR pair. 3,477 PRs (3.9%) are classified as reworked.

=== AI-Tagged (`ai_tagged`)

A pull request is classified as AI-assisted if its description matches any of the following patterns via regex on the PR body: co-author tags (e.g., `Co-authored-by: Copilot`), generation attribution strings (`Generated with`, `Claude Code`, `written with/by` followed by a tool name), AI agent markers (`CURSOR_AGENT`, `coderabbit.ai`, `AI-generated`), or the robot emoji (🤖), which AI tools commonly append to generated descriptions. 2,650 PRs (3.0%) carry AI tags after bot exclusion. This is a lower bound: self-tagging is voluntary, and developers who use AI assistance without attribution are invisible to this method. The false-negative rate is unknown.

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
  *Within-author:* Linear probability model (LPM) with full author demeaning and clustered standard errors. All variables --- treatment, controls, and outcome --- are demeaned by author, equivalent to author fixed effects via the Frisch--Waugh--Lovell theorem. Standard errors are clustered at the author level to account for within-author residual correlation. We use LPM rather than logistic regression because demeaning is exact for OLS but produces biased estimates in logit due to the incidental parameters problem #cite(<neyman1948>). This follows Angrist and Pischke's recommendation for fixed-effects estimation with binary outcomes #cite(<angrist2009>). Primary models use size controls (log additions, log deletions, log files changed); we verify that results hold when adding JIT defect prediction features #cite(<kamei2013>) as additional controls (Section~4.7).
]

The within-author estimate is the most credible. Observational studies of developer practices face severe confounding: developers who write specifications may differ systematically from those who do not in skill, experience, task selection, and organizational context. The within-author design addresses this by comparing the same developer's specified PRs to their own unspecified PRs, eliminating all time-invariant author-level confounding. The treatment effect is identified only from authors who have _both_ specified and unspecified PRs in the dataset.

We restrict within-author analysis to authors with ≥2 PRs and report the number of authors with treatment variation (those who have both spec'd and unspec'd PRs), as these are the observations that identify the effect.

We do not apply multiple-comparison corrections across the five hypotheses. At α = 0.05, approximately 0.25 false positives are expected by chance. We interpret all results with this in mind.

= Results

== H1: Specifications Reduce Defects

#par(first-line-indent: 0pt)[
  Analysis restricted to 79,049 PRs in the 103 repositories with SZZ coverage.
]

#align(center)[
  #table(
    columns: 4,
    table.header[Method][Coefficient][_p_-value][Interpretation],
    [Pooled (Fisher's exact)], [OR = 1.294], [< 0.001], [Spec'd PRs have _higher_ bug rate],
    [Controlled (logit + repo FE)], [0.295], [< 0.001], [Effect persists with size + repo controls],
    [Within-author (LPM)], [+0.019], [0.011], [+1.9pp _increase_ in bug rate],
  )
]

Identified from 897 authors with treatment variation (out of 4,346 authors with ≥2 PRs).

*H1 is not supported.* The table should be read bottom-up. The pooled comparison (top row) is the naive analysis: spec'd PRs have a 29.4% higher odds of introducing a bug than unspec'd PRs. But this comparison is confounded --- developers who write specs are different from those who don't, and the repos that encourage specs are different from those that don't. The controlled logistic regression (middle row) adds size controls and repository fixed effects, removing between-repo confounding. The effect persists.

The within-author estimate (bottom row) is the most credible. It compares the _same developer's_ spec'd PRs to their own unspec'd PRs, eliminating all time-invariant author-level confounding --- skill, experience, coding style, and organizational context are held constant because both the "treatment" and "control" come from the same person. The result: within-author, spec'd PRs are associated with a 1.9 percentage-point _increase_ in defect-introduction rates (_p_ = 0.011). The direction is opposite to the vendor claim at every level of analysis.

This is consistent with confounding by indication: harder, riskier tasks receive specifications _and_ introduce more defects. A developer rationally invests specification effort in proportion to task complexity. The spec does not cause the bugs --- the task difficulty that motivates the spec also produces the bugs. When JIT risk features are added as controls (Section~4.7), the within-author spec coefficient drops 71% and loses significance (_p_ = 0.517), confirming that measurable task complexity explains most of the association.

A plausible alternative explanation is detection bias: if spec'd PRs have better test coverage and more granular QA, their bugs may be detected and fixed individually, making them more visible to SZZ tracing. Unspec'd PRs might have bugs that go undetected longer or get fixed in bulk refactoring commits that SZZ cannot trace, producing artificially low bug rates. We cannot rule this out entirely. However, two observations weigh against it. First, the rework measure (H2) does not depend on SZZ tracing and shows the same directional pattern. Second, propensity score matching (Section~4.8) eliminates the defect association entirely by matching on observable risk features. This suggests task complexity --- not detection asymmetry --- is the primary driver.

== H2: Specifications Reduce Rework

#par(first-line-indent: 0pt)[
  Analysis includes all 89,599 PRs.
]

#align(center)[
  #table(
    columns: 4,
    table.header[Method][Coefficient][_p_-value][Interpretation],
    [Pooled (Fisher's exact)], [OR = 6.071], [< 0.001], [Spec'd PRs have _6.1×_ higher rework],
    [Controlled (logit, no repo FE#super[†])], [1.779], [< 0.001], [Massive effect persists],
    [Within-author (LPM)], [+0.050], [< 0.001], [+5.0pp _increase_ in rework rate],
  )
]

#text(size: 9pt)[#super[†] Repository fixed effects caused a singular matrix; controlled estimate uses size controls only.]

Identified from 988 authors with treatment variation (out of 4,918 with ≥2 PRs).

*H2 is not supported.* The within-author effect is strong and in the wrong direction: the same author's spec'd PRs have a 5.0 percentage-point higher rework rate than their unspec'd PRs. The pooled odds ratio (6.1×) dramatically overstates the association --- most of the pooled effect is between-author confounding --- but even within-author, specs are associated with more rework, not less.

== H3: Specification Quality Reduces Defects

#par(first-line-indent: 0pt)[
  H1 and H2 tested specification _presence_ --- whether having any specification artifact matters. H3 and H4 test specification _quality_ --- whether, among PRs that already have specifications, better-written specifications predict better outcomes. This is the stronger version of the SDD claim: not just "write a spec" but "write a _good_ spec."
]

Quality is the mean of seven rubric dimensions (described in Section~3.3), each scored 0--100. The overall quality score is the mean across dimensions. These dimensions were chosen to align with the quality criteria that SDD tools themselves prescribe (Section~3.3). The scoring is automated and has not been validated against human expert judgment --- a limitation we acknowledge (Section~6). The quality score measures _formal_ specification completeness (are error states described? are acceptance criteria present?) rather than _functional_ correctness (are the right error states described? are the acceptance criteria valid for this domain?). A specification can score highly on every dimension and still specify the wrong behavior.

#par(first-line-indent: 0pt)[
  Analysis restricted to 5,246 PRs with LLM-scored specification quality (6.6% of SZZ-covered PRs). Selection bias caveat: only specified PRs with substantial descriptions were scored.
]

#align(center)[
  #table(
    columns: 4,
    table.header[Method][Coefficient][_p_-value][Interpretation],
    [Controlled (logit + repo FE)], [−0.005], [0.042], [Quality predicts fewer bugs],
    [Within-author (LPM)], [−0.001], [0.018], [−0.08pp per quality point],
  )
]

Identified from 358 authors with treatment variation.

*H3 is marginally supported on a biased subsample.* The within-author coefficient is statistically significant but substantively negligible: a 10-point improvement in specification quality (the full scale range) predicts a 0.8 percentage-point reduction in defect rate. This is identified from only 358 authors on 5.9% of the data, in a subsample that was non-randomly selected for having substantial specification content. We do not consider this finding robust.

== H4: Specification Quality Reduces Rework

#align(center)[
  #table(
    columns: 4,
    table.header[Method][Coefficient][_p_-value][Interpretation],
    [Controlled (logit + repo FE)], [0.003], [0.253], [Quality does not predict rework],
    [Within-author (LPM)], [−0.000], [0.767], [Effectively zero],
  )
]

Identified from 358 authors with treatment variation.

*H4 is not supported.* Specification quality has no meaningful relationship with rework rates within-author. The coefficient is effectively zero, with _p_ = 0.767. The controlled logistic regression is also non-significant (_p_ = 0.253), consistent with the within-author finding (thorough specifications accompany difficult tasks that are more likely to be reworked).

== H5: Specifications Constrain AI Scope

#par(first-line-indent: 0pt)[
  Analysis uses log code churn (additions + deletions) as outcome. PRs with zero churn excluded (missing data artifact).
]

#align(center)[
  #table(
    columns: 4,
    table.header[Group][Within-author coef][_p_-value][Interpretation],
    [AI-tagged PRs], [+0.058], [0.521], [No scope constraint for AI],
    [Human PRs], [+0.120], [< 0.001], [Spec'd human PRs are _larger_],
    [Interaction (spec × AI)], [−0.047], [0.505], [No differential AI effect],
  )
]

AI analysis identified from 107 authors with treatment variation; interaction from 189.

*H5 is not supported.* Within-author, specifications do not constrain AI-generated code scope. The interaction term --- which tests whether specs reduce churn _more_ for AI PRs than human PRs --- is null (_p_ = 0.505). For both AI and human PRs, spec'd work is directionally _larger_, not smaller, consistent with the confounding-by-indication pattern: larger, more complex tasks receive specifications.

The pooled descriptive statistics appear to support the scope-constraint claim: AI spec'd PRs have median churn of 125 vs. 82 for AI unspec'd. However, this is a Simpson's paradox: authors who spec their AI PRs are working on different (larger) tasks than those who don't.

== Robustness Checks

Nine additional analyses test whether the null result is an artifact of our primary measures or insufficient controls.

=== Alternative Outcome Measures

In addition to SZZ-traced defects and rework, we test specification effects on two additional outcome measures: _escaped defects_ (PRs whose CI passed but were subsequently followed by a fix or revert) and _strict escaped_ (escaped PRs where the follow-up PR's title explicitly indicates a fix or regression).

#align(center)[
  #table(
    columns: 4,
    table.header[Outcome][Within-author coef][_p_-value][N],
    [SZZ bugs], [+0.019], [0.011], [73,276],
    [Rework], [+0.050], [< 0.001], [83,188],
    [Escaped], [−0.002], [0.169], [83,188],
    [Strict escaped], [−0.000], [0.870], [83,188],
  )
]

The SZZ bugs and rework rows reproduce the H1 and H2 findings (included here for comparison). Both show significant _positive_ associations --- specs accompany more bugs and more rework, not less --- which we attribute to confounding by indication (Section~5.2): harder tasks receive specifications and independently produce more defects and rework. The escaped and strict escaped measures, which capture a different class of defect (CI-passing code that subsequently required a fix), are directionally protective but not significant. No outcome measure shows specifications reducing defects at _p_ < 0.05.

=== Incremental Validity Beyond JIT Features

The JIT defect prediction framework #cite(<kamei2013>) uses 14 code-change features (subsystems touched, file entropy, developer experience, etc.) to predict defect-introducing commits. We test whether specification information adds predictive power beyond JIT features on the 62,126 PRs with both complete JIT features and SZZ outcomes.

#align(center)[
  #table(
    columns: 4,
    table.header[Model][Pseudo~_R_#super[2]][AIC][Spec variable _p_],
    [JIT features only], [0.075], [45,850], [---],
    [JIT + spec presence], [0.075], [45,851], [0.250],
    [JIT + spec quality#super[†]], [0.094], [---], [0.044],
  )
]

#text(size: 9pt)[#super[†] Scored subset only (5,246 PRs). JIT-only Pseudo~_R_#super[2] on same subset = 0.093.]

Spec presence adds nothing to the JIT model: Δ Pseudo~_R_#super[2] = 0.00003, _p_ = 0.250, and AIC increases (worse fit). Spec quality adds a marginally significant but substantively negligible increment (Δ~_R_#super[2] = 0.001, _p_ = 0.044) on a biased subsample. JIT features alone account for all the predictive power that specifications claim to provide.

=== Individual Quality Dimensions

We test each of the seven specification quality dimensions independently against SZZ bugs and rework (within-author LPM, 4,955 PRs):

#align(center)[
  #table(
    columns: 5,
    table.header[Dimension][→ bugs coef][_p_][→ rework coef][_p_],
    [Outcome clarity], [−0.001], [0.140], [−0.000], [0.495],
    [Error states], [−0.000], [0.074], [+0.000], [0.437],
    [Scope boundaries], [−0.001], [0.033], [−0.000], [0.214],
    [Acceptance criteria], [−0.001], [0.079], [−0.000], [0.879],
    [Data contracts], [−0.001], [0.031], [+0.000], [0.602],
    [Dependency context], [−0.000], [0.512], [+0.000], [0.461],
    [Behavioral specificity], [−0.001], [0.023], [−0.000], [0.693],
  )
]

All coefficients in the bugs column are negative (directionally protective) but extremely small. To put the magnitudes in plain language: the largest coefficient is −0.001 (scope boundaries). This means that scoring the maximum possible improvement on scope boundaries --- moving from 0 to 100 on the rubric --- would predict 0.1 fewer percentage points of bugs. In a codebase with a 12% base bug rate, that is a reduction from 12.0% to 11.9%. No individual quality dimension produces a practically meaningful reduction in defects. The rework column is even starker: every coefficient rounds to zero.

Three dimensions show marginal statistical significance for bugs (scope boundaries _p_ = 0.033, data contracts _p_ = 0.031, behavioral specificity _p_ = 0.023), but none survive Bonferroni correction#footnote[Bonferroni correction adjusts the significance threshold for multiple comparisons. When testing 7 dimensions simultaneously, the probability of at least one false positive at α = 0.05 is approximately 30%. Dividing the threshold by the number of tests (0.05 / 7 = 0.007) controls the family-wise error rate.] (threshold: _p_ < 0.007 for 7 tests). Statistical significance at these magnitudes reflects the large sample size, not a meaningful effect. Even if these tiny coefficients reflected real causal relationships, they would be too small to justify the specification effort required to achieve them.

=== Repo-Level Analysis

As a final robustness check, we aggregate to the repository level (_N_ = 98 repos with ≥50 PRs) and test whether repos with higher specification rates have lower defect or rework rates.

#align(center)[
  #table(
    columns: 3,
    table.header[Comparison][Spearman _ρ_][_p_-value],
    [Spec rate vs. bug rate], [+0.091], [0.371],
    [Spec rate vs. rework rate], [+0.919], [< 0.001],
  )
]

At the repository level, specification rate has no relationship with bug rate (_ρ_ = 0.09, _p_ = 0.37) and a massive _positive_ correlation with rework rate (_ρ_ = 0.92, _p_ < 0.001). The latter is confounding by indication at the repo level: projects that use specifications tend to be complex projects with higher rework rates. An OLS regression controlling for mean PR size shows the spec rate coefficient dropping to +0.025 (_p_ = 0.60) --- effectively zero.

=== Subgroup Analysis

SDD tools are marketed primarily for AI-assisted workflows. We test whether the null result holds across human-only PRs, AI-tagged PRs, and repos stratified by AI adoption rate. As in all analyses, bot PRs are excluded.

#align(center)[
  #table(
    columns: 5,
    table.header[Subgroup][→ bugs coef][_p_][→ rework coef][_p_],
    [All non-bot PRs (89,599)], [+0.019], [0.011], [+0.050], [< 0.001],
    [Human-only, no AI (86,949)], [+0.022], [0.006], [+0.055], [< 0.001],
    [AI-tagged, non-bot (2,650)], [−0.000], [0.984], [−0.017], [0.325],
    [Zero-AI repos (62,882)], [+0.005], [0.878], [+0.021], [0.389],
    [Low-AI repos (12,596)], [+0.023], [0.016], [+0.043], [< 0.001],
    [High-AI repos (14,121)], [+0.023], [0.037], [+0.038], [< 0.001],
  )
]

The pattern is identical across every subgroup. For human-authored PRs, specs are associated with _more_ bugs and _more_ rework --- the confounding-by-indication pattern. For AI-tagged PRs specifically, the coefficients are directionally negative but nowhere near significant (_p_ = 0.98 for bugs, _p_ = 0.33 for rework), with only 107 and 115 identifying authors respectively. The null holds whether a repo has zero AI adoption, moderate adoption, or high adoption. Excluding bots does not change the main result.

Notably, AI-tagged PRs have substantially higher base rates than human PRs: 18.1% bug rate vs. 12.7%, and 18.6% rework rate vs. 3.4%. Specs do not ameliorate this gap.

=== High-Quality Specs Only

A likely reviewer objection is that our `specd` measure is too loose --- that linked Jira tickets are not "real" specifications in the SDD sense, and only high-quality structured specs should show the benefit. We test this directly by restricting to top-quartile (quality score ≥ 67) and top-decile (≥ 77) specs. Quality thresholds are computed from the scored subset's distribution (median = 55, p75 = 67, p90 = 77).

#align(center)[
  #table(
    columns: 4,
    table.header[Test][→ bugs coef][_p_][Identifying authors],
    [Top-quartile specs vs. all others], [−0.023], [0.047], [226],
    [Top-decile specs vs. all others], [−0.013], [0.412], [114],
    [High-quality vs. NO spec (low-quality excluded)], [−0.019], [0.146], [201],
    [AI-tagged + high-quality spec], [−0.048], [0.045], [42],
  )
]

The top-quartile result is marginally significant (−2.3pp, _p_ = 0.047) but does not survive scrutiny. First, when we perform the cleanest comparison --- high-quality specs vs. PRs with _no spec at all_, excluding low-quality specs entirely --- the effect is not significant (_p_ = 0.146). Second, if there were a real dose-response relationship, top-decile specs should show a _stronger_ effect than top-quartile. Instead the effect weakens (_p_ = 0.412) --- the opposite of what a causal relationship predicts. Third, the top-quartile result would not survive Bonferroni correction across the four tests shown. Fourth, even top-quartile specs still _increase_ rework (+2.8pp, _p_ = 0.078).

The AI + high-quality spec result (_p_ = 0.045, −4.8pp) is the closest test to the agentic SDD workflow vendors are selling. However, it is identified from only 42 authors --- far too few for a stable estimate --- and the effect vanishes when comparing AI specs broadly (_p_ = 0.984). We note it as suggestive but not robust.

The objection that our measure is "too loose" does not rescue the SDD claims. Even restricting to the best-quality specs, the protective effect is fragile, does not follow a dose-response pattern, and does not reduce rework.

=== JIT Features as Primary Controls

A reviewer concern is that size controls (log additions, deletions, files) are insufficient --- the JIT defect prediction framework #cite(<kamei2013>) captures task complexity dimensions (entropy, file age, developer experience) that may confound the specification–defect association. We re-run H1 and H2 with 13 JIT features as additional controls alongside size controls (sexp excluded for zero variance).

#align(center)[
  #table(
    columns: 4,
    table.header[Test][Size controls only][+ JIT controls][Change],
    [H1: specs → bugs (coef)], [+0.019 (_p_ = 0.011)], [+0.006 (_p_ = 0.517)], [−71%],
    [H2: specs → rework (coef)], [+0.050 (_p_ < 0.001)], [+0.035 (_p_ < 0.001)], [−31%],
  )
]

For H1, the spec coefficient drops 71% and loses significance when JIT features are added, indicating that the apparent spec–defect association is largely explained by task complexity dimensions that size alone does not capture. For H2, the coefficient drops 31% but remains significant: specifications remain associated with more rework even after controlling for JIT risk features, though the effect is attenuated. The within-author spec coefficient in the JIT-controlled model (+0.006, _p_ = 0.517) is indistinguishable from zero for defects.

=== Propensity Score Matching

As an alternative to regression-based controls, we match each spec'd PR to an unspec'd PR with a similar JIT risk profile using nearest-neighbor propensity score matching (caliper = 0.05 SD of the logit propensity score). This directly addresses confounding by indication by comparing spec'd PRs to observationally similar unspec'd PRs.

#align(center)[
  #table(
    columns: 4,
    table.header[Outcome][Spec'd (matched)][Unspec'd (matched)][Difference],
    [Bug rate (7,217 pairs)], [16.2%], [16.6%], [−0.5pp (_p_ = 0.47)],
    [Rework rate (7,529 pairs)], [15.0%], [4.7%], [+10.3pp (_p_ < 0.001)],
  )
]

All 16 covariates are well-balanced after matching (all standardized mean differences < 0.1). For defects, the matched spec'd and unspec'd bug rates are indistinguishable: the raw +2.8pp difference is entirely explained by JIT risk profile differences. For rework, the result is different: spec'd PRs still show 3.2× higher rework even after matching on all observable risk features (only 11% attenuated vs. raw). This suggests that the rework association is not fully explained by task complexity --- either specifications mark tasks with unmeasured complexity dimensions, or the specification process itself generates downstream rework (e.g., by creating a documented target for reviewers to request changes against).

=== Temporal Analysis: The SDD Era

Specification adoption in our dataset is not uniform over time. Monthly specification rates rose from near zero before September 2025 to 14.6% by March 2026, coinciding with the release of Spec Kit (September 2025) and Kiro (July 2025). AI-tagged PR rates rose from 0.9% to 5.6% over the same period. If SDD tools are driving specification adoption and those specifications improve outcomes, the effect should be visible in the most recent data --- the period closest to production SDD usage.

We restrict the within-author analysis to the most recent three months of the observation window (January--March 2026), when specification rates are highest (13.5%) and AI adoption is most prevalent (4.4%):

#align(center)[
  #table(
    columns: 5,
    table.header[Test][Recent 3 months coef][_p_][Full dataset coef][_p_],
    [Specs → SZZ bugs], [+0.017], [0.036], [+0.019], [0.011],
    [Specs → rework], [+0.042], [< 0.001], [+0.050], [< 0.001],
    [AI + specs → bugs], [+0.009], [0.646], [---], [---],
    [AI + specs → rework], [−0.010], [0.588], [---], [---],
  )
]

The pattern is identical. In the period of highest SDD adoption, specification artifacts are still associated with _more_ bugs (+1.7pp) and _more_ rework (+4.2pp), not less. For AI-tagged PRs specifically, specs have no effect in either direction. The null result is not a historical artifact --- it persists in the data most representative of the SDD era.

A caveat on the temporal data: SZZ-traced bug rates for the most recent months are likely underestimates, because defects introduced recently may not yet have been fixed (and therefore cannot be traced back to their introducing commits). This right-censoring affects absolute bug rates but not the _relative_ comparison between spec'd and unspec'd PRs within the same time window, which is the quantity of interest.

The null result holds across every angle: four outcome measures, two predictive frameworks (LPM and JIT), propensity score matching on JIT risk profiles, seven quality dimensions, two units of analysis (PR-level and repo-level), six subgroup cuts, multiple quality thresholds, and temporal restriction to the period of highest SDD adoption. When JIT features are added as controls, the H1 spec coefficient drops 71% and loses significance; propensity score matching eliminates the association entirely. No specification measure robustly predicts fewer defects or less rework under any operationalization.

= Discussion

== Scale and Power

We analyze 89,599 pull requests across 119 repositories, with 897 authors who have both spec'd and unspec'd work. A 2-percentage-point reduction in bug rate would be detectable with high power given our sample size. The within-author estimates are not merely insignificant but _directionally reversed_ across most tests, suggesting this is not a power problem.

However, three caveats apply. First, our specification proxy is imperfect (Section~6): if SDD tools produce qualitatively different specifications from the organic artifacts we measure, the true effect could differ. Second, SZZ measurement noise (46--71% misattribution; #cite(<dacosta2017>)) reduces statistical power, though non-differential error attenuates toward the null rather than creating reversed associations. Third, residual within-author confounding (task selection) remains possible despite the fixed-effects design.

The strongest candidate for a real effect --- top-quartile spec quality reducing bugs by 2.3 percentage points --- does not survive the cleanest comparison (high-quality specs vs. no spec, _p_ = 0.146) and violates dose-response (top-decile weaker than top-quartile).

== All Roads Lead to Confounding by Indication

The pattern across all five hypotheses is identical: naive analysis suggests an association (sometimes in the claimed direction, sometimes opposite), but within-author analysis reveals this as confounding by indication. Harder, larger, riskier tasks are more likely to receive specifications --- and independently more likely to produce defects and require rework.

The same pattern is well-known in clinical medicine as confounding by indication: patients who receive treatment are sicker than those who don't, creating a naive association between treatment and worse outcomes #cite(<salas1999>). The same logic applies here: pull requests that receive specifications are _harder_ than those that don't, because developers (rationally) invest specification effort in proportion to task complexity.

JIT risk feature profiles confirm this directly. In the most recent three months (January--March 2026), spec'd PRs have significantly higher change entropy (1.3×, _p_ < 0.001), more lines added (1.6×, _p_ < 0.001), touch older files (1.8×, _p_ < 0.001), and involve more prior developers (1.2×, _p_ < 0.001) than unspec'd PRs. Every JIT risk dimension is elevated in spec'd work. Notably, spec'd PR authors have _less_ experience than unspec'd PR authors (median 62 vs. 121 prior commits in the repository, _p_ < 0.001) --- less experienced developers spec more, not less, consistent with specifications being a support mechanism for harder tasks rather than an optimization used by experts.

The implication is that any observational study comparing spec'd to unspec'd work will overestimate the positive association between specifications and poor outcomes (or underestimate any benefit) unless it controls for the endogenous selection of which tasks receive specifications.

== What Actually Predicts Defects

If specifications do not predict defects, what does? The JIT risk features provide a clear answer. In the most recent three months, bug-introducing PRs differ from clean PRs on every code-change dimension: median lines added is 5.5× higher (203 vs. 37, _p_ < 0.001), prior changes to the affected files are 3.5× higher (122 vs. 35, _p_ < 0.001), file size is 3.1× larger (3,408 vs. 1,091 lines, _p_ < 0.001), and change entropy is 1.9× higher (_p_ < 0.001). These are structural properties of the change, not properties of the specification.

Developer experience does not protect against defects --- it predicts _more_ of them. Bug-introducing PR authors have 2.1× more experience than clean PR authors (median 213 vs. 101 prior commits, _p_ < 0.001). This is not because experience causes bugs; it is because experienced developers work on harder, riskier code. The same confounding-by-indication pattern that explains the specification association explains the experience association.

AI-tagged PRs show the same defect predictors as human PRs. Within AI-authored work, buggy PRs touch 2× more directories, add 3.7× more lines, and modify files with 3.7× more prior changes than clean AI PRs. AI does not introduce a novel failure mode --- it works on riskier code more often (median lines added: 75 for AI vs. 44 for human, _p_ < 0.001) and produces bugs at a commensurately higher rate (14.8% vs. 9.3%).

AI bugs are caught faster than human bugs (median 14.6 days to fix vs. 27.0 days, _p_ < 0.001), though this is partly a right-censoring artifact: AI adoption is recent, so AI bugs mechanically have shorter maximum possible fix times. AI bug authors are more likely to fix their own bugs (51.9% self-fix rate vs. 41.4%, _p_ < 0.001).

Pooled data suggest that AI bugs cascade more: 45% of AI-tagged SZZ bugs also trigger rework, compared to 11.2% of human bugs. However, this does not hold within repositories. In repos with at least 5 AI and 5 human buggy PRs (14 repos), AI rework|buggy is higher in only 7 of 14 (mean Δ = −1.6%, _p_ = 0.70). The pooled difference is driven by repo composition: AI adoption rate correlates _ρ_ = 0.92 with repo-level rework rate (_p_ < 0.001). AI-heavy repos have high rework rates for all contributors, not just AI-tagged PRs. This is another instance of the confounding-by-indication pattern --- repos that adopt AI tools are different kinds of projects, and those projects have higher rework rates independent of AI.

== Review Does Not Mediate the Claimed Effect

A plausible mechanism for specification-driven quality improvement is that specifications improve the review process: reviewers who can compare code against a spec should catch more defects. If this mechanism operated, spec'd PRs should receive more thorough review and, conditional on that review, produce fewer defects.

Spec'd PRs do receive more review. Within-author, the same developer's spec'd PRs take 56% longer to merge (median 23.8 vs. 15.3 hours, _p_ < 0.001) and accumulate more review cycles (+0.024 log-cycles, _p_ < 0.001). But this additional review does not translate into fewer defects. Within-author, more review cycles predict _more_ bugs (+0.026, _p_ < 0.001), not fewer --- the same confounding pattern: harder PRs receive both more review and more bugs.

AI-tagged PRs receive _less_ review scrutiny than human PRs: median time-to-merge is 15.2 hours for AI vs. 17.4 hours for human (_p_ = 0.002). This is concerning independently of the specification question --- AI-generated code, which has a higher base defect rate (14.8% vs. 9.3%), is being merged faster, not slower.

== What This Study Shows

We test the specific, concrete claims made by SDD tool vendors --- that specification artifacts reduce defects, prevent rework, and constrain AI scope --- using the closest available proxy: organic specification artifacts scored on the same quality dimensions SDD tools prescribe. Across 89,599 pull requests spanning 119 repositories, the naive association is reversed: specifications accompany _more_ defects. After within-author controls, we cannot distinguish the true effect from zero. The most parsimonious interpretation is confounding by indication: harder tasks receive specifications and independently produce more defects, with no residual protective effect visible at our resolution.

This does not prove specifications are useless. It means we cannot detect the claimed benefits at this scale, with this proxy, using the strongest observational design available. Specifications may provide value through mechanisms we cannot measure (team alignment, downstream review quality, audit trails) --- but these are not the claims being made. The vendors claim measurably "fewer bugs" and "reduced rework." Our data test these claims and find no support.

The alternative interpretation --- that specifications genuinely prevent defects but only for the hardest tasks, and the difficulty effect dominates --- does not rescue the marketing claims either. If the benefit exists only for tasks so difficult that their inherent defect propensity overwhelms the specification benefit, then "specifications reduce defects" is misleading at best. The net observable effect is more defects, not fewer.

SDD vendors assert that the specification artifact itself is the causal mechanism --- that the spec constrains agent behavior and enables self-validation during generation (Section~3.1). Our results are incompatible with this assertion.

A likely objection is that our data predates true agentic workflows, where the specification is the primary input to an AI agent rather than a human reference document. We address this empirically in our subgroup analysis (AI-tagged PRs show no spec benefit), but there is also a conceptual response. SDD vendors conflate two distinct functions: _directing_ the AI (telling it what to build) and _ensuring quality_ (fewer bugs, less rework, functional completeness). Specifications may be effective at the first --- giving an agent a structured task description is clearly better than a vague prompt. But direction is not quality. An agent faithfully executing a spec will reproduce every gap, ambiguity, and wrong assumption in that spec, with high confidence. A spec can be exhaustively long and still incomplete. It can specify the wrong behavior precisely. It can omit error cases, edge conditions, and integration constraints that the agent will not independently discover, because the agent treats the spec as ground truth. The specification tells the AI _what_ to build. It does not tell the AI _what it forgot to specify_. The quality improvement claimed by SDD vendors requires the spec itself to be correct and complete --- which is the hard part of software engineering that specifications do not solve, they merely relocate.

== Where Specifications May Still Have Value

Specifications may provide value through mechanisms our study does not measure: audit trails (what the code was _supposed_ to do), durable documentation (reducing the knowledge gap as AI generates more code), and team alignment (shared understanding before implementation). These are organizational benefits, not defect-prevention benefits, and our data does not speak to them. There is also a timing distinction: a specification written _after_ iterative validation may function differently from one written _before_ any code exists. SDD tools treat the spec as the starting point, but a spec written before validation is a structured guess. Our data cannot distinguish specification-as-input from specification-as-output, but the distinction may matter for future research.

== Vendor Evidence and Construct Gap

No SDD tool vendor has published empirical evidence for the quality claims tested here. The evidence base consists of first-principles reasoning ("clearer input → better output") and developer testimonials. GitHub describes Spec Kit as "an experiment" #cite(<speckit2025>) and publishes no effectiveness data. The third-party evaluations that do exist are negative: Böckeler found Spec Kit's overhead "overkill for the size of the problem" #cite(<fowler2025>); Eberhardt found it roughly ten times slower than iterative development #cite(<scottlogic2025>).

The specification artifacts in our dataset are not generated by SDD tools. A text search of all 100,247 PR descriptions, titles, and file paths for `.specify/`, `.speckit/`, `.kiro/`, and `spec-kit` returns zero matches. The specification adoption we observe --- rising from near zero to 14% over 2025--2026 --- reflects organic specification behavior: linked issues, design documents, structured PR descriptions. We measure the _kind_ of specification content that SDD tools claim to improve upon, scored on the same quality dimensions those tools prescribe, but the artifacts are not tool-generated.

This is a genuine limitation. SDD tools produce specifications in a specific format through a guided workflow, fed directly to an AI agent. Our proxy measures organic specification artifacts scored on the same dimensions. If the tool's format itself is the active ingredient --- something beyond the seven quality dimensions we measure --- that would be a testable claim. Our data show that the content typically found in specifications, measured on the dimensions SDD tools prescribe, does not predict quality improvement.

An important implication: SDD tooling imposes real costs (specification-writing time, process overhead, organizational change). Teams adopting SDD on the basis of vendor claims are making investment decisions on unsubstantiated assertions. We do not argue that thinking about requirements is wasted effort. We argue that the _products_ claiming to reduce defects through specification artifacts have not demonstrated that they do. The best available proxy evidence shows no such effect. Production-scale data from purpose-built SDD tools does not yet exist in the public domain, and vendors with the resources to produce it have not done so.

= Threats to Validity

== Are We Measuring the Right Thing?

Three gaps separate what we measure from what SDD vendors claim.

*We detect specification artifacts, not specification processes.* Our classifier flags linked issues, structured descriptions, and referenced design documents. A linked Jira ticket created to satisfy a process requirement counts the same as a detailed design document written after iterative refinement. If the benefit comes from the _thinking_ rather than the _artifact_, our measure is too coarse. Two observations partially address this concern. First, the within-author design compares the same developer's spec'd and unspec'd work, controlling for that person's consistent habits. Second, H3 and H4 test quality _within_ spec'd PRs on seven SDD-aligned dimensions. If deeper thinking produced better artifacts, those artifacts should predict better outcomes. They do not. The remaining objection --- that process depth helps through a mechanism invisible in the artifact itself --- is difficult to test with any observational design.

*We test organic specifications, not SDD tool output.* Spec Kit generates structured documents through a guided workflow and feeds them to a coding agent. A linked GitHub issue is not the same thing. Our operationalization is the broadest reasonable proxy available, but it may miss whatever specific mechanism the tools provide. The high-quality spec subsample (top-quartile, scored on the dimensions SDD tools prescribe) is the closest approximation. It too shows no robust effect.

*We cannot observe agentic workflows directly.* Even for AI-tagged PRs with specifications, we do not know whether the spec was actually used as input to an agent or just written for human consumption. True agentic SDD --- where the agent reads the spec, generates code from it, and validates against it --- is not observable in our data. The 42-author AI + high-quality spec subsample is the closest proxy we have.

== Are We Measuring Outcomes Accurately?

*Defect detection is noisy.* The SZZ algorithm traces fix commits back to their introducing commits via `git blame`. da Costa et al. #cite(<dacosta2017>) found that basic SZZ misattributes 46--71% of bug-introducing changes. We use the basic variant for implementation simplicity across 103 repositories. This noise is substantial, but we expect it to be non-differential --- there is no reason SZZ accuracy would vary with specification status. Non-differential measurement error attenuates true associations toward the null, reducing power but not creating spurious reversed effects. Small true effects may be undetectable in our data.

*Quality scoring is automated and unvalidated.* Our LLM-based rubric (Claude Haiku) measures _formal_ quality --- whether the text contains outcome descriptions, error states, and acceptance criteria --- not _functional_ quality. A spec can score highly and still describe the wrong behavior. The rubric's seven dimensions align with what SDD tools prescribe, which means our scoring shares whatever blind spots those templates have. The scoring was applied only to PRs with substantial description text, creating a non-random subsample.

*AI detection relies on voluntary tagging.* We identify AI-assisted PRs via self-reported markers in the PR body. Developers who use AI without attribution are invisible. The false-negative rate is unknown. If many untagged PRs involved AI, the H5 comparison would be diluted toward the null.

*The control group may be contaminated.* Some "unspec'd" PRs may have had specifications shared verbally, in Slack, or in external tools. This would attenuate any treatment effect. However, if informal specification produces equivalent outcomes to formal artifacts, the SDD value proposition is undermined: vendors claim the _tooling and artifact_ add value, not that thinking about requirements helps in general.

== Could Something Else Explain the Results?

*Confounding by indication* is the primary threat. Developers spec hard tasks. Hard tasks produce bugs. The within-author design addresses this by comparing each developer to themselves, but within-author task selection remains possible: if an author consistently specs their hardest work and skips specs on easy tasks, the comparison is biased. The JIT-controlled models (Section~4.7) and propensity score matching (Section~4.8) address this further, and both confirm the null for defects.

*Time-varying confounding.* An author's skill, tooling, and project context may change over the observation period. The within-author estimator assumes these are stable.

== Can These Results Generalize?

*Open-source only.* All 119 repositories are open-source. SDD tools target commercial teams with product managers, QA processes, and sprint planning. The specification practices and defect economics may differ.

*Convenience sample.* Repositories were not randomly selected. Results cannot be generalized beyond the sample.

*Pre-agentic era.* Most PRs predate widespread agentic AI coding tools. The dataset contains 2,650 non-bot AI-tagged PRs, the closest available proxy for agentic workflows. Within this subsample, specs show no effect on bugs (_p_ = 0.98) or rework (_p_ = 0.33). We cannot rule out that true agentic workflows would produce different results --- but that is itself an untested claim.

== Statistical Caveats

*Multiple comparisons.* We test five hypotheses without correction. At α = 0.05, approximately 0.25 false positives are expected by chance.

*Power for AI interaction.* The scope-constraint test (H5) is identified from only 189 authors with variation in both specification and AI use. This test may be underpowered for small effects.

= Conclusion

Spec-driven development tools make five specific, testable claims: specifications reduce defects (H1), prevent rework (H2), improve outcomes through higher-quality requirements (H3, H4), and constrain AI-generated code scope (H5). Production-scale data from purpose-built SDD tools is not yet publicly available. We test the claims using the best available proxy: 89,599 pull requests across 119 open-source repositories, where specification artifacts are scored on the same quality dimensions that SDD tools prescribe, using within-author fixed-effects estimation.

Zero of five hypotheses are supported. The naive association between specifications and defects is reversed (specifications accompany _more_ defects); after within-author controls, the most parsimonious interpretation is confounding by indication. Specification quality has no meaningful effect on rework (_p_ = 0.767). The claimed AI scope-constraint effect vanishes under within-author analysis. Nine robustness checks all confirm the null. Adding specification presence to a JIT defect model contributes Δ Pseudo~_R_#super[2] = 0.00003 (_p_ = 0.250). Specification presence proxies for task complexity, not for quality improvement.

Three important caveats bound these findings. First, we test organic specification artifacts, not SDD tool-generated specifications --- the construct gap is real (Section~6). Second, SZZ defect tracing has substantial measurement noise (46--71% misattribution), which attenuates true effects. Third, our open-source convenience sample may not generalize to commercial teams. Whether purpose-built SDD tooling would produce different results on commercial codebases remains an open question. The best available proxy evidence offers no support for the quality claims being made.

The dataset and analysis code are available at: `github.com/brennhill/delivery-gap-research`.

#pagebreak()

= References

#set par(first-line-indent: 0pt, hanging-indent: 0.5in)

#bibliography(style: "apa", title: none,
  "ssrn-sdd-refs.yml",
)
