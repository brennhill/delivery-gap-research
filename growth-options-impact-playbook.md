# Growth Options: Learn More, Do More, Prove Impact

This is the next layer after the 7-day and 30-day learning plans.

Use this to:
1. Increase your individual capability.
2. Increase your team/company leverage.
3. Produce evidence that your work changed outcomes.

## The Growth Ladder

1. Level 1: Operator
   - You can run a reliable loop on your own work.
2. Level 2: Multiplier
   - You make other engineers faster and safer.
3. Level 3: System Builder
   - You shape standards, controls, and economics at org level.

Move up only when you can prove the current level with metrics.

## Growth Tracks (Pick 2-3, Not 10)

## Track A: Delivery Reliability

Learn more:
1. Deterministic eval patterns.
2. Trace-first debugging.
3. Rollback and recovery design.

Do more:
1. Add one invariant eval to a critical workflow.
2. Add trace IDs and one trace-grade rule.
3. Run one controlled failure drill monthly.

Prove impact:
1. Defect escape down.
2. MTTR down.
3. Rework rate down.

## Track B: Eval Maturity

Learn more:
1. Capability vs regression evals.
2. pass@k vs pass^k interpretation.
3. Noise control and false-positive management.

Do more:
1. Define eval suites for top 3 workflows.
2. Add weekly eval report cadence.
3. Add canary-based security/policy checks.

Prove impact:
1. Pre-merge failure catches up.
2. Post-merge incidents down.
3. Eval stability trend improves week-over-week.

## Track C: Cost and Throughput Engineering

Learn more:
1. Cost per accepted change as core unit.
2. Model routing and context-window economics.
3. Human review as cost line.

Do more:
1. Route tasks by risk and complexity.
2. Enforce context/tool hygiene by default.
3. Set weekly cost and rework guardrails.

Prove impact:
1. Cost per accepted change down.
2. Lead time down without reliability drop.
3. Reviewer minutes per accepted change down.

## Track D: Architecture and Modularity

Learn more:
1. Interface-first design.
2. Boundary and dependency discipline.
3. Legacy seam extraction patterns.

Do more:
1. Set module and naming standards.
2. Ban mixed-purpose mega diffs in critical zones.
3. Add architecture checks in review templates.

Prove impact:
1. Integration failures down.
2. Change blast radius down.
3. Onboarding time for new contributors down.

## Track E: Influence and Organizational Adoption

Learn more:
1. Security/compliance/leadership incentive mapping.
2. Policy-to-control-to-evidence design.
3. Pilot design and stop-go governance.

Do more:
1. Run one constrained team pilot.
2. Create one shared evidence pack format.
3. Implement risk-tiered lanes for approvals.

Prove impact:
1. Faster decision cycles.
2. Fewer rollout stalls.
3. Better speed + stability trend together.

## How to Prove Impact (Personal and Company)

## Personal Proof Pack

For every meaningful initiative, save:
1. Baseline.
2. Intervention.
3. Outcome.
4. Caveat.
5. Reusable artifact.

Reusable artifacts include:
1. Eval definitions.
2. Review templates.
3. Playbooks.
4. Incident/postmortem improvements.

## Company Proof Pack

For each pilot or rollout phase, report:
1. Lead time.
2. Defect escape.
3. Rework rate.
4. Cost per accepted change.
5. MTTR.
6. Reviewer minutes per accepted change.

Do not report only activity metrics.

## Metrics Definitions (Simple and Defensible)

1. Lead time:
   - From first commit on a change to production deploy.
2. Rework rate:
   - Reopened work + rollback/hotfix work / total delivered work.
3. Defect escape:
   - Defects found after release / total defects.
4. Cost per accepted change:
   - Model + infra + review + rework costs / accepted changes.
5. Reviewer minutes per accepted change:
   - Total review time / accepted changes.
6. MTTR:
   - Mean time from incident start to service restoration.

## Tooling Options to Automate Evidence

You can automate most of this from:
1. Git host data:
   - PR timestamps, merge latency, review duration.
2. CI/CD:
   - Build/test pass rates, workflow success, recovery timings.
3. Incident tools:
   - MTTR, incident count, severity trends.
4. Ticketing:
   - Reopened issue rate, cycle times.
5. Eval harness logs:
   - Pass/fail trends, noise trends, drift trends.

Start with export scripts and weekly CSV snapshots. Fancy dashboards can come later.

## 90-Day Growth Plans by Ambition

## Option 1: Solo Engineer Growth Plan

Days 1-30:
1. Stabilize personal delivery loop.
2. Stand up baseline metrics.

Days 31-60:
1. Add eval discipline on top 2 workflows.
2. Publish first proof pack.

Days 61-90:
1. Create reusable standards.
2. Mentor one teammate on your loop.

## Option 2: Team Lead Growth Plan

Days 1-30:
1. Run one constrained pilot.
2. Set shared evidence format.

Days 31-60:
1. Add risk-tiered delivery lanes.
2. Reduce review and rework bottlenecks.

Days 61-90:
1. Expand to second team/workflow.
2. Make stop-go governance objective.

## Option 3: Org Program Growth Plan

Days 1-30:
1. Define shared metrics and control baseline.
2. Select 2-3 pilots with business relevance.

Days 31-60:
1. Compare pilots against baseline.
2. Standardize policy-to-control mapping.

Days 61-90:
1. Scale what is proven.
2. Kill what is noisy and unproven.

## Decision Rule: Where to Invest Next

Invest where this ratio is highest:

`Impact Gain / Coordination Cost`

Good next investment candidates:
1. A missing deterministic eval in a high-risk workflow.
2. A noisy review bottleneck that can be shifted upstream.
3. A recurring incident class with weak diagnostics.
4. A policy requirement that is still manual and inconsistent.

## Failure Patterns to Avoid

1. More tooling without a stronger operating loop.
2. More output without stronger verification.
3. More process without better evidence quality.
4. More dashboards without better decisions.

## Bottom Line

Growth is not "learn more tools."

Growth is:
1. Better loop.
2. Better evidence.
3. Better outcomes.

If those three are improving together, your personal moat and company results both compound.
