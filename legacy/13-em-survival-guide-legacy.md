# Chapter 13: The Engineering Manager's Survival Guide

Your job is not to adopt AI. Your job is to keep your teams shipping trusted software while everything underneath them shifts.

Chapter 12 covered governance mechanics. This chapter is for the person in the middle: accountable for delivery, responsible for people, and caught between a VP who saw a demo and expects 2x throughput and a team where half the engineers are excited, a quarter are skeptical, and the rest are quietly terrified.

If you manage people through this transition, this chapter is yours.

> **Who needs this chapter:**
>
> **EMs:** This is your home chapter. VP translation scripts, leveling rubrics, adoption curve management, burnout policies, and the coordination overhead data are all here. None of this is delegatable.
>
> **ICs:** This chapter is written for your manager, not for you. You can skip it — but if you read it, you will understand the pressures your EM is navigating: bimodal adoption, executive expectations, review bottlenecks, burnout tracking, and the political cost of every process decision. That understanding makes you a better teammate and a more effective communicator upward. The leveling rubric section also shows you exactly what "good" looks like at each level now, which is worth reading regardless of your role.
>
> **PMs and designers:** The EM is your closest partner in shipping. This chapter explains what is changing about their job, why timelines feel different now, and how to support the transition instead of adding pressure to it. **PM action:** Have a 1:1 with your EM specifically about how AI is changing their review and integration load — then adjust how you communicate urgency and scope accordingly.

## The Quarter My VP Expected Magic

I had a VP who watched an AI demo and came to our next planning meeting with a simple question: "If AI makes developers twice as fast, why are we not cutting the timeline in half?"

I did not have a good answer. Not because the question was unfair — it was reasonable given what he saw. But the demo showed generation. Our delivery included integration, review, testing, deployment, monitoring, incident response, and the three weeks of cleanup after someone merged a giant AI-generated diff that looked clean and was structurally broken.

I tried explaining that generation speed is not delivery speed. He heard "excuses." I tried showing DORA metrics. He wanted a simpler story. I tried saying "we need time to build the process." He heard "we are not ready," which in executive language means "you are behind."

That meeting taught me the most important EM skill in this era: translating between what AI actually does and what leadership reasonably expects. Not by sandbagging, not by overselling, but by showing the gap between generation and delivery with evidence your VP can act on.

The answer I wish I had given: "AI makes generation fast. Here is the data showing our bottleneck is now review and integration, not coding. Give me one quarter to fix the bottleneck, and I will show you the throughput number you want — measured on shipped outcomes, not PRs opened."

## You Are Not a Senior IC With Reports

Most of this book is written for people who write code. You are the person who creates the conditions for code to ship safely at scale. That is a different job.

Your levers are not prompts and evals. Your levers are team structure, expectations, hiring criteria, performance standards, process design, and the political air cover that lets your teams do focused work instead of reacting to hype cycles.

Think of a restaurant manager. The kitchen staff needs sharp knives and good ingredients. The manager needs the right number of cooks on the right stations, a reservation system that does not overbook, and the ability to tell the owner that adding 30 seats without adding kitchen capacity will produce slower service, not faster revenue.

Your kitchen just got a very fast new appliance. Your job is not to learn to operate it yourself. Your job is to figure out how many cooks still need to be on the line, which stations change, and how to keep food quality up while throughput increases.

## What Happens When Controls Are Weak: The Amazon Case

In March 2026, Amazon experienced a series of production incidents that cost millions of orders and forced a 90-day safety reset across 335 Tier-1 services.[^amazon-reset]

The headline incident: on March 5, a single config change caused a 99% drop in orders across North American marketplaces — 6.3 million lost orders in one event. Root cause: the change was deployed without using Amazon's formal documentation and approval process. A single authorized operator executed a high-blast-radius change with no guardrails.

Three days earlier, Amazon's AI coding assistant Q was identified as a primary contributor to a delivery-time display error that generated 1.6 million website errors and roughly 120,000 lost orders. The internal review noted: "GenAI's usage in control plane operations will accelerate exposure of sharp edges and places where guardrails do not exist."

Amazon's response is instructive for every EM reading this. Dave Treadwell, SVP of E-Commerce Services, announced "temporary safety practices which will introduce controlled friction" — including mandatory two-person code review for all changes to Tier-1 systems, mandatory use of formal change management tooling, and VP-level audits of all production code change activities. Longer term, Amazon is investing in "both deterministic and agentic safeguards."

Read that again: two-person review, formal change management, deterministic gates. This is exactly the delivery loop from Chapter 6 — spec, review, eval — applied at Amazon scale after the controls were missing.

The review bottleneck is not just an Amazon problem. The volume and review data from Chapter 9 tell the story: AI-generated code produces dramatically more lines, review time per PR climbs sharply, and AI code surfaces more issues than human-written code. Even Anthropic acknowledged the problem publicly in March 2026: "Code review has become a bottleneck, and we hear the same from customers every week. Developers are stretched thin, and many PRs get skims rather than deep reads."[^anthropic-review]

The lesson for EMs is not "AI is dangerous." The lesson is: review capacity did not scale with output. When that avalanche of new code hit traditional review processes that were already thin, problems did not emerge gradually. They emerged as 6.3 million lost orders on a Tuesday.

Your job is to make sure the controls exist *before* that Tuesday, not after. The cost of "controlled friction" is always less than the cost of an incident review with your VP and legal team.

## Managing the Bimodal Adoption Curve

You will not get uniform adoption. You will get a distribution, and it will be frustrating.

**The eager adopters** will go fast, merge big diffs, and feel productive. Some of them are genuinely productive. Some of them are creating integration debt that will arrive in two sprints. Your job is not to slow them down but to make sure the delivery loop (Chapter 6) applies to AI-assisted work the same way it applies to everything else. Spec first. Small diffs. Deterministic checks. No exceptions for speed.

**The skeptics** will resist, sometimes for good reasons and sometimes out of fear. Do not dismiss either motivation. The engineer who says "I tried Copilot and it generated garbage for our codebase" may be telling you something real about your codebase's complexity, not about the tool. The engineer who says "I do not trust it" may need to see evidence from their own workflow, not someone else's demo. Give skeptics a bounded experiment: one feature, one sprint, measured outcomes. If it does not help on their workflow, that is valid data. Not every workflow benefits equally.

**The reckless adopters** are the most dangerous. They use AI for everything, stop reading what it generates, and merge with confidence they have not earned. You will recognize them by the pattern: fast PRs, green CI, and a rising rework rate three weeks later. This is where your review process has to be strongest. If your team's definition of "reviewed" is "I skimmed it and it looked fine," AI will exploit that gap ruthlessly.

**The quietly terrified** will not tell you they are scared. They will just get quieter. Watch for the senior engineer who stops contributing to architecture discussions, the mid-level who starts working longer hours without visible output, or the junior who asks fewer questions. These are people whose professional identity is under pressure. Your job is to name the fear explicitly in 1:1s and connect it to concrete actions: "Your debugging depth is more valuable now, not less. Here is how to prove that."

![Adoption curve: eager, skeptical, reckless, and quietly terrified](images/13.01-adoption-distribution-curve.png)

## The VP Conversation: A Script That Works

Your VP does not need to understand evals or traces. Your VP needs to understand three things: what AI is doing for the team right now, what the risks are, and when to expect measurable improvement.

Here is the structure that has worked for me:

**Frame 1: Generation vs. delivery.** "AI has accelerated code generation by roughly X% on our team. But generation is only one stage. Our current bottleneck is [review queue / integration testing / deployment confidence]. We are investing in fixing the bottleneck so the generation gains actually reach customers."

**Frame 2: One metric that matters.** Use cost per accepted change from Chapter 11. "Our cost per shipped outcome is currently $Y. I am targeting a Z% improvement this quarter by reducing rework and review drag, not by generating more code."

**Frame 3: What to watch.** "If you see our PR volume drop while shipped outcomes stay flat or improve, that is the plan working — fewer speculative changes, more trusted ones. If you see both drop, I will flag it and we will adjust."

This conversation works because it gives your VP a mental model, a number, and a leading indicator — without requiring them to understand your delivery pipeline.

Where this analogy breaks: some VPs do not want nuance. They want "are we faster, yes or no." If that is your situation, lead with the shipped-outcome number and keep the explanation in your back pocket. You are managing up, not teaching a class.

### When Your VP Is Pushing Reckless Adoption

The harder version of this conversation is when your VP does not just expect magic — they mandate it. "Use AI for everything. I want to see adoption numbers. Why is your team not using Copilot on every PR?"

Your instinct will be to push back with concerns. Do not lead with "not possible." VPs need to show progress. They set culture and direction, but they are often missing the low-level detail that turns direction into results. That is your job to provide.

Instead of resistance, give them a roadmap to success. "I agree we should go all-in on AI. Here is my plan to do it without breaking production. Week 1-4: these two workflows, these metrics, these guardrails. Week 5-8: expand based on data. Week 9-12: measurable before/after for your staff meeting." That gives your VP the progress narrative they need while you control the implementation quality.

The key move: attach guardrails and metrics to every adoption push. Not as a brake — as a steering wheel. "We are adopting aggressively, and here is how we will know it is working" is a sentence no VP will argue with. It gives them what they actually need most: measurable results they can report upward.

VPs who push reckless adoption are usually VPs under pressure from their own leadership. Help them succeed with evidence instead of fighting them with caution. You both want the same outcome — you just disagree about the path. A roadmap with milestones resolves that disagreement faster than a debate about risk tolerance.

## Performance Criteria: What "Good" Looks Like Now

Your leveling rubrics probably need updating. Most performance frameworks were written for a world where code production was a meaningful signal of individual contribution. In a world where code generation is partially automated, the signal shifts.

Here is a starting framework. Adapt it to your org's language.

### Junior Engineer

**Meets expectations:** Uses AI tools within the delivery loop. Writes specs before generating code. Adds deterministic checks to their own work. Asks for review and acts on feedback. Identifies when AI output is wrong and escalates instead of merging.

**Exceeds expectations:** Identifies failure patterns in AI-generated code that the team had not caught. Contributes reusable test patterns. Writes post-incident notes that improve team process. Demonstrates that their delivery quality is improving quarter over quarter with evidence.

### Mid-Level Engineer

This is the largest population on most teams and often the most productive with AI tools — fast, capable, generating volume. That is also the trap. AI can mask the gap between "writes code fast" and "understands the system." Mid-levels who look senior because of output velocity may not be building the judgment and system-design skills the new senior bar requires.

**Meets expectations:** Uses AI tools effectively within the delivery loop. Writes specs for their own work without prompting. Reviews AI-generated PRs from others, not just their own. Identifies when AI output violates system invariants, not just syntax. Owns a feature area end-to-end including tests, deployment, and monitoring. Asks architecture questions before generating code, not after.

**Exceeds expectations:** Catches failure patterns across PRs, not just within their own work. Proposes invariant or contract checks the team did not have before. Demonstrates deepening system knowledge — can explain why a design decision was made, not just what it does. Begins mentoring junior engineers on spec quality and review discipline. Shows evidence of moving toward the senior bar: system-level thinking, blast-radius reasoning, cross-service awareness.

The specific risk with mid-levels is that AI makes them productive enough to look like they are performing at a senior level, but they may be skipping the struggle that builds real system understanding. Watch for the mid-level who ships fast but cannot explain the architecture of what they shipped. That is your coaching conversation.

### Senior Engineer

**Meets expectations:** Maintains delivery quality while using AI to increase throughput. Reviews AI-assisted PRs with the same rigor as human-written ones. Owns eval and trace quality for their services. Mentors others on the delivery loop without gatekeeping tool access.

**Exceeds expectations:** Designs system boundaries that make AI-assisted development safer for the whole team. Identifies and fixes architectural debt introduced by AI-generated code. Builds reusable eval patterns or review tooling that reduces team-wide rework. Demonstrates measurable improvement in team metrics (not just personal output).

### Staff+ Engineer

**Meets expectations:** Sets technical direction for AI-assisted delivery across multiple teams. Defines and maintains quality standards that scale. Owns the cost-per-accepted-change metric and drives improvement.

**Exceeds expectations:** Builds organizational capability — the team is better at AI-assisted delivery because of systems this person created, not because they personally reviewed every PR. Translates technical risk into business language that leadership acts on. Creates durable standards adopted beyond their immediate teams.

![Leveling expectations: junior, senior, staff — what "good" means now](images/13.02-leveling-expectations-grid.png)

## Creating Slack With AI, Not Waiting For It

The EM reviewer complaint I hear most often: "This book assumes schedule slack that does not exist."

Fair. But here is the reframe: AI is how you *create* the slack. You do not wait for a quiet quarter to start adopting. You adopt on disciplined, clearly defined tasks — ones with good test coverage, clear success criteria, and bounded blast radius — to ship faster, build political wins, and grow the team's skills with the technology.

The slack does not come first. The slack comes from doing this well.

Three approaches that work inside real constraints:

**1. Attach process improvement to an existing deliverable.** Do not ask for "AI adoption time." Instead, pick a feature already on the roadmap and say: "We are going to deliver this one using the spec-first delivery loop. Same deadline, same scope. The only change is how we work." That costs nothing on the roadmap and gives you a clean before/after comparison. If it ships faster — and on disciplined tasks it usually does — the time you saved is your slack for the next experiment.

**2. Use rework as your budget argument.** If your team spends 20% of sprint capacity on rework and bug fixes, that is your slack. "I want to invest half of our current rework budget into preventing rework — deterministic checks, spec quality, and review discipline. If it works, we get the time back as capacity. If it does not work, we are no worse off." This is not asking for permission. This is showing that you already have the budget — it is just being spent on cleanup instead of improvement.

**3. Run the pilot on the highest-pain workflow.** Do not pick an easy workflow for the pilot. Pick the one that generates the most incidents, rework, or review friction. That way, improvement is immediately visible and politically defensible. A successful pilot on a painful workflow gives you two things: capacity back and a story your VP can repeat in their staff meeting.

The compounding effect matters. Each successful disciplined adoption builds three things: faster delivery on that workflow, political capital with leadership, and team confidence with the tools. Those compound into more slack, more trust, and more ambition for the next adoption. The EM who waits for slack never gets it. The EM who creates slack with early wins gets more room every quarter.

When the first pilot produces ambiguous results — and it often does — do not abandon the approach. Diagnose why. Was the task too complex for a first experiment? Was measurement too noisy to show signal? Was the team still learning the tools? Adjust scope, pick a simpler second target, and run again. The first attempt is calibration, not proof. Two clean data points beat one noisy one.

## Cross-Team Dependencies Are the Real Constraint

Your team's adoption speed is limited by the slowest team in your dependency chain.

If your team writes clean specs and deterministic evals but the platform team you depend on deploys with prayer-based testing, your reliability story has a hole that is not yours to fix. If the security team has not updated their review process for AI-generated code, your merge velocity is gated by their capacity.

Two things help:

**Make your team's discipline visible.** Share your spec templates, eval patterns, and delivery metrics openly. Not as a lecture — as an offer. "Here is what we are using. It is working. Take what is useful." Teams adopt practices they can see working, not practices they are told to adopt.

**Identify the binding constraint and escalate with data.** If your delivery is blocked by another team's process gap, do not complain in Slack. Bring the data to your VP: "Our team's cycle time is X. The cross-team integration adds Y. Here is where the gap is, and here is what fixing it would unlock." EMs who escalate with evidence get action. EMs who escalate with frustration get sympathy.

## AI Does Not Reduce Work — It Intensifies It

An eight-month ethnographic study at a 200-person tech company, published in Harvard Business Review, found that generative AI consistently intensifies work rather than reducing it.[^hbr-intensifies]

The researchers identified three patterns that every EM should watch for:

**Task expansion.** People take on work they did not own before. PMs start coding. Designers write scripts. Engineers spend additional time reviewing and correcting AI-assisted work from non-engineers. The scope of each role creeps outward, and nobody adjusts capacity expectations to match.

**Blurred boundaries.** The conversational interface makes work feel like chatting. People fire off "one last prompt" before leaving. Recovery periods vanish. Work fills every gap that AI opens.

**Increased multitasking.** People manage multiple AI threads simultaneously. Speed expectations rise through normalized visibility. If everyone can see how fast output is arriving, slow-and-careful starts to look like slow-and-lazy.

The self-reinforcing cycle: AI accelerates some tasks, which raises expectations for speed, which makes people more reliant on AI, which widens the scope of attempted work, which increases total load. One study participant said it plainly: "You had thought that maybe...you can work less. But then really, you don't work less. You just work the same amount or even more."

A BCG survey of nearly 1,500 workers found the pattern quantified: workers using four or more AI tools saw productivity *plummet*, not rise. High AI oversight correlated with 14% more mental effort, 12% greater mental fatigue, and 19% greater information overload. The most enthusiastic adopters are burning out first.[^bcg-brain-fry]

The critical warning for EMs: this expansion is voluntary and framed as enjoyable experimentation, so you risk overlooking how much additional load your people are carrying. Asking employees to self-regulate is not a winning strategy. You have to set boundaries — protected focus time, explicit scope limits, and clear signals that working-while-chatting-with-AI at 10 PM is not the expectation.

## Coordination Overhead: The Hidden AI Killer

Here is a hypothesis worth taking seriously: the primary reason most companies are not seeing transformative AI gains is not model quality, tool choice, or adoption resistance. It is organizational overhead.

Coordination cost scales with team size. Meetings, alignment sessions, cross-team dependencies, approval chains, status updates, Slack threads, and the ambient friction of keeping fifty people pointed in the same direction — all of it consumes hours that AI cannot reclaim because those hours are not spent coding. They are spent coordinating.

When AI makes individual contributors 2-5x more productive at generation, the *opportunity cost* of coordination overhead does not stay constant. It multiplies. Every hour an engineer spends in a sync meeting is now an hour where they could have been 3x more productive with an AI tool. Every day lost to cross-team alignment is a day where AI-amplified output did not happen. The overhead that was tolerable at human speed becomes painful at AI speed.

The evidence is in the revenue-per-employee numbers.

AI-native companies operate in a different structural universe. Cursor reached $100M ARR with 20 people and now runs at roughly $3-5M revenue per employee with ~150 staff. Lovable hit $400M ARR with 146 employees — $2.7M per head. Midjourney built to $500M with fewer than 165 people. Bolt reached $40M ARR with 35 people.[^lean-ai][^vc-corner]

Compare that to the SaaS gold standard of $300K revenue per employee. AI-native companies are running at 10-17x that benchmark. They are not doing this by working harder. They are doing it by having almost zero coordination overhead. Small teams, tight alignment, minimal management layers, no cross-team dependency chains.

Traditional companies see this and try to add AI tools to their existing structure. But if your org has 400 engineers across 30 teams with a matrix reporting structure, three layers of management, and quarterly planning cycles that take six weeks — the AI multiplier is fighting the coordination tax. The multiplier loses.

![Coordination overhead vs. AI gains: small teams capture most of the value](images/13.03-coordination-overhead-vs-ai-gains.png)

The Cortex 2026 Engineering Benchmark found that PRs per author rose 20% year-over-year while incidents per PR increased 23.5% and change failure rates climbed ~30%. Their conclusion: "AI acts as an indiscriminate amplifier. It takes your existing engineering practices, both the good and the bad, and magnifies their impact."[^cortex-2026] If your existing practices include high coordination overhead, AI amplifies that too.

Goldman Sachs reported in March 2026 finding "no meaningful relationship" between AI adoption and economy-wide productivity gains. A C-suite survey of 6,000 leaders found 90% saw no evidence of AI impacting productivity over three years. Gartner predicts a 40% AI project failure rate due to hype-driven investment, with only 1 in 50 AI initiatives delivering transformative value.[^gartner-failure]

My read on this data: the failure is not AI. The failure is applying AI inside organizational structures that were designed for a pre-AI world. The coordination overhead eats the gains before they reach the customer.

**What you can do within your team (no escalation needed):**

- Protect focus time. Block 4-hour uninterrupted windows. Cancel any recurring sync that does not have a decision outcome. Default to async.
- Batch cross-team requests. Instead of ad-hoc Slack threads to the platform team, accumulate requests and send one batched ask per day or per sprint.
- Reduce internal handoffs. If two people on your team are passing work back and forth, give one person end-to-end ownership.
- Measure your team's maker-time ratio. If engineers spend less than 60% of their week on focused work, coordination is eating your AI multiplier.

**What requires escalation with evidence (multi-quarter campaign):**

- Team structure changes across the org chart — this requires director or VP sponsorship. Bring the coordination cost data and your team's before/after comparison, not a reorg proposal.
- Planning cycle changes — shortening quarterly planning or changing approval chains is above your pay grade. But you can show the cost: "Our team lost X days this quarter to planning overhead. Here is what that cost in shipped outcomes."
- Cross-team dependency restructuring — you cannot force another team to change. You can make the dependency cost visible with data and escalate to your VP.

Worklytics benchmarks suggest 3-5 developers hit the highest per-person productivity; beyond that, coordination overhead grows faster than output.[^worklytics] The Cursor/Lovable/Midjourney numbers are the destination. Your job is to prove the principle works at your scale, within your scope, with evidence your leadership can act on. That is a multi-quarter campaign, not a Monday morning action.

## Burnout Is the Risk You Are Not Tracking

The HBR "Brain Fry" study (March 2026) found 1 in 7 knowledge workers report mental fatigue from juggling AI tools — with a 33% increase in decision fatigue and a 39% increase in major error rates among affected staff.[^hbr-brain-fry] UC Berkeley researchers found AI had "the opposite effect it was supposed to": employees worked faster, on wider scope, for longer periods — not because managers forced them, but because they felt empowered. Lunch breaks became prompting sessions. Recovery time vanished.[^uc-berkeley-burnout]

Here is the paradox: AI can both reduce burnout and create it. When workers use AI to offload repetitive tasks, stress drops. When workers must constantly supervise multiple AI systems, mental strain spikes. The difference is whether AI reduces cognitive load or adds a supervision layer.

Your high performers are at the highest risk. They adopt most aggressively and push hardest. They are also the people you can least afford to lose.

**Three concrete policies:**

1. **Enforce disconnection time.** Not as a feel-good gesture — as an operational decision. Research suggests rigid forced-break mandates can backfire by frustrating autonomy.[^disconnect-research] Instead, set explicit team norms: no AI-thread work after hours, no expectation of weekend prompting sessions, and visible modeling from you. If the EM is prompting Claude at 10 PM, the team reads that as the standard.

2. **Limit concurrent AI supervision.** The BCG data showed sharp declines when workers used four or more AI tools simultaneously. Set a default: one primary AI workflow per focus block. Sequential beats parallel when cognitive load is the constraint.

3. **Budget learning time explicitly.** If someone needs two weeks to figure out how AI fits into their workflow and their output dips, do not let performance metrics punish them. Name the learning investment out loud in team meetings. "This sprint, Alex is spending 30% on delivery loop adoption. That is planned, not a gap."

The EM who ignores burnout will eventually explain to their VP why their best senior engineer just accepted an offer somewhere with fewer agents and more sanity.

## Change Management: An Honest Note

You will look for an established change management framework for AI adoption. There is not one yet.

Prosci's research on 2,600 change practitioners describes AI adoption as "a never-ending Phase 2" — the technology evolves so fast that traditional models designed for finite transitions break down.[^prosci] McKinsey's 2025 report argues that bolting AI onto existing processes delivers incremental-at-best impact, and that workflow redesign is the #1 predictor of AI value creation.[^mckinsey-reconfig]

The honest advice a book can give in a field moving this fast: build tight feedback loops, measure what matters (Chapter 11), iterate in 30-day cycles, and accept that your change process will itself change quarterly. Anyone selling you a rigid 18-month AI transformation roadmap is selling furniture for a house that is still being built.

## The Emotional Dimension You Cannot Skip

People on your teams are not just learning new tools. Some of them are experiencing an identity shift.

The senior engineer who spent ten years mastering a craft is watching a tool produce mediocre versions of their work in seconds. The fact that "mediocre" is not "good" does not fully offset the psychological impact of seeing the entry cost to their profession drop. The junior engineer who got hired for their ability to write code is wondering whether that ability has a shelf life.

You cannot fix this with a process document. But you can do three things that matter:

**Name it.** In 1:1s, say explicitly: "This transition is hard, and it is normal to feel uncertain about where you fit. Let me tell you specifically what I see as valuable about your work and where that value is increasing, not decreasing." Vague reassurance is worthless. Specific reassurance based on observable work lands.

**Reframe the identity.** "Your job is not to write code. Your job is to make sure the right code ships safely. That job just got harder and more important, not easier and less important." Chapter 15's moat framework is useful here — help people see that the four moats (design judgment, reliability depth, domain compression, cross-functional translation) are skills they can develop, and each one becomes more valuable as output volume rises.

**Protect space for learning.** The burnout section above covers this operationally. The emotional version: publicly treating learning time as legitimate investment — not as a productivity gap — sets the cultural tone for the whole team. People who feel safe experimenting adopt faster and more durably than people who feel watched.

### When Someone Says "No Thanks" After a Fair Ramp

A good engineer meets the delivery bar, tried the tools for a real ramp period, and says no. This is not hypothetical. Here is how to think about it.

**The workflow genuinely does not benefit.** Some work — complex legacy systems, heavily regulated codebases, deep kernel-level debugging — does not see meaningful AI gains yet. If the engineer gave the tools a fair shot and the data shows marginal or negative impact on their specific work, that is valid data. Not resistance. Forcing adoption where it does not help is cargo-culting, not management.

**Identity protection masking as a workflow objection.** If peers on similar workflows are seeing gains and this person is not, dig deeper. The tell: the objection shifts. First "the tool is bad," then "my work is different," then "I do not need it." That pattern earns a direct conversation: "I want to understand what is really making this hard. Your job is not at risk for being honest with me."

**The refusal is creating team friction.** If the team has adopted shared practices — spec-first, AI-assisted review, deterministic gates — and one person opts out of the shared workflow, that is a process compliance issue, not a tools issue. You can respect someone's choice not to use AI for generation while still requiring them to participate in the team's review and eval standards.

The key distinction: adoption of AI generation is a preference. Participation in the team's quality process is not optional.

## QA, Observability, and Error Reporting: Your Insurance Policy

If there is one operational investment that pays for itself faster than any other in AI-assisted delivery, it is your quality and observability stack.

Generation speed is a multiplier. Without controls, it multiplies mistakes. With controls, it multiplies trusted output. Your job as an EM is to make sure the controls exist, are used, and are not bypassed under schedule pressure.

**QA coverage is your first line.** Chapter 7's three forms of anti-suck technology (QA checks, model evals, human judgment) are not optional extras for your teams. They are the minimum. If your team does not have contract checks on critical endpoints, invariant checks on business logic, and policy checks for security/compliance, AI-assisted development will create the same category of failure Amazon experienced — structurally broken changes that look clean on the surface.

The EM-specific action: make QA coverage part of your definition of done. Not "write some tests." Specific coverage: every PR to a Tier-1 service must have at least one contract check, one invariant check, and one policy check. Track coverage as a team metric. If coverage drops while PR volume rises, that is the leading indicator of an incident.

**Observability is your second line.** When something breaks — and it will — your team needs to debug from a trace, not from a Slack thread. Chapter 8's trace-first debugging is the operational standard. If your services do not have trace IDs, span-level timing, and retry/timeout visibility, you are debugging by committee. That costs hours per incident and destroys trust.

The EM-specific action: require trace evidence in incident reviews. Not "what do you think happened" but "show me the trace." If the trace does not exist, that is the first finding, not the incident itself.

**Error reporting is your early warning system.** Most teams have some form of error reporting (Sentry, Datadog, PagerDuty). The AI-specific risk is that error volume increases because code volume increased, and the signal-to-noise ratio degrades. Teams start ignoring alerts. That is how a 120,000-order incident hides in a noisy dashboard.

The EM-specific action: review your error reporting weekly with your tech leads. Not the individual errors — the trends. Is error volume climbing? Is it climbing faster than deployment volume? Are new error classes appearing that were not there before? If yes, slow down and fix the source before it compounds.

These three layers — QA, observability, error reporting — are not engineering busywork. They are your insurance policy against the VP conversation you do not want to have: "What happened, and why did nobody catch it?"

## The EM's 90-Day Transition Plan

Chapter 15 has a 90-day plan for ICs. Here is the parallel for EMs. The milestones are different because your levers are different — you are building conditions, not personal skill reps.

**Days 1-30: Understand the system yourself.**

Run the delivery loop (Chapter 6) on one real task yourself — not to become a power user, but to feel where it leaks. You cannot manage a process you have not experienced. Map your team's adoption distribution (eager, skeptical, reckless, quietly terrified). Have the first explicit AI-transition 1:1 with each direct report. Baseline your team's current lead time, rework rate, and review queue time using git history and your issue tracker — you need numbers before you can show improvement.

**Days 31-60: Run the first pilot and publish the first scorecard.**

Pick one committed deliverable and run it through the spec-first loop as a team. Publish the first weekly scorecard (start with whatever metrics you have — even two numbers and one outlier autopsy is enough). Hold the first Thursday 2 PM review. Draft the VP conversation using the three-frame script. Identify your binding cross-team constraint and bring it to your VP with data, not frustration.

**Days 61-90: Prove repeatability and make the case.**

Expand to a second workflow with a different risk shape. Deliver the before/after comparison to your VP. Update your leveling rubric if it still rewards code volume without mentioning delivery quality. Make the headcount or tooling investment case using cost-per-accepted-change data. If gains are repeatable without heroics, propose the next expansion. If not, diagnose and run another cycle — the first attempt is calibration, not proof.

By day 90, you should have: a working scorecard, a VP who understands your delivery-vs-generation framing, a team with at least one clean pilot under their belt, and enough data to make a credible case for whatever comes next.

## Performance Calibration During the Transition

The hardest conversation you will have this year is not about AI adoption. It is about scoring an engineer whose output profile changed and whose rating is ambiguous under the old rubric.

### The 3x Volume / Higher Defect Problem

You will encounter this exact scenario: an engineer who shipped three times the volume with AI assistance, but their defect rate also rose 30%. Under the old rubric, they look like a star (output) and a liability (quality) simultaneously. Under the new rubric, they are over-indexed on the commodity layer and under-indexed on the scarce layer.

Here is how to calibrate:

**Step 1: Separate output metrics from outcome metrics.** PRs merged is output. Accepted changes that stayed in production without rework or rollback are outcomes. Compute both. If outcome count rose even though defect rate rose, the engineer is net-positive but needs coaching on review discipline. If outcome count is flat despite 3x output, they are manufacturing rework.

**Step 2: Score against the new rubric, not the old one.** Use the leveling rubric from earlier in this chapter. Rate the engineer on spec quality, review rigor, eval contribution, and system judgment — not lines shipped. Present both the old score and the new score side by side in the review, so the engineer sees exactly what changed and why.

**Step 3: Frame the conversation around growth, not punishment.** "Your output velocity is exceptional. The next step for you is converting that velocity into trusted outcomes — fewer review cycles, fewer post-merge fixes. Here is specifically what I want to see next quarter." That framing keeps the high performer engaged instead of defensive.

### A Simple Calibration Template

For each direct report, fill in this grid before calibration meetings:

| Dimension | Evidence | Rating (1-5) |
|-----------|----------|---------------|
| Spec quality | Did they write specs before generating? Were non-goals explicit? | |
| Review contribution | Did they catch real issues in others' PRs? Or rubber-stamp? | |
| Delivery quality | Rework rate on their changes. Rollbacks. Post-merge fixes. | |
| System judgment | Did they make a design decision that reduced coordination cost? | |
| Eval/reliability | Did they add or improve deterministic checks? | |
| Mentoring (senior+) | Did they help others ship more reliably, not just faster? | |

The grid forces you to score on the scarce layer. If you cannot fill in the evidence column, you do not have enough data — which is its own finding.

### Defending Headcount When Productivity Rises

Your CFO will ask: "If AI makes developers more productive, why are we not cutting the team?"

This is the most important conversation you will have with Finance. Here is the three-part answer:

**Part 1: Reframe the unit.** "We are not paying for typing. We are paying for judgment, review, and integration. AI accelerated one step in a multi-step process. The bottleneck moved — it did not disappear. Our data shows review queue time is now X% of cycle time, up from Y%. Cutting heads would move the bottleneck back to generation and lose the gains."

**Part 2: Show the capacity reallocation.** "We are not using the productivity gain to do the same work with fewer people. We are using it to do higher-value work with the same people. Specifically: [list 2-3 things the team is now doing that they could not before — backlog reduction, technical debt paydown, new product exploration, reliability improvements]."

**Part 3: Show the fragility risk.** "Our team is [N] people. Our bus factor on [critical system] is [M]. AI does not change the bus factor — it changes the blast radius when someone leaves. If we cut to [N-2] and lose one more person to attrition, we have [M-1] people who understand the system that generates [revenue/uptime/compliance]. That is a business continuity risk, not a productivity discussion."

Write this down and bring it to the Finance conversation. Verbal arguments get forgotten. A one-page memo with the three frames, backed by your scorecard data, gets filed and referenced.

### Measurable Burnout Leading Indicators

The burnout section earlier in this chapter tells you what to watch for qualitatively. Here are the quantitative signals to track weekly:

| Signal | Where to Find It | Warning Threshold |
|--------|------------------|-------------------|
| After-hours commits | `git log --format="%aI" --author="name"` filtered by hour | >20% of commits outside working hours, trending up |
| PR size inflation | GitHub PR insights, LinearB | Median PR size rising >50% over 4 weeks |
| Review participation drop | GitHub/GitLab contribution graphs | Senior engineer goes from 5+ reviews/week to <2 for 3 consecutive weeks |
| 1:1 cancellation rate | Your calendar | Same person cancels or shortens >50% of 1:1s in a month |
| Scope expansion without pushback | Sprint retrospectives | Engineer takes on 3+ unplanned tasks per sprint without flagging capacity |
| Architecture discussion silence | Meeting notes, Slack | Senior engineer stops contributing to design discussions for 2+ weeks |

None of these alone means burnout. Three or more trending in the wrong direction on the same person over a 4-week window is your signal to have a direct conversation — not about performance, about workload.

The cheapest intervention: "I noticed [specific signal]. I am not evaluating you — I am asking whether your current load is sustainable. What would you drop if you could?" That question, asked early, prevents the resignation conversation three months later.

## Why 996 Is Not the Way

There is a seductive logic in the AI era: if AI makes every hour more productive, then more hours means more output. Work longer. Prompt more. Review more. Ship more. Some organizations have always believed this — the Chinese tech industry's 996 culture (9 a.m. to 9 p.m., six days a week) is the extreme version. But even milder forms are spreading: the "always-on" Slack thread, the weekend agent session, the expectation that if AI works at midnight, you should be reviewing its output at midnight.

This logic is precisely backwards. When the bottleneck was typing, more hours meant more code. When the bottleneck is *judgment* — reviewing AI output, catching subtle errors, making design decisions, evaluating tradeoffs — more hours means worse judgment.

The entire thesis of this book is that the scarce layer is decision quality, not production speed. Burning out the decision-makers to increase production speed is like running a hospital's triage nurses on double shifts so the appointment scheduler can book more patients. You get more volume and worse outcomes.

### The Research Is Not Subtle

Stanford economist John Pencavel studied the relationship between hours and output and found that productivity per hour drops sharply after 50 hours per week. After 55 hours, the decline is so steep that the additional hours produce almost nothing.[^pencavel] A 70-hour week — roughly the 996 schedule — produces little more than a 55-hour week in total output. The extra 15 hours are not free. They cost health, judgment, and next week's performance.

The Whitehall II study tracked 2,214 workers over five years and found that those working more than 55 hours per week showed measurably lower cognitive function — including reasoning ability — compared to those working 40 hours or fewer. The cognitive deficit was comparable in magnitude to the effect of smoking.[^whitehall-hours]

The WHO and ILO joint analysis estimated that working 55+ hours per week is associated with a 35% higher risk of stroke and 17% higher risk of heart disease. In 2016, overwork caused an estimated 745,000 deaths globally.[^who-overwork] A 996 schedule is 72 hours per week — well past every threshold in the research.

For software specifically, research on overtime and code quality found that defect counts rise with overtime hours. Even a 10% increase in work hours correlated with measurable productivity drops, and 60-hour weeks showed a 25% decline in productivity.[^overtime-quality]

### Tired People Miss Mistakes — Exactly the Mistakes That Matter Most

The AI era's most important human skill is catching the 10% of generated output that is confidently wrong. That skill runs on exactly the cognitive faculties that fatigue degrades first.

A study of software developers found that a single night of sleep deprivation reduced code quality by 50%.[^fucci-sleep] A meta-analysis of sleep loss and error monitoring confirmed that sleep-deprived workers show consistent impairment in their ability to *consciously recognize errors in real time* — they make more mistakes and catch fewer of them.[^boardman-sleep]

A systematic review of burnout and cognitive functioning found that burnout degrades three specific cognitive domains: executive function, attention, and memory.[^deligkaris-burnout] A follow-up meta-analysis confirmed that burned-out workers show significantly impaired cognitive shifting and inhibition — the exact skills needed to switch between "this AI output looks plausible" and "wait, something is wrong here."[^hanson-burnout] Neuroimaging research found that burnout patients show thinning of the medial prefrontal cortex, the brain region responsible for judgment and decision-making.[^burnout-brain]

Burned-out workers do not just make more errors. They adopt low-effort cognitive strategies — heuristic shortcuts instead of careful evaluation. One study found 33% of burned-out employees defaulted to low-effort decision-making compared to 8% of healthy controls.[^burnout-decisions] In an AI-assisted workflow, low-effort review means rubber-stamping generated output. That is exactly the failure mode that produced Amazon's incidents.

### Rest Is Not Idleness — It Is Where Strategic Thinking Happens

The argument for rest is not just "tired people make mistakes." It is that the most valuable cognitive work — the work that separates senior engineers from juniors, that separates good architectural decisions from bad ones — requires mental states that sustained intensity makes impossible.

Researchers found that engaging in undemanding tasks during breaks from a problem led to a 41% improvement in creative problem-solving compared to sustained focus.[^baird-incubation] REM sleep improved creative problem-solving by almost 40%, through a mechanism the researchers described as "priming associative networks" — the brain connecting ideas that focused attention keeps separate.[^cai-rem]

This is the default mode network at work. When you stop focusing on the immediate problem, your brain does not stop working. It engages in spontaneous processing — self-reflection, future planning, pattern recognition across unrelated domains. That processing is where architectural insight comes from. It is where you realize that the system you are building has the same failure mode as something you saw three years ago. It is where "something about this design feels wrong" crystallizes into "the dependency direction is backwards."

You cannot access this processing at hour 11 of a 12-hour day. You access it on a walk. In the shower. On a Saturday morning when you are not thinking about work and suddenly see the answer. The manager who schedules 996 is not just burning out their team. They are cutting off access to the cognitive mode that produces the highest-value engineering work.

### AI Works While You Sleep — If You Set It Up

Here is the organizational design argument: a team that structures its AI workflow properly gets productive output during every hour of the day, including the hours when humans are resting.

Agent workflows can run overnight. A well-scoped task — with a clear spec, deterministic checks, and automated eval gates — can be assigned to an agent at 6 p.m. and produce a reviewable PR by 8 a.m. Background agents can run test suites, generate migration scaffolds, perform codebase-wide refactors, and produce first-draft implementations while the team sleeps.

The key phrase is *well-scoped task*. An agent running overnight without a spec, without checks, and without eval gates is not productive — it is generating unreviewed code that someone will spend the morning cleaning up. The discipline described in Chapters 6 and 7 — spec-first, deterministic gates, clear acceptance criteria — is what makes async AI work productive instead of wasteful.

The organizational design implication: instead of asking "how do we get more hours from our people," ask "how do we structure work so agents produce reviewable output during off-hours?" That is a management question, not a heroics question. Teams that answer it well get effective 16-hour days from an 8-hour human workday. Teams that answer it with "everyone work longer" get 12-hour human days with degrading judgment and rising defect rates.

### The Manager's Responsibility

If your team is regularly working more than 50 hours a week, that is not dedication. That is a management failure. Either the workload is unsustainable (fix staffing or scope), the process is inefficient (fix the delivery loop), or the culture rewards presence over output (fix the incentives).

Intensity for a defined period — a launch week, an incident response, a critical deadline — is fine. Sustained intensity is organizational debt that compounds in missed defects, design shortcuts, attrition, and the slow degradation of the judgment that makes your team valuable.

The most effective teams I have seen work focused 40-45 hour weeks, use agents for async work, and produce more trusted output than teams grinding 60-hour weeks with degrading attention. The former is a system. The latter is a burnout machine with good intentions.

Protect your team's rest the way you protect your team's deployment pipeline: as critical infrastructure, not as a luxury.

## Incident Response Starts Before the Incident

This has nothing to do with AI specifically. Good incident response is good incident response. But it belongs in this chapter because EMs own the operational readiness that determines whether an incident is a five-minute toggle or a three-hour fire drill.

**Pre-launch resilience checklist.** Before shipping any feature — AI-assisted or not — verify three things. Can you roll back in under five minutes? Do you have a fallback path (feature flag off, fallback API, previous model version)? Are your golden signals dashboarded and alerted? If any answer is no, you are not ready to ship. Full stop.

**Golden signals still matter.** Latency, error rate, traffic, saturation. AI does not change the fundamentals of observability. If anything, AI-generated code makes golden signals *more* important because you have less manual familiarity with the code paths. For AI-specific features, add two signals: token cost per request and model response latency. These catch cost runaway and degraded inference before users notice.

**First 30 minutes: mitigation, not root cause.** The goal in the first half hour is not to understand why it broke. The goal is: can you roll back, toggle off, or switch to a fallback? If you invested in resilience pre-launch, this takes minutes. If you skipped it, you are debugging in production under pressure — which is where the worst decisions get made.

**Then root cause.** After mitigation, trace the failure. Use the postmortem template from Appendix M and the Five Whys framework. Chapter 8 covers trace-first debugging in detail — the same tracing discipline that catches bugs in development is the discipline that accelerates root cause analysis in production.

**The key insight:** Incident response efficiency is directly tied to pre-incident resilience work. Teams that invest in rollback mechanisms, feature flags, and golden signal dashboards resolve incidents in minutes. Teams that skip this work resolve them in hours. The AI element does not change this equation — it amplifies it. More generated code means more surface area you did not write by hand, which means resilience infrastructure is not optional. It is the price of velocity.

## What to Do Monday Morning

1. Have one 1:1 this week where you explicitly ask: "How are you feeling about the AI transition? What is hard?" Listen more than you talk.
2. Pick your next committed deliverable and run it through the spec-first loop (Chapter 6) as a team. Same deadline, same scope, different process. Measure before and after.
3. Draft one slide for your VP using the three-frame structure: generation vs. delivery gap, one metric (cost per accepted change), and what to watch.
4. Review your leveling rubric. If it still rewards code volume without mentioning delivery quality, spec discipline, or eval contribution, update it.
5. Identify the team in your dependency chain with the weakest AI delivery discipline. Offer to share your templates. If that does not work, bring the bottleneck data to your VP.

## Failure Modes to Avoid

The first trap is treating this as a tools problem. "We rolled out Copilot" is not a delivery strategy. It is a procurement decision. The tools are table stakes. The operating model around the tools is where value lives or dies.

The second trap is managing to the median. If you set expectations based on your average adopter, your eager adopters will feel held back and your skeptics will feel ignored. Manage the distribution, not the average.

The third trap is hiding behind the team. When your VP asks "why are we not faster," the answer is yours to give, not your team's. Protect your people from unrealistic expectations by translating the delivery reality upward with data. That is your job.

The fourth trap is ignoring the emotional dimension. If people feel threatened and you only talk about process, you will get compliance without commitment. Compliance ships code. Commitment ships systems.

## 3 Main Takeaways You Need to Remember

1. Your job is not to adopt AI tools — it is to create the conditions for trusted delivery at scale while everything shifts underneath.
2. Manage the adoption distribution (eager, skeptical, reckless, terrified), not the average. Each group needs different support.
3. The VP conversation is a translation problem: frame generation vs. delivery, give one outcome metric, and tell them what to watch.

## Wrapping up on the EM's role

Chapter 1 drew the distinction between artisans and builders — and noted that managers, by definition, already live in the builder camp. You gave up being the person who writes every line years ago. You are already comfortable with ambiguity, delegation, and reviewing output you did not produce. That gives you a head start on this transition, not because the job gets easier, but because your existing skills map more naturally to the new world.

But a head start is not a free pass. The job is changing shape. You are managing delivery quality, team capability, and organizational trust while the production substrate shifts underneath you. That is harder and more important than coordinating headcount ever was.

The managers who survive this transition will be the ones who can translate between the technical reality and the executive narrative, protect their teams from hype-cycle whiplash, and build operating systems that make AI-assisted delivery predictable and reliable instead of exciting and fragile.

Predictable wins. You know this already.

The next chapter examines hiring, team shape, and the org chart changes that nobody wants to draw but everybody needs.

---

[^amazon-reset]: Eugene Kim, "Amazon Orders 90-Day Reset After Code Mishaps Cause Millions of Lost Orders." Business Insider, March 2026. https://www.businessinsider.com/amazon-tightens-code-controls-after-outages-including-one-ai-2026-3
[^hbr-intensifies]: Aruna Ranganathan and Xingqi Maggie Ye, "AI Doesn't Reduce Work — It Intensifies It." Harvard Business Review, February 2026. https://hbr.org/2026/02/ai-doesnt-reduce-work-it-intensifies-it
[^bcg-brain-fry]: Julie Bedard et al., BCG/HBR study on AI cognitive overload, reported in Fortune, March 10, 2026. https://fortune.com/2026/03/10/ai-brain-fry-workplace-productivity-bcg-study/
[^anthropic-review]: TechCrunch, "Anthropic launches code review tool to check flood of AI-generated code." March 9, 2026. https://techcrunch.com/2026/03/09/anthropic-launches-code-review-tool-to-check-flood-of-ai-generated-code/
[^lean-ai]: Lean AI Leaderboard. https://leanaileaderboard.com/
[^vc-corner]: The VC Corner, "The Billion-Dollar Startup Formula." March 21, 2025. https://www.thevccorner.com/p/the-billion-dollar-startup-formula
[^cortex-2026]: Cortex, "AI Is Making Engineering Faster but Not Better: State of AI Benchmark 2026." https://www.cortex.io/post/ai-is-making-engineering-faster-but-not-better-state-of-ai-benchmark-2026
[^gartner-failure]: Gartner, AI project failure rate survey. June 2025. https://www.gartner.com/en/newsroom/press-releases/2025-06-30-gartner-survey-finds-forty-five-percent-of-organizations-with-high-artificial-intelligence-maturity-keep-artificial-intelligence-projects-operational-for-at-least-three-years
[^worklytics]: Worklytics, "Software Engineering Productivity Benchmarks 2025." https://www.worklytics.co/resources/software-engineering-productivity-benchmarks-2025-good-scores
[^hbr-brain-fry]: Harvard Business Review, "When Using AI Leads to 'Brain Fry.'" March 2026. https://hbr.org/2026/03/when-using-ai-leads-to-brain-fry
[^uc-berkeley-burnout]: Fortune, "UC Berkeley researchers warn AI is having 'the opposite effect it was supposed to.'" February 2026. https://fortune.com/2026/02/10/ai-future-of-work-white-collar-employees-technology-productivity-burnout-research-uc-berkeley/
[^disconnect-research]: Oxford Academic, "Digital Disconnection: A Framework for Research and Practice." Communications Theory, 2024. https://academic.oup.com/ct/article/34/1/3/7595753
[^prosci]: Prosci, "8 Ways AI-Driven Change is Different." 2025. https://www.prosci.com/blog/8-ways-ai-driven-change-is-different
[^mckinsey-reconfig]: McKinsey, "Reconfiguring work: Change management in the age of gen AI." August 2025. https://www.mckinsey.com/capabilities/quantumblack/our-insights/reconfiguring-work-change-management-in-the-age-of-gen-ai
[^pencavel]: John Pencavel, "The Productivity of Working Hours." Stanford Institute for Economic Policy Research Discussion Paper No. 13-006, 2014. https://siepr.stanford.edu/publications/working-paper/productivity-working-hours
[^whitehall-hours]: Virtanen et al., "Long Working Hours and Cognitive Function: The Whitehall II Study." American Journal of Epidemiology, 2009, 169(5), 596-605. https://pmc.ncbi.nlm.nih.gov/articles/PMC2727184/
[^who-overwork]: Pega et al., "Global, Regional, and National Burdens of Ischemic Heart Disease and Stroke Attributable to Exposure to Long Working Hours." WHO/ILO Joint Estimates, Environment International, 2021. https://www.who.int/news/item/17-05-2021-long-working-hours-increasing-deaths-from-heart-disease-and-stroke-who-ilo
[^overtime-quality]: "Impact of Overtime and Stress on Software Quality." ResearchGate. https://www.researchgate.net/publication/259781769_Impact_of_Overtime_and_Stress_on_Software_Quality
[^fucci-sleep]: Fucci et al., "Need for Sleep: The Impact of a Night of Sleep Deprivation on Novice Developers' Performance." IEEE Transactions on Software Engineering, 2018. https://arxiv.org/abs/1805.02544
[^boardman-sleep]: Boardman et al., "The Impact of Sleep Loss on Performance Monitoring and Error-Monitoring: A Systematic Review and Meta-Analysis." Sleep Medicine Reviews, 2021. https://pubmed.ncbi.nlm.nih.gov/33894599/
[^deligkaris-burnout]: Deligkaris et al., "Job Burnout and Cognitive Functioning: A Systematic Review." Work & Stress, 2014, 28(2), 107-123. https://www.tandfonline.com/doi/abs/10.1080/02678373.2014.909545
[^hanson-burnout]: Magnusson Hanson et al., "Cognitive Function in Clinical Burnout: A Systematic Review and Meta-Analysis." Work & Stress, 2021. https://www.tandfonline.com/doi/full/10.1080/02678373.2021.2002972
[^burnout-brain]: "Burnout and the Brain." Association for Psychological Science, Observer. https://www.psychologicalscience.org/observer/burnout-and-the-brain
[^burnout-decisions]: "The Relationship Between Burnout and Decision-Making Style." ResearchGate, 2016. https://researchgate.net/publication/305811893_The_relationship_between_burnout_and_risk-taking_in_workplace_decision-making_and_decision-making_style
[^baird-incubation]: Baird et al., "Inspired by Distraction: Mind Wandering Facilitates Creative Incubation." Psychological Science, 2012, 23(10), 1117-1122. https://pubmed.ncbi.nlm.nih.gov/22941876/
[^cai-rem]: Cai et al., "REM, Not Incubation, Improves Creativity by Priming Associative Networks." PNAS, 2009. https://www.pnas.org/doi/10.1073/pnas.0900271106
