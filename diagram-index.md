# Diagram Index

Tracks planned visuals by chapter/section, with intent and rationale.

## Chapter 6

1. Diagram ID: `C06-D01`
   - File: `/Users/brenn/dev/ai-augmented-dev/06-the-core-delivery-loop.md`
   - Section: `Think Like a Manufacturing Line, Not a Slot Machine`
   - Image reference: `images/06.01-manufacturing-vs-slot-machine.png`
   - Description: Split-panel cartoon. Left: manufacturing line with labeled stations (`spec -> scaffold -> tests -> implement -> review -> evaluation`) and a stable finished product. Right: slot machine labeled "prompt" with shiny UI output, hidden bug traps, and scattered rework tickets.
   - What it conveys: Reliable speed comes from sequence discipline, not prompt roulette.
   - Why it matters: Gives readers an operational mental model they can apply immediately.

2. Diagram ID: `C06-D02`
   - File: `/Users/brenn/dev/ai-augmented-dev/06-the-core-delivery-loop.md`
   - Section: `Step 6: Eval (Prove, Don't Assume)`
   - Image reference: `images/06.02-output-vs-trace-grading.png`
   - Description: Two-layer evaluation stack (output checks and trace checks) with feedback loop.
   - What it conveys: Final answers alone are insufficient for agent reliability.
   - Why it matters: Moves teams from "it worked once" to diagnosable, repeatable quality.

3. Diagram ID: `C06-D03`
   - File: `/Users/brenn/dev/ai-augmented-dev/06-the-core-delivery-loop.md`
   - Section: `The Weekly Scorecard (So Progress Is Not a Feeling)`
   - Image reference: `images/06.03-weekly-scorecard-dashboard.png`
   - Description: Dashboard mock with lead time, defect escape, rework, and cost per accepted change.
   - What it conveys: Balanced metrics prevent speed-only self-deception.
   - Why it matters: Supports stakeholder alignment and continuous improvement.

## Chapter 7

1. Diagram ID: `C07-D01`
   - File: `/Users/brenn/dev/ai-augmented-dev/07-deterministic-feedback-or-it-didnt-happen.md`
   - Section: `The Anti-Suck Pyramid`
   - Image reference: `images/07.01-anti-suck-eval-pyramid.png`
   - Description: Pyramid showing deterministic checks at the base, trace checks in the middle, and judgment/rubric checks at the top.
   - What it conveys: Stable deterministic checks are the foundation for trustworthy eval systems.
   - Why it matters: Prevents teams from starting with fuzzy scoring and skipping hard guarantees.

2. Diagram ID: `C07-D02`
   - File: `/Users/brenn/dev/ai-augmented-dev/07-deterministic-feedback-or-it-didnt-happen.md`
   - Section: `Build Three Eval Loops, Not One`
   - Image reference: `images/07.02-three-eval-loops.png`
   - Description: Three-lane timeline showing fast PR gates, deeper nightly eval runs, and final pre-release human smoke checks.
   - What it conveys: Speed, depth, and human-visible release confidence can coexist when loops are split by purpose.
   - Why it matters: Prevents false confidence from fully automated checks alone.

3. Diagram ID: `C07-D03`
   - File: `/Users/brenn/dev/ai-augmented-dev/07-deterministic-feedback-or-it-didnt-happen.md`
   - Section: `Failure Taxonomy: Name the Suck Quickly`
   - Image reference: `images/07.03-eval-failure-taxonomy-matrix.png`
   - Description: Matrix mapping failure class to detection signal, owner, and immediate action.
   - What it conveys: Fast classification improves triage speed and fix quality.
   - Why it matters: Stops teams from treating all failures as one generic bug pile.

## Chapter 8

1. Diagram ID: `C08-D01`
   - File: `/Users/brenn/dev/ai-augmented-dev/08-trace-first-debugging-and-reliability-basics.md`
   - Section: `From Output-Centric to Timeline-Centric Debugging`
   - Image reference: `images/08.01-trace-anatomy-request-timeline.png`
   - Description: End-to-end timeline showing model call, retrieval, tool use, retries, and first failing span.
   - What it conveys: Root cause usually appears in sequence, not in final output.
   - Why it matters: Teaches readers to find first bad span quickly.

2. Diagram ID: `C08-D02`
   - File: `/Users/brenn/dev/ai-augmented-dev/08-trace-first-debugging-and-reliability-basics.md`
   - Section: `The Five Controls That Prevent Most Trace Chaos`
   - Image reference: `images/08.02-reliability-control-map.png`
   - Description: Control map linking timeout budgets, retries, idempotency, permissions, and approvals to failure types they prevent.
   - What it conveys: Reliability controls are system design, not prompt tweaks.
   - Why it matters: Helps teams prioritize high-leverage controls first.

3. Diagram ID: `C08-D03`
   - File: `/Users/brenn/dev/ai-augmented-dev/08-trace-first-debugging-and-reliability-basics.md`
   - Section: `Human-Visible Smoke + Trace = Honest Releases`
   - Image reference: `images/08.03-human-smoke-trace-loop.png`
   - Description: Loop diagram connecting human smoke steps to captured trace IDs and feedback into fixes.
   - What it conveys: Human observation plus trace evidence creates actionable debugging.
   - Why it matters: Prevents anecdotal bug reports and accelerates remediation.

## Chapter 10 — Real Systems: Legacy Code, Security, and Blast-Radius Control

1. Diagram ID: `C10-D01`
   - File: `10-real-systems-legacy-and-security.md`
   - Section: `Stabilize the Boundary First`
   - Image reference: `images/10.01-legacy-migration-flow.png`
   - Description: Flow showing boundary setup, dual-path compatibility window, output comparison, and controlled cutover.
   - What it conveys: Legacy migrations should be sequence-controlled, not big-bang rewrites.
   - Why it matters: Gives readers a concrete safe-migration path they can execute in brittle systems.

2. Diagram ID: `C10-D02`
   - File: `10-real-systems-legacy-and-security.md`
   - Section: `Threat Modeling in Plain English`
   - Image reference: `images/10.02-ai-dev-threat-surface-map.png`
   - Description: Surface map showing input channels, retrieval sources, model context, tool permissions, and side effects, with trust boundaries highlighted.
   - What it conveys: AI-assisted development introduces new control points across prompt, tool, and data pathways.
   - Why it matters: Helps teams visualize where to place controls before implementing them.

3. Diagram ID: `C10-D03`
   - File: `10-real-systems-legacy-and-security.md`
   - Section: `Put Security Controls Directly Into the Delivery Loop`
   - Image reference: `images/10.03-delivery-loop-security-controls.png`
   - Description: The `spec -> scaffold -> tests -> implement -> review -> eval` loop with embedded security checkpoints and evidence artifacts at each stage.
   - What it conveys: Security should be integrated into normal delivery flow rather than bolted on at release time.
   - Why it matters: Shows how teams can increase speed and safety simultaneously.

4. Diagram ID: `C10-D04`
   - File: `10-real-systems-legacy-and-security.md`
   - Section: `A Fast Attack-Chain Drill You Can Run This Week`
   - Image reference: `images/10.04-attack-chain-breakpoints.png`
   - Description: Attack-chain timeline from untrusted content ingestion to attempted secret exfiltration, with explicit breakpoints for controls.
   - What it conveys: Defense-in-depth means multiple stoppage points, not one fragile guardrail.
   - Why it matters: Gives teams a practical method for tabletop testing and control validation.

## Chapter 11

1. Diagram ID: `C11-D01`
   - File: `/Users/brenn/dev/ai-augmented-dev/11-cost-roi-and-weekly-metrics-that-matter.md`
   - Section: `Why ROI Discussions Keep Going Sideways`
   - Image reference: `images/11.01-weekly-roi-scorecard.png`
   - Description: Single dashboard combining cost per accepted change, lead time, defect escape rate, and rework trend.
   - What it conveys: ROI is multi-dimensional; cost alone cannot represent delivery economics.
   - Why it matters: Gives teams an immediately actionable weekly measurement template.

2. Diagram ID: `C11-D02`
   - File: `/Users/brenn/dev/ai-augmented-dev/11-cost-roi-and-weekly-metrics-that-matter.md`
   - Section: `Routing, Caching, and Budgets Are Architecture Decisions`
   - Image reference: `images/11.02-cost-control-loop.png`
   - Description: Loop showing model routing, caching, budget limits, fallback behavior, and feedback into planning.
   - What it conveys: Cost control comes from architecture and control loops, not one-time prompting tricks.
   - Why it matters: Helps readers operationalize cost governance in day-to-day engineering workflow.

## Chapter 12

1. Diagram ID: `C12-D01`
   - File: `/Users/brenn/dev/ai-augmented-dev/12-the-engineering-managers-survival-guide.md`
   - Section: `Translate Policy Into Controls and Evidence`
   - Image reference: `images/12.01-policy-control-evidence-matrix.png`
   - Description: Matrix mapping policy statements to technical controls, evidence artifacts, and named ownership.
   - What it conveys: Governance is executable only when policy has direct technical and accountability mapping.
   - Why it matters: Reduces audit friction and clarifies implementation responsibility.

2. Diagram ID: `C12-D02`
   - File: `/Users/brenn/dev/ai-augmented-dev/12-the-engineering-managers-survival-guide.md`
   - Section: `Use the Three-Lane Model`
   - Image reference: `images/12.02-three-lane-governance-model.png`
   - Description: Three-lane dashboard model for security, compliance, and leadership views connected to a shared evidence spine.
   - What it conveys: Stakeholders need differentiated views of the same governed system.
   - Why it matters: Prevents governance debates caused by mixing incompatible success metrics.

3. Diagram ID: `C12-D03`
   - File: `/Users/brenn/dev/ai-augmented-dev/12-the-engineering-managers-survival-guide.md`
   - Section: `The 30/60/90 Buy-In Cadence`
   - Image reference: `images/12.03-buy-in-306090-roadmap.png`
   - Description: Phase timeline with baseline, pilot, and scale gates plus explicit stop/go criteria.
   - What it conveys: Political adoption must be managed as staged delivery with evidence gates.
   - Why it matters: Helps teams scale only when controls and outcomes are proven.

## Chapter 13

1. Diagram ID: `C13-D01`
   - File: `/Users/brenn/dev/ai-augmented-dev/13-sustainable-pace-and-the-burnout-trap.md`
   - Section: `The AI Work Intensification Cycle`
   - Image reference: `images/13.01-work-intensification-cycle.png`
   - Description: Cycle diagram: acceleration → expectation → reliance → scope expansion → total load increase.
   - What it conveys: AI doesn't automatically reduce work; it often intensifies it through shifting norms.
   - Why it matters: Warns EMs to track cognitive load, not just output speed.

## Chapter 15

1. Diagram ID: `C15-D01`
   - File: `/Users/brenn/dev/ai-augmented-dev/15-your-durable-moat-as-a-developer.md`
   - Section: `The Four Moats That Compound`
   - Image reference: `images/15.01-career-moat-stack.png`
   - Description: Layered stack for system design, reliability/debugging, domain compression, and cross-functional translation.
   - What it conveys: Durable career leverage comes from scarce system-level capabilities, not raw code output.
   - Why it matters: Gives readers a concrete framework for skill investment decisions.

2. Diagram ID: `C15-D02`
   - File: `/Users/brenn/dev/ai-augmented-dev/15-your-durable-moat-as-a-developer.md`
   - Section: `How to Train Moats Weekly`
   - Image reference: `images/15.02-moat-compounding-loop.png`
   - Description: Weekly practice loop turning recurring reps into compounding career leverage.
   - What it conveys: Moats are built by routine behavior, not one-time learning binges.
   - Why it matters: Makes long-term positioning actionable under real work constraints.

## Chapter 18

1. Diagram ID: `C18-D01`
   - File: `/Users/brenn/dev/ai-augmented-dev/15-your-durable-moat-as-a-developer.md`
   - Section: `The Portfolio Packet That Works`
   - Image reference: `images/18.01-portfolio-evidence-packet.png`
   - Description: Five-part portfolio packet map: impact, judgment, reliability, enablement, and eval maturity.
   - What it conveys: Career proof should be structured as verifiable evidence, not narrative alone.
   - Why it matters: Helps readers build promotion/hiring artifacts with high signal.

2. Diagram ID: `C18-D02`
   - File: `/Users/brenn/dev/ai-augmented-dev/15-your-durable-moat-as-a-developer.md`
   - Section: `Anti-Patterns That Create Career Drag`
   - Image reference: `images/18.02-anti-pattern-control-map.png`
   - Description: Matrix mapping common portfolio anti-patterns to corrective controls.
   - What it conveys: Avoidable behavior patterns are a major source of hidden career drag.
   - Why it matters: Gives fast remediation path for weak portfolio signals.

## Chapter 15 (continued)

3. Diagram ID: `C15-D03`
   - File: `/Users/brenn/dev/ai-augmented-dev/15-your-durable-moat-as-a-developer.md`
   - Section: `Phase 3 (Days 61-90): Hardening and Scale Decision`
   - Image reference: `images/15.04-90-day-transition-blueprint.png`
   - Description: Three-phase transition blueprint with explicit phase gates and success/failure criteria.
   - What it conveys: Effective transitions are staged and measured, not motivational.
   - Why it matters: Helps teams run adoption as operational execution, not abstract intent.

4. Diagram ID: `C15-D04`
   - File: `/Users/brenn/dev/ai-augmented-dev/15-your-durable-moat-as-a-developer.md`
   - Section: `Keep Evolving After Day 90`
   - Image reference: `images/15.05-quarterly-evolution-loop.png`
   - Description: Quarterly loop for benchmark reruns, control audits, policy refresh, and standards updates.
   - What it conveys: Capability advantage decays without explicit recurring adaptation cycles.
   - Why it matters: Prevents 90-day rollouts from collapsing into slow drift.

## Chapter 19

1. Diagram ID: `C19-D01`
   - File: `/Users/brenn/dev/ai-augmented-dev/18-appendix-a-state-of-the-art-2026-snapshot.md`
   - Section: `Practical Interpretation Rules`
   - Image reference: `images/19.01-state-of-the-art-map.png`
   - Description: Map connecting provider updates, constraints, and delivery-system implications.
   - What it conveys: State-of-the-art tracking should drive operational decisions, not benchmark hype.
   - Why it matters: Helps readers convert ecosystem news into practical engineering posture changes.
