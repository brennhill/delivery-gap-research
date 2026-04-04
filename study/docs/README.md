# 30-Repo Empirical Study

Runs UPFRONT (spec quality) and CATCHRATE (pipeline trustworthiness) against 30 public GitHub repos and aggregates cross-repo results.

## Prerequisites

- `spec-signals` CLI installed and on PATH (from `~/dev/upfront`)
- `catchrate` CLI installed and on PATH (from `~/dev/catchrate`)
- `gh` CLI authenticated with sufficient API rate limits

## Step 1: Collect data

```bash
# Dry run first — prints commands without executing
python runner.py --dry-run

# Test with a single repo
python runner.py --repo cli/cli

# Run all 30 repos (takes a while — ~10 min per repo max)
python runner.py
```

Output goes to `data/` with one JSON file per tool per repo, plus `data/manifest.json` tracking success/failure.

## Step 2: Aggregate results

```bash
python aggregate.py
```

Reads from `data/` and writes to `results/`:

| File | Contents |
|------|----------|
| `summary.json` | Cross-repo aggregate statistics |
| `per-repo-summary.csv` | One row per repo: coverage, catch rates, rework rates |
| `per-pr-detail.csv` | One row per PR across all repos: classification, size, rework |
| `complexity-bucketed.csv` | Rework/friction by (repo, size bucket, spec status) |
| `cross-repo-hypotheses.csv` | Tests the four SSRN paper hypotheses per size bucket |

## Directory structure

```
study/
  runner.py              # Step 1: collect data
  aggregate.py           # Step 2: aggregate results
  data/                  # Raw JSON outputs (gitignored)
    spec-signals-owner-repo.json
    catchrate-owner-repo.json
    manifest.json
  results/               # Aggregated outputs
    summary.json
    per-repo-summary.csv
    per-pr-detail.csv
    complexity-bucketed.csv
    cross-repo-hypotheses.csv
```
