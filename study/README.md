# Delivery Gap Research

89,599 pull requests (after bot exclusion) across 119 open-source repositories. SZZ defect tracing, JIT features, within-author fixed-effects estimation, propensity score matching.

**Paper:** Hill, B. (2026). *Does Spec-Driven Development Reduce Defects? An Empirical Test of Industry Claims Across 119 Open-Source Repositories.* Zenodo. https://doi.org/10.5281/zenodo.19415188

**Data collection window:** March 28 -- April 3, 2026, with 365-day lookback per repository (observation period: ~April 2025 -- April 2026).

> We have tried to find all bugs in this analysis, but we're humans (even with artificial augmentation). If you think there is a bug, please open a GitHub issue. We take data quality seriously and will investigate.

## Reproduce

```bash
# From the study root directory:
bash scripts/pipeline/run-all-analysis.sh
```

Prerequisites: Python 3.10+, pandas, numpy, statsmodels, scipy.

This runs the full 7-step pipeline:

| Step | Script | Output |
|------|--------|--------|
| 1 | (inline merge) | `szz-results-merged.csv`, `jit-features-merged.csv` |
| 2 | `build-unified-csv.py` | `unified-prs.csv` |
| 3 | `build-master-csv.py` | `master-prs.csv` |
| 4 | `full-szz-analysis.py` | `results/analysis-results.txt` |
| 5 | `robustness-subgroups.py` | `results/robustness-subgroups.txt` |
| 6 | `robustness-highquality.py` | `results/robustness-highquality.txt` |
| 7 | `robustness-temporal.py` | `results/robustness-temporal.txt` |

Additional robustness scripts (run separately):

| Script | What it does |
|--------|--------------|
| `primary-with-jit-controls.py` | H1/H2 with JIT features as primary controls |
| `propensity-score-matching.py` | PSM on JIT risk profile for bugs and rework |

Source data in `data/` is never modified by the analysis pipeline.

## Directory Structure

```
study/
├── data/                    # Source and derived data (never modified by analysis)
│   ├── prs-*.json           # Raw PR data per repo (119 files)
│   ├── szz-checkpoint-*.json # SZZ/JIT batch checkpoints
│   ├── spec-quality-*.json  # LLM spec quality scores
│   ├── engagement-*.json    # LLM engagement scores
│   ├── spec-signals-*.json  # Spec coverage and rework signals
│   ├── catchrate-*.json     # CatchRate classifications
│   ├── pr-features.csv      # Regex text features
│   ├── repo-manifest.json   # Canonical repo list
│   ├── unified-prs.csv      # [derived] All PRs merged
│   ├── master-prs.csv       # [derived] All PRs + all features
│   ├── szz-results-merged.csv  # [derived] Merged SZZ blame links
│   └── jit-features-merged.csv # [derived] Merged JIT features
│
├── results/                 # Analysis outputs
│   ├── analysis-results.txt     # Main analysis report
│   └── robustness-subgroups.txt # Subgroup robustness checks
│
├── scripts/
│   ├── pipeline/            # Reproducible analysis pipeline
│   │   ├── run-all-analysis.sh      # Orchestrator (7 steps)
│   │   ├── build-unified-csv.py     # Step 2: merge PR data
│   │   ├── build-master-csv.py      # Step 3: join all features
│   │   ├── full-szz-analysis.py     # Step 4: main analysis (H1-H5)
│   │   ├── robustness-subgroups.py  # Step 5: subgroup checks
│   │   ├── robustness-highquality.py # Step 6: high-quality spec subsample
│   │   ├── robustness-temporal.py   # Step 7: recent 3-month window
│   │   ├── primary-with-jit-controls.py  # JIT features as primary controls
│   │   ├── propensity-score-matching.py  # PSM robustness check
│   │   ├── runner.py                # PR fetch engine
│   │   └── fetch_progress.py        # Fetch resume/checkpoint
│   │
│   ├── collection/          # Data collection scripts
│   │   ├── fetch-all-repos.py       # Fetch PRs from GitHub
│   │   ├── szz-score.py             # SZZ + JIT computation
│   │   └── ...
│   │
│   ├── scoring/             # Feature extraction & LLM scoring
│   │   ├── compute-features.py      # Text features
│   │   ├── score-specs.py           # Spec quality (LLM)
│   │   ├── score-engagement.py      # Engagement (LLM)
│   │   └── ...
│   │
│   ├── analysis/            # Exploratory / legacy analyses
│   ├── validation/          # Tests and validation scripts
│   └── util/                # Utilities
│
└── docs/                    # Methodology notes and findings
```

## Specification Quality Scoring

Specs are scored by Claude Haiku using a structured rubric in `scripts/scoring/score-specs.py` (lines 23--96). Seven dimensions scored 0--100:

1. **outcome_clarity** -- Is the desired end state clear?
2. **error_states** -- Are error conditions and edge cases described?
3. **scope_boundaries** -- Is it clear what's in and out of scope?
4. **acceptance_criteria** -- Are there testable success conditions?
5. **data_contracts** -- Are data shapes and API contracts described?
6. **dependency_context** -- Does it reference existing code/modules?
7. **behavioral_specificity** -- Are specific behaviors described concretely?

Plus `change_type` (feature/bugfix/refactor/etc.) and `spec_length_signal` (empty/minimal/short/medium/detailed).

The LLM scoring is **unvalidated against human judgment**. A 99-PR stratified sample for human rating is in `results/human-rating-sheet.csv`. After completing ratings, run `scripts/validation/compare-human-llm-ratings.py` to compute Cohen's kappa.

## Methodology

- **Within-author LPM**: Linear probability model with full demeaning (Frisch-Waugh-Lovell) and author-clustered standard errors. Equivalent to author fixed effects via the incidental parameters workaround (Angrist & Pischke 2009).
- **Propensity score matching**: Nearest-neighbor 1:1 matching on logit(PS) with caliper = 0.05 SD. 16 covariates (JIT features + size controls).
- **SZZ**: Basic SZZ variant tracing fix commits to bug-introducing commits via git blame. Known misattribution rate: 46--71% (da Costa et al. 2017). Non-differential with respect to specification presence.
- **JIT**: Kamei et al. (2013) 14-feature defect prediction model (13 used; sexp excluded for zero variance).
- **Bot exclusion**: 27-pattern list removing dependabot, renovate, and other automated authors. Applied consistently across all scripts.

## SZZ Coverage

103 of 119 repositories have SZZ defect tracing. The remaining 16 produced zero traceable blame links: their merge commit SHAs (from GitHub's API) are unreachable in single-branch clones, typically because the repository uses squash-merge workflows where GitHub's synthetic merge commits are garbage-collected. This is a limitation of the SZZ method on squash-merge repos, not a data collection failure.

## Exploratory Analysis

Scripts in `scripts/analysis/` informed the paper but are not part of the reproducible pipeline:

| Script | What it explores |
|--------|------------------|
| `jit-feature-profiles.py` | JIT feature differences: AI vs human, buggy vs clean, spec'd vs unspec'd |
| `review-dynamics.py` | Review as mediator: do specs change review behavior? |
| `ai-defect-patterns.py` | AI bug characteristics: time-to-fix, file types, self-fix rate |
| `ai-cascade-repo-controlled.py` | Within-repo test of AI cascading rework (debunked as repo composition) |
| `repo-descriptive-stats.py` | Sample descriptive statistics |

## Key Finding

Across 89,599 PRs, 119 repos, 4 outcome measures, 7 quality dimensions, 6 subgroup cuts, propensity score matching, and 2 predictive frameworks: **zero evidence that specification-driven development reduces defects.** Specifications increase rework (+10.3pp after PSM matching, p<0.001), likely through reviewer accountability rather than defect introduction. Task complexity drives defect rates; the specification artifact is a proxy, not a mechanism.

Specification _presence_ (H1/H2) and specification _quality_ (H3/H4) are tested separately. Even among the subset of PRs that have specifications, higher quality scores do not predict fewer defects or less rework. The quality analysis uses the 5,246 PRs with LLM-scored specifications — a non-random subsample restricted to spec'd PRs with substantial description text. Top-quartile specs show a marginal protective effect for bugs (−2.3pp, p=0.047) that does not survive the cleanest comparison (high-quality vs. no spec, p=0.146) and violates dose-response (top-decile weaker than top-quartile).
