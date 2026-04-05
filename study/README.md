# Delivery Gap Research

Replication package for: Hill, B. (2026). *Does Spec-Driven Development Reduce Defects? An Empirical Test of Industry Claims Across 119 Open-Source Repositories.*

**Preprint:** https://doi.org/10.5281/zenodo.19415187

> We have tried to find all bugs in this analysis, but we're humans (even with artificial augmentation). If you think there is a bug, please open a GitHub issue. We take data quality seriously and will investigate.

## What This Study Does

Spec-driven development (SDD) tools claim that writing specifications before implementation reduces defects, prevents rework, and improves code quality. We test five hypotheses derived from these vendor claims against 88,052 pull requests across 119 open-source repositories.

**The short answer:** None of the five hypotheses are supported. Specifications proxy for task complexity, not quality improvement.

## How the Data Was Collected

We collected pull request data from 119 open-source repositories between March 28 and April 3, 2026, using the GitHub API. Each repository has a 365-day lookback window, so the observation period spans approximately April 2025 through April 2026.

For each of the 119 repos, the collection pipeline produced:

1. **PR metadata** (`prs-*.json`) -- Author, title, body, merge date, additions, deletions, files changed, linked issues, review comments, co-author tags. One JSON file per repo.

2. **SZZ blame links** (`szz-results-merged.csv`) -- For 103 of the 119 repos, we cloned the repository and ran the SZZ algorithm: identify commits that fix bugs (via commit message keywords), then use `git blame` to trace each fix back to the commit that introduced the bug. This produces blame links from fix commits to bug-introducing commits. We then map each bug-introducing commit to its originating PR. 16 repos produced zero blame links because their squash-merge workflows make merge SHAs unreachable.

3. **JIT features** (`jit-features-merged.csv`) -- For each PR, we computed 14 code-change features from the Kamei et al. (2013) JIT defect prediction framework: number of subsystems, directories, and files touched; change entropy; lines added/deleted; file age; whether it's a fix; number of prior developers; developer experience; and recent/subsystem experience.

4. **Spec classification** (`spec-signals-*.json`) -- Each PR is classified as "spec'd" or "unspec'd" based on whether it has specification artifacts: linked GitHub issues, ticket IDs (PROJ-123), spec URLs (Notion, Confluence, Jira, etc.), or filled PR template sections with substantive content (>20 words). Rework is also detected here: a PR is "reworked" if a subsequent PR within 30 days modifies overlapping files and has fix/revert keywords in its title.

5. **Spec quality scores** (`spec-quality-*.json`) -- For the subset of spec'd PRs with substantial description text, Claude Haiku scored specification quality across seven dimensions (0--100 each): outcome clarity, error states, scope boundaries, acceptance criteria, data contracts, dependency context, and behavioral specificity.

6. **Text features** (`pr-features.csv`) -- Pure text-statistical features computed from PR descriptions: typo counts, casual language markers, organizational context signals, reasoning quality indicators, template/slop detection, and vocabulary statistics. Also includes bot detection and AI self-tag detection.

## Bot Exclusion

We exclude 12,195 bot-authored PRs, leaving 88,052 for analysis. Bot detection uses a single source of truth in `scripts/scoring/compute-features.py` with three layers:

1. **GitHub API flag** -- accounts with `[bot]` suffix or `app/` prefix
2. **Exact username match** -- 27 known automation accounts:
   - CI/release: robobun, denobot, nextjs-bot, vercel-release-bot, ti-chi-bot, dotnet-bot
   - Dependency/automation: renovate, dependabot, github-actions, clerk-cookie, greenkeeper, snyk, mergify, codecov, mendral-app, n8n-assistant, promptfoobot, scheduled-actions, grafana-pr-automation, grafana-delivery-bot, langchain-model-profile-bot
   - Project-specific: vitess-bot, pwshbot, k8s-infra-cherrypick-robot, medplumbot, refine-bot, lobehubbot, qdrant-cloud-bot
   - AI agents: copilot-swe-agent, devin-ai-integration, cursor
3. **Substring match** -- any username containing "bot", plus substring matching against the 27 names above (catches variants like `scheduled-actions-posthog`, `snyk-tim`, `renovate-sh-app`)

All downstream scripts use the `f_is_bot_author` flag from `pr-features.csv`. There is no secondary bot detection.

## How the Pipeline Works

The analysis pipeline has three stages: build, analyze, and robustness.

### Stage 1: Build the dataset

These scripts merge the per-repo source files into a single analysis-ready CSV.

| Step | Script | What it does | Output |
|------|--------|--------------|--------|
| 1 | (inline in `run-all-analysis.sh`) | Concatenate per-batch SZZ and JIT files | `szz-results-merged.csv`, `jit-features-merged.csv` |
| 2 | `build-unified-csv.py` | Merge PR metadata + spec classification + rework signals + quality scores into one row per PR | `unified-prs.csv` |
| 3 | `build-master-csv.py` | Join unified-prs.csv with text features, formality scores, and a stylometric AI classifier | `master-prs.csv` (100,247 rows, 84 columns) |

### Stage 2: Primary analysis

| Step | Script | What it does | Output |
|------|--------|--------------|--------|
| 4 | `full-szz-analysis.py` | Tests all 5 hypotheses using pooled, controlled, and within-author estimation. Also runs alternative outcomes, JIT incremental validity, individual quality dimensions, and repo-level analysis. | `results/analysis-results.txt` |

The within-author analysis uses a linear probability model (LPM) with full Frisch-Waugh-Lovell demeaning and author-clustered standard errors. This compares each developer's spec'd PRs to their own unspec'd PRs, eliminating all time-invariant author-level confounding.

### Stage 3: Robustness checks

| Step | Script | What it does | Output |
|------|--------|--------------|--------|
| 5 | `robustness-subgroups.py` | Tests spec effects across human-only, AI-tagged, and AI-adoption-stratified subgroups | `results/robustness-subgroups.txt` |
| 6 | `robustness-highquality.py` | Tests top-quartile and top-decile specs, dose-response, AI + high-quality spec | `results/robustness-highquality.txt` |
| 7 | `robustness-temporal.py` | Restricts to Jan--Mar 2026 (highest SDD adoption) | `results/robustness-temporal.txt` |
| -- | `primary-with-jit-controls.py` | H1/H2 with 13 JIT features as additional controls | `results/jit-controls.txt` |
| -- | `propensity-score-matching.py` | Nearest-neighbor 1:1 PSM on JIT risk profile | `results/propensity-score-matching.txt` |

## Reproduce

```bash
# Prerequisites: Python 3.10+, pandas, numpy, statsmodels, scipy
pip install pandas numpy statsmodels scipy

# From the study/ directory — single command, runs everything:
python3 replicate-results.py
```

This runs the full 11-step pipeline: data merging, main analysis (H1-H5), and all robustness checks (subgroups, high-quality specs, temporal, complexity stratification, issue-linked specs, JIT controls, propensity score matching). All results are written to `results/*.txt`.

Source data in `data/` (prs-*.json, szz-checkpoint-*.json, spec-quality-*.json, etc.) is never modified by the analysis pipeline. Derived files (unified-prs.csv, master-prs.csv, szz-results-merged.csv) are regenerated from source on each run.

## Specification Quality Scoring

Specs are scored by Claude Haiku using a structured rubric in `scripts/scoring/score-specs.py`. Seven dimensions scored 0--100:

1. **outcome_clarity** -- Is the desired end state clear?
2. **error_states** -- Are error conditions and edge cases described?
3. **scope_boundaries** -- Is it clear what's in and out of scope?
4. **acceptance_criteria** -- Are there testable success conditions?
5. **data_contracts** -- Are data shapes and API contracts described?
6. **dependency_context** -- Does it reference existing code/modules?
7. **behavioral_specificity** -- Are specific behaviors described concretely?

These dimensions align with the quality criteria prescribed by SDD tools themselves (Spec Kit, Kiro).

**Validation:** The LLM scoring was validated against independent human ratings on 38 PRs (`results/human-rating-sheet.csv`). Overall rank-order agreement is moderate (Spearman rho = 0.42, p = 0.01). Four dimensions show significant human-LLM agreement: behavioral specificity (rho = 0.45), scope boundaries (0.43), dependency context (0.40), and outcome clarity (0.39). Three dimensions show weak agreement: error states (0.22), data contracts (0.19), and acceptance criteria (0.17). The LLM reliably detects whether specification content is present but cannot judge whether it is correct for the domain.

## Directory Structure

```
study/
├── data/                    # Source and derived data
│   ├── prs-*.json           # Raw PR data per repo (119 files)
│   ├── szz-checkpoint-*.json # SZZ/JIT batch checkpoints
│   ├── spec-quality-*.json  # LLM spec quality scores (10 files)
│   ├── engagement-*.json    # LLM engagement/formality scores
│   ├── spec-signals-*.json  # Spec coverage + rework signals (119 files)
│   ├── catchrate-*.json     # CatchRate classifications
│   ├── pr-features.csv      # Text features (from compute-features.py)
│   ├── repo-manifest.json   # Canonical repo list
│   ├── unified-prs.csv      # [derived] All PRs merged
│   ├── master-prs.csv       # [derived] All PRs + all features (84 columns)
│   ├── szz-results-merged.csv  # [derived] 64,805 blame links across 103 repos
│   └── jit-features-merged.csv # [derived] JIT features for all PRs
│
├── results/                 # Analysis outputs (text reports)
│   ├── analysis-results.txt
│   ├── robustness-subgroups.txt
│   ├── robustness-highquality.txt
│   ├── robustness-temporal.txt
│   ├── propensity-score-matching.txt
│   ├── human-rating-sheet.csv      # Human validation ratings (N=38)
│   └── human-rating-answer-key.csv # LLM scores for validation sample
│
├── scripts/
│   ├── pipeline/            # Reproducible analysis pipeline (steps 1-7)
│   ├── collection/          # Data collection (GitHub API, SZZ, JIT)
│   ├── scoring/             # Feature extraction & LLM scoring
│   ├── analysis/            # Exploratory analyses (not in pipeline)
│   ├── validation/          # Tests and validation scripts
│   └── util/                # Utilities
│
└── tools/                   # Consolidated tool code (spec detection, rework)
    ├── signals/             # Shared signal extraction primitives
    ├── spec_signals/        # Spec coverage and quality classification
    ├── catchrate/           # Rework/escape classification
    ├── run_spec_signals.py  # Entry point for spec signal generation
    └── run_catchrate.py     # Entry point for CatchRate classification
```

## Methodology Notes

- **Within-author LPM**: Linear probability model with full demeaning (Frisch-Waugh-Lovell) and author-clustered standard errors. Preferred over logistic regression to avoid the incidental parameters problem (Neyman & Scott 1948). Follows Angrist & Pischke (2009) recommendation for fixed-effects with binary outcomes.
- **Propensity score matching**: Nearest-neighbor 1:1 matching on logit(PS) with caliper = 0.05 SD. 16 covariates (13 JIT features + 3 size controls). All standardized mean differences < 0.1 after matching.
- **SZZ**: Basic variant tracing fix commits to bug-introducing commits via git blame. Known misattribution rate: 46--71% (da Costa et al. 2017). Noise is non-differential with respect to specification presence.
- **JIT**: Kamei et al. (2013) 14-feature defect prediction framework (13 used; subsystem experience excluded for zero variance).
- **Rework detection**: File overlap + fix/revert keywords within 30-day window. High-frequency files (>30% of PRs) excluded.
- **AI detection**: Two-layer regex (co-author tags, generation attribution, AI agent markers) + structured AI disclosure parsing. Precision 98.8%, recall 24.2% (validated on 537 PRs).

## Key Findings

Across 88,052 PRs, 119 repos, 4 outcome measures, 7 quality dimensions, 6 subgroup cuts, propensity score matching, and 10 robustness checks: **no evidence that specification artifacts reduce defects or rework.**

| Hypothesis | Within-author result | Interpretation |
|------------|---------------------|----------------|
| H1: Specs reduce defects | +1.4pp, p=0.003 | Wrong direction (confounding by indication) |
| H2: Specs reduce rework | +1.2pp, p=0.001 | Wrong direction (confounding by indication) |
| H3: Better specs, fewer defects | -0.08pp/point, p=0.016 | Tiny, doesn't survive robustness checks |
| H4: Better specs, less rework | ~0, p=0.827 | Null |
| H5: Specs constrain AI scope | ~0, p=0.997 | Null |

Propensity score matching on JIT risk features eliminates both the defect and rework associations entirely, confirming confounding by indication: developers spec hard tasks, and hard tasks produce defects.
