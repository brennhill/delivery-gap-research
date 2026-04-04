# 30-Repo Study: Candidate Repos

Run UPFRONT and CATCHRATE against these 30 public repos to produce cross-repo data on spec quality, pipeline trustworthiness, and complexity-bucketed effectiveness.

## Selection Criteria

- Active PR workflow (not direct-to-main)
- Mix of issue-linking rates (some near 100%, some 30-50% for natural spec'd/unspec'd variance)
- 100+ merged PRs in recent 90-day window
- Code review culture (PRs get reviewed)
- Diverse languages, team sizes, domains

## The 30 Repos

### Tier A: Near-100% Issue Linking (gold standard for classification)

| # | Repo | Language | ~90d PRs | Issue Linking | Domain |
|---|------|----------|----------|---------------|--------|
| 1 | kubernetes/kubernetes | Go | ~971 | 95% (KEP refs, mandatory template) | Cloud native |
| 2 | cockroachdb/cockroach | Go | ~2,439 | 95% (RFC refs, backport chains) | Database |
| 3 | microsoft/vscode | TypeScript | ~3,933 | 95% (fix #NNN universal) | IDE |
| 4 | pingcap/tidb | Go | ~737 | 100% (all sampled PRs linked) | Database |
| 5 | apache/arrow | Multi (C++/Py/Rust/Java) | ~352 | 100% (GH-NNNNN mandatory) | Data format |
| 6 | apache/kafka | Java/Scala | ~458 | High (KAFKA-NNNNN JIRA convention, KIPs) | Messaging |
| 7 | biomejs/biome | Rust | ~531 | 95% | Dev tools |
| 8 | sveltejs/svelte | TypeScript | ~290 | 90% | Web framework |

### Tier B: 60-90% Issue Linking (strong but not universal)

| # | Repo | Language | ~90d PRs | Issue Linking | Domain |
|---|------|----------|----------|---------------|--------|
| 9 | rust-lang/rust | Rust | ~1,918 | 80% (tracking issues for features) | Language |
| 10 | python/cpython | C/Python | ~1,773 | 90% (gh-NNNNN in titles) | Language |
| 11 | grafana/grafana | Go/TypeScript | ~3,050 | 70% (structured template) | Observability |
| 12 | prometheus/prometheus | Go | ~326 | 90% | Observability |
| 13 | django/django | Python | ~200 | 80% (Refs #NNNNN, Trac tickets) | Web framework |
| 14 | envoyproxy/envoy | C++ | ~797 | 75% | Proxy/networking |
| 15 | cli/cli | Go | ~98 | 80% | Dev tools |
| 16 | astral-sh/ruff | Rust | ~1,251 | 70% | Dev tools |
| 17 | denoland/deno | Rust/TypeScript | ~645 | 70% | Runtime |
| 18 | oven-sh/bun | Zig/TypeScript | ~483 | 65% | Runtime |
| 19 | temporalio/temporal | Go | ~507 | Moderate | Workflow engine |
| 20 | pnpm/pnpm | TypeScript | ~288 | 55% | Package manager |

### Tier C: 30-50% Issue Linking (natural spec'd/unspec'd variance)

| # | Repo | Language | ~90d PRs | Issue Linking | Domain |
|---|------|----------|----------|---------------|--------|
| 21 | vercel/next.js | TypeScript | ~1,143 | 40% (community links, maintainers skip) | Web framework |
| 22 | huggingface/transformers | Python | ~825 | 40% (model additions unlinked) | ML/AI |
| 23 | langchain-ai/langchain | Python | ~578 | 30% (fast-moving, many skip links) | ML/AI |
| 24 | supabase/supabase | TypeScript | ~1,213 | 30% | BaaS |
| 25 | elastic/elasticsearch | Java | ~2,982 | 55% | Search/database |
| 26 | facebook/react | JavaScript | ~180 | 45% (detailed bodies, few public links) | UI framework |

### Tier D: Low Linking (contrast cases)

| # | Repo | Language | ~90d PRs | Issue Linking | Domain |
|---|------|----------|----------|---------------|--------|
| 27 | astral-sh/uv | Rust | ~723 | 20% (maintainers ship fast) | Dev tools |
| 28 | tailwindlabs/tailwindcss | Rust/TypeScript | ~200 | Moderate (body-as-spec pattern) | CSS framework |
| 29 | traefik/traefik | Go | ~150 | Moderate | Proxy/networking |
| 30 | nats-io/nats-server | Go | ~100 | Moderate | Messaging |

## Diversity Coverage

| Dimension | Spread |
|-----------|--------|
| Languages | Go (8), Rust (5), TypeScript (5), Python (4), Java (2), C++ (2), C (1), Zig (1), JavaScript (1), Multi (1) |
| Team size | Small OSS (svelte, nats, cli/cli) → mid (pnpm, biome, deno) → large company (k8s, vscode, grafana, elastic) |
| Domains | Infra/cloud, databases, web frameworks, languages/runtimes, ML/AI, dev tools, observability, messaging |
| Issue linking | 100% (arrow, tidb) → 95% (k8s, vscode, cockroach) → 70-90% → 30-55% → 20% (uv) |

## Study Design Notes

- **Tier A repos** validate that UPFRONT/CATCHRATE classify correctly on well-structured PRs
- **Tier C repos** provide the natural spec'd/unspec'd split within the same codebase — strongest comparison because it controls for team, tooling, and domain
- **Tier D repos** test whether the tools handle low-linking gracefully and whether PR body quality substitutes for issue linking
- **Apache Kafka** is the only JIRA-convention repo — tests PROJ-NNNNN pattern detection
- **Complexity bucketing** (small/medium/large by lines changed) should show specs mattering more in medium and large PRs across all tiers

## Runner Script (TODO)

```bash
#!/bin/bash
REPOS=(kubernetes/kubernetes cockroachdb/cockroach ...)
for repo in "${REPOS[@]}"; do
  upfront report --repo "$repo" --json "data/upfront-${repo//\//-}.json"
  catchrate check --repo "$repo" --json "data/catchrate-${repo//\//-}.json"
done
# Aggregate: python aggregate.py data/ --output study-results.json
```
