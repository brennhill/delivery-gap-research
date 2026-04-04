# Short Chapter Expansion Plan: Detailed Sub-TOCs

Goal: expand only where it improves clarity, evidence, and narrative power. No filler.

Scope used here: core chapters under 1,500 words (`00`, `02`, `03`, `04`, `05`, `09`, `10`, `11`, `12`, `13`, `14`, `15`, `16`, `17`).

## Word-Band Targets (Planning)

| Chapter | Current Words | Suggested Band | Net Add Range | Priority |
|---|---:|---:|---:|---|
| 00 Preface | 636 | 900-1,200 | +260 to +560 | Medium |
| 02 Junior Gap | 1,305 | 1,900-2,300 | +595 to +995 | High |
| 03 Machine in the Ghost | 1,087 | 1,900-2,400 | +813 to +1,313 | High |
| 04 Prompts | 1,065 | 2,000-2,500 | +935 to +1,435 | High |
| 05 Agents | 1,167 | 2,100-2,700 | +933 to +1,533 | High |
| 09 Legacy Strategy | 1,479 | 2,100-2,600 | +621 to +1,121 | High |
| 10 Security Threat Model | 1,391 | 2,100-2,700 | +709 to +1,309 | High |
| 11 Governance | 1,345 | 2,000-2,500 | +655 to +1,155 | High |
| 12 Cost and ROI | 1,396 | 2,100-2,700 | +704 to +1,304 | High |
| 13 Politics and Buy-In | 1,237 | 1,900-2,400 | +663 to +1,163 | Medium-High |
| 14 Productivity Trap | 1,465 | 2,100-2,800 | +635 to +1,335 | High |
| 15 Durable Moat | 1,202 | 2,000-2,500 | +798 to +1,298 | Medium-High |
| 16 Portfolio Proof | 1,051 | 1,900-2,400 | +849 to +1,349 | Medium-High |
| 17 90-Day Transition | 985 | 1,900-2,500 | +915 to +1,515 | High |

## Chapter 00: Preface (Detailed Sub-TOC)

1. Why this book exists now (economic and career pressure)
2. What this book is and is not (no hype, no fatalism)
3. Author stake and constraints (why this is written from necessity)
4. The cyborg authorship method (architect, engine, auditor)
5. Evidence policy (how claims are sourced, caveats, update behavior)
6. How to read this book by role (IC, manager, founder, team lead)
7. What to expect in each chapter (stories, analogies, takeaways, actions)
8. Living-book operating model (Leanpub update cadence and reader feedback loop)

## Chapter 02: The Junior Gap (Detailed Sub-TOC)

1. The hiring shock in one sentence
2. Where entry-level work moved (from implementation to verification)
3. The new hiring math from the manager side
4. The new interview filters (what is silently being tested now)
5. The early-career trap (high output, low understanding)
6. The manager trap (cut juniors now, pay later in fragility)
7. Apprenticeship redesign for AI-era teams
8. Two candidate profiles (same output, different trust level)
9. 30-day reposition path for early-career engineers
10. 30-day upgrade path for managers building pipelines
11. Common objections and blunt responses
12. Wrap: what changes this quarter vs this year

## Chapter 03: The Machine in the Ghost (Detailed Sub-TOC)

1. Reset mental model: probability engine, not hidden person
2. Tokenization failures in plain examples
3. Embeddings and semantic geometry (why similarity works)
4. Attention as prioritization (what gets weighted, what gets dropped)
5. Context length economics (latency, cost, dilution)
6. Decoding controls and reliability tradeoffs
7. Alignment side effects (sycophancy, over-accommodation)
8. Hallucination mechanics (compression, uncertainty, lock-in)
9. Failure-mode-to-control mapping (what to do when each failure appears)
10. Practical developer implications (what to trust, what to verify)
11. Myths to retire
12. Wrap: mechanics-first engineering posture

## Chapter 04: Prompt Engineering (Detailed Sub-TOC)

1. Prompting vs context engineering: hard distinction
2. Prompt packet anatomy (task, context, constraints, output contract)
3. Context assembly pipeline (retrieval, pruning, ordering)
4. Instruction hierarchy and precedence rules
5. Long-context layout patterns that hold up in practice
6. Structured outputs and constrained decoding in production
7. Retrieval quality checks (relevance, faithfulness, answerability)
8. Reasoning modes: when extra thinking is worth the cost
9. Prompt eval loop (gold set, deterministic checks, drift monitoring)
10. Prompt change management (versioning, rollback, owner)
11. Anti-pattern gallery (persona theater, dump-all-context, eval-free tuning)
12. Wrap: from clever prompts to repeatable systems

## Chapter 05: Agents (Detailed Sub-TOC)

1. Agent loop anatomy (propose, act, observe, repeat)
2. When to use an agent vs plain software control flow
3. Tool contract design (schema, constraints, negative guidance)
4. State and memory boundaries (what lives in runtime vs model context)
5. Orchestration patterns (single, supervisor, specialist swarm)
6. Why swarms fail (context overload, error cascade, silent drift)
7. Guardrails and human gates by risk tier
8. Agent observability (trace structure and failure attribution)
9. Eval strategy for agents (output and process grading)
10. Rollout path (single agent to multi-agent without chaos)
11. Team operating model changes (review, ownership, on-call)
12. Wrap: action systems, not chat systems

## Chapter 09: Legacy Strategy (Detailed Sub-TOC)

1. Why legacy changes the game
2. Risk mapping for monoliths (churn, incidents, side effects, ownership)
3. Stabilize before accelerate (how to stage this)
4. Seam discovery and branch-by-abstraction in practice
5. Characterization tests and invariant capture
6. PR risk budgets for brittle zones
7. Compatibility windows and dual-run comparison
8. Rollback protocol and trigger criteria
9. Legacy-specific eval stack and trace practices
10. What "safe progress" looks like weekly
11. Case pattern: green tests, bad behavior, recovery
12. Wrap: controlled modernization instead of rewrite theater

## Chapter 11: Cost and ROI (Detailed Sub-TOC)

1. The "wrong metric" story and why it repeats
2. Unit economics definition (cost per accepted outcome)
3. Full cost stack (model, infra, human review, rework, incidents)
4. Value-side stack (customer impact, cycle time, reliability)
5. Hidden human costs and review bottlenecks
6. Architecture levers (routing, caching, model mix, retry discipline)
7. Weekly ROI ritual and decision cadence
8. How to read external productivity claims responsibly
9. Executive ROI memo template
10. Tradeoff scenarios (fast/cheap/reliable tensions)
11. First-month instrumentation checklist
12. Wrap: outcome economics, not token economics

## Chapter 12: Governance, Policy, and Buy-In (Detailed Sub-TOC)

1. Governance definition for builders
2. Policy-to-control-to-evidence chain
3. Three-lane governance model (security, compliance, leadership)
4. Risk tier rubric with concrete examples
5. Minimum evidence pack and storage conventions
6. Approval boundaries and automation defaults
7. Review meeting protocol that ends in decisions
8. Dashboards by audience, one data spine
9. Why technical success can still fail (buy-in dynamics)
10. Stakeholder incentive map (security, compliance, leadership, engineering)
11. 30/60/90 buy-in cadence and stop-go gates
12. Ownership contract and escalation paths
13. Wrap: governance as steering, not bureaucracy

## Chapter 15: Productivity Trap (Detailed Sub-TOC)

1. The trap setup (fast activity, weak outcomes)
2. Incentives and executive pressure dynamics
3. Behavioral dynamics (metric substitution, local optimization, ownership blur)
4. Evidence review and caveats (studies, benchmarks, CI data)
5. What top 5% teams do differently operationally
6. Trap diagnostics (how to detect it early)
7. Corrective controls (integration, eval, review, recovery)
8. How to communicate trap status upward without panic
9. Case-style walkthrough: fake speed to real speed
10. Wrap: bridge to individual career strategy

## Chapter 16: Durable Moat (Detailed Sub-TOC)

1. Activity vs value, revisited
2. Commodity work vs scarce work in AI-era engineering
3. Moat 1: system design judgment (how to train it)
4. Moat 2: reliability depth (how to prove it)
5. Moat 3: domain compression (how to practice it)
6. Moat 4: cross-functional translation (how to practice it)
7. Evidence artifacts that make moats visible
8. Career conversations and promotion narrative framing
9. Anti-moats and recovery plan
10. 90-day personal moat training plan
11. Wrap: compounding value over output volume

## Chapter 17: Portfolio Proof (Detailed Sub-TOC)

1. Why effort alone does not transfer to decisions
2. What panels are actually deciding under time pressure
3. Evidence packet architecture and quality bar
4. Strong proof language patterns (with caveat discipline)
5. Role-based packet variants (IC, lead, manager)
6. Case-study template with reproducible claims
7. Anti-patterns and credibility killers
8. Portfolio maintenance cadence (monthly/quarterly)
9. Interview usage playbook (how to present proof fast)
10. Wrap: portable credibility in a noisy market

## Chapter 16: 90-Day Transition Plan (Detailed Sub-TOC)

1. Why most transition plans fail in week two
2. Part I: your personal transition first (why sequence matters)
3. Personal Phase 1 (days 1-30): baseline and focus
4. Personal Phase 2 (days 31-60): pilot and repeatability proof
5. Personal Phase 3 (days 61-90): hardening and career proof
6. Personal weekly scorecard and cadence
7. Part II: how personal proof should affect the org
8. Team pilot design and stop-go scale criteria
9. Ownership model across product/platform/security/compliance/leadership
10. Org-level metrics and quarterly adaptation loop
11. Failure contingencies and wrap: self-sustaining system

## Recommendation for Next Step

1. Approve this sub-TOC plan chapter-by-chapter.
2. Prioritize expansion in this order: `17 -> 04 -> 05 -> 03 -> 10 -> 12 -> 11 -> 14 -> 09 -> 16 -> 15 -> 02 -> 13 -> 00`.
3. Expand each chapter against its sub-TOC with a hard rule: every new subsection must add at least one of these, a concrete example, a decision framework, a practical template, or an evidence-backed claim.
