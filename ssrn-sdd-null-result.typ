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
*Context.* Spec-driven development (SDD) tools claim that writing specifications before implementation reduces defects, prevents rework, and improves code quality. No vendor has published empirical evidence for these claims.
*Method.* We test five hypotheses derived from SDD vendor claims against 88,052 pull requests across 119 open-source repositories. We score 25,209 specification artifacts on the same quality dimensions SDD tools prescribe, trace defects via the SZZ algorithm, and compare each developer's spec'd PRs to their own unspec'd PRs. Twelve robustness checks include propensity score matching, complexity stratification, and AI/human subgroup analysis.
*Results.* None of the five hypotheses are supported. Spec'd PRs introduce _more_ defects, not fewer --- developers spec their hardest work, and hard work produces defects (confounding by indication). Specification quality does not predict fewer defects (_p_ = 0.164) or less rework (_p_ = 0.860). Specifications do not constrain AI-generated code scope (_p_ = 0.997). One exception: in repositories with no AI adoption, specifications are associated with less rework (_p_ = 0.014) --- the only protective signal, appearing where AI is absent.
*Conclusion.* Specification artifacts proxy for task complexity, not quality improvement. The one protective signal appears in human-only workflows, not AI-assisted ones.
  ]
]

#pagebreak()

// === BODY ===

= Introduction

#par(first-line-indent: 0pt)[
The rise of AI-assisted software development has produced a new category of developer tooling: specification-driven development (SDD) frameworks. These tools --- including GitHub's Spec Kit #cite(<speckit2025>) and Amazon's Kiro #cite(<kiro2025>) --- claim that writing formal specifications before implementation leads to fewer defects, less rework, and higher-quality code, particularly when AI agents perform the implementation.
]

Böckeler #cite(<fowler2025>) defines spec-driven development as "writing a 'spec' before writing code with AI" where "[t]he spec becomes the source of truth for the human and the AI." The GitHub Copilot Academy frames it more strongly: "Specifications don't serve code --- code serves specifications" #cite(<copilotacademy2025>). The movement gained momentum in 2025 with the release of GitHub's Spec Kit (open-source) and Amazon's Kiro IDE. Böckeler examined three tools pursuing the approach #cite(<fowler2025>). More broadly, SDD is positioned as an antidote to "vibe coding" --- iteratively prompting AI without formal requirements --- which practitioners associate with scope creep, rework, and defects.

The core premise is intuitive: if developers articulate what software should do before writing it, AI systems will produce more reliable output. The GitHub Copilot Academy lists "reduced rework, living documentation, systematic quality" among SDD's benefits #cite(<copilotacademy2025>). Kiro claims that specifications enable "fewer iterations and higher accuracy" and "prevent costly rewrites" #cite(<kiro2025b>). GitHub's Spec Kit blog post promises "less guesswork, fewer surprises, and higher-quality code" #cite(<speckit2025>).

These claims rest on a plausible causal chain: clearer requirements → less ambiguity → fewer defects. Yet vendors cite no empirical evidence for these claims in their marketing materials, documentation, or blog posts. No study has tested SDD's quality claims on production-scale data prior to this paper.

This paper provides the first large-scale empirical test. We analyze 88,052 merged pull requests across 119 open-source repositories, after excluding 12,195 bot-authored PRs. Defects are traced to their introducing commits using the SZZ algorithm (named for Śliwerski, Zimmermann, and Zeller), which works backward from bug-fixing commits through version control history to identify which earlier commits introduced each bug. We compare each developer's spec'd PRs to their own unspec'd PRs to control for developer-level confounding, and derive five hypotheses directly from vendor claims.

= Related Work

== Requirements Engineering and Defect Prevention

The claim that upfront specification prevents defects has deep roots in software engineering. Boehm's cost-of-change curve #cite(<boehm1981>) argued that requirements defects are exponentially cheaper to fix early. However, subsequent work has challenged the universality of this finding. Shull et al. #cite(<shull2002>) found that the cost multiplier depends heavily on project context, and agile methodologies have demonstrated that iterative refinement can be more effective than upfront specification for certain project types #cite(<beck2001>).

The question of whether requirements quality predicts software defects has been studied directly. Mund et al. #cite(<mund2015>) combined two empirical studies and found only weak evidence that requirements specification quality predicts implementation defects, with effect sizes that varied substantially across projects. Femmer et al. #cite(<femmer2017>) developed automated detection of "requirements smells" (ambiguity, incompleteness, inconsistency) and found that while smells were prevalent, their relationship to downstream defects was context-dependent. These findings suggest that the relationship between specification quality and code quality is not as straightforward as SDD vendors assume --- a pattern our study confirms at larger scale.

== SDD Literature

The academic literature on SDD perpetuates the pattern of unsubstantiated claims. Piskala #cite(<piskala2026>) claims "controlled studies showing error reductions of up to 50%," citing a Red Hat Developer blog post #cite(<naszcyniec2025>) and an InfoQ article #cite(<griffin2026>) as evidence. Neither source contains any controlled study, any experiment, or any quantitative data. The "50%" figure traces through a citation chain that ultimately rests on practitioner opinion pieces with no empirical backing. Guo et al. #cite(<sedeve2025>) claim SDD "guarantees software quality" without empirical validation. Marri #cite(<marri2026>) reports a 73% security defect reduction from constitutional specs, but on a single project (_n_ = 1), with the same developer implementing both conditions sequentially --- the author acknowledges "small sample size limits statistical power." Roy #cite(<roy2026>) proposes iterative spec-code co-evolution but reports no independently validated quality outcomes. Zietsman #cite(<zietsman2026>) runs small planted-bug experiments and is honest about their limitations ("directional, not statistically significant"), while contributing the useful observation that AI reviewers without specs suffer circular reasoning --- but does not test whether specs reduce defects at scale.

Practitioner evaluations have been more skeptical. Eberhardt, writing for Scott Logic, found Spec Kit roughly ten times slower than iterative development, producing thousands of lines of specification markdown that still resulted in buggy code #cite(<scottlogic2025>). Zaninotto argued that "SDD shines when starting a new project from scratch, but as the application grows, the specs miss the point more often and slow development," and proposed iterative natural-language development as a faster alternative #cite(<zaninotto2025>).

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

GitHub's Spec Kit blog states that "providing a clear specification up front, along with a technical plan and focused tasks, gives the coding agent more clarity, improving its overall efficacy" #cite(<speckit2025>). Kiro claims specifications enable "fewer iterations and higher accuracy" #cite(<kiro2025b>). This implies a dose-response relationship: higher specification quality should predict fewer defects.

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

We collected pull request data from 119 open-source repositories spanning 17 programming languages. Repositories were selected to represent large, active projects with diverse contribution patterns. We collected data between March 28 and April 3, 2026, with a 365-day lookback window per repository. The resulting dataset spans April 2025 through early April 2026 (1st--99th percentile: April 8, 2025 to April 1, 2026), totaling 100,247 PRs. We excluded 12,195 bot-authored PRs (dependabot, renovate, and other automated accounts identified by username pattern and bot flags), leaving 88,052 PRs from human and AI-assisted authors.

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
    [Quality-scored PRs], [25,209], [28.6% of total; 17,973 enriched with issue body],
  ),
  caption: [Study dataset overview.],
) <tab:dataset-overview>

The sample spans 17 programming languages, with Python (31 repos, 26%), TypeScript (26, 22%), Go (17, 14%), and Rust (13, 11%) predominating. The median repository has a 26.2% specification rate (IQR 16.0--41.1%). AI tagging is present in most repositories: the median AI tag rate is 1.2% (IQR 0.4--8.1%). The 5,989 AI-tagged PRs provide sufficient statistical power for the primary AI analyses, though we recognize that the AI-specific results would benefit from a larger AI-tagged sample as agentic workflows become more prevalent.

== Variables

=== Specification Presence (`specd`)

A pull request is classified as "specified" (hereafter "spec'd") if it meets any of the following criteria: (a) it links to a GitHub issue or external tracking ticket, (b) its description references a specification document, RFC, or design doc, or (c) its description contains structured requirements content (acceptance criteria, behavioral descriptions, scope boundaries). Classification is performed programmatically by parsing PR metadata: issue references (`#123`, `fixes #456`), cross-reference URLs, and description structure (presence of headings, checklists, or requirement-style language). 24,298 of 88,052 PRs (27.6%) are classified as specified.

This operationalization is deliberately generous: it captures any form of upfront specification artifact, from a linked Jira ticket to a detailed RFC. SDD tools claim benefits from _any_ form of specification, so we test the broadest reasonable definition. Specification _presence_ and specification _quality_ are tested separately: H1 and H2 test whether having any specification artifact predicts fewer defects or less rework; H3 and H4 test whether, among the subset of PRs that have specifications, higher-quality specifications predict better outcomes. This two-level design addresses the objection that our binary `specd` measure is too coarse by also testing whether the content of the specification matters.

=== Specification Quality (`q_overall`)

For the subset of specified PRs with substantial descriptions (body length > 50 characters), we scored specification quality by prompting Claude Haiku (Anthropic) with the PR title and body and a structured rubric. The LLM scored each PR across seven dimensions: outcome clarity, error states, scope boundaries, acceptance criteria, data contracts, dependency context, and behavioral specificity. Each dimension is scored 0--100, and the overall quality score is the mean across dimensions.

These seven dimensions were chosen to align with the quality criteria recommended by SDD tools themselves. Spec Kit's template prescribes "core requirements" (outcome clarity), "acceptance criteria" (our acceptance criteria dimension), "edge cases" (error states), "data models" and "API contracts" (data contracts), and "user stories" (behavioral specificity) #cite(<speckit2025>). Kiro prescribes "clear requirements," "acceptance criteria," "system architecture," and "technology choices" #cite(<kiro2025b>). Six of our seven dimensions have direct equivalents in Spec Kit's recommended structure; all seven are covered across both tools. This alignment is deliberate: we measure specification quality on the dimensions that SDD vendors themselves say matter.

We validated the LLM scoring against independent human ratings on a stratified random sample of 38 PRs. The human rater scored each dimension on the same rubric, blind to the LLM scores. Overall agreement was moderate: the human and LLM ranked PRs in roughly the same order#footnote[Spearman rank correlation _ρ_ = 0.42 (_p_ = 0.01); Pearson linear correlation _r_ = 0.45 (_p_ < 0.01). Spearman measures whether the LLM and human rank PRs in the same order; Pearson measures whether the scores move together linearly. Both indicate moderate agreement --- the LLM and human agree more often than chance but disagree on many individual PRs.]. The LLM scores systematically higher than the human rater (mean bias: +4 points on the 0--100 scale, mean absolute difference: 13 points). Per-dimension agreement varies: behavioral specificity (_ρ_ = 0.45, _p_ = 0.004), scope boundaries (_ρ_ = 0.43, _p_ = 0.007), dependency context (_ρ_ = 0.40, _p_ = 0.01), and outcome clarity (_ρ_ = 0.39, _p_ = 0.02) show significant agreement, while error states (_ρ_ = 0.22), data contracts (_ρ_ = 0.19), and acceptance criteria (_ρ_ = 0.17) show weak correlation. The LLM reliably detects whether specification content is _present_ but cannot judge whether it is _correct_ for the domain --- a distinction between formal completeness and functional quality. Since even this completeness-oriented measure shows no defect benefit, the null finding is conservative: a more precise quality measure would sharpen the estimate, not reverse it.

25,209 PRs (28.6% of total) received quality scores across all 119 repositories. For PRs linked to GitHub issues, we fetched the issue body and scored the combined content. 17,973 scores include linked issue content; the remainder were scored on PR description alone. This subsample is non-random --- only spec'd PRs with sufficient text were scored.

A further limitation: we cannot distinguish specifications written before implementation from descriptions written after. Many PR descriptions in our dataset are likely post-hoc --- the developer wrote the code, then described what it does. However, linked GitHub issues are the strongest available proxy for pre-implementation intent: the issue typically exists before the PR is opened, describes the problem or desired behavior, and is not written by the same person who writes the code. We test this subset separately in Section~5.6.12 (Issue-Linked Specifications), where we fetch the actual issue body, score the combined content, and test defect and rework outcomes for issue-linked PRs specifically. The null result holds for this subset as well. We also compared quality scores for issue-linked PRs (median quality 49, _N_ = 10,190) to PRs classified by description content alone (more likely post-hoc; median quality 47, _N_ = 12,128). The difference is statistically significant (_p_ < 0.001) but substantively small (2 points on the 0--100 scale). The pre/post distinction does not appear to matter for our quality measure.

Furthermore, many effective AI instructions are inherently underspecified by our rubric's standards. A prompt like "improve the error handling, it looks ugly" scores low on outcome clarity, acceptance criteria, and behavioral specificity --- yet it is a perfectly successful instruction for an AI agent that can read the surrounding code. The agent does not need the spec to enumerate every error case; it can infer them from context. This class of task --- where the codebase itself provides sufficient specification --- is invisible to our quality measure but may represent a large share of productive AI-assisted work. If detailed specifications add no value for tasks where the code context is sufficient, the marginal benefit of specification effort is even smaller than our results suggest.

=== Defect Introduction (`szz_buggy`)

We applied the SZZ algorithm #cite(<szz2005>) to 103 of 119 repositories, tracing 64,805 blame links from fix commits to bug-introducing commits. The remaining 16 repositories produced zero traceable blame links. Their merge commit SHAs (recorded by the GitHub API) are not reachable in single-branch clones, typically because squash-merge workflows cause GitHub's synthetic merge commits to be garbage-collected after merging. The SZZ algorithm uses `git blame` to trace defect-fixing commits back to the commits that introduced the defect. We use the basic SZZ variant, which da Costa et al. #cite(<dacosta2017>) found misattributes 46--71% of bug-introducing changes depending on the project. This noise is substantial, but it is non-differential with respect to specification presence: there is no reason to expect SZZ to systematically misattribute more for spec'd PRs than unspec'd PRs. Non-differential measurement error attenuates associations toward the null, which works against finding a protective effect but does not create spurious reversed associations. We acknowledge the implications for statistical power in Section~7. Each bug-introducing commit was mapped to its originating pull request. A PR is marked `szz_buggy = True` if any of its commits were identified as introducing a defect that was later fixed. 9,754 PRs (12.5% of those in SZZ-covered repos) are marked as bug-introducing.

=== Rework (`reworked`)

A pull request is classified as reworked if a subsequent PR within 30 days by any author modifies overlapping files and has a title or description indicating correction (matching patterns such as "fix," "revert," "bugfix," "hotfix," "regression," "broke," or "broken"). File overlap is computed by comparing the set of files changed in each PR pair; high-frequency files (touched by >30% of PRs in the repository) are excluded to avoid spurious attribution. 11,820 PRs (13.4%) are classified as reworked. The 30-day window was chosen based on sensitivity analysis: rework detection increases from 14 to 30 days but shows diminishing returns beyond 30 days (the spec--rework association is directionally consistent across 14-, 30-, 60-, and 90-day windows).

=== AI-Tagged (`ai_tagged`)

A pull request is classified as AI-assisted through two detection layers. First, a regex matches co-author tags (e.g., `Co-authored-by: Copilot`), generation attribution strings (`Generated with`, `Claude Code`, `written with/by` followed by a tool name), AI agent markers (`CURSOR_AGENT`, `coderabbit.ai`, `AI-generated`), and the robot emoji (🤖). Second, we parse structured "AI Disclosure" and "AI Usage" sections that some repositories include in their PR templates, classifying the disclosure content as AI-used or no-AI-used. We validated the combined classifier against 537 PRs with clear self-reported AI disclosures: precision is 98.8% (1 false positive) and recall is 24.2% (75.8% false negatives). The low recall reflects that many developers describe AI use in natural language that our patterns do not capture. 5,989 PRs (6.8%) carry AI tags after bot exclusion. This remains a lower bound.

=== Code Churn (`total_churn`)

Total code churn is defined as additions + deletions. We use `log(1 + churn)` in regressions to normalize the heavily right-skewed distribution (median: 55, mean: 698).

== Statistical Approach

For each hypothesis, we report three levels of analysis. Each level controls for more potential confounders than the last, so readers can see how the result changes as we account for more alternative explanations:

#par(first-line-indent: 0pt)[
  *Pooled:* Raw rates compared directly. This is the analysis that unadjusted claims would cite --- it ignores all confounders.
]

#par(first-line-indent: 0pt)[
  *Controlled:* Logistic regression adjusting for PR size (log additions, log deletions, log files changed) and _repository fixed effects_ --- a separate adjustment for each repository, so the model compares spec'd and unspec'd PRs _within the same repo_ rather than across repos. This matters because some repositories are inherently buggier than others (different languages, test coverage, team norms), and repos with higher spec rates may also have higher defect rates for reasons unrelated to specs. Without this adjustment, a repo-level correlation could masquerade as a spec-level effect. In two analyses (H1, H3), including 100+ repository adjustments caused the statistical model to fail (singular matrix), so those estimates use size controls only --- a weaker but still informative comparison.
]

#par(first-line-indent: 0pt)[
  *Within-author:* The strongest test. We subtract each developer's own average from every variable, then run a linear regression on the residuals. This compares each developer's spec'd PRs to their own unspec'd PRs, eliminating all stable differences between developers --- skill, experience, coding style, and organizational context are held constant because both "treatment" and "control" come from the same person.#footnote[Technically: a linear probability model (LPM) with full author demeaning, equivalent to author fixed effects via the Frisch--Waugh--Lovell theorem. We use LPM rather than logistic regression because author demeaning is exact for OLS but produces biased estimates in logit due to the incidental parameters problem #cite(<neyman1948>). Chamberlain's conditional logit avoids this but requires discarding groups without outcome variation, reducing power. We follow Angrist and Pischke's recommendation #cite(<angrist2009>).] Standard errors account for the fact that PRs from the same author are correlated (clustered at the author level). Primary models use size controls; Section~5.6 confirms results hold when adding Just-In-Time (JIT) defect prediction features #cite(<kamei2013>) --- a set of 14 code-change metrics (lines added, file age, developer experience, etc.) known to predict defect-introducing commits.
]

The within-author estimate is the most credible. The treatment effect is identified only from authors who have _both_ specified and unspecified PRs in the dataset --- authors who always or never write specs contribute no information.

We restrict within-author analysis to authors with ≥2 PRs and report the number of authors with treatment variation (those who have both spec'd and unspec'd PRs), as the treatment effect is identified from these authors' within-author variation. For within-author estimates, we report 95% confidence intervals based on clustered standard errors to allow readers to assess what effect sizes are compatible with the data.

We do not apply multiple-comparison corrections across the five hypotheses. At α = 0.05, approximately 0.25 false positives are expected by chance. We interpret all results with this in mind.

Sample sizes vary across hypotheses because of SZZ coverage, quality scoring, and within-author filtering:

#figure(
  table(
    columns: (auto, auto, auto, auto),
    align: (left, right, right, right),
    table.header[Hypothesis][PRs (pre-filter)][Within-author _N_][Identifying authors],
    [H1: specs → bugs], [77,814 (103 SZZ repos)], [72,046], [2,181],
    [H2: specs → rework], [88,052 (all 119 repos)], [81,647], [2,524],
    [H3: quality → bugs], [22,672 (scored, SZZ repos)], [19,688], [2,030],
    [H4: quality → rework], [25,209 (scored subset)], [21,881], [2,297],
    [H5: spec × AI → churn], [88,052 (all 119 repos)], [71,932], [366],
  ),
  caption: [Sample sizes by hypothesis.],
)

#text(size: 9pt)[Within-author _N_ is after restricting to authors with ≥2 PRs and dropping rows with missing controls. Identifying authors are those with variation in both treatment and control conditions.]

= Results

== H1: Specifications Reduce Defects

#par(first-line-indent: 0pt)[
  Analysis restricted to 77,814 PRs in the 103 repositories with SZZ coverage.
]

#figure(
  table(
    columns: 4,
    table.header[Method][Coefficient][_p_-value][Interpretation],
    [Pooled (raw comparison)], [OR = 1.20#super[a]], [< 0.001], [Spec'd PRs have _higher_ defect rate],
    [Controlled (size only#super[†])], [0.067], [0.006], [Effect persists with size controls],
    [Within-author], [+0.014 \[+0.005, +0.024\]], [0.003], [+1.4pp _increase_ in defect rate],
  ),
  caption: [H1: Specifications and defect-introduction rates.],
)

#text(size: 9pt)[#super[a] Odds ratio: spec'd PRs are 1.20× as likely to introduce a defect as unspec'd PRs. #super[†] Including a separate adjustment for each of 100+ repositories caused the model to fail; this estimate adjusts for PR size only. Within-author 95% CI in brackets.]

Identified from 2,181 authors with treatment variation (out of 4,328 authors with ≥2 PRs).

*H1 is not supported.* The pooled comparison is the unadjusted analysis: spec'd PRs are 20% more likely to introduce a defect than unspec'd PRs. But this comparison is confounded --- developers who write specs are different from those who don't, and the repos that encourage specs are different from those that don't. The controlled estimate adds size controls (repository adjustments could not be included --- see footnote). The effect persists.

The within-author estimate is the most credible. It compares the _same developer's_ spec'd PRs to their own unspec'd PRs, eliminating all stable author-level differences.

Within-author, spec'd PRs are associated with a 1.4 percentage-point _increase_ in defect-introduction rates (_p_ = 0.003). The effect is small in absolute terms#footnote[Odds ratio = 1.13 (spec'd PRs are 13% more likely to have a defect); Cohen's _d_ = 0.07, well below the conventional "small effect" threshold of 0.20. The effect is statistically significant because of the large sample, but it is practically tiny --- and in the wrong direction.] but the direction is opposite to the vendor claim at every level of analysis.

This pattern is called _confounding by indication_ --- in plain terms, developers tend to write specs for the hardest work, and harder work produces more defects. The specification does not cause the defects --- the task difficulty that motivates writing one does. When JIT risk features are added as controls (Section~5.6), the within-author spec coefficient drops 55% and loses significance (_p_ = 0.229), confirming that measurable task complexity explains most of the association.

A plausible alternative explanation is detection bias: if spec'd PRs have better test coverage and more granular QA, their defects may be detected and fixed individually, making them more visible to SZZ tracing. Unspec'd PRs might have defects that go undetected longer or get fixed in bulk refactoring commits that SZZ cannot trace, producing artificially low defect rates. We cannot rule this out entirely. However, two observations weigh against it. First, the rework measure (H2) does not depend on SZZ tracing and shows the same directional pattern. Second, propensity score matching (Section~5.6) eliminates the defect association entirely by matching on observable risk features. This suggests task complexity --- not detection asymmetry --- is the primary driver.

== H2: Specifications Reduce Rework

#par(first-line-indent: 0pt)[
  Analysis includes all 88,052 PRs.
]

#figure(
  table(
    columns: 4,
    table.header[Method][Coefficient][_p_-value][Interpretation],
    [Pooled (raw comparison)], [OR = 1.18#super[a]], [< 0.001], [Spec'd PRs have higher rework],
    [Controlled (size + repo)], [0.178], [< 0.001], [Effect persists],
    [Within-author], [+0.012 \[+0.005, +0.019\]], [0.001], [+1.2pp _increase_ in rework rate],
  ),
  caption: [H2: Specifications and rework rates.],
)

Identified from 2,524 authors with treatment variation (out of 4,892 with ≥2 PRs).

*H2 is not supported.* The within-author effect is in the wrong direction: the same author's spec'd PRs have a 1.2 percentage-point higher rework rate than their unspec'd PRs (_p_ = 0.001). The effect is small --- spec'd PRs are 10% more likely to need rework, and the practical difference is about one extra rework event per 83 PRs --- but it is in the wrong direction. Specifications are associated with more rework, not less.

#text(size: 9pt)[#super[a] Odds ratio: spec'd PRs are 1.18× as likely to be reworked as unspec'd PRs.]

== H3: Specification Quality Reduces Defects

#par(first-line-indent: 0pt)[
  H1 and H2 tested specification _presence_ --- whether having any specification artifact matters. H3 and H4 test specification _quality_ --- whether, among PRs that already have specifications, better-written specifications predict better outcomes. This is the stronger version of the SDD claim: not just "write a spec" but "write a _good_ spec." We consider H3 and H4 _exploratory_ rather than confirmatory: the quality measure has limited construct validity (human--LLM agreement _ρ_ = 0.42 on _N_ = 38).
]

Quality is the mean of seven rubric dimensions (described in Section~4.2), each scored 0--100. These dimensions were chosen to align with the quality criteria that SDD tools themselves prescribe (Section~4.2). The scoring is automated with limited human validation (_ρ_ = 0.42 on 38 PRs; Section~4.2) --- a limitation we acknowledge (Section~7). The quality score measures _formal_ specification completeness (are error states described? are acceptance criteria present?) rather than _functional_ correctness (are the right error states described? are the acceptance criteria valid for this domain?). A specification can score highly on every dimension and still specify the wrong behavior.

For PRs whose specification source is a linked GitHub issue, we fetched the issue body and concatenated it with the PR description before scoring, giving the LLM scorer access to the actual pre-implementation specification rather than just the PR summary. 25,209 PRs (28.6% of total) received quality scores across all 119 repositories; 17,973 of these were enriched with linked issue content.

#par(first-line-indent: 0pt)[
  Of the 22,672 quality-scored PRs in SZZ-covered repos, 19,688 remain after restricting to authors with ≥2 PRs and dropping rows with missing controls.
]

#figure(
  table(
    columns: 4,
    table.header[Method][Coefficient][_p_-value][Interpretation],
    [Controlled (size only#super[†])], [−0.002], [0.080], [Approaches significance],
    [Within-author], [−0.0003 \[−0.0007, +0.0001\]], [0.164], [Not significant],
  ),
  caption: [H3: Specification quality and defect-introduction rates.],
)

#text(size: 9pt)[#super[†] Repository adjustments caused the model to fail; this estimate adjusts for PR size only.]

Identified from 2,030 authors with treatment variation.

*H3 is not supported.* The controlled estimate (_p_ = 0.080) approaches significance, which deserves scrutiny. The coefficient is −0.002 on a 0--100 quality scale: a 10-point improvement in specification quality --- roughly the difference between a bare issue title and a structured description with acceptance criteria --- predicts a 2 percentage-point reduction in defect probability. Even if the effect were real, this means a team would need to improve every specification by 10 quality points to prevent one defect in fifty PRs. The within-author estimate, which is more credible because it compares the same developer's work, is smaller and not significant (_p_ = 0.164): a 10-point improvement predicts a 0.3 percentage-point reduction. The quality signal does not hold up under stronger controls and is non-significant across all robustness checks, including subgroups, complexity strata, quality thresholds, and propensity-score-matched samples (Section~5.6).

== H4: Specification Quality Reduces Rework

#figure(
  table(
    columns: 4,
    table.header[Method][Coefficient][_p_-value][Interpretation],
    [Controlled (size + repo)], [−0.000], [0.920], [Quality does not predict rework],
    [Within-author], [+0.000 \[−0.000, +0.000\]], [0.860], [Effectively zero],
  ),
  caption: [H4: Specification quality and rework rates.],
)

Identified from 2,297 authors with treatment variation (same scored subsample as H3).

*H4 is not supported.* Specification quality has no meaningful relationship with rework rates within-author. The coefficient is effectively zero (_p_ = 0.860). The controlled logistic regression is also non-significant (_p_ = 0.920).

== H5: Specifications Constrain AI Scope

#par(first-line-indent: 0pt)[
  Analysis uses log code churn (additions + deletions) as outcome. PRs with zero churn are excluded (these represent missing data rather than true zero-change events). AI detection combines regex pattern matching with structured AI disclosure parsing (Section~4.2), identifying 5,989 AI-tagged PRs --- 2.3× more than co-author tags alone.
]

#figure(
  table(
    columns: 4,
    table.header[Group][Within-author coef][_p_-value][Interpretation],
    [AI-tagged PRs], [+0.120], [0.030], [Spec'd AI PRs are _larger_],
    [Human PRs], [+0.140], [< 0.001], [Spec'd human PRs are _larger_],
    [Interaction (spec × AI)], [+0.000 \[−0.101, +0.102\]], [0.997], [No differential scope constraint],
  ),
  caption: [H5: Specifications and AI-generated code scope.],
)

AI analysis identified from 224 authors with treatment variation; interaction from 366.

*H5 is not supported.* Rather than constraining scope, specifications accompany _larger_ PRs for both AI-tagged (+12.0%) and human-authored (+14.0%) work. The interaction term is effectively zero (_p_ = 0.997): specifications have the same relationship with code churn for AI and human PRs alike --- the same confounding-by-indication pattern seen in H1 and H2. Harder tasks get specs and produce more code.

== Robustness Checks

Twelve additional analyses test whether the null result is an artifact of our primary measures or insufficient controls.

=== Alternative Outcome Measures

In addition to SZZ-traced defects and rework, we test specification effects on two additional outcome measures: _escaped defects_ (PRs whose CI passed but were subsequently followed by a fix or revert) and _strict escaped_ (escaped PRs where the follow-up PR's title explicitly indicates a fix or regression).

#figure(
  table(
    columns: 4,
    table.header[Outcome][Within-author coef][_p_-value][N],
    [SZZ bugs], [+0.014], [0.003], [72,046],
    [Rework], [+0.012], [0.001], [81,647],
    [Escaped], [+0.001], [0.333], [81,647],
    [Strict escaped], [+0.001], [0.108], [81,647],
  ),
  caption: [Alternative outcome measures (within-author LPM).],
)

N reflects within-author estimation restricted to authors with ≥2 PRs; the smaller samples compared to H1 (77,814) and H2 (88,052) reflect this filtering. The SZZ bugs and rework rows reproduce the H1 and H2 findings (included here for comparison). Both show significant positive associations --- specs accompany more defects and more rework, not less --- which we attribute to confounding by indication. The escaped and strict escaped measures, which capture a different class of defect (CI-passing code that subsequently required a fix), are also directionally positive but not significant. No outcome measure shows specifications reducing defects at _p_ < 0.05.

=== Incremental Validity Beyond JIT Features

The JIT defect prediction framework #cite(<kamei2013>) uses 14 code-change features (subsystems touched, file entropy, developer experience, among others) to predict defect-introducing commits. We test whether specification information adds predictive power beyond JIT features on the 61,192 PRs with both complete JIT features and SZZ outcomes.

#figure(
  table(
    columns: 4,
    table.header[Model][Fit#super[a]][AIC#super[b]][Spec variable _p_],
    [JIT features only], [0.078], [44,793], [---],
    [JIT + spec presence], [0.078], [44,786], [0.003],
    [JIT + spec quality#super[†]], [0.082], [---], [0.142],
  ),
  caption: [Does adding specification information improve defect prediction beyond JIT features alone?],
)

#text(size: 9pt)[#super[a] Pseudo _R_#super[2]: how much of the variation in defect rates the model explains (higher = better, 1.0 = perfect). #super[b] AIC: a model comparison score where lower is better; differences < 10 are negligible. #super[†] Scored subset only (19,969 PRs). JIT-only fit on same subset = 0.082.]

Spec presence is statistically significant when added to the JIT model (_p_ = 0.003) but the improvement in predictive accuracy is negligible: the model's explanatory power increases by 0.02 percentage points, and AIC decreases by only 7 points --- neither change would affect predictions in practice. Spec quality does not add a significant increment (_p_ = 0.142). JIT features account for nearly all the predictive power; knowing whether a PR has a specification tells you almost nothing beyond what the code-change metrics already reveal.

=== Individual Quality Dimensions

We test each of the seven specification quality dimensions independently against SZZ bugs and rework (within-author LPM, 19,688 PRs):

#figure(
  table(
    columns: 5,
    table.header[Dimension][→ bugs coef][_p_][→ rework coef][_p_],
    [Outcome clarity], [−0.000], [0.103], [−0.000], [0.792],
    [Error states], [−0.000], [0.262], [+0.000], [0.307],
    [Scope boundaries], [−0.000], [0.053], [−0.000], [0.220],
    [Acceptance criteria], [−0.000], [0.165], [−0.000], [0.454],
    [Data contracts], [−0.000], [0.489], [+0.000], [0.603],
    [Dependency context], [+0.000], [0.640], [+0.000], [0.140],
    [Behavioral specificity], [−0.000], [0.083], [+0.000], [0.822],
  ),
  caption: [Individual quality dimensions vs. defects and rework (within-author LPM).],
)

No individual quality dimension is statistically significant for defects at _p_ < 0.05. Every coefficient rounds to zero. Scope boundaries (_p_ = 0.053) and behavioral specificity (_p_ = 0.083) are the closest, but neither would remain significant after correcting for running seven tests simultaneously#footnote[Bonferroni correction: when testing multiple hypotheses at once, the significance threshold is divided by the number of tests to account for the increased chance of a false positive. With 7 tests at α = 0.05, the corrected threshold is _p_ < 0.007. This is conservative --- it may miss real effects --- but it prevents over-interpreting results that are significant by chance alone.] (_p_ < 0.007 required). The rework column is even starker: no dimension shows any relationship with rework. No individual quality dimension produces a practically meaningful reduction in either defects or rework.

=== Validated Quality Dimensions Only

Our LLM quality rubric was validated against human ratings on 38 PRs (Section~4.2). Four of seven dimensions showed significant human--LLM agreement: behavioral specificity (_ρ_ = 0.45), scope boundaries (_ρ_ = 0.43), dependency context (_ρ_ = 0.40), and outcome clarity (_ρ_ = 0.39). Two dimensions showed weak agreement: acceptance criteria (_ρ_ = 0.17) and error states (_ρ_ = 0.22). If measurement noise in the unvalidated dimensions attenuates the quality coefficient toward zero (classical errors-in-variables bias), restricting to validated dimensions should recover a larger effect.

#figure(
  table(
    columns: 5,
    table.header[Quality composite][→ bugs coef][_p_][→ rework coef][_p_],
    [All 7 dimensions], [−0.0003], [0.164], [+0.0000], [0.860],
    [4 validated dimensions only], [−0.0002], [0.184], [+0.0000], [0.913],
    [3 unvalidated dimensions only], [−0.0003], [0.158], [+0.0001], [0.663],
  ),
  caption: [Validated vs. unvalidated quality dimension composites.],
)

All three composites are non-significant for defects: all 7 dimensions (_p_ = 0.164), 4 validated dimensions (_p_ = 0.184), and 3 unvalidated dimensions (_p_ = 0.158). The validated and unvalidated composites perform similarly, consistent with the quality score capturing noise rather than a real defect-predictive signal. For rework, all three composites produce coefficients indistinguishable from zero.

=== Repo-Level Analysis

We also aggregate to the repository level (_N_ = 98 repos with ≥50 PRs) and test whether repos with higher specification rates have lower defect or rework rates.

#figure(
  table(
    columns: 3,
    table.header[Comparison][Correlation#super[a]][_p_-value],
    [Spec rate vs. defect rate], [−0.113], [0.268],
    [Spec rate vs. rework rate], [−0.047], [0.643],
  ),
  caption: [Repo-level specification rate vs. outcome rates.],
)

#text(size: 9pt)[#super[a] Spearman rank correlation: +1 means perfect positive relationship, −1 means perfect negative, 0 means no relationship. Values near zero indicate repos that spec more do not have meaningfully different defect or rework rates.]

At the repository level, specification rate has no relationship with either defect rate (correlation = −0.11, _p_ = 0.27) or rework rate (correlation = −0.05, _p_ = 0.64). Neither is significant. Repos that write more specs do not have fewer bugs or less rework.

=== Subgroup Analysis

SDD tools are marketed primarily for AI-assisted workflows. We test whether the null result holds across human-only PRs, AI-tagged PRs, and repos stratified by AI adoption rate. As in all analyses, bot PRs are excluded.

#figure(
  table(
    columns: 5,
    table.header[Subgroup][→ bugs coef][_p_][→ rework coef][_p_],
    [All non-bot PRs (88,052)], [+0.014], [0.003], [+0.012], [0.001],
    [Human-only, no AI (82,063)], [+0.015], [0.003], [+0.011], [0.004],
    [AI-tagged, non-bot (5,989)], [+0.011], [0.424], [+0.010], [0.399],
    [Zero-AI repos (3,562)], [−0.016], [0.377], [−0.033], [0.014],
    [Low-AI repos (51,877)], [+0.019], [0.001], [+0.009], [0.061],
    [High-AI repos (32,613)], [+0.010], [0.185], [+0.018], [0.003],
  ),
  caption: [Subgroup analysis: specification effects across populations.],
)

One subgroup breaks the pattern. In repositories with no AI-tagged PRs, specifications are associated with _less_ rework (−3.3pp, _p_ = 0.014). This is the only result in the dataset consistent with the SDD rework claim, and it appears precisely where AI involvement is absent --- in purely human workflows. The finding comes from a small subsample (3,562 PRs), is one of six subgroup tests, and does not remain significant after correcting for running six tests simultaneously. We note it as suggestive but not conclusive. That the protective effect appears only where AI is absent, not where AI is present, is itself inconsistent with the SDD vendor claim that specifications are _most_ valuable for AI-assisted work.

For all other subgroups, the pattern holds. For human-authored PRs, specs are associated with _more_ defects and _more_ rework --- the confounding-by-indication pattern. For AI-tagged PRs, the coefficients are positive but not significant (_p_ = 0.42 for defects, _p_ = 0.40 for rework). The null holds whether a repo has low or high AI adoption.

=== High-Quality Specs Only

A likely reviewer objection is that our `specd` measure is too loose --- that linked Jira tickets are not "real" specifications in the SDD sense, and only high-quality structured specs should show the benefit. We test this directly by restricting to top-quartile (quality score ≥ 58) and top-decile (≥ 66) specs. Quality thresholds are computed from the scored subset's distribution (median = 48, p75 = 58, p90 = 66).

#figure(
  table(
    columns: 4,
    table.header[Test][→ bugs coef][_p_][Identifying authors],
    [Top-quartile specs vs. all others], [−0.007], [0.190], [1,370],
    [Top-decile specs vs. all others], [−0.005], [0.545], [751],
    [High-quality vs. NO spec (low-quality excluded)], [−0.006], [0.348], [1,117],
    [AI-tagged + high-quality spec], [−0.005], [0.790], [175],
  ),
  caption: [High-quality specification thresholds vs. defect rates.],
)

No quality threshold produces a significant defect reduction. The top-quartile result (−0.7pp, _p_ = 0.190) is not significant. The top-decile result is weaker still (−0.5pp, _p_ = 0.545) --- the opposite of what a dose-response relationship would predict. The cleanest comparison --- high-quality specs vs. PRs with _no spec at all_, excluding low-quality specs entirely --- is also non-significant (_p_ = 0.348). Top-quartile specs do not reduce rework either (+0.9pp, _p_ = 0.100).

The AI + high-quality spec result (_p_ = 0.790) is the closest test to the agentic SDD workflow vendors are selling. There is no signal: the coefficient is near zero and identified from 175 authors.

We also test a three-tier dose-response by splitting PRs into three mutually exclusive groups: high-quality specs (top-quartile scored PRs), any other spec (spec'd but below top-quartile or unscored), and no spec at all. If specification quality matters, the tiers should show a monotonic gradient.

#figure(
  table(
    columns: 5,
    table.header[Tier][Raw bug rate][→ bugs coef][_p_][→ rework coef \ _p_],
    [High-quality spec (_N_ = 5,253)], [12.6%], [−0.004], [0.566], [+0.017 \ _p_ = 0.006],
    [Any other spec (_N_ = 16,505)], [14.5%], [+0.020], [< 0.001], [+0.010 \ _p_ = 0.012],
    [No spec (_N_ = 56,056)], [12.0%], [---], [ref.], [--- \ ref.],
  ),
  caption: [Three-tier dose-response. PRs are split into: high-quality specs (top-quartile quality score ≥ 58), all other spec'd PRs (below top-quartile or unscored), and PRs with no specification artifact. If specification quality matters, defect and rework rates should decrease from bottom to top. Coefficients from within-author analysis; "no spec" is the reference group. Bug analysis restricted to 103 SZZ-covered repos.],
)

The expected gradient does not appear. The best specs show a raw defect rate (12.6%) indistinguishable from no spec (12.0%), while ordinary specs show the highest rate (14.5%) --- the confounding-by-indication pattern. Within-author, high-quality specs produce a non-significant −0.4pp reduction in defects (_p_ = 0.566). Ordinary specs produce a significant +2.0pp _increase_ (_p_ < 0.001). Neither tier reduces rework: both are associated with _more_ rework than no spec. The direct comparison of high-quality vs. ordinary specs approaches significance for defects (−1.5pp, _p_ = 0.066) but the rework difference is not significant (_p_ = 0.180). The pattern is consistent with confounding, not a quality gradient: developers write better specifications for harder tasks, and harder tasks produce more defects regardless.

=== JIT Features as Primary Controls

A reviewer concern is that size controls (log additions, deletions, files) are insufficient --- the JIT defect prediction framework #cite(<kamei2013>) captures task complexity dimensions (entropy, file age, developer experience) that may confound the specification–defect association. We re-run H1 and H2 with 13 JIT features as additional controls alongside size controls (subsystem experience excluded for zero variance).

#figure(
  table(
    columns: 4,
    table.header[Test][Size controls only][+ JIT controls][Change],
    [H1: specs → bugs (coef)], [+0.014 (_p_ = 0.003)], [+0.006 (_p_ = 0.229)], [−55%],
    [H2: specs → rework (coef)], [+0.012 (_p_ = 0.001)], [+0.009 (_p_ = 0.024)], [−23%],
  ),
  caption: [JIT features as primary controls.],
)

For H1, the spec coefficient drops 55% and loses significance when JIT features are added, indicating that much of the apparent spec--defect association is explained by task complexity dimensions that size alone does not capture. For H2, the coefficient drops 23% but remains significant: specifications remain associated with more rework even after controlling for JIT risk features. The within-author spec coefficient in the JIT-controlled model (+0.006, _p_ = 0.229) is not significant for defects.

Note a discrepancy between this result and propensity score matching (below): the JIT-controlled regression finds specifications still predict more rework (_p_ = 0.024), while PSM finds no significant rework difference (_p_ = 0.146). This inconsistency likely reflects functional form: JIT regression assumes a linear relationship between complexity features and rework, while PSM compares PRs at the same point in the complexity distribution without imposing linearity. If the relationship between complexity and rework is nonlinear --- as one would expect, since very complex PRs produce disproportionate rework --- PSM handles this better. Either way, the rework association is directionally _positive_ (more rework with specs, not less) under both methods. The direction never supports the SDD claim.

=== Propensity Score Matching

As an alternative to regression-based controls, we directly pair each spec'd PR with an unspec'd PR that has a similar complexity profile#footnote[Propensity score matching: we first build a model predicting which PRs receive specifications based on their JIT features, then pair each spec'd PR with an unspec'd PR that had the same predicted probability of being spec'd. This ensures we compare like with like --- a complex spec'd PR is matched to a similarly complex unspec'd PR, not to a trivial one-liner. We use nearest-neighbor matching with a caliper (maximum allowed distance) of 0.05 standard deviations to ensure match quality.]. If confounding by indication is the explanation --- developers spec hard tasks, and hard tasks produce defects --- then comparing spec'd PRs to equally hard unspec'd PRs should eliminate the association.

#figure(
  table(
    columns: 4,
    table.header[Outcome][Spec'd (matched)][Unspec'd (matched)][Difference],
    [Defect rate (17,375 pairs)], [14.7%], [15.2%], [−0.6pp (_p_ = 0.133)],
    [Rework rate (19,648 pairs)], [15.2%], [14.7%], [+0.5pp (_p_ = 0.146)],
  ),
  caption: [Propensity score matching results.],
)

All 16 covariates are well-balanced after matching (no meaningful differences between the spec'd and unspec'd groups on any complexity measure). For defects, the matched spec'd and unspec'd defect rates are indistinguishable --- propensity score matching eliminates the raw association entirely. For rework, the result is the same: after matching on observable risk features, the rework difference is +0.5 percentage points and not significant (_p_ = 0.146). Both the defect and rework associations are explained by the JIT risk profile of the tasks that receive specifications.

=== Temporal Analysis: The SDD Era

Specification adoption in our dataset is not uniform over time. Monthly specification rates rose from 23.7% in April 2025 to 31.3% by March 2026, with AI-tagged PR rates rising from 0.3% to 9.8% over the same period. If SDD tools are driving specification adoption and those specifications improve outcomes, the effect should be visible in the most recent data --- the period closest to production SDD usage.

We restrict the within-author analysis to the most recent three months of the observation window (January--March 2026), when specification rates are highest (29.3%) and AI adoption is most prevalent (8.8%):

#figure(
  table(
    columns: 5,
    table.header[Test][Recent 3 months coef][_p_][Full dataset coef][_p_],
    [Specs → SZZ bugs], [+0.004], [0.435], [+0.014], [0.003],
    [Specs → rework], [+0.016], [0.001], [+0.012], [0.001],
    [AI + specs → bugs], [+0.003], [0.822], [---], [---],
    [AI + specs → rework], [+0.016], [0.212], [---], [---],
    [Spec × AI interaction (H5)], [+0.011], [0.861], [+0.000], [0.997],
  ),
  caption: [Temporal analysis: recent three months vs. full dataset.],
)

The pattern is consistent. In the period of highest SDD adoption, specifications are associated with more rework (+1.6pp, _p_ = 0.001) and directionally more defects (+0.4pp, _p_ = 0.435, not significant). For AI-tagged PRs, specs have no effect in either direction. The H5 scope-constraint interaction is null in both the full dataset and the recent window. The null result is not a historical artifact --- it persists in the data most representative of the SDD era.

A caveat on the temporal data: SZZ-traced defect rates for the most recent months are likely underestimates, because defects introduced recently may not yet have been fixed (and therefore cannot be traced back to their introducing commits). This right-censoring affects absolute defect rates but not the _relative_ comparison between spec'd and unspec'd PRs within the same time window, which is the quantity of interest.

=== Complexity Stratification

A likely objection is that specifications should help most on the hardest tasks --- where ambiguity is highest and the cost of getting it wrong is greatest. We stratify by the top 20% of five complexity measures: code churn (additions + deletions), lines added, files changed, change entropy, and composite JIT risk (rank-normalized mean of 8 JIT features). For each stratum, we test both specification presence (H1/H2) and quality (H3/H4).

#figure(
  table(
    columns: 5,
    table.header[Stratum][→ bugs coef][_p_][→ rework coef][_p_],
    [Top 20% churn], [+0.040], [< 0.001], [+0.051], [< 0.001],
    [Bottom 80% churn], [+0.007], [0.114], [+0.005], [0.238],
    [Top 20% entropy], [+0.024], [0.057], [+0.039], [< 0.001],
    [Bottom 80% entropy], [+0.000], [0.986], [+0.005], [0.201],
    [Top 20% JIT risk], [+0.028], [0.028], [+0.039], [< 0.001],
    [Bottom 80% JIT risk], [+0.002], [0.713], [+0.008], [0.059],
  ),
  caption: [Specification effects stratified by task complexity (within-author LPM).],
)

The result is the opposite of what the SDD hypothesis predicts. On the hardest tasks, specifications are associated with _more_ defects and _more_ rework --- the confounding-by-indication signal is _strongest_ where specs should help most. On simpler tasks, the association largely disappears (coefficients near zero, not significant). Specification quality (H3/H4) is null across all strata: no complexity stratum shows quality predicting fewer defects or less rework at _p_ < 0.05.

=== Issue-Linked Specifications

A further objection is that our `specd` measure includes weak signals (Jira ticket IDs, template sections). We restrict to the 18,600 PRs that link to a GitHub issue --- the closest proxy for a pre-implementation specification. For issue-linked PRs with quality scores, we also fetched the linked issue body and scored the combined content, giving the quality rubric access to the actual specification rather than just the PR summary.

#figure(
  table(
    columns: 5,
    table.header[Test][→ bugs coef][_p_][→ rework coef][_p_],
    [Issue-linked vs no spec], [+0.011], [0.037], [+0.014], [< 0.001],
    [AI + issue vs AI + no spec], [+0.014], [0.436], [+0.017], [0.192],
    [Human + issue vs human + no spec], [+0.012], [0.035], [+0.013], [0.002],
    [Top-20% quality issue vs no spec], [−0.007], [0.363], [+0.019], [0.007],
    [Issue-linked vs ticket-only], [+0.007], [0.637], [+0.026], [0.025],
  ),
  caption: [Issue-linked specifications vs. other operationalizations (within-author LPM).],
)

Issue-linked specifications show the same pattern as all other operationalizations: the association with defects is positive (wrong direction) or null, never protective. Even the cleanest pre-implementation proxy --- top-20% quality GitHub issues --- shows no defect reduction (_p_ = 0.363). Issue-linked PRs are associated with _more_ rework than ticket-only specs (+2.6pp, _p_ = 0.025), likely because visible issue threads create accountability and invite scrutiny. For AI-tagged PRs with issue-linked specs, the coefficients are positive but not significant for both defects (_p_ = 0.436) and rework (_p_ = 0.192): specification quality does not differentially benefit AI-generated code.

=== Summary

The null result holds across nearly every angle we can construct from this dataset: four outcome measures, two predictive frameworks (LPM and JIT), propensity score matching on JIT risk profiles, seven quality dimensions, two units of analysis (PR-level and repo-level), six subgroup cuts, five complexity strata, issue-linked specifications with enriched content, multiple quality thresholds, dose-response tests, a specification × AI quality interaction, and temporal restriction to the period of highest SDD adoption. When JIT features are added as controls, the H1 spec coefficient drops 55% and loses significance; propensity score matching eliminates the association entirely. The one exception is zero-AI repositories, where specifications are associated with less rework (−3.3pp, _p_ = 0.014) --- discussed in Section~5.6.5. Across twelve robustness checks, no specification measure robustly predicts fewer defects under any operationalization.

= Discussion

== Confounding by Indication

The pattern across all five hypotheses is identical: unadjusted analysis suggests specifications accompany worse outcomes; within-author analysis attenuates but does not eliminate the reversed association; propensity score matching on JIT features eliminates it entirely, confirming confounding by indication #cite(<salas1999>). Developers rationally invest specification effort in proportion to task complexity. Harder tasks receive specifications _and_ produce more defects --- the specification does not cause the defects.

JIT risk feature profiles confirm this directly. Spec'd PRs have more lines added (1.8×), touch older files (2.3×), and involve more prior developers (1.3×) than unspec'd PRs. Notably, spec'd PR authors have _less_ experience than unspec'd PR authors (median 64 vs. 116 prior commits) --- less experienced developers spec more, not less, consistent with specifications being a support mechanism for harder tasks.

Confounding by indication complicates interpretation in both directions. The within-author null is consistent with two readings: specifications genuinely have no effect, or specifications have a small positive effect that residual task selection conceals. We cannot distinguish these with observational data. What we can say is that the within-author estimates are not merely insignificant --- they are _directionally reversed_ across most tests, and propensity score matching eliminates both the defect and rework associations entirely. Any protective effect, if it exists, is smaller than our study can detect.

Spec'd PRs take substantially longer to merge (median 29.4 hours vs. 11.6 hours for unspec'd), but this additional review time does not translate into fewer defects --- the same confounding pattern. AI-tagged PRs receive less review scrutiny despite a higher base defect rate (16.7% vs. 12.2%), a separately concerning finding.

== Why Specifications May Not Prevent Defects

One possible explanation for the null result is structural: for a specification to prevent a defect, every link in a causal chain must hold:

+ The developer must correctly identify the problem.
+ The developer must know in advance what will solve the problem.
+ The developer must know exactly how to execute the solution.
+ The developer must be able to perfectly describe the solution in natural language.
+ The natural language description must not be misinterpreted by the AI.
+ The AI must not introduce bugs in its implementation.
+ The specification must not have substantial omissions --- the developer must specify what they do not yet know they do not know.

Each condition is individually uncertain. Together the probability of the full chain succeeding diminishes rapidly. Defects arise precisely where human understanding is incomplete --- and specifications are written by the same humans whose incomplete understanding produces the defects. This chain explains not only _why_ we observe a null result, but why a large effect should not be expected in principle.

Specifications are, in effect, a lossy compression of code. The developer compresses their understanding of the solution into natural language, and the AI decompresses it back into code. The only specification that does not lose information in the round trip is the code itself. We already have a perfectly unambiguous language for specifying how to solve a problem --- it is called a programming language. Specifications may be valuable as a _human-readable summary_ of intent, but they cannot be more precise than the code they describe, and any imprecision creates room for defects.

SDD vendors conflate _directing_ the AI (telling it what to build) with _ensuring quality_ (fewer defects, less rework). Specifications may be effective at direction --- a structured task description is better than a vague prompt. But an agent faithfully executing a spec will reproduce every gap, ambiguity, and wrong assumption in that spec. The specification tells the AI _what_ to build. It does not tell the AI _what it forgot to specify_. Direction is not quality.

== Vendor Evidence

No SDD tool vendor has published empirical evidence for the quality claims tested here. The evidence base consists of first-principles reasoning and developer testimonials. GitHub describes Spec Kit as "an experiment" #cite(<speckit2025>) and publishes no effectiveness data. Third-party evaluations are negative: Böckeler found Spec Kit's overhead "overkill for the size of the problem" #cite(<fowler2025>); Eberhardt found it roughly ten times slower than iterative development #cite(<scottlogic2025>). Notably, none of the 119 repositories in our dataset show evidence of SDD tooling --- a text search for `.specify/`, `.speckit/`, `.kiro/`, and `spec-kit` across 100,247 PRs returns zero matches. GitHub, Amazon, and other SDD vendors have the data and engineering resources to conduct controlled evaluations of their products. The absence of published evaluations alongside specific quality claims represents a gap that controlled experiments could close.

We measure the _kind_ of specification content that SDD tools claim to improve upon, scored on the same quality dimensions those tools prescribe. If the tool's format itself is the active ingredient --- something beyond the seven quality dimensions we measure --- that would be a testable claim that vendors have not tested.

SDD tooling imposes real costs: specification-writing time, process overhead, organizational change. We do not argue that thinking about requirements is wasted effort. We argue that the _products_ claiming to reduce defects through specification artifacts have not yet demonstrated that they do --- and neither this study nor any other has found evidence for those claims.

= Threats to Validity

== Construct Validity

Three gaps separate what we measure from what SDD vendors claim.

*We detect specification artifacts, not specification processes.* Our classifier flags linked issues, structured descriptions, and referenced design documents. A linked Jira ticket created to satisfy a process requirement counts the same as a detailed design document written after iterative refinement. If the benefit comes from the _thinking_ rather than the _artifact_, our measure is too coarse. Two observations partially address this concern. First, the within-author design compares the same developer's spec'd and unspec'd work, controlling for that person's consistent habits. Second, H3 and H4 test quality _within_ spec'd PRs on seven SDD-aligned dimensions. If deeper thinking produced better artifacts, those artifacts should predict better outcomes. They do not. The remaining objection --- that process depth helps through a mechanism invisible in the artifact itself --- is difficult to test with any observational design.

*We test organic specifications, not SDD tool output.* Spec Kit generates structured documents through a guided workflow and feeds them to a coding agent. A linked GitHub issue is not the same thing. Our operationalization is the broadest reasonable proxy available, but it may miss whatever specific mechanism the tools provide. The high-quality spec subsample (top-quartile, scored on the dimensions SDD tools prescribe) is the closest approximation. It too shows no robust effect.

*We cannot observe agentic workflows directly.* Even for AI-tagged PRs with specifications, we do not know whether the spec was actually used as input to an agent or just written for human consumption. True agentic SDD --- where the agent reads the spec, generates code from it, and validates against it --- is not observable in our data. The 175-author AI + high-quality spec subsample is the closest proxy we have.

== Internal Validity

*Defect detection is noisy.* The SZZ algorithm traces fix commits back to their introducing commits via `git blame`. da Costa et al. #cite(<dacosta2017>) found that basic SZZ misattributes 46--71% of bug-introducing changes. We use the basic variant for implementation simplicity across 103 repositories. This noise is substantial. We initially assumed it to be non-differential with respect to specification status, but this assumption deserves scrutiny: spec'd PRs have 1.8× more lines added and touch older files (2.3×), creating more `git blame` targets per commit. If SZZ misattributes more for larger changesets, the measurement error could be differential --- inflating the apparent defect rate for spec'd PRs. Two observations partially mitigate this concern: the rework measure (H2) does not depend on SZZ and shows the same directional pattern, and propensity score matching on size and complexity features eliminates the defect association entirely. Nonetheless, the reversed H1 association (specs predict _more_ bugs) should be interpreted cautiously --- confounding by indication and differential SZZ noise are difficult to disentangle.

*Quality scoring is automated and unvalidated.* Our LLM-based rubric (Claude Haiku) measures _formal_ quality --- whether the text contains outcome descriptions, error states, and acceptance criteria --- not _functional_ quality. A spec can score highly and still describe the wrong behavior. The rubric's seven dimensions align with what SDD tools prescribe, which means our scoring shares whatever blind spots those templates have. The scoring was applied only to PRs with substantial description text, creating a non-random subsample.

*AI detection relies on voluntary tagging.* We identify AI-assisted PRs via self-reported markers in the PR body. Developers who use AI without attribution are invisible. The false-negative rate is unknown. If many untagged PRs involved AI, the H5 comparison would be diluted toward the null.

*The control group may be contaminated.* Some "unspec'd" PRs may have had specifications shared verbally, in Slack, or in external tools. This would attenuate any treatment effect. However, if informal specification produces equivalent outcomes, the SDD value proposition still fails: vendors claim the _tooling and artifact_ add value beyond what any structured thinking would provide.

*Confounding by indication* is the primary threat. Developers spec hard tasks. Hard tasks produce defects. The within-author design addresses this by comparing each developer to themselves, but within-author task selection remains possible: if an author consistently specs their hardest work and skips specs on easy tasks, the comparison is biased. The JIT-controlled models and propensity score matching (both in Section~5.6) address this further, and both confirm the null for defects.

*Time-varying confounding.* An author's skill, tooling, and project context may change over the observation period. The within-author estimator assumes these are stable.

== External Validity

*Open-source only.* All 119 repositories are open-source. SDD tools target commercial teams with product managers, QA processes, and sprint planning. The specification practices and defect economics may differ.

*Convenience sample.* Repositories were not randomly selected. Results cannot be generalized beyond the sample.

*Pre-agentic era.* Most PRs predate widespread agentic AI coding tools. The dataset contains 5,989 AI-tagged PRs (after bot exclusion) --- the closest available proxy for agentic workflows. Within this subsample, specs show no effect on defects (_p_ = 0.424) or rework (_p_ = 0.399). We cannot rule out that true agentic workflows would produce different results --- but that is itself an untested claim.

== Conclusion Validity

*Multiple comparisons.* We test five hypotheses without correction. At α = 0.05, approximately 0.25 false positives are expected by chance.

*Power for AI interaction.* The scope-constraint interaction (H5) is identified from 366 authors with variation in both specification and AI use. The null result (_p_ = 0.997) is not a power issue --- the coefficient is effectively zero.

*No pre-registration.* The five hypotheses, operationalizations, quality thresholds, and robustness checks were not pre-registered. All analyses are post-hoc. We cannot rule out that alternative analyst choices (different quality thresholds, different rework definitions, different control sets) would produce different results. The ten robustness checks are intended to address this concern by showing stability across specifications, but a pre-registered confirmatory study would provide stronger evidence.

= Conclusion

Spec-driven development tools make five specific, testable claims: specifications reduce defects (H1), prevent rework (H2), improve outcomes through higher-quality requirements (H3, H4), and constrain AI-generated code scope (H5). We test the claims using the best available proxy --- purpose-built SDD tool data is not publicly available --- analyzing 88,052 pull requests across 119 open-source repositories, where specification artifacts are scored on the same quality dimensions that SDD tools prescribe, comparing each developer's spec'd work to their own unspec'd work.

None of the five hypotheses are supported under any operationalization. The unadjusted association between specifications and defects is reversed (specifications accompany _more_ defects); after within-author controls, the most parsimonious interpretation is confounding by indication. Specification quality does not predict fewer defects (_p_ = 0.164) or less rework (_p_ = 0.860). Specifications do not constrain AI-generated code scope (_p_ = 0.997). Across nearly all twelve robustness checks, the null holds: for human-authored PRs and AI-tagged PRs; for simple tasks and complex tasks; for linked GitHub issues and ticket references; for top-quartile and top-decile quality specifications; for recent temporal windows and the full dataset; and after propensity score matching on observable risk features. Specification presence proxies for task complexity, not for quality improvement.

One exception merits attention: in repositories with zero AI adoption, specifications are associated with significantly less rework (−3.3pp, _p_ = 0.014). This is the only subgroup where specifications show a protective effect, and it appears precisely where AI is absent. If this finding replicates, it suggests specifications may benefit human-only workflows through accountability and review visibility --- but not the AI-assisted workflows that SDD tools are designed for.

Three important caveats bound these findings. First, we test organic specification artifacts, not SDD tool-generated specifications --- this construct gap is acknowledged and substantial (Section~7). Second, SZZ defect tracing has substantial measurement noise (46--71% misattribution), which attenuates true effects toward zero. Third, our open-source convenience sample may not generalize to commercial teams. Whether purpose-built SDD tooling would produce different results on commercial codebases remains an open question --- but it is a question vendors can answer with the data they already have.

Specifications may still have value --- but not the value being claimed. A specification is an auditable record of what the code was _meant_ to do, which is valuable for compliance, debugging, and onboarding regardless of whether it prevents defects. Specifications may improve developer efficiency by enabling task batching: a developer can queue structured work for an AI agent and shift attention elsewhere, reclaiming time without improving code quality. Specifications create accountability, making it harder for defects to pass unchallenged through review --- and the zero-AI rework finding suggests this accountability mechanism may genuinely reduce rework in human-reviewed workflows. These are real benefits. They are not "fewer defects" in the aggregate, and the evidence does not support the claim that specifications are most valuable when AI implements the code.

== Data Availability

The dataset, analysis scripts, and replication package supporting this study are openly available on Zenodo at https://doi.org/10.5281/zenodo.19415187 under a CC-BY 4.0 license. The repository contains all source data, the full 11-step analysis pipeline, and a single-command replication script (`python3 replicate-results.py`) that reproduces every result reported in this paper. Source code is also available at `github.com/brennhill/delivery-gap-research`.

#pagebreak()

= References

#set par(first-line-indent: 0pt, hanging-indent: 0.5in)

#bibliography(style: "apa", title: none,
  "ssrn-sdd-refs.yml",
)
