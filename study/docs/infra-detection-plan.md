# Infrastructure & Culture Detection Plan

## Goal

Define tiers by PROCESS/INFRASTRUCTURE metrics (independent variable), then test whether these predict OUTCOME metrics (rework, escape) as the dependent variable. This avoids the circularity problem of defining tiers by the outcome itself.

## The Pattern (from book research)

Every successful AI-assisted delivery system shares these layers:

| Layer | What they all have | Specific tools |
|-------|-------------------|----------------|
| **Agent** | Single-agent architecture (not multi-agent) | Claude Code, Codex, Cursor, Goose |
| **Model** | Claude or GPT (frontier models, not small/cheap) | Claude Sonnet, GPT-4+ |
| **Sandbox** | Isolated execution, no prod access | Containers, devboxes, network-disabled |
| **Verification** | Automated gates before human review | CI, deterministic verifiers, LLM-as-judge |
| **Context** | Structured project context files | CLAUDE.md, AGENTS.md, blueprints, version-controlled prompts |
| **Human review** | All PRs reviewed by humans. No exceptions. | GitHub PR review |
| **Foundation** | Pre-existing CI/CD, testing, and platform maturity | Backstage, Fleet Management, monorepo tooling |

## Quality Gate Tiers (from Chapter 7)

| Tier | What it catches | Examples |
|------|----------------|----------|
| **Tier 0: Static Analysis** | Type errors, formatting, secrets, PR size | Linting, type checking, secret detection, PR size limits |
| **Tier 1: Contract Gates** | API contract drift, schema validation | Interface checks, input/output format verification |
| **Tier 2: Invariant Gates** | Business rule violations, state transition errors | Idempotency, no double charges, ordering constraints |
| **Tier 3: Policy Gates** | Security, compliance, permission violations | OWASP checks, PII handling, permission boundaries, sandbox |
| **Tier 4: Behavioral Gates** | Drift, anomalies, regression under load | Trace grading, behavioral baselines, canary analysis |

## Detection Signals

### Detectable from PR data (already have)

| Signal | How detected | Measures |
|--------|-------------|----------|
| CI enforcement | % PRs with ci_status != 'no_checks' | Foundation: CI exists |
| CI strictness | % of CI runs that failed | Foundation: CI catches things |
| Approval rate | % PRs with 'approved' review state | Human review: required approvals |
| Changes requested rate | % PRs with 'changes_requested' state | Human review: pushback culture |
| Comment density | avg total_comments_count per PR | Culture: discussion depth |
| Review substance | % reviews with body > 20 chars | Culture: substantive feedback |
| Bot reviewers | distinct bot reviewers (sourcery, codecov) | Verification: automated review |
| Conventional commits | % commits starting feat:/fix:/chore: | Foundation: commit discipline |
| Test PR rate | % PRs with 'test' in title | Foundation: test culture |
| Spec/ticket linking | % PRs with ticket_ids populated | Context: traceability |
| PR template usage | % PRs with consistent body structure | Context: structured descriptions |
| AI tool usage | co-author tags by tool (copilot, cursor, claude) | Agent/Model layer |
| Review iteration | review_cycles count | Human review: iteration before merge |

### Detectable from GitHub API (need to scrape)

| Signal | API endpoint | Measures |
|--------|-------------|----------|
| CODEOWNERS | repos/{repo}/contents/CODEOWNERS | Verification: ownership model |
| Workflow count | repos/{repo}/contents/.github/workflows | Foundation: CI pipeline breadth |
| Required reviewers | repos/{repo}/branches/main/protection | Human review: enforcement |
| Branch protection | repos/{repo}/branches/main/protection | Verification: merge gates |
| Pre-commit config | repos/{repo}/contents/.pre-commit-config.yaml | Tier 0: static analysis |
| Linter configs | eslint, ruff.toml, biome.json presence | Tier 0: code quality enforcement |
| Test framework | jest.config, pytest.ini, Cargo.toml presence | Foundation: test infrastructure |
| Contributing guide | CONTRIBUTING.md presence | Context: onboarding process |
| CLAUDE.md/AGENTS.md | repos/{repo}/contents/CLAUDE.md | Context: AI-specific guidance |

### NOT detectable from GitHub (would need code analysis)

| Signal | Why | Measures |
|--------|-----|----------|
| Sandbox isolation | Docker configs don't prove runtime isolation | Sandbox layer |
| Invariant tests | Would need to parse test code for business rules | Tier 2 |
| Policy enforcement | Security scanning is usually vendor-specific | Tier 3 |
| Behavioral monitoring | Requires production observability access | Tier 4 |
| Model quality | Which model is used in AI assistance | Model layer |

## Data Gaps (as of 2026-03-26)

### Repos needing full re-fetch (missing commits, comments, review bodies)

1. cockroachdb/cockroach
2. django/django
3. elastic/elasticsearch
4. envoyproxy/envoy
5. facebook/react
6. grafana/grafana
7. kubernetes/kubernetes
8. n8n-io/n8n
9. prometheus/prometheus
10. tailwindlabs/tailwindcss

### Repos needing partial re-fetch (incomplete fields)

11. python/cpython (missing review_body)
12. rust-lang/rust (missing commits, comments, last_edited)
13. calcom/cal.com (only 10/1364 with commits)
14. oven-sh/bun (only 50/509 with commits)
15. PostHog/posthog (only 377/844 with commits)

## Analysis Plan

1. **Re-fetch 15 repos** with updated GraphQL adapter
2. **Scrape repo-level signals** from GitHub API for all 43 repos
3. **Build infra score** from detectable signals (NOT outcomes)
4. **Build culture score** from PR interaction signals (NOT outcomes)
5. **Test each independently** against rework and escape (repo-level Spearman, N=42)
6. **Test combination** — does infra + culture together predict better?
7. **Control for maturity** (repo age, author count) to isolate the signal
8. **If significant**: this is the non-circular finding — process predicts outcomes

## Current Results (with incomplete data)

With N=33 repos (excluding 9 with missing comment data):
- Culture composite (comments + review cycles + specs): ρ=-0.376 vs rework (p=0.031), ρ=-0.373 vs escape (p=0.032)
- Infrastructure composite (test PRs + review modifications): ρ=-0.011 vs rework (p=0.95) — NOT predictive
- Combined: ρ=-0.156 vs rework (p=0.38) — infra dilutes culture signal

**Problem**: infra measures are poor. CI coverage/fail rate correlate POSITIVELY with defects (detection bias). Need repo-level API data for better infra proxies.
