# Codex GitHub Auto Review + Agentic Evals Research Notes

Compiled on March 2, 2026 from our discussion.

## 1) How to set up auto code review in GitHub for Codex

As of March 2, 2026, the setup is:

1. Open [Codex web](https://chatgpt.com/codex) and connect your GitHub account.
2. Go to [Codex Settings → Code review](https://chatgpt.com/codex/settings/code-review).
3. Enable **Code review** for the repo.
4. Enable **Automatic reviews** for that repo (this is the auto-review toggle).
5. Open a PR and verify it works (or force a run with `@codex review` in a PR comment).

If you’re on a managed workspace (Business/Enterprise/Edu), an admin must first:

1. Enable the **ChatGPT GitHub Connector**.
2. Enable **Allow members to use Codex cloud**.
3. Install/authorize the connector for your org/repos.

Optional but useful: add `## Review guidelines` in your repo’s `AGENTS.md` so Codex reviews match your standards.

### Sources

- https://developers.openai.com/codex/integrations/github
- https://developers.openai.com/codex/cloud
- https://developers.openai.com/codex/enterprise/admin-setup
- https://help.openai.com/en/articles/11369540

---

## 2) Why repos may not appear in Code review settings

Most likely root cause: the GitHub connector is installed, but that repo/org isn’t granted to it yet.

Try this in order:

1. Wait 5–10 minutes after connecting GitHub or creating a new repo.
2. In ChatGPT, go to `Settings → Apps → GitHub → ⚙` and re-check app access:
   - correct installation target (your org vs personal account)
   - repo access includes the missing repo (or set to all repos)
3. If it’s an org repo, ask a GitHub org owner to approve/install the app and grant repo access (org policy can block it).
4. If you’re on Business/Enterprise/Edu, ask your ChatGPT workspace admin to enable:
   - `ChatGPT GitHub Connector`
   - `Allow members to use Codex cloud`
5. For a repo that still doesn’t appear, run this search in GitHub to force indexing, then wait ~10 min:
   - `repo:OWNER/REPO import`
6. Reopen Codex `Settings → Code review` and check again.

Also note: Codex cloud code review requires GitHub cloud-hosted repos (not on-prem GHES).

### Sources

- https://help.openai.com/en/articles/11145903-connecting-github-to-chatgpt-deep-resear
- https://developers.openai.com/codex/integrations/github
- https://developers.openai.com/codex/enterprise/admin-setup
- https://docs.github.com/en/organizations/managing-oauth-access-to-your-organizations-data/approving-oauth-apps-for-your-organization
- https://docs.github.com/en/organizations/managing-programmatic-access-to-your-organization/reviewing-github-apps-installed-in-your-organization

---

## 3) State of the art for agentic computing: hype vs reality

As of March 2, 2026, the state of the art is strong but still very bounded.

### Reality

- Coding agents are useful, not autonomous engineers. On harder, contamination-resistant benchmarks, top scores are still far from full automation. On SWE-Bench Pro public, Scale’s leaderboard shows top models in the ~40s resolve rate (e.g., mid-40s). OpenAI reports higher with its own scaffold (56.8%), which shows harness setup matters a lot.
- Old benchmark scores are less trustworthy now. OpenAI (Feb 23, 2026) says SWE-bench Verified is increasingly contaminated and should not be used as a frontier metric.
- Computer-use agents have improved dramatically, but are not “done.” OSWorld started with best model ~12% vs human ~72%. OSWorld-Verified (Jul 2025) reports best systems around ~60.8%, still below human baseline (~72%).
- Task horizon is rising fast, reliability is still the bottleneck. METR’s Jan 29, 2026 update shows frontier 50%-success horizons in the multi-hour range (e.g., Opus 4.5 at ~320 min, GPT-5 at ~214 min in their setup), but that is not equivalent to robust end-to-end autonomy.
- Evaluation noise is a first-class issue. Anthropic (Feb 2026) found infra config alone can swing Terminal-Bench by up to 6 points, and says <3-point leaderboard gaps deserve skepticism unless configs are matched.

### Hype

- “Agents can replace whole teams today.” False for most real workflows; oversight and retries are still required.
- “Leaderboard winner = best in production.” Often false; scaffold/infrastructure differences can dominate small score gaps.
- “One general agent works reliably across arbitrary tools and environments.” Not yet; systems are still brittle under UI drift, ambiguous specs, and long error chains.
- “Multi-agent orchestration automatically solves reliability.” Not by itself; it helps throughput/search, but adds complexity and new failure modes.

### Best practical mental model

- [Inference] Treat today’s agents as high-leverage copilots + semi-autonomous workers for scoped tasks, not independent operators.
- [Inference] They perform best with: narrow scope, strong tool interfaces, deterministic checks, human approval on consequential actions, and strong eval loops.

### Sources

- https://openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/
- https://scale.com/leaderboard/swe_bench_pro_public
- https://scaleapi.github.io/SWE-bench_Pro-os/
- https://openai.com/index/introducing-gpt-5-3-codex/
- https://metr.org/blog/2026-1-29-time-horizon-1-1/
- https://metr.org/blog/2025-03-19-measuring-ai-ability-to-complete-long-tasks/
- https://os-world.github.io/
- https://xlang.ai/blog/osworld-verified
- https://www.anthropic.com/engineering/infrastructure-noise
- https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents

---

## 4) Standards for building evals, and the deterministic feedback gap

Short answer: yes, but fragmented. As of March 2, 2026, there is no single “agent eval standard” everyone uses.

### What’s real today

- There are governance/risk standards: NIST AI RMF (voluntary), NIST GenAI Profile, ISO/IEC 42001 (AI management system), ISO/IEC 23894 (AI risk management).
- There are emerging standardization efforts for agents: IEEE P3777 exists, but it is still Active PAR (in development, not a finished standard).
- In the EU, AI Act harmonized standards are being developed; the Commission says standards are still under development and use remains voluntary (with legal presumption if adopted).

### De facto engineering standards (what strong teams actually do)

- Reproducible harnesses with isolated environments (Docker/K8s). SWE-bench explicitly requires Docker for reproducibility.
- Deterministic graders where possible, then LLM/human grading for softer dimensions.
- Multi-run statistics for non-determinism (`pass@k`, `pass^k`), not single-shot scores.
- Full trace logging + trace grading to debug why an agent failed, not just whether it failed.

### Where the deterministic-feedback critique is right

- Deterministic feedback infra is a core bottleneck.
- Anthropic shows infra config alone moved Terminal-Bench 2.0 by 6 percentage points.
- MLCommons explicitly says current agentic benchmarks are often not sufficient for real deployment decisions and that reliable benchmarking capacity is still immature.
- [Inference] So the gap is less “no benchmarks exist” and more “benchmark infrastructure is not yet standardized enough to trust small score deltas across setups.”

### Sources

- https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-ai-rmf-10
- https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence
- https://airc.nist.gov/
- https://www.iso.org/standard/42001
- https://www.iso.org/standard/77304.html
- https://standards.ieee.org/ieee/3777/12350/
- https://digital-strategy.ec.europa.eu/en/policies/ai-act-standardisation
- https://mlcommons.org/ailuminate/agentic/
- https://www.swebench.com/SWE-bench/reference/harness/
- https://www.swebench.com/SWE-bench/faq/
- https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
- https://www.anthropic.com/engineering/infrastructure-noise
- https://developers.openai.com/api/docs/guides/agent-evals
- https://developers.openai.com/api/docs/guides/trace-grading

---

## 5) Minimal eval + observability stack for agent systems

As of March 2, 2026, the practical pattern is:

1. Instrument agent runs as traces first (not just final outputs).
2. Grade both outputs and traces (deterministic graders first, LLM judges second).
3. Run evals continuously in CI and production traffic slices.

### Minimal stack (works today)

1. Tracing
- Use built-in tracing from your agent runtime (for OpenAI Agents SDK, tracing is on by default and includes LLM/tool/handoff/guardrail spans).
- Export to one backend first; add second backend later only if needed.
- Propagate W3C trace headers (`traceparent`/`tracestate`) across services.

2. Telemetry schema
- Use OpenTelemetry as the transport.
- For GenAI fields, pick one schema and pin versions.
- Important caveat: OpenTelemetry GenAI semantic conventions are still marked Development, so expect churn.
- [Inference] In practice, many teams use OpenInference conventions for richer AI span attributes while keeping OTEL transport.

3. Deterministic feedback layer
- Add rule/code-based graders before LLM-as-judge:
  - exact/contains checks
  - JSON/schema validity
  - tool argument validation
  - unit/integration test pass/fail
- If using OpenAI graders, Python graders run sandboxed (no network, bounded runtime/resources), which is useful for deterministic checks.

4. Eval runner
- Keep a versioned dataset of tasks and expected outcomes.
- Run small eval suite on every PR; full suite nightly.
- Track pass rate, latency, token/cost, and failure type over time.

5. Online evaluation + alerting
- Sample production traces.
- Auto-grade sampled runs (or run scheduled grading jobs).
- Alert on regressions in success rate/latency/cost and on failure clusters.

6. Automation plumbing
- Use webhooks for eval/run events and verify signatures before triggering automation.

### Where determinism comes from

- Containerized execution for eval workloads is key (SWE-bench explicitly requires Docker for reproducible environments).
- [Inference] Add infra metadata to every run (image hash, SDK versions, model version, region, timeout caps), because infra differences can materially move benchmark scores.

### Sources

- https://openai.github.io/openai-agents-python/tracing/
- https://developers.openai.com/api/docs/guides/agent-evals
- https://developers.openai.com/api/docs/guides/trace-grading
- https://developers.openai.com/api/docs/guides/evals
- https://developers.openai.com/api/docs/guides/evaluation-best-practices
- https://developers.openai.com/api/docs/guides/graders
- https://developers.openai.com/api/docs/guides/webhooks
- https://www.w3.org/TR/trace-context/
- https://opentelemetry.io/docs/specs/semconv/gen-ai/
- https://github.com/Arize-ai/openinference
- https://arize-ai.github.io/openinference/spec/semantic_conventions.html
- https://www.swebench.com/SWE-bench/reference/harness/
- https://www.swebench.com/SWE-bench/faq/
- https://www.anthropic.com/engineering/infrastructure-noise

---

## 6) Proposed Book Outline: *AI-Accelerated Developer* (practical, anti-hype)

### Positioning

- Audience: working developers, staff+ engineers, engineering managers.
- Promise: become meaningfully faster with AI while increasing code quality, reliability, and career durability.
- Throughline: AI leverage comes from systems (workflow + eval + judgment), not prompt tricks.

### Part I: Reset the Mental Model

#### Chapter 1: The New Production Function for Software
- Core idea: output is now `human judgment x AI throughput x org quality systems`.
- Explain why “replace developers” is the wrong framing.
- Figure ideas:
  - Throughput vs reliability frontier curve.
  - Task decomposition: automate, accelerate, human-only.
- Case studies:
  - One small feature shipped with and without AI workflow.

#### Chapter 2: Hype, Reality, and Benchmark Literacy
- Core idea: learn to read benchmark claims critically.
- Cover contamination, harness effects, infra noise, pass@k, and external validity.
- Figure ideas:
  - “Leaderboard delta vs real-world confidence” chart.
  - Benchmark risk checklist.
- Case studies:
  - SWE-bench style delta under different harness settings.

#### Chapter 3: Your Durable Moat as a Developer
- Core idea: what compounds in value: architecture, debugging, domain judgment, communication.
- Map skills into declining/flat/rising value bands.
- Figure ideas:
  - Skill moat matrix (automation risk vs business impact).
- Case studies:
  - Senior engineer intervention points where agent runs fail.

### Part II: Build the AI-Native Workbench

#### Chapter 4: The Practical Toolchain
- Core idea: editor agent, CLI agent, CI agent, and tracing backend as one loop.
- Introduce minimal stack and dependency choices.
- Figure ideas:
  - Reference architecture: IDE <-> agent runtime <-> tools <-> eval backend.
- Case studies:
  - Day-1 setup in a greenfield repo.

#### Chapter 5: Context Engineering Over Prompt Engineering
- Core idea: quality comes from curated context, not clever wording.
- Cover repo maps, coding standards, test contracts, and retrieval boundaries.
- Figure ideas:
  - Context precision/recall diagram for code tasks.
- Case studies:
  - Same task with raw prompt vs structured context pack.

#### Chapter 6: Workflow Patterns That Actually Work
- Core idea: reliable patterns: spec -> scaffold -> tests -> implementation -> review -> eval.
- Introduce bounded autonomy and approval gates.
- Figure ideas:
  - Human-in-the-loop workflow states.
- Case studies:
  - PR lifecycle with automatic review and remediation loop.

### Part III: Evals and Observability as the Core Advantage

#### Chapter 7: Minimal Deterministic Eval Stack
- Core idea: deterministic feedback is the force multiplier.
- Include offline dataset evals + CI gates + nightly deep runs.
- Figure ideas:
  - Eval pyramid (unit graders -> integration -> scenario).
  - Scorecard template: success, latency, cost, regressions.
- Case studies:
  - Regression caught by schema/tool-arg grader before merge.

#### Chapter 8: Instrumentation and Trace-Driven Debugging
- Core idea: no trace, no trust.
- Cover traces, spans, tool calls, retries, and failure taxonomies.
- Figure ideas:
  - Trace anatomy for one agent run.
  - Failure heatmap by step type.
- Case studies:
  - Diagnosing flaky agent behavior with trace grading.

#### Chapter 10: Production Guardrails and Reliability Engineering
- Core idea: agent reliability is an SRE problem.
- Cover timeouts, retries, backoff, circuit breakers, policy checks.
- Figure ideas:
  - Reliability budget dashboard.
- Case studies:
  - Incident postmortem: silent degradation due to model/version drift.

### Part IV: Secure, Compliant, and Scalable by Default

#### Chapter 11: Cost, ROI, and Weekly Metrics That Matter
- Core idea: cost optimization is architecture + policy, not just cheaper models.
- Cover caching, routing, budget caps, and model fallback policies.
- Figure ideas:
  - Cost per accepted PR / cost per resolved ticket trendline.
- Case studies:
  - 40% spend reduction with routing + eval-gated quality.

#### Chapter 12: Governance, Policy, and Organizational Buy-In
- Core idea: map regulation to concrete engineering controls; win adoption with stakeholder-specific success criteria.
- Cover NIST/ISO-aligned controls, logging, approvals, auditability, and political mechanics.
- Figure ideas:
  - Policy-to-control traceability matrix.
- Case studies:
  - Passing an internal compliance review with automated evidence.

### Part IV: Career Durability and Upside

#### Chapter 15: The Productivity Trap and the Integration Gap
- Core idea: more generated code does not equal more delivered value.
- Cover metric substitution, local optimization, ownership blur, and top-5% team patterns.
- Figure ideas:
  - Trap diagnostic checklist.
- Case studies:
  - Quarter that looked fast but delivered poorly.

#### Chapter 16: Your Durable Moat as a Developer
- Core idea: career progression now includes workflow design and eval literacy.
- Define new competencies and portfolio artifacts.
- Figure ideas:
  - Competency ladder for AI-native engineers.
- Case studies:
  - Mid-level to staff transition via platform-level impact.

#### Chapter 17: Portfolio Proof and Anti-Patterns
- Core idea: evidence packets beat narrative in hiring and promotion.
- Cover proof language, anti-patterns, and portfolio maintenance cadence.
- Figure ideas:
  - Portfolio evidence packet layout.
- Case studies:
  - Rolling out agent workflows across 3 squads.

#### Chapter 16: 90-Day Transition Plan
- Core idea: execute in phases: baseline, pilot, hardening, scale.
- Include scorecards and go/no-go checkpoints.
- Figure ideas:
  - 90-day roadmap with metrics gates.
- Case studies:
  - Pilot-to-production plan with failure criteria.

### Appendix Pack (highly practical)

- Appendix A: AI-native PR checklist.
- Appendix B: Agent eval template (YAML/JSON schema).
- Appendix C: Trace taxonomy and failure labels.
- Appendix D: Security red-team prompts for coding agents.
- Appendix E: Metrics dashboard starter (quality, speed, cost, reliability).
- Appendix F: Reading list with annotated papers/reports.

### Suggested Signature Artifacts for the Book

- 1 end-to-end repository case study with before/after metrics.
- 1 reproducible benchmark lab notebook (infra config pinned).
- 1 production incident + postmortem + fixed control.
- 1 career development worksheet (skills gap -> 12-week plan).

### Research Backlog to Complete Before Drafting

1. Collect 3-5 high-quality productivity studies with effect sizes and caveats.
2. Build a benchmark-claims rubric (contamination, harness parity, infra parity, variance).
3. Create a deterministic grader catalog (schema, tool args, tests, policy checks).
4. Draft one reference architecture diagram for small team and one for enterprise.
5. Gather 2-3 real anonymized agent failure traces and convert to teaching examples.
6. Define a standard metrics dictionary used consistently across all chapters.

---

## 7) Chapter-by-Chapter Writing Brief (Drafting Spec)

Use this as the production brief for first manuscript pass. Word counts are target ranges for the main chapter body (excluding references/appendices).

### Global rules for every chapter

- Include explicit labels for claims:
  - `Evidence-backed` (supported by cited source)
  - `Inference` (reasoned synthesis)
  - `Opinion` (author recommendation)
- Include one concrete developer workflow example per chapter.
- End each chapter with:
  - Practical action section — structured as rhythm/habit, not "Monday morning" lists (reserve "Monday morning" framing only for chapters with genuinely urgent week-one actions)
  - `Failure modes to avoid` (3-5 pitfalls)
- Prefer primary sources, then high-quality syntheses.

### Chapter 1: The New Production Function for Software
- Target words: 2,500-3,500
- Key arguments:
  - AI changes the unit economics of software delivery but does not remove need for engineering judgment.
  - Throughput gains without quality systems increase defect leakage and rework.
  - The right optimization target is sustained value delivered per engineer-hour, not raw code volume.
- Required citations (minimum):
  - 1 labor-market/macroeconomic source
  - 2 developer productivity studies
  - 1 organization/operating-model study
- Candidate sources:
  - WEF Future of Jobs 2025
  - NBER developer productivity studies
  - DORA AI-assisted software development report

### Chapter 2: Hype, Reality, and Benchmark Literacy
- Target words: 2,000-3,000
- Key arguments:
  - Benchmark scores are directional, not absolute measures of production readiness.
  - Contamination, harness design, and infra variance can dominate claimed gains.
  - Teams need an internal benchmark-reading rubric before procurement or rollout.
- Required citations (minimum):
  - 2 benchmark methodology critiques
  - 2 benchmark result sources
  - 1 infra-variance source
- Candidate sources:
  - OpenAI SWE-bench Verified deprecation post
  - METR time-horizon reports
  - Anthropic infrastructure noise analysis

### Chapter 3: Your Durable Moat as a Developer
- Target words: 2,500-3,500
- Key arguments:
  - Durable advantage shifts toward system design, debugging, product judgment, and communication.
  - Tool fluency compounds only when paired with domain depth.
  - Career resilience requires evidence of outcomes, not tool familiarity alone.
- Required citations (minimum):
  - 1 labor/economic trend source
  - 2 capability/skills trend sources
  - 1 practical hiring or org competency framework
- Candidate sources:
  - Anthropic Economic Index
  - Stanford AI Index
  - DORA capability model

### Chapter 4: The Practical Toolchain
- Target words: 2,000-3,000
- Key arguments:
  - A minimal integrated stack beats fragmented best-of-breed tooling early on.
  - Instrumentation and evals are first-class architecture concerns.
  - Tool permissions and trust boundaries must be explicit from day one.
- Required citations (minimum):
  - 2 technical implementation docs
  - 1 observability standard
  - 1 security baseline/control source
- Candidate sources:
  - OpenAI Agents tracing docs
  - OpenTelemetry docs
  - NIST SSDF

### Chapter 5: Context Engineering Over Prompt Engineering
- Target words: 2,000-3,000
- Key arguments:
  - Structured context quality has larger performance impact than prompt cleverness.
  - Context boundaries reduce hallucination and unsafe actions.
  - Repo-specific standards and contracts are multiplicative assets.
- Required citations (minimum):
  - 2 practical implementation sources
  - 1 evaluation best-practices source
  - 1 failure-mode source
- Candidate sources:
  - OpenAI eval best practices
  - OpenAI graders/trace grading docs
  - Anthropic evals post

### Chapter 6: Workflow Patterns That Actually Work
- Target words: 2,500-3,500
- Key arguments:
  - Reliable velocity comes from repeatable workflow patterns, not ad hoc prompting.
  - Human approvals should gate high-blast-radius actions.
  - CI-native feedback loops are the backbone of safe autonomy.
- Required citations (minimum):
  - 2 workflow/tooling references
  - 1 quality engineering reference
  - 1 empirical source on outcomes/variance
- Candidate sources:
  - OpenAI API eval guides
  - DORA report
  - Internal case study data (if available)

### Chapter 7: Minimal Deterministic Eval Stack
- Target words: 2,500-3,500
- Key arguments:
  - Deterministic graders should be default; LLM judges are secondary.
  - Small PR-gate evals + nightly deep evals is the practical baseline.
  - Without versioned eval datasets, capability claims are not trustworthy.
- Required citations (minimum):
  - 3 eval methodology sources
  - 1 benchmark harness reproducibility source
  - 1 infra-variance source
- Candidate sources:
  - OpenAI eval/agent-eval guides
  - SWE-bench harness reference
  - Anthropic infrastructure noise

### Chapter 8: Instrumentation and Trace-Driven Debugging
- Target words: 2,000-3,000
- Key arguments:
  - Trace-level visibility is required for debugging multi-step agent failures.
  - Correlating tool calls, retries, and outputs turns failure analysis from guesswork into engineering.
  - Shared trace taxonomy accelerates team learning.
- Required citations (minimum):
  - 2 tracing/telemetry standards or docs
  - 1 trace grading source
  - 1 reliability/debugging case source
- Candidate sources:
  - OpenAI Agents tracing
  - W3C Trace Context
  - OpenTelemetry GenAI semantic conventions

### Chapter 10: Production Guardrails and Reliability Engineering
- Target words: 2,000-3,000
- Key arguments:
  - Agent systems require SRE-style reliability budgets and controls.
  - Timeouts/retries/backoff/circuit breakers are mandatory design primitives.
  - Reliability posture must be measured continuously, not audited occasionally.
- Required citations (minimum):
  - 2 reliability engineering sources
  - 1 agent-eval production guidance source
  - 1 incident pattern source
- Candidate sources:
  - OpenAI webhooks/evals docs
  - Anthropic eval guidance
  - Internal incident/postmortem evidence

### Chapter 11: Cost, ROI, and Weekly Metrics That Matter
- Target words: 2,000-3,000
- Key arguments:
  - Cost should be tied to accepted outcomes, not request volume.
  - Model routing/caching/budget controls are architectural responsibilities.
  - ROI reporting must include quality and reliability, not only speed.
- Required citations (minimum):
  - 1 productivity evidence source
  - 1 engineering metrics framework source
  - 1 operations/cost case source
- Candidate sources:
  - NBER productivity studies
  - DORA metrics framing
  - Internal cost/perf dashboards

### Chapter 12: Governance, Policy, and Organizational Buy-In
- Target words: 2,000-3,000
- Key arguments:
  - Governance can be translated into specific engineering controls and evidence.
  - Policy-to-control traceability reduces compliance drag.
  - Buy-in requires stakeholder-specific success criteria and phased evidence.
- Required citations (minimum):
  - 2 governance/risk standards
  - 1 regulatory source
  - 1 implementation guide/reference
- Candidate sources:
  - NIST AI RMF + GenAI profile
  - ISO/IEC 42001 and 23894
  - EU AI Act policy pages

### Chapter 15: The Productivity Trap and the Integration Gap
- Target words: 2,000-3,000
- Key arguments:
  - More generated code does not equal more delivered value.
  - Top teams win by integrating and recovering faster, not typing faster.
  - Metric substitution and ownership blur drive the trap.
- Required citations (minimum):
  - 1 productivity evidence source
  - 1 engineering metrics framework source
  - 1 CI/delivery data source
- Candidate sources:
  - CircleCI 2026 report
  - DORA metrics framing
  - METR productivity study

### Chapter 16: Your Durable Moat as a Developer
- Target words: 2,000-3,000
- Key arguments:
  - Career progression now includes workflow and eval system design.
  - High leverage comes from solving cross-team bottlenecks.
  - Portfolio artifacts should show measurable AI-enabled impact.
- Required citations (minimum):
  - 1 workforce trend source
  - 1 skills/capability source
  - 1 org operating model source
- Candidate sources:
  - WEF Future of Jobs
  - Stanford AI Index
  - DORA capability model

### Chapter 17: Portfolio Proof and Anti-Patterns
- Target words: 2,000-3,000
- Key arguments:
  - Evidence packets beat narrative in hiring and promotion decisions.
  - Proof language requires measured outcomes and caveats.
  - Anti-patterns create hidden career drag.
- Required citations (minimum):
  - 1 org performance source
  - 1 software delivery/DevEx source
  - 1 implementation playbook or case study
- Candidate sources:
  - DORA report
  - SPACE framework
  - StaffEng archetypes

### Chapter 16: 90-Day Transition Plan
- Target words: 2,500-3,500
- Key arguments:
  - Adoption should be phased: baseline -> pilot -> hardening -> scale.
  - Every phase needs pre-defined success/fail criteria.
  - Scaling without control maturity amplifies risk and spend.
- Required citations (minimum):
  - 1 change management source
  - 1 engineering productivity source
  - 1 reliability/governance source
- Candidate sources:
  - DORA
  - NIST AI RMF/SSDF
  - Internal pilot metrics

### Manuscript-level citation and quality gates

- Minimum chapter citations: 4 (hard floor), target 6-10.
- Minimum primary-source ratio: 70%.
- Any single quantitative claim must cite a direct source.
- Any benchmark claim must include:
  - task definition
  - harness/environment note
  - metric definition
  - uncertainty caveat
- Add `Limitations` subsection in each chapter.

### Drafting sequence (recommended)

1. Draft Chapters 7-9 first (evals/observability/reliability core).
2. Draft Chapters 4-6 next (toolchain/workflows/context engineering).
3. Draft Chapters 1-3 next (framing and career moat).
4. Draft Chapters 10-12 next (security/governance/cost).
5. Draft Chapters 13-16 last (leadership, roadmap, future view).

### Done criteria per chapter

1. Word count within range.
2. Required citations met.
3. At least one concrete workflow example included.
4. Includes Monday-morning actions and failure modes.
5. Claims labeled as Evidence-backed / Inference / Opinion.
6. Limitations section present.

---

## 8) Progress Plan + Ahead-of-Curve Topics

As of March 2, 2026, the fastest path forward is to make this book evidence-heavy and execution-heavy.

### Immediate Progress Plan (High Impact)

1. Build a `claims ledger` for every chapter:
   - fields: claim, evidence type, source link, confidence level, counterargument.
2. Add three longitudinal case studies you can re-measure:
   - solo developer workflow
   - small team workflow
   - enterprise-ish workflow
3. Create a companion "eval lab" repository:
   - repeatable tasks
   - deterministic graders
   - CI gates and regression snapshots
4. Run structured interviews (11-20):
   - senior ICs
   - engineering managers
   - staff/platform engineers
   - security leads
5. Add a dedicated failure chapter:
   - real postmortems
   - which controls failed
   - what controls fixed recurrence
6. Define chapter acceptance criteria now:
   - each chapter includes metrics, limits, and Monday-morning playbook.
7. Add a 10-minute hype-audit rubric readers can apply to any vendor claim.

### Topics Developers Need to Master to Get Ahead

1. Eval engineering as a core skill (deterministic graders first, LLM judges second).
2. Trace-first observability (span-level debugging for tools, retries, handoffs).
3. Agent contract design (strict schemas, idempotency, validation, rollback).
4. Reliability/SRE for agents (SLOs, timeout budgets, retry envelopes, drift detection).
5. Security for tool-using agents (prompt injection, excessive agency, exfiltration).
6. AI supply-chain integrity (provenance, signing, attestation, dependency risk).
7. Protocol literacy (MCP evolution and interoperability tradeoffs).
8. Cost engineering (routing, caching, eval-gated model selection, per-outcome ROI).
9. Governance by automation (policy checks in CI and default audit trails).
10. Career moat design (architecture judgment, debugging depth, domain expertise, communication leverage).

### High-Signal Points to Emphasize in the Book

1. OpenTelemetry GenAI semantic conventions are still marked `Development`, so telemetry schema churn is expected.
2. MCP is evolving quickly with dated protocol revisions; compatibility strategy matters.
3. DORA 2025 framing is more practical than replacement narratives: AI amplifies existing team strengths and weaknesses.
4. Security and compliance pressure is increasing (NIST/ISO/EU); engineers who map policy to controls gain disproportionate leverage.

### Sources

- https://dora.dev/research/2025/dora-report/
- https://opentelemetry.io/docs/specs/semconv/gen-ai/
- https://modelcontextprotocol.io/specification/
- https://modelcontextprotocol.io/specification/2025-11-25/basic/transports
- https://owasp.org/www-project-top-10-for-large-language-model-applications/
- https://slsa.dev/
- https://scorecard.dev/
- https://docs.sigstore.dev/quickstart/quickstart-cosign/
- https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence
- https://digital-strategy.ec.europa.eu/en/policies/contents-code-gpai

---

## 9) Maximum-Impact AI Usage for Developers

Maximum-impact developers use AI as a force multiplier with hard verification, not as autopilot.

### Mental Model

1. Treat AI as a fast junior+pair programmer; keep architecture and correctness ownership.
2. Optimize for `validated outcomes/hour`, not `lines/hour`.
3. Split work into low-risk automation and high-risk human decisions.

### Core Skills

1. Task decomposition:
   - break work into small, testable units with explicit acceptance criteria.
2. Context engineering:
   - provide repository rules, architecture constraints, examples, and known failure patterns.
3. Eval design:
   - write deterministic checks first (tests, schema checks, linters, contract tests).
4. Trace debugging:
   - inspect tool calls, retries, and intermediate outputs, not just final answers.
5. Risk control:
   - apply least privilege for tools, approval gates for destructive actions, and rollback plans.
6. Cost/performance judgment:
   - choose model/workflow by task criticality, latency sensitivity, and budget.

### High-Leverage Practices

1. Use a repeatable workflow loop:
   - `spec -> scaffold -> tests -> implement -> review -> eval`.
2. Require AI-generated changes to pass the same CI quality gates as human-authored code.
3. Maintain a repository playbook:
   - `AGENTS.md`, coding standards, architecture map, and review rules.
4. Run small eval suites on every PR and broader eval suites nightly.
5. Track personal/team metrics weekly:
   - cycle time
   - defect rate
   - rework percentage
   - AI assist rate by task type
6. Perform short postmortems on AI misses and convert lessons into new tests/checks.

### Mindset Shifts That Separate Top Performers

1. From prompt writing to system design for reliability.
2. From trusting output to trusting evidence.
3. From single-shot answers to instrumented iteration.
4. From tool user to workflow owner.

---

## 10) Missing Topics to Cover

These are high-value gaps most AI/developer books under-cover and should be included explicitly.

1. Where AI should not be used:
   - decision framework for high-risk domains and low-signal tasks.
2. Skill atrophy prevention:
   - drills/practices that preserve debugging and design ability under heavy AI use.
3. AI failure postmortems:
   - real bad-merge examples with root cause and preventive controls.
4. Build vs buy for agent platforms:
   - lock-in, portability, data residency, and total-cost tradeoffs.
5. Legal/IP and OSS provenance:
   - generated code policy, license hygiene, attribution workflows.
6. Data governance for dev workflows:
   - secrets handling, PII boundaries, retention, and redaction defaults.
7. Adoption by role and seniority:
   - different playbooks for junior ICs, senior ICs, managers, and platform teams.
8. Legacy codebase strategy:
   - safe AI adoption patterns for monoliths and low-test-coverage systems.
9. Org politics and change management:
   - alignment tactics across engineering, security, compliance, and leadership.
10. Career portfolios for the AI era:
   - artifacts that prove leverage in hiring and promotion.
11. Hands-on labs:
   - practical exercises with expected outputs and grading criteria.
12. Anti-pattern catalog:
   - "looks productive now, causes drag later" behaviors and how to avoid them.

---

## 11) Deep Dive: Topics 8-12 (with references)

### 8. Legacy codebase strategy: safe AI use in monoliths and low-test-coverage systems

#### Why this matters

- AI can accelerate edits faster than a legacy codebase can safely absorb them.
- In low-test-coverage repos, the bottleneck is not generation speed; it is confidence and blast-radius control.
- [Inference] The winning pattern is "stabilize before accelerate": increase observability and behavioral safety nets first, then increase AI autonomy.

#### Practical strategy (chapter-ready)

1. Stabilize boundaries first:
   - identify high-churn, high-incident modules
   - define seams/interfaces around those modules before replacement work
2. Capture current behavior:
   - add characterization/golden-master tests around critical paths
   - lock down I/O contracts (API schemas, DB shape, key invariants)
3. Migrate incrementally, not via big-bang rewrites:
   - use Strangler and Branch-by-Abstraction patterns to run old/new paths side-by-side
   - gate rollout with feature flags and diff-based canaries
4. Constrain AI to low-regret operations first:
   - safe refactors, test scaffolding, adapter/interface extraction, documentation synchronization
   - require human approval for schema changes, cross-cutting architecture edits, and deletion-heavy diffs
5. Enforce deterministic gates:
   - fast PR gates (unit + contract + schema checks)
   - deeper nightly gates (integration + regression)
   - require rollback plan on risky changes

#### Monolith-specific guardrails

- Set a per-PR risk budget:
  - max files changed
  - max public-interface changes
  - no mixed refactor+feature PRs in critical modules
- Require "compatibility windows" when replacing components:
  - both implementations available behind one abstraction
- Add release evidence to PR template:
  - behavior diff summary
  - test delta
  - rollback procedure

#### Suggested references

- Martin Fowler, Strangler Fig pattern: https://martinfowler.com/bliki/StranglerFigApplication.html
- Martin Fowler, Branch by Abstraction: https://martinfowler.com/bliki/BranchByAbstraction.html
- Martin Fowler, Workflows of Refactoring: https://martinfowler.com/articles/workflowsOfRefactoring/fallback.html
- AWS Prescriptive Guidance (Strangler Fig): https://docs.aws.amazon.com/prescriptive-guidance/latest/cloud-design-patterns/strangler-fig.html
- NIST SSDF (SP 800-218): https://csrc.nist.gov/pubs/sp/800/218/final
- OpenAI eval best practices: https://platform.openai.com/docs/guides/evaluation-best-practices
- SWE-bench harness reproducibility (Docker): https://www.swebench.com/SWE-bench/reference/harness/
- Feathers, *Working Effectively with Legacy Code* (book; characterization tests)

### 9. Org politics and change management: winning buy-in from security, compliance, and leadership

#### Why this matters

- Technical quality alone does not unlock adoption.
- Security asks "what can go wrong?"; compliance asks "can we prove control?"; leadership asks "what business result do we get?"
- [Inference] Adoption succeeds when all three groups see their success criteria in the rollout plan.

#### Stakeholder-aligned rollout model

1. Security lane (risk containment):
   - threat model for agent workflows (prompt injection, excessive agency, data exfiltration)
   - least-privilege tool scopes and approval gates
   - red-team checks and incident playbooks
2. Compliance lane (evidence and traceability):
   - policy-to-control mapping (who approved what, where logs live, retention/redaction)
   - auditable documentation and periodic control tests
3. Leadership lane (business outcomes):
   - baseline and target metrics: cycle time, defect escape, rework, MTTR, cost per accepted PR
   - phased pilot with hard stop/go criteria

#### 30/60/90 day political strategy

1. Days 0-30:
   - run a small pilot in one low-risk team
   - establish baseline metrics and top 3 risks
2. Days 31-60:
   - introduce policy-backed guardrails and evaluator gates
   - publish first measured wins and first avoided failures
3. Days 61-90:
   - scale to 2-3 teams with shared standards
   - formalize ownership: platform, security, and team-level responsibilities

#### Artifacts that unlock buy-in

- 1-page risk register with controls
- policy-to-control matrix
- pilot scorecard (before/after)
- incident/postmortem template specific to AI-assisted changes

#### Suggested references

- DORA 2025 (AI amplifies existing strengths/weaknesses): https://dora.dev/research/2025/dora-report/
- NIST AI RMF 1.0: https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-ai-rmf-10
- NIST AI RMF Playbook: https://www.nist.gov/itl/ai-risk-management-framework/nist-ai-rmf-playbook
- NIST GenAI Profile: https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence
- OWASP Top 10 for LLM Apps: https://owasp.org/www-project-top-10-for-large-language-model-applications/
- ISO/IEC 42001 (AI management systems): https://www.iso.org/standard/81230.html
- ISO/IEC 23894 (AI risk management): https://www.iso.org/standard/77304.html
- EU AI Act timeline (official): https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai
- AI Office GPAI Code process: https://digital-strategy.ec.europa.eu/en/library/ai-office-invites-providers-sign-gpai-code-practice

### 10. Career portfolios for the AI era: artifacts that prove leverage in hiring and promotion

#### Why this matters

- "Used AI tools" is weak evidence.
- Hiring/promotion decisions favor repeated, measurable impact under constraints.
- [Inference] The strongest portfolio shows that you improved speed, quality, reliability, and organizational capability at the same time.

#### Portfolio structure (what to include)

1. Impact dossier (quantified outcomes):
   - before/after metrics for at least 2 projects
   - include throughput + instability + cost
2. Technical judgment artifacts:
   - ADRs, design docs, tradeoff memos
   - examples where you rejected high-risk AI suggestions and why
3. Reliability and safety artifacts:
   - postmortems, runbooks, risk controls, rollback evidence
4. Enablement artifacts:
   - standards/playbooks you authored
   - onboarding material that raised team capability
5. Evaluation maturity artifacts:
   - grader definitions, eval scorecards, regression trend charts

#### Promotion/hiring proof points

- "I reduced lead time by X while keeping change-fail rate at or below Y"
- "I introduced deterministic eval gates that prevented Z class of regressions"
- "I created a reusable standard used by N teams"

#### What to avoid

- raw prompt galleries without outcomes
- vanity metrics (token count, suggestion count) disconnected from business/system impact
- one-off heroics without reusable process change

#### Suggested references

- SPACE framework (multi-dimensional productivity):
  - Microsoft Research page: https://www.microsoft.com/en-us/research/publication/the-space-of-developer-productivity-theres-more-to-it-than-you-think/
  - CACM version: https://cacm.acm.org/practice/the-space-of-developer-productivity/
- DORA delivery metrics: https://dora.dev/guides/dora-metrics/
- DORA metrics history (definitions evolve): https://dora.dev/guides/dora-metrics/history
- Google SRE service best practices (operational excellence): https://sre.google/sre-book/service-best-practices/
- ADR practice reference: https://adr.github.io/
- Staff archetypes (role-shape signal): https://staffeng.com/guides/staff-archetypes

### 11. Hands-on labs: practice exercises with expected outputs

#### Lab design principles

- Each lab should have:
  - explicit objective
  - fixed inputs
  - deterministic pass/fail checks where possible
  - expected artifacts to submit

#### Recommended lab set

1. Legacy hardening lab:
   - task: add characterization tests around a brittle module
   - expected outputs: failing-then-passing tests, risk notes, rollback plan
2. Incremental monolith migration lab:
   - task: replace one module using branch-by-abstraction + flag
   - expected outputs: abstraction interface, dual implementation, migration checklist
3. Eval/grader lab:
   - task: build deterministic graders for a coding agent task
   - expected outputs: grader specs, pass/fail report, edge-case notes
4. Trace instrumentation lab:
   - task: instrument agent workflow with end-to-end traces
   - expected outputs: trace screenshots/IDs, failure classification table
5. Secure-agent lab:
   - task: identify and mitigate prompt injection / excessive-agency risks
   - expected outputs: threat model, control mapping, red-team findings
6. PR review operations lab:
   - task: run AI-assisted review with human gate criteria
   - expected outputs: review checklist, accepted/rejected suggestion log, final rationale
7. Cost-control lab:
   - task: introduce model routing and budget caps
   - expected outputs: before/after cost and latency chart, quality impact report
8. Portfolio artifact lab:
   - task: compile one promotion-ready case study packet
   - expected outputs: metrics narrative, ADR, postmortem excerpt, reusable playbook

#### Grading rubric template

- correctness (0-40)
- safety/compliance (0-20)
- reliability and rollback readiness (0-20)
- communication quality (0-20)

#### Suggested references

- OpenAI evals guide: https://platform.openai.com/docs/guides/evals
- OpenAI agent evals guide: https://platform.openai.com/docs/guides/agent-evals
- OpenAI graders guide: https://platform.openai.com/docs/guides/graders/
- OpenAI trace grading guide: https://platform.openai.com/docs/guides/trace-grading
- SWE-bench datasets: https://www.swebench.com/SWE-bench/guides/datasets/
- SWE-bench FAQ/eval process: https://www.swebench.com/SWE-bench/faq/
- OpenTelemetry demo docs: https://opentelemetry.io/ecosystem/demo/
- OpenTelemetry demo repo: https://github.com/open-telemetry/opentelemetry-demo
- OWASP Juice Shop: https://owasp.org/www-project-juice-shop/
- GitHub Skills PR review lab: https://github.com/skills/review-pull-requests

### 12. Anti-pattern catalog: high-velocity behaviors that create long-term drag

#### Anti-patterns to include in the book

1. "Benchmark theater":
   - symptom: quoting headline benchmark scores without harness details
   - fix: require reproducibility notes and variance ranges
2. "Single-metric obsession":
   - symptom: optimize speed while instability/rework rises
   - fix: use balanced multi-metric scorecards
3. "Autopilot merges":
   - symptom: accepting AI output without deterministic checks
   - fix: mandatory gate checks and reviewer accountability
4. "Big-bang AI refactors":
   - symptom: massive rewrites in low-test-coverage systems
   - fix: strangler + branch-by-abstraction + progressive rollout
5. "Context flooding":
   - symptom: dumping full repos into prompts without curation
   - fix: scoped, task-relevant context packs
6. "No trace, no diagnosis":
   - symptom: only final-output logging
   - fix: span-level trace capture and failure taxonomy
7. "Policy by PDF":
   - symptom: governance written but not encoded in CI/tooling
   - fix: automate policy checks with auditable outputs
8. "Over-privileged agents":
   - symptom: agents can take high-blast actions by default
   - fix: least privilege + human approval for destructive operations
9. "Cost-blind scaling":
   - symptom: usage grows but cost/outcome ratio degrades
   - fix: routing, caching, and budget guardrails
10. "No rollback discipline":
   - symptom: fast deploys without reversal plan
   - fix: explicit rollback section in every risky PR

#### Suggested references

- DORA 2025 report (AI amplifies system qualities): https://dora.dev/research/2025/dora-report/
- DORA metric balance guidance: https://dora.dev/guides/dora-metrics/
- SPACE framework (multi-dimensional productivity): https://cacm.acm.org/practice/the-space-of-developer-productivity/
- OWASP LLM Top 10 (overreliance, excessive agency): https://owasp.org/www-project-top-10-for-large-language-model-applications/
- NIST AI RMF: https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-ai-rmf-10
- NIST GenAI profile: https://www.nist.gov/publications/artificial-intelligence-risk-management-framework-generative-artificial-intelligence
- Anthropic infrastructure noise in coding evals: https://www.anthropic.com/engineering/infrastructure-noise
- OpenAI eval best practices: https://platform.openai.com/docs/guides/evaluation-best-practices
- Martin Fowler, Branch by Abstraction: https://martinfowler.com/bliki/BranchByAbstraction.html


---

## 12) Panic-First Table of Contents (Chapter Titles + Outcomes + Exercises)

Audience: developers who feel behind, worried about job risk, and need a concrete transition plan fast.

### Part I: Stabilize the Mindset and Map the Terrain

#### Chapter 1: Stop the Panic: Your 72-Hour Stabilization Plan
- Outcome: You leave panic mode with a practical 30-day learning and execution plan.
- Exercise: Complete a personal baseline audit (current workflow, strengths, risk areas, target role).

#### Chapter 2: How the Tech Actually Works (Without the Hype)
- Outcome: You can explain model limits, agent loops, tool use, and why verification matters.
- Exercise: Run one task with and without deterministic checks; compare outcomes.

#### Chapter 3: Task Risk Map: What Gets Automated First, What Stays Human
- Outcome: You can classify your daily work into automate/augment/human-judgment buckets.
- Exercise: Build your own task-risk matrix from one week of real work.

### Part II: Build Your Leverage System

#### Chapter 4: The Core Workflow: `spec -> scaffold -> tests -> implement -> review -> eval`
- Outcome: You can run a repeatable AI-assisted delivery loop that improves speed without quality collapse.
- Exercise: Ship one small feature end-to-end using this exact workflow and document deltas.

#### Chapter 5: Deterministic Feedback or It Didn’t Happen
- Outcome: You can design test/schema/contract/policy gates that prevent low-confidence merges.
- Exercise: Add at least 3 deterministic gates to a repo and show one prevented failure.

#### Chapter 6: Trace-First Engineering
- Outcome: You can debug AI-assisted failures from traces, not guesswork.
- Exercise: Instrument one workflow with spans and produce a failure taxonomy report.

#### Chapter 7: Context Packs That Make Agents Useful
- Outcome: You can build high-signal context packs (architecture map, standards, boundaries, failure history).
- Exercise: Create `AGENTS.md` + boundary rules for one codebase and compare output quality.

### Part III: Survive and Win in Real Organizations

#### Chapter 8: Legacy Codebase Strategy (Monoliths, Low Coverage, High Risk)
- Outcome: You can apply AI safely in brittle systems using incremental migration and blast-radius control.
- Exercise: Implement branch-by-abstraction on one legacy seam with rollback plan.

#### Chapter 10: Politics, Compliance, and Leadership Buy-In
- Outcome: You can pitch AI adoption in language security, compliance, and exec stakeholders accept.
- Exercise: Produce a one-page pilot proposal with risk controls and success/fail criteria.

#### Chapter 11: Cost, ROI, and Weekly Metrics That Matter
- Outcome: You can track lead time, defect escape, rework, and cost per accepted change.
- Exercise: Build a weekly scorecard and run it for 4 consecutive weeks.

#### Chapter 12: Governance, Policy, and Organizational Buy-In
- Outcome: You can pitch AI adoption in language security, compliance, and exec stakeholders accept.
- Exercise: Produce a one-page pilot proposal with risk controls and success/fail criteria.

### Part IV: Career Durability and Upside

#### Chapter 15: The Productivity Trap and the Integration Gap
- Outcome: You can spot output theater and distinguish it from real delivery gains.
- Exercise: Run a monthly trap check against five integration health signals.

#### Chapter 16: Your Durable Moat as a Developer
- Outcome: You can identify roles and skill clusters with lower displacement risk and higher leverage.
- Exercise: Map your current profile against the four moat dimensions and choose one weekly rep.

#### Chapter 17: Portfolio Proof and Anti-Patterns
- Outcome: You can present measurable AI-enabled impact, not tool usage anecdotes.
- Exercise: Assemble one portfolio packet (impact metrics, ADR, postmortem, reusable playbook).

#### Chapter 16: 90-Day Transition Plan
- Outcome: You have a phased plan with milestones, checkpoints, and fallback triggers.
- Exercise: Build and commit a personal 90-day roadmap with weekly deliverables.

### Suggested chapter pattern (use in every chapter)

1. What panicked developers usually get wrong
2. What actually works in production
3. One repeatable workflow
4. One measurable scorecard
5. One exercise with pass/fail criteria

