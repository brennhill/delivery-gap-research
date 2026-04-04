# Reconciled ToC Proposal

Audience: developers worried about AI reducing demand for traditional coding roles.

Date: March 3, 2026

## What to keep from current draft

1. Personal urgency and credibility from the preface.
2. Economic framing in Chapter 1 ("headcount era is over").
3. Career pressure and hiring reality in Chapter 2 ("junior gap").
4. Technical demystification in Chapter 3 (how models work, why they fail).
5. Strong framing in Chapter 4 ("context engineering over prompt magic").

## Gaps identified from `research/evals.md`

1. Task-risk classification (what to automate vs what must stay human).
2. Deterministic evals and CI gates as core workflow.
3. Trace-first debugging and reliability engineering.
4. Legacy monolith adoption strategy (low-test-coverage reality).
5. Security, governance, compliance, and auditability.
6. Cost/ROI measurement and weekly scorecards.
7. Org politics/change management for adoption.
8. Career proof artifacts (portfolio, promotion packet).
9. Anti-pattern catalog and skill-atrophy prevention.
10. A concrete 90-day transition plan.

## Reconciliation map (current draft -> final structure)

1. `00-preface.md` -> Keep as Preface with minor updates.
2. `01-end-of-an-era.md` -> Final Chapter 1 (trim repetition; keep core story).
3. `02-junior-trap` -> Final Chapter 2 (career risk) + move "durable moat" material into Chapter 16.
4. `03-the-machine-in-the-ghost.md` -> Final Chapter 3 (keep conceptual model; move very deep internals to appendix/sidebar).
5. `04-prompts.md` -> Split across:
   - Chapter 5 (context engineering),
   - Chapter 6 (workflow patterns),
   - Chapter 7 (verification/evals),
   - Chapter 8 (trace debugging setup).

## Proposed final Table of Contents

### Preface

- Why this book exists now.
- The "cyborg author" method and how to use the book.

### Part I: From Panic to Clarity

#### Chapter 1: The End of the Headcount Era
- Outcome: Understand the macro shift and why this is structural, not hype.

#### Chapter 2: The Junior Gap and the New Hiring Math
- Outcome: Understand role compression and where entry-level paths are changing.

#### Chapter 3: How the Machine Actually Works (Without the Myth)
- Outcome: Explain tokenization, context limits, hallucinations, and tool-use limits.

#### Chapter 4: Task Risk Map: Automate, Augment, or Keep Human
- Outcome: Classify your own workload by risk and automation fit.

### Part II: Build Your Personal Leverage System

#### Chapter 5: Context Engineering Over Prompt Tricks
- Outcome: Build high-signal context packs for reliable output.

#### Chapter 6: The Core Delivery Loop
- Outcome: Run `spec -> scaffold -> tests -> implement -> review -> eval` repeatably.

#### Chapter 7: Deterministic Feedback or It Didn’t Happen
- Outcome: Add tests/schema/contract/policy gates before accepting AI output.

#### Chapter 8: Trace-First Debugging and Reliability Basics
- Outcome: Debug failures from traces, retries, and tool-call evidence.

### Part III: Ship Safely in Real Codebases

#### Chapter 10: Legacy Codebase Strategy (Monoliths, Low Coverage, High Risk)
- Outcome: Apply AI safely in brittle systems with bounded blast radius.

#### Chapter 11: Cost, ROI, and Weekly Metrics That Matter
- Outcome: Measure throughput, quality, rework, latency, and cost per accepted change.

#### Chapter 12: Governance, Policy, and Organizational Buy-In
- Outcome: Map policy to engineering controls and auditable evidence; win adoption with stakeholder-specific success criteria.

### Part IV: Career Durability and Upside

#### Chapter 15: The Productivity Trap and the Integration Gap
- Outcome: Distinguish real delivery gains from output theater.

#### Chapter 16: Your Durable Moat as a Developer
- Outcome: Build compounding advantage in architecture, debugging, domain, and communication.

#### Chapter 17: Portfolio Proof and Anti-Patterns
- Outcome: Build promotion/hiring artifacts and eliminate "looks fast, creates drag" behaviors.

#### Chapter 16: Your 90-Day Transition Plan (and How to Keep Evolving)
- Outcome: Execute a phased transition plan with measurable checkpoints.

### Part V: Appendices and Evidence

#### Chapter 18 (Appendix A): State of the Art (2026 Snapshot)
- Outcome: Give readers a current map of frontier tools, benchmark realities, and practical constraints.
- Scope: curated "what changed recently and why it matters" notes with direct links.

#### Chapter 19 (Appendix B): Static Tooling and Eval Defaults by Language
- Outcome: Give readers practical static-analysis defaults by language so AI-generated code is gated before merge.
- Scope: category model, best-of tool stacks for JS/TS, Python, Go, Rust, C#, Java, and fast/full/release CI profiles.

#### Chapter 20 (Appendix C): References and Links
- Outcome: Give readers a complete bibliography and implementation link index.
- Scope: chapter-by-chapter citations, standards, benchmark sources, docs, and further reading.

#### Chapter 21 (Appendix D): The Context-Anchor Spec Template
- Outcome: Give readers a practical spec format they can use before any AI-assisted implementation.
- Scope: reusable template, filled example, and pre-implementation quality checks.

#### Chapter 22 (Appendix E): Provider-Agnostic Code Review Template
- Outcome: Give readers a reusable review checklist that works across Claude, Codex, Gemini, and human-authored changes.
- Scope: merge-gate review criteria, evidence prompts, and fast sniff test for time-constrained reviews.

## Draft link blurbs for Chapter 18 (State of the Art)

As of March 3, 2026.

### OpenAI (research + tools)

1. GPT-5.3-Codex (Feb 5, 2026)
   - Link: https://openai.com/index/introducing-gpt-5-3-codex/
   - Blurb: Frontier coding model release; useful for framing current coding-agent capability and limits.
2. GPT-5.3-Codex-Spark (Feb 12, 2026)
   - Link: https://openai.com/index/introducing-gpt-5-3-codex-spark/
   - Blurb: Faster coding variant; good example of latency/quality tradeoff in real workflows.
3. SWE-bench Verified deprecation note (Feb 23, 2026)
   - Link: https://openai.com/index/why-we-no-longer-evaluate-swe-bench-verified/
   - Blurb: Explains benchmark contamination risk and why headline scores need stronger scrutiny.
4. Agent evals guide
   - Link: https://developers.openai.com/api/docs/guides/agent-evals
   - Blurb: Practical guidance for evaluating multi-step agent behavior.
5. Trace grading guide
   - Link: https://developers.openai.com/api/docs/guides/trace-grading
   - Blurb: Methods to score intermediate agent steps, not just final outputs.
6. Codex GitHub integration docs
   - Link: https://developers.openai.com/codex/integrations/github
   - Blurb: Operational setup for AI-assisted PR review and automation in real repos.

### Anthropic (research + tools)

1. Claude Opus 4.6 (Feb 5, 2026)
   - Link: https://www.anthropic.com/news/claude-opus-4-6
   - Blurb: Latest model update for coding/reasoning context in the Anthropic stack.
2. Infrastructure noise in coding benchmarks (Feb 2026)
   - Link: https://www.anthropic.com/engineering/infrastructure-noise
   - Blurb: Shows infra configuration can materially shift benchmark scores.
3. Demystifying evals for AI agents (Jan 9, 2026)
   - Link: https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
   - Blurb: Strong methodology framing for realistic, reproducible agent evaluation.
4. Building a C compiler with parallel Claudes (Feb 5, 2026)
   - Link: https://www.anthropic.com/engineering/building-a-c-compiler-with-a-team-of-parallel-claudes
   - Blurb: Concrete case study showing parallel-agent collaboration patterns.
5. Advanced tool use for Claude Code (Nov 24, 2025)
   - Link: https://www.anthropic.com/engineering/advanced-tool-use-for-claude-code
   - Blurb: Tool orchestration patterns relevant for production coding workflows.
6. Code execution tool for Claude Code (Nov 4, 2025)
   - Link: https://www.anthropic.com/engineering/claude-code-execution-tool
   - Blurb: Explains secure execution loop design for agentic coding.

### Ecosystem references ("etc.")

1. METR time-horizon update (Jan 29, 2026)
   - Link: https://metr.org/blog/2026-1-29-time-horizon-1-1/
   - Blurb: Empirical view on how long frontier models sustain task performance.
2. OpenTelemetry GenAI semantic conventions
   - Link: https://opentelemetry.io/docs/specs/semconv/gen-ai/
   - Blurb: Current telemetry standardization effort; important for trace schema decisions.
3. Model Context Protocol specification
   - Link: https://modelcontextprotocol.io/specification/
   - Blurb: Interoperability layer for tool-connected agent systems.

## Draft contents for Chapter 20 (References and Links)

1. Primary research bibliography by chapter.
2. Benchmark and eval methodology index.
3. Tooling documentation index (OpenAI, Anthropic, ecosystem).
4. Standards and governance index (NIST, ISO, OWASP, EU AI Act resources).
5. Implementation resources and templates:
   - PR checklist for AI-assisted changes.
   - Eval/grader templates.
   - Trace taxonomy and failure labels.
   - Security red-team prompt set.
   - Weekly scorecard template.
   - Portfolio packet template.
6. Detailed research appendix sources:
   - Primary source notes from `research/evals.md`.
   - Claims ledger and chapter-to-source mapping.
   - Extended benchmark, governance, and security references.

## Why this ToC is better for the target reader

1. Starts with fear-reduction and clarity, not tooling complexity.
2. Moves quickly from theory to repeatable workflows.
3. Treats safety, reliability, and career strategy as one system.
4. Ends with execution and an auditable evidence trail.
