#!/usr/bin/env python3
"""
Descriptive statistics table for the 119-repo study dataset.

Reads: master-prs.csv
Writes: stdout (human-readable + LaTeX/Typst table)

Computes per-repo: PR count, language, median PR size, spec rate, AI tag rate,
date range.
Computes aggregate: totals, language breakdown, distribution summaries.
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

# ── Language mapping (inferred from well-known repo identities) ───────────────
# Primary language for each repo slug (org/name). "Multi" where multiple
# languages are genuinely co-primary. "C/C++" for mixed C/C++ repos.

REPO_LANGUAGE = {
    "Aider-AI/aider":                        "Python",
    "BerriAI/litellm":                       "Python",
    "ClickHouse/ClickHouse":                 "C++",
    "Lightning-AI/pytorch-lightning":        "Python",
    "Mintplex-Labs/anything-llm":            "JavaScript",
    "PostHog/posthog":                       "Python",
    "PowerShell/PowerShell":                 "C#",
    "QuivrHQ/quivr":                         "Python",
    "TabbyML/tabby":                         "Rust",
    "all-hands-ai/OpenHands":               "Python",
    "anthropics/anthropic-cookbook":         "Python",
    "antiwork/gumroad":                      "Ruby",
    "apache/airflow":                        "Python",
    "apache/arrow":                          "C++",
    "apache/flink":                          "Java",
    "apache/kafka":                          "Java",
    "apache/spark":                          "Scala",
    "astral-sh/ruff":                        "Rust",
    "astral-sh/uv":                          "Rust",
    "bevyengine/bevy":                       "Rust",
    "biomejs/biome":                         "Rust",
    "calcom/cal.com":                        "TypeScript",
    "celery/celery":                         "Python",
    "chroma-core/chroma":                    "Python",
    "clerkinc/javascript":                   "TypeScript",
    "cli/cli":                               "Go",
    "cline/cline":                           "TypeScript",
    "cockroachdb/cockroach":                 "Go",
    "containerd/containerd":                 "Go",
    "continuedev/continue":                  "TypeScript",
    "crewAIInc/crewAI":                      "Python",
    "dagster-io/dagster":                    "Python",
    "danny-avila/LibreChat":                 "JavaScript",
    "dbt-labs/dbt-core":                     "Python",
    "denoland/deno":                         "Rust",
    "django/django":                         "Python",
    "dmlc/xgboost":                          "C++",
    "dotnet/aspire":                         "C#",
    "dotnet/maui":                           "C#",
    "dotnet/runtime":                        "C#",
    "e2b-dev/E2B":                           "TypeScript",
    "elastic/elasticsearch":                 "Java",
    "elixir-lang/elixir":                    "Elixir",
    "envoyproxy/envoy":                      "C++",
    "etcd-io/etcd":                          "Go",
    "excalidraw/excalidraw":                 "TypeScript",
    "facebook/react":                        "JavaScript",
    "fastapi/fastapi":                       "Python",
    "flutter/flutter":                       "Dart",
    "getmaxun/maxun":                        "TypeScript",
    "ggerganov/llama.cpp":                   "C++",
    "godotengine/godot":                     "C++",
    "grafana/grafana":                       "Go",
    "hashicorp/terraform":                   "Go",
    "hashicorp/vault":                       "Go",
    "haskell/cabal":                         "Haskell",
    "home-assistant/core":                   "Python",
    "huggingface/transformers":              "Python",
    "juspay/hyperswitch":                    "Rust",
    "kubernetes/kubernetes":                 "Go",
    "langchain-ai/langchain":                "Python",
    "langflow-ai/langflow":                  "Python",
    "liam-hq/liam":                          "TypeScript",
    "lm-sys/FastChat":                       "Python",
    "lobehub/lobe-chat":                     "TypeScript",
    "medplum/medplum":                       "TypeScript",
    "mendableai/firecrawl":                  "TypeScript",
    "microsoft/vscode":                      "TypeScript",
    "milvus-io/milvus":                      "Go",
    "mlflow/mlflow":                         "Python",
    "n8n-io/n8n":                            "TypeScript",
    "nats-io/nats-server":                   "Go",
    "nestjs/nest":                           "TypeScript",
    "nocodb/nocodb":                         "TypeScript",
    "novuhq/novu":                           "TypeScript",
    "nushell/nushell":                       "Rust",
    "ollama/ollama":                         "Go",
    "open-webui/open-webui":                 "Python",
    "openmrs/openmrs-core":                  "Java",
    "oven-sh/bun":                           "Zig",
    "oxc-project/oxc":                       "Rust",
    "phoenixframework/phoenix":              "Elixir",
    "pingcap/tidb":                          "Go",
    "pnpm/pnpm":                             "TypeScript",
    "prefecthq/prefect":                     "Python",
    "prometheus/prometheus":                 "Go",
    "promptfoo/promptfoo":                   "TypeScript",
    "pydantic/pydantic":                     "Python",
    "pytest-dev/pytest":                     "Python",
    "python/cpython":                        "Python",
    "qdrant/qdrant":                         "Rust",
    "quarkusio/quarkus":                     "Java",
    "rails/rails":                           "Ruby",
    "ray-project/ray":                       "Python",
    "redis/redis":                           "C",
    "refinedev/refine":                      "TypeScript",
    "remix-run/remix":                       "TypeScript",
    "run-llama/llama_index":                 "Python",
    "rust-lang/rust":                        "Rust",
    "shadcn-ui/ui":                          "TypeScript",
    "square/okhttp":                         "Kotlin",
    "stanfordnlp/dspy":                      "Python",
    "strapi/strapi":                         "TypeScript",
    "streamlit/streamlit":                   "Python",
    "stripe/stripe-ios":                     "Swift",
    "supabase/supabase":                     "TypeScript",
    "sveltejs/svelte":                       "TypeScript",
    "tailwindlabs/tailwindcss":              "JavaScript",
    "temporalio/temporal":                   "Go",
    "tikv/tikv":                             "Rust",
    "tokio-rs/tokio":                        "Rust",
    "traefik/traefik":                       "Go",
    "vercel/ai":                             "TypeScript",
    "vercel/next.js":                        "JavaScript",
    "vitejs/vite":                           "TypeScript",
    "vitessio/vitess":                       "Go",
    "vllm-project/vllm":                     "Python",
    "weaviate/weaviate":                     "Go",
    "zephyrproject-rtos/zephyr":             "C",
}

# ── Load & prepare ─────────────────────────────────────────────────────────────

df = pd.read_csv(DATA_DIR / "master-prs.csv", low_memory=False)
print(f"Loaded: {len(df):,} PRs, {df['repo'].nunique()} repos")

df["merged_at"] = pd.to_datetime(df["merged_at"], utc=True, errors="coerce")
for col in ["specd", "f_ai_tagged", "f_is_bot_author"]:
    if col in df.columns:
        df[col] = df[col].fillna(False).astype(bool)

# Bot exclusion
df["is_bot"] = df["f_is_bot_author"].fillna(False).astype(bool)
n_bots = df["is_bot"].sum()
df = df[~df["is_bot"]].copy()
print(f"Bot exclusion: {n_bots:,} bot PRs removed, {len(df):,} remaining")
print()

# PR size
df["pr_size"] = df["additions"].fillna(0) + df["deletions"].fillna(0)

# ── Per-repo stats ─────────────────────────────────────────────────────────────

def date_range_str(series):
    valid = series.dropna()
    if valid.empty:
        return "N/A"
    return f"{valid.min().strftime('%Y-%m')} – {valid.max().strftime('%Y-%m')}"

rows = []
for repo, grp in df.groupby("repo"):
    n_prs = len(grp)
    language = REPO_LANGUAGE.get(repo, "Unknown")
    median_size = grp["pr_size"].median()
    spec_rate = grp["specd"].mean() * 100
    ai_rate = grp["f_ai_tagged"].mean() * 100
    date_range = date_range_str(grp["merged_at"])
    rows.append({
        "repo": repo,
        "language": language,
        "n_prs": n_prs,
        "median_size": median_size,
        "spec_rate": spec_rate,
        "ai_rate": ai_rate,
        "date_range": date_range,
    })

repo_df = pd.DataFrame(rows).sort_values("repo")

# ── Aggregate stats ────────────────────────────────────────────────────────────

total_repos = len(repo_df)
total_prs = repo_df["n_prs"].sum()

lang_counts = repo_df["language"].value_counts()

pr_counts = repo_df["n_prs"]
median_repo_prs = pr_counts.median()
mean_repo_prs = pr_counts.mean()
min_repo_prs = pr_counts.min()
max_repo_prs = pr_counts.max()
p25_repo_prs = pr_counts.quantile(0.25)
p75_repo_prs = pr_counts.quantile(0.75)

spec_rates = repo_df["spec_rate"]
ai_rates = repo_df["ai_rate"]

# ── Print human-readable summary ──────────────────────────────────────────────

print("=" * 70)
print("STUDY DATASET — DESCRIPTIVE STATISTICS")
print("=" * 70)
print()
print(f"Total repositories:  {total_repos}")
print(f"Total PRs (post-bot): {total_prs:,}")
print()

print("── Repository size (PRs per repo) ──────────────────────────────────")
print(f"  Median:  {median_repo_prs:.0f}")
print(f"  Mean:    {mean_repo_prs:.0f}")
print(f"  Min:     {min_repo_prs}")
print(f"  Max:     {max_repo_prs}")
print(f"  P25/P75: {p25_repo_prs:.0f} / {p75_repo_prs:.0f}")
print()

print("── Spec rate (% of PRs with specification, per repo) ─────────────────")
print(f"  Median:  {spec_rates.median():.1f}%")
print(f"  Mean:    {spec_rates.mean():.1f}%")
print(f"  Min:     {spec_rates.min():.1f}%")
print(f"  Max:     {spec_rates.max():.1f}%")
print(f"  P25/P75: {spec_rates.quantile(0.25):.1f}% / {spec_rates.quantile(0.75):.1f}%")
print()

print("── AI tag rate (% of PRs tagged as AI-augmented, per repo) ──────────")
print(f"  Median:  {ai_rates.median():.1f}%")
print(f"  Mean:    {ai_rates.mean():.1f}%")
print(f"  Min:     {ai_rates.min():.1f}%")
print(f"  Max:     {ai_rates.max():.1f}%")
print(f"  P25/P75: {ai_rates.quantile(0.25):.1f}% / {ai_rates.quantile(0.75):.1f}%")
print()

print("── Primary language breakdown ────────────────────────────────────────")
for lang, count in lang_counts.items():
    pct = count / total_repos * 100
    print(f"  {lang:<20} {count:>3} repos  ({pct:.1f}%)")
print()

# ── Per-repo table ─────────────────────────────────────────────────────────────

print("=" * 70)
print("PER-REPO TABLE")
print("=" * 70)
header = f"{'Repository':<45} {'Lang':<12} {'PRs':>6} {'Med.Size':>9} {'Spec%':>6} {'AI%':>6}  {'Date Range'}"
print(header)
print("-" * len(header))
for _, r in repo_df.iterrows():
    print(
        f"{r['repo']:<45} {r['language']:<12} {r['n_prs']:>6} "
        f"{r['median_size']:>9.0f} {r['spec_rate']:>6.1f} {r['ai_rate']:>6.1f}"
        f"  {r['date_range']}"
    )
print()

# ── LaTeX/Typst table ─────────────────────────────────────────────────────────
#
# Produces a two-part table:
#   Part 1 — per-repo details (suitable for an appendix)
#   Part 2 — aggregate summary (suitable for the body of the paper)

print("=" * 70)
print("LATEX TABLE — AGGREGATE SUMMARY (for paper body)")
print("=" * 70)
print(r"""
\begin{table}[h]
\centering
\caption{Study dataset overview. All counts are post-bot-exclusion.
  Spec rate and AI tag rate are means across repositories (not pooled).}
\label{tab:dataset-overview}
\begin{tabular}{lrr}
\toprule
\textbf{Metric} & \textbf{Value} & \textbf{Notes} \\
\midrule""")
print(f"Repositories & {total_repos} & convenience sample \\\\")
print(f"PRs (post-bot exclusion) & {total_prs:,} & \\\\")
print(f"Median PRs per repo & {median_repo_prs:.0f} & range {min_repo_prs}--{max_repo_prs} \\\\")
print(f"Mean PRs per repo & {mean_repo_prs:.0f} & \\\\")
print(f"Median spec rate & {spec_rates.median():.1f}\\% & IQR {spec_rates.quantile(0.25):.1f}--{spec_rates.quantile(0.75):.1f}\\% \\\\")
print(f"Median AI tag rate & {ai_rates.median():.1f}\\% & IQR {ai_rates.quantile(0.25):.1f}--{ai_rates.quantile(0.75):.1f}\\% \\\\")
print(r"""\bottomrule
\end{tabular}
\end{table}
""")

print("=" * 70)
print("LATEX TABLE — LANGUAGE BREAKDOWN")
print("=" * 70)
print(r"""
\begin{table}[h]
\centering
\caption{Primary language distribution across the 119 study repositories.}
\label{tab:language-breakdown}
\begin{tabular}{lrr}
\toprule
\textbf{Language} & \textbf{Repos} & \textbf{\%} \\
\midrule""")
for lang, count in lang_counts.items():
    pct = count / total_repos * 100
    print(f"{lang} & {count} & {pct:.1f}\\% \\\\")
print(r"""\bottomrule
\end{tabular}
\end{table}
""")

print("=" * 70)
print("LATEX TABLE — PER-REPO DETAILS (for appendix)")
print("=" * 70)
print(r"""
\begin{longtable}{llrrrr}
\caption{Per-repository descriptive statistics.
  Med.\ size = median lines changed (additions + deletions).
  Spec\% = percentage of PRs with an specificationification.
  AI\% = percentage of PRs tagged as AI-augmented.}
\label{tab:per-repo-stats} \\
\toprule
\textbf{Repository} & \textbf{Lang} & \textbf{PRs} & \textbf{Med.\ size} & \textbf{Spec\%} & \textbf{AI\%} \\
\midrule
\endfirsthead
\multicolumn{6}{c}{\tablename\ \thetable{} (continued)} \\
\toprule
\textbf{Repository} & \textbf{Lang} & \textbf{PRs} & \textbf{Med.\ size} & \textbf{Spec\%} & \textbf{AI\%} \\
\midrule
\endhead
\bottomrule
\endfoot""")
for _, r in repo_df.iterrows():
    # Escape underscores for LaTeX
    repo_esc = r['repo'].replace("_", r"\_").replace(".com", r".com")
    print(
        f"\\texttt{{{repo_esc}}} & {r['language']} & {r['n_prs']:,} & "
        f"{r['median_size']:.0f} & {r['spec_rate']:.1f} & {r['ai_rate']:.1f} \\\\"
    )
print(r"""\end{longtable}
""")

print("=" * 70)
print("TYPST TABLE — AGGREGATE SUMMARY")
print("=" * 70)
print(f"""
#figure(
  table(
    columns: (auto, auto, auto),
    align: (left, right, left),
    table.header([*Metric*], [*Value*], [*Notes*]),
    [Repositories], [{total_repos}], [convenience sample],
    [PRs (post-bot exclusion)], [{total_prs:,}], [],
    [Median PRs per repo], [{median_repo_prs:.0f}], [range {min_repo_prs}--{max_repo_prs}],
    [Mean PRs per repo], [{mean_repo_prs:.0f}], [],
    [Median spec rate], [{spec_rates.median():.1f}%], [IQR {spec_rates.quantile(0.25):.1f}--{spec_rates.quantile(0.75):.1f}%],
    [Median AI tag rate], [{ai_rates.median():.1f}%], [IQR {ai_rates.quantile(0.25):.1f}--{ai_rates.quantile(0.75):.1f}%],
  ),
  caption: [Study dataset overview. All counts are post-bot-exclusion. Spec rate and AI tag rate are medians across repositories (not pooled).],
) <tab:dataset-overview>
""")

print("=" * 70)
print("TYPST TABLE — LANGUAGE BREAKDOWN")
print("=" * 70)
lang_rows = "\n    ".join(
    f"[{lang}], [{count}], [{count / total_repos * 100:.1f}%],"
    for lang, count in lang_counts.items()
)
print(f"""
#figure(
  table(
    columns: (auto, auto, auto),
    align: (left, right, right),
    table.header([*Language*], [*Repos*], [*%*]),
    {lang_rows}
  ),
  caption: [Primary language distribution across the {total_repos} study repositories.],
) <tab:language-breakdown>
""")
