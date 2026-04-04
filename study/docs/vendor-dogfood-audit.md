# SDD Vendor Dogfood Audit

Do SDD tool vendors use their own tools? Do they publish evidence that their tools work?

This document audits public repositories and published materials from GitHub (Spec Kit) and Amazon (Kiro) to determine whether either vendor (a) uses their SDD workflow in their own projects, or (b) has published empirical evidence for their quality claims.

**Audit date:** 2026-04-03
**Methodology:** GitHub API queries for `.specify/` and `.kiro/` directories, git history analysis, `.gitignore` inspection, documentation review, web search for published metrics.

---

## GitHub Spec Kit

### What Spec Kit claims

Spec Kit prescribes a `.specify/` directory containing structured specification files that guide AI code generation. The GitHub blog promises "less guesswork, fewer surprises, and higher-quality code" ([source](https://github.blog/ai-and-ml/generative-ai/spec-driven-development-with-ai-get-started-with-a-new-open-source-toolkit/)).

### Does GitHub use Spec Kit in their own repos?

**No.** We checked 10 GitHub-org public repositories for `.specify/` directories via the GitHub API. Results:

| Repo | URL | `.specify/` present | Details |
|------|-----|---------------------|---------|
| github/spec-kit | https://github.com/github/spec-kit | **No** | The tool itself does not use its own spec-driven workflow for development. Top-level tree contains `src/`, `templates/`, `tests/`, `docs/` — no `.specify/` directory. |
| github/gh-aw-firewall | https://github.com/github/gh-aw-firewall | **Partial** | Contains `.specify/prd.md` and `.specify/progress.txt`. The PRD references ~35 spec files at `.specify/specs/*/spec.md` — but those files do not exist. Only 1 of ~35 tasks is marked complete. See detailed analysis below. |
| github/gh-aw | https://github.com/github/gh-aw | **No** | |
| github/docs | https://github.com/github/docs | **No** | |
| github/copilot | https://github.com/github/copilot | **No** | May be private |
| github/copilot-docs | https://github.com/github/copilot-docs | **No** | |
| github/copilot-chat | https://github.com/github/copilot-chat | **No** | May be private |
| github/actions-runner | https://github.com/github/actions-runner | **No** | |
| github/cli | https://github.com/github/cli | **No** | |
| github/codeql | https://github.com/github/codeql | **No** | |

### gh-aw-firewall: detailed analysis

The only GitHub-org repo with any `.specify/` content is `github/gh-aw-firewall` (a small agentic-workflows firewall tool, ~51 stars). Investigation reveals this is not meaningful Spec Kit adoption:

- **`.specify/prd.md`**: A product requirements document listing ~35 tasks with spec file references (e.g., `.specify/specs/002-minimatch-redos-vuln/spec.md`). Only 1 task is checked `[x]`; the rest are `[ ]`.
- **`.specify/specs/` does not exist**: Git history (`git log --all -- .specify/specs`) returns zero commits. The referenced spec files were never created on any branch.
- **How it got there**: The PRD was committed as part of PR #1152 ("fix(deps): resolve minimatch ReDoS and ajv vulnerabilities") on 2026-03-05. It was a side artifact of an AI agent session — the agent created the PRD to track its work plan and committed it alongside the actual dependency fix.
- **Not the Spec Kit workflow**: The current Spec Kit CLI uses `$REPO_ROOT/specs/` (not `.specify/specs/`) as its specs directory. The repo's branches follow `claude/*` and `copilot/*` naming, not the `NNN-feature-name` pattern that Spec Kit's branching convention produces.

### Are specs gitignored?

**No.** We verified that Spec Kit is designed to have `.specify/` version-controlled:

- **Spec Kit's `.gitignore`** (in the spec-kit repo itself) only ignores:
  - `.specify/extensions/.cache/`
  - `.specify/extensions/.backup/`
  - `.specify/extensions/*/local-config.yml`
  - It does **not** ignore `.specify/` or `.specify/specs/`
- **Spec Kit documentation**: No page in the README, `spec-driven.md` methodology doc, or CLI source recommends adding `.specify/` to `.gitignore`
- **`specify init` command**: Source code inspection (in `src/specify_cli/__init__.py`) confirms init creates `.specify/integration.json`, `.specify/init-options.json`, copies templates — but never writes a `.gitignore` entry
- **gh-aw-firewall's `.gitignore`**: Contains standard Node.js/IDE patterns plus `design-docs/`, `reports/`, `release/`. No `.specify` entries.

The missing specs are not hidden — they were never created.

### Broader adoption

- GitHub code search for `.specify/spec.md` across all of GitHub: ~1,120 repos. These are overwhelmingly small/hobby projects (novel-writer, physics sandbox, todo apps, dashboard apps). No major open-source project or production codebase was found using Spec Kit.
- 85,000+ stars on the spec-kit repo, but stars do not equal usage.
- ~57 repos with `.speckit/spec.md` files (an older convention).
- Community discussion #1482 (January 2026) raised maintenance concerns: "22 PRs opened and exactly zero commits" in the prior month.

### Published effectiveness data

**None.** GitHub has published no data on defect rates, rework rates, productivity improvements, or any measured outcome from Spec Kit usage. The official blog post, documentation, and repository contain no quantitative claims. Visual Studio Magazine (September 2025) quotes the team calling it "an experiment" with "a lot of questions" still to answer ([source](https://visualstudiomagazine.com/articles/2025/09/16/github-spec-kit-experiment-a-lot-of-questions.aspx)).

### Third-party evaluations

- **Böckeler (Martin Fowler's site)**: Never completed the full implementation. Found specs "repetitive and tedious to review." Concluded: "in the same time it took me to run and review the spec-kit results I could have implemented the feature with plain AI-assisted coding." ([source](https://martinfowler.com/articles/exploring-gen-ai/sdd-3-tools.html))
- **Eberhardt (Scott Logic)**: Found Spec Kit roughly ten times slower than iterative development. Produced 689 LOC + 2,577 lines of markdown overhead. Called it "reinvented waterfall." ([source](https://blog.scottlogic.com/2025/11/26/putting-spec-kit-through-its-paces-radical-idea-or-reinvented-waterfall.html))

### Personnel

Den Delimarsky, the Principal Product Manager who created Spec Kit, left GitHub for Anthropic in late 2025/early 2026.

---

## Amazon Kiro

### What Kiro claims

Kiro prescribes a `.kiro/` directory containing `specs/` subdirectories with structured `requirements.md`, `design.md`, and `tasks.md` files. Kiro claims specs provide "a North Star to guide the work of the agent, allowing it to take on larger tasks without getting lost" ([source](https://kiro.dev/blog/kiro-and-the-future-of-software-development/)) and enable "fewer iterations and higher accuracy" ([source](https://kiro.dev/blog/from-chat-to-specs-deep-dive/)).

### Does Amazon use Kiro specs in their own repos?

**Minimally.** We checked 17 AWS production repositories and ~30 Kiro-related sample repositories for `.kiro/` directories.

#### Production AWS repos

| Repo | URL | `.kiro/` present | Details |
|------|-----|-----------------|---------|
| aws/aws-sdk-java-v2 | https://github.com/aws/aws-sdk-java-v2 | **Steering only** | Has `.kiro/settings` and `.kiro/steering` (7 steering docs for coding guidelines). No specs. |
| aws/graph-explorer | https://github.com/aws/graph-explorer | **Steering only** | Has `.kiro/settings`, `.kiro/steering`, `.kiro/skills`. No specs. |
| awslabs/aws-solutions-constructs | https://github.com/awslabs/aws-solutions-constructs | **1 spec** | Has `.kiro/specs` with one spec (`aws-lambda-polly` with requirements/design/tasks). The only production AWS repo found using Kiro's spec-driven workflow. |
| aws/aws-cdk | https://github.com/aws/aws-cdk | **No** | |
| aws/aws-sdk-go-v2 | https://github.com/aws/aws-sdk-go-v2 | **No** | |
| aws/aws-sdk-rust | https://github.com/aws/aws-sdk-rust | **No** | |
| aws/aws-cli | https://github.com/aws/aws-cli | **No** | |
| aws/chalice | https://github.com/aws/chalice | **No** | |
| aws/mountpoint-s3 | https://github.com/aws/mountpoint-s3 | **No** | |
| aws/multi-agent-orchestrator | https://github.com/aws/multi-agent-orchestrator | **No** | |
| aws/amazon-q-developer-cli | https://github.com/aws/amazon-q-developer-cli | **No** | |
| aws/aws-sdk-net | https://github.com/aws/aws-sdk-net | **No** | |
| aws/aws-sdk-pandas | https://github.com/aws/aws-sdk-pandas | **No** | |
| aws/sagemaker-python-sdk | https://github.com/aws/sagemaker-python-sdk | **No** | |
| awslabs/cdk-nag | https://github.com/awslabs/cdk-nag | **No** | |
| aws/aws-lambda-powertools-python | https://github.com/aws/aws-lambda-powertools-python | **No** | |
| awslabs/generative-ai-cdk-constructs | https://github.com/awslabs/generative-ai-cdk-constructs | **No** | |

Two production repos use Kiro's `.kiro/steering` (coding guidelines — the equivalent of a `.cursorrules` file), but **not** the spec-driven workflow. One production repo has a single spec. The major AWS SDKs, CDK, CLI, and infrastructure repos do not use Kiro's spec workflow.

#### Kiro's own repo

The repo `kirodotdev/Kiro` ([link](https://github.com/kirodotdev/Kiro)) contains `.kiro/specs/github-issue-automation` with a complete `requirements.md`/`design.md`/`tasks.md` for an automated GitHub issue management feature. Tasks are partially completed. This is the strongest evidence of dogfooding found — but it is one spec for a repo-automation feature, not evidence that Kiro's own IDE development is spec-driven.

`kirodotdev/spirit-of-kiro` (a game project) has `.kiro/steering` only — no specs.

#### AWS sample repos

Approximately 30 repos under `aws-samples` are Kiro-related. Roughly half have `.kiro/specs`:

**With specs:** sample-target-identification-agent-using-kiro (11 spec directories — the most extensive), sample-food-tracker-tanstack-kiro, sample-kiro-cli-prompts-for-product-teams, sample-pcs-kiro-agent, sample-agentic-arcade-game-starter, sample-reddit-ai-game-starter.

**Without `.kiro/`:** sample-kiro-assistant, sample-aidlc-kiro-power, sample-kiro-user-analytics-dashboard, sample-kiro-harness-hive, sample-kiro-steering-studio, sample-kiro-cli-multiagent-development, sample-sfc-agentic-control-plane, sample-voice-driven-development, sample-quicksuite-kiro-quickstarts.

These are demo/tutorial repos, not production systems. Half the Kiro sample repos don't even ship with `.kiro/` directories.

### Broader adoption

GitHub code search for `path:.kiro/specs` returned **no results** outside the repos already identified. The `.kiro/` spec format has essentially zero visible third-party adoption in public repositories.

### Published effectiveness data

**None.** We checked:

- **kiro.dev/blog** (~50 posts): No post reports measured outcomes (defect rates, rework rates, quality comparisons). The introductory blog posts contain no metrics.
- **Kiro docs on specs**: Describe the process (requirements → design → tasks) but make no quantitative claims about quality improvements.
- **AWS DevOps blog**: No Kiro-specific posts with metrics found.
- **AWS re:Invent sessions**: No talks reporting SDD/Kiro quality data found. Amazon reports broad Q Developer metrics (deployment frequency, cost savings) but nothing SDD-specific.
- **AWS drug discovery case study** ([source](https://aws.amazon.com/blogs/industries/from-spec-to-production-a-three-week-drug-discovery-agent-using-kiro/)): Three solution architects built a target identification agent in three weeks. No before/after comparison, no quality measurement — just "it was fast."

There are no published defect rates, rework rates, or quality measurements from Kiro's spec-driven development anywhere we could find.

---

## Summary

| Vendor | Uses own tool in public repos? | Published quality metrics? | Third-party evidence |
|--------|-------------------------------|--------------------------|---------------------|
| GitHub (Spec Kit) | No (0/10 repos; 1 partial false positive) | None | Negative (slower, no quality benefit) |
| Amazon (Kiro) | Minimally (1 spec in 1/17 production repos; 1 spec in own repo) | None | None found |

## SDD Tool Footprint in Study Data

A text search of all 100,247 PR descriptions, titles, and file paths in the study dataset for SDD tool references:

| Pattern | Matches | Details |
|---------|---------|---------|
| `.specify/` | 0 | |
| `.speckit/` | 0 | |
| `.kiro/` | 0 | |
| `spec-kit` | 0 | |
| `speckit` | 0 | |
| `kiro` | 5 | 3 are Apache Airflow PRs listing Kiro as IDE in contributor checklist; 2 are username mentions of `kiroushi`. None reference Kiro's spec workflow. |

**Zero PRs in the study dataset use SDD tool-generated specifications.** The specification adoption observed in the data (rising from ~0% to 14% over 2025-2026) reflects organic specification behavior: linked issues, design documents, structured PR descriptions.

This mirrors the vendors' own behavior: GitHub uses Spec Kit in 0 of 10 public repos checked (the tool doesn't even use its own framework), and Amazon uses Kiro specs in 1 of 17 production repos (a single spec in one repo). If these tools dramatically reduced defects, the companies building them would be the first to adopt them across their own codebases. They have not.

**Checked on:** 2026-04-04

## Implications

Neither vendor meaningfully uses their own SDD workflow in production. GitHub's Spec Kit repo does not use its own framework. Amazon's major SDKs, CDK, and CLI do not use Kiro specs. Both vendors have the engineering resources and internal data to validate their quality claims and have chosen not to publish evidence. No effectiveness data — defect rates, rework rates, or quality comparisons — has been published by any SDD vendor.

The two repos that use Kiro's `.kiro/steering` (aws-sdk-java-v2, graph-explorer) adopted the configuration/guidelines feature, not the spec-driven workflow. Steering files are the equivalent of a `.cursorrules` or `.editorconfig` — useful, but not the "specifications reduce defects" claim under test.

---

## Reproduction

To reproduce this check:

```bash
# Check any GitHub-org repo for .specify/ directory
gh api repos/github/REPO_NAME/contents/.specify 2>&1

# Check git history for spec files
gh api "repos/github/REPO_NAME/commits?path=.specify/specs" --jq 'length'

# Check .gitignore for .specify entries
gh api repos/github/REPO_NAME/contents/.gitignore --jq '.content' | base64 -d | grep specify

# Broader search across GitHub
# (requires GitHub code search access)
# Search query: path:.specify/spec.md

# --- Kiro ---

# Check any AWS-org repo for .kiro/ directory
gh api repos/aws/REPO_NAME/contents/.kiro 2>&1

# Check for specs specifically
gh api repos/aws/REPO_NAME/contents/.kiro/specs 2>&1

# Broader search for Kiro specs
# Search query: path:.kiro/specs
```
