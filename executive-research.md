# Executive Research: AI Augmented Development
## Strategic Brief for CTO / CPO / CEO

**Compiled:** March 2026
**Purpose:** Raw research brief — source data, strategic synthesis, hidden dynamics. Not yet shaped for a chapter or argument.

---

## PART 1: SOURCE TABLE — The Four Articles + Original Studies

| Article | Original Study | Headline Finding | Sample / Methodology | Key Caveats |
|---------|---------------|-----------------|----------------------|-------------|
| [Inc.com — "AI Isn't Saving Companies Much Time or Money"](https://www.inc.com/kit-eaton/not-so-fast-ai-isnt-saving-companies-much-time-or-money-study-says/91183471) | **"The Adoption of ChatGPT"** — Humlum & Vestergaard, BFI Working Paper No. 2024-50, Univ. of Chicago ([link](https://bfi.uchicago.edu/wp-content/uploads/2025/04/BFI_WP_2025-56-2.pdf)) | Average time savings: **2.8%** (~1 hr/week). No firm-level impact on employment or wages. | 100,000 Danish workers across 11 occupations exposed to ChatGPT. Survey linked to admin labor data. Nov 2023–Jan 2024. | Denmark-only. Adoption still early. Workers recognize productivity potential but information about capabilities has "limited impact" on adoption. |
| [Adecco — "AI Saves Workers an Average of One Hour Each Day"](https://www.adeccogroup.com/our-group/media/press-releases/ai-saves-workers-an-average-of-one-hour-each-day) | **"Global Workforce of the Future 2024"** — The Adecco Group ([landing page](https://www.adeccogroup.com/global-workforce-of-the-future-research-2024)) | AI saves workers **~1 hr/day** on average. 75% report increased productivity. | 35,000 workers across 27 economies, 20 industries. 5th annual survey. | Only 25% received AI training. 23% tackle same workload, not new work. 21% spend savings on personal time. 13% report job loss. Sector range: 52–75 min saved. |
| [TechRadar — "Just 16 Minutes a Week"](https://www.techradar.com/pro/how-much-time-is-ai-really-saving-your-workers-apparently-just-16-minutes-a-week-as-time-saved-generating-content-is-being-absorbed-by-the-time-required-to-trust-it) | **"The State of Document Intelligence"** — Foxit Software / Sapio Research ([PR Newswire](https://www.prnewswire.com/news-releases/research-finds-89-of-executives-say-ai-boosts-productivity-yet-only-gain-16-minutes-weekly-302710354.html)) | Executives net **+16 min/week**. End users net **−14 min/week** once verification is subtracted. | 1,000 desk-based end users + 400 senior executives. US + UK. Published March 11, 2026. | Focused on document work only. Executives believe they save 4.6 hrs/week; actually spend 4 hrs 20 min verifying. End users: save 3.6 hrs, spend 3 hrs 50 min verifying. |
| [Mashable — AI Report: Time Saved, Executives vs. Workers](https://mashable.com/article/ai-report-time-saved-workplace-executives-workers) | **Section AI survey of 5,000 white-collar workers** (referenced via Wall Street Journal) | Exec/worker perception gap: >40% of execs claim 8+ hrs/week savings; 2/3 of non-management report <2 hrs or zero. | 5,000 white-collar workers. AI consulting firm Section. | Execs measure their own use; workers report actual task-level impact. Different measurement objects. |

---

## PART 2: MAJOR STUDIES — Full Detail

### METR Randomized Controlled Trial (July 2025)
**"Measuring the Impact of Early-2025 AI on Experienced Open-Source Developer Productivity"**
- URL: https://metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study/ | https://arxiv.org/abs/2507.09089
- **Design:** RCT — 16 experienced developers, 246 real issues, randomly assigned to allow/disallow AI
- **AI tools:** Cursor Pro with Claude 3.5/3.7 Sonnet
- **Repos:** Major open-source projects with 22,000+ stars, 1M+ lines of code; devs had avg. 5 years of prior experience
- **Core finding: AI made developers 19% SLOWER**
- **The perception gap:** Before tasks, devs forecast AI would speed them up 24%. After tasks, they reported AI sped them up 20%. Actual: 19% slower.
- **Five likely causes:** Miscommunication with AI, time correcting suggestions, context-switching, integration challenges, testing/docs overhead
- **Caveats:** Only 16 devs; mature repos may be harder for AI; not generalizable to greenfield, junior devs, or simpler tasks; learning effects may appear after 100s of hours of usage
- **Follow-up:** Later sub-study estimated −18% speedup with CI between −38% and +9%

### NBER "Firm Data on AI" (2026)
**Yotzov, Barrero, Bloom et al. — NBER Working Paper No. 34836**
- URL: https://www.nber.org/papers/w34836
- **Design:** Representative international survey of ~6,000 CFOs/CEOs/executives across US, UK, Germany, Australia
- **Core finding: Over 80% of firms report NO impact on employment or productivity over the last 3 years**
- 70% of firms actively use AI; over 2/3 of top execs use AI (avg. 1.5 hrs/week; 25% report zero use)
- Forward forecast: firms expect AI to boost productivity 1.4%, output 0.8%, cut employment 0.7% over next 3 years
- **Expectation gap:** Senior executives predict job cuts; employees predict net job creation
- Historical parallel: Solow Productivity Paradox — "You can see the computer age everywhere but in the productivity statistics" (1987)
- Apollo economist Torsten Slok: "AI is everywhere except in the incoming macroeconomic data"

### PwC 29th Global CEO Survey (January 2026 / Davos)
- URL: https://fortune.com/2026/01/19/pwc-global-chairman-mohamed-kande-ai-nothing-basics-29th-ceo-survey-davos-world-economic-forum/
- **Design:** 4,454 CEOs across 95 countries
- **Core finding: 56% of CEOs report "getting nothing out of" AI**
- Only 10–12% report seeing benefits on revenue or cost
- PwC Chairman Mohamed Kande: companies "forgot the basics" — clean data, solid processes, proper governance
- CEO revenue-growth confidence at 5-year low: 30% confident (down from 56% in 2022)
- MIT study cited alongside: 95% of generative AI pilots failing

### McKinsey State of AI 2025
**"How Organizations Are Rewiring to Capture Value"**
- URL: https://www.mckinsey.com/capabilities/quantumblack/our-insights/the-state-of-ai-how-organizations-are-rewiring-to-capture-value
- **Core finding: Only 39% of organizations report any EBIT impact from AI**
- Only **6% of respondents** qualify as "AI high performers" (5%+ EBIT impact + "significant" value)
- 88% use AI in at least one function; only 1/3 have scaled it enterprise-wide
- **Workflow redesign = #1 correlate with EBIT impact** (tested against 25 attributes)
  - High performers: nearly 3x more likely to fundamentally redesign workflows
  - High performers: 3.6x more likely to pursue transformative (not incremental) change
  - High performers: 3x more likely to have active senior leadership ownership
  - High performers: 5x more likely to spend >20% of digital budget on AI
- 62% experiment with AI agents; only 23% scaling at least one agentic system
- 32% expect workforce reductions; simultaneously hiring for AI-specialized roles

### Workday "Beyond Productivity" (January 2026)
- URL: https://newsroom.workday.com/2026-01-14-New-Workday-Research-Companies-Are-Leaving-AI-Gains-on-the-Table
- **Design:** 3,200 full-time employees, orgs with $100M+ revenue, North America + APAC + EMEA. Fielded by Hanover Research, November 2025. All respondents were active AI users.
- **Core findings:**
  - **Nearly 40% of AI time savings are lost to rework** (error correction, rewriting, output verification)
  - **77% of daily AI users review AI-generated work as carefully as or more carefully than human work**
  - **Only 14% of employees consistently get clear, positive net outcomes from AI**
  - 85% report AI saves 1–7 hours/week, but the rework tax erases most of it
  - "Employees are using 2025 tools inside 2015 job structures" — fewer than 10% of orgs have updated roles for AI
  - 79% of employees with positive AI outcomes had access to increased skills training
- Quote from Gerrit Kazmaier (President, Product & Technology, Workday): "Too many AI tools push the hard questions of trust, accuracy, and repeatability back onto individual users"

### EY Work Reimagined Survey 2025
- URL: https://www.ey.com/en_gl/newsroom/2025/11/ey-survey-reveals-companies-are-missing-out-on-up-to-40-percent-of-ai-productivity-gains-due-to-gaps-in-talent-strategy
- **Design:** 15,000 employees + 1,500 employers across 29 countries, 19 sectors
- **Core finding: Companies are missing up to 40% of potential AI productivity gains due to talent strategy gaps**
- 88% of employees use AI daily — but almost all for basic tasks (search, summarization)
- **Only 5%** use AI in sophisticated ways that meaningfully reshape their work
- 23–58% of workers (varies by sector) deploy unauthorized AI tools despite employer provisions
- 37% worry AI reliance will diminish their professional capabilities
- 64% report escalating workload demands
- 12% receive adequate training
- Only **28% of organizations** are positioned to achieve "Talent Advantage"
- Five talent dimensions: AI adoption excellence, learning infrastructure, talent health metrics, organizational culture, reward alignment

### BCG AI at Work 2025
- URL: https://www.bcg.com/publications/2025/ai-at-work-momentum-builds-but-gaps-remain
- **Core finding:** Companies in "Reshape" mode (redesigning workflows around AI) save significantly more time and report higher-quality outputs than those in "Deploy" mode (using AI as a point tool)
- When leaders demonstrate strong AI support: employees who feel positive about GenAI rises from **15% → 55%**
- Only **1 in 4 frontline employees** currently receives that level of leadership support
- High-performing orgs invest in training, change management, and role evolution — not just tool rollout
- Culture must adapt to sustain new behaviors; frontline engagement is the limiting factor

### Faros AI: "The AI Productivity Paradox Research Report"
- URL: https://www.faros.ai/blog/ai-software-engineering
- **Design:** Telemetry from 1,255 teams, 10,000+ developers, up to 2 years of data
- **Core finding: Individual developer gains are real; company-level gains are not**
  - Teams with high AI adoption: +21% tasks completed, +98% pull requests merged
  - BUT: PR review time increases **91%**
  - Bug rate increases **9%** per developer
  - Average PR size increases **154%**
  - Result: No significant correlation between AI adoption and company-level DORA metrics, throughput, or quality KPIs
- Four adoption patterns explaining the plateau:
  1. Critical mass adoption only recent
  2. Uneven team-level usage
  3. Senior engineers skeptical; junior engineers adopt faster
  4. Surface-level usage (autocomplete only; advanced features underused)

### Bain Technology Report 2025
**"From Pilots to Payoff: Generative AI in Software Development"**
- URL: https://www.bain.com/insights/from-pilots-to-payoff-generative-ai-in-software-development-technology-report-2025/
- **Core finding:** Two-thirds of software firms deployed GenAI tools; typical result is 10–15% productivity boost that doesn't translate to business value because "time saved isn't redirected toward higher-value work"
- **The bottleneck:** Coding = only 25–35% of dev lifecycle. Speeding up coding while leaving testing, integration, release, maintenance unchanged creates downstream congestion
- **High performers** (Goldman Sachs, Netflix): 25–30% gains from end-to-end lifecycle transformation
- Five organizational barriers:
  1. Leadership vacuum
  2. Adoption resistance (75% cite difficulty changing workflows; engineers distrust or fear displacement)
  3. Skills gaps in prompt engineering and output review
  4. No ROI tracking or KPIs for freed capacity
  5. Legacy process/tooling mismatches
- Micro-productivity trap: individual speed gains without system redesign = flat delivery metrics

### DORA 2025 Report
- URL: https://dora.dev/dora-report-2025/
- **Core finding:** "AI's primary role is as an amplifier — magnifying an organization's existing strengths and weaknesses"
- Greatest ROI on AI investment comes from organizational systems, not tools
- AI adoption alone does not guarantee improved delivery performance

### GitHub Copilot: Longitudinal Study (NAV IT, Norway)
- URL: https://arxiv.org/pdf/2509.20353
- **Design:** Observational, 39 developers (25 Copilot users, 14 non-users), 703 repos, 2 years of data
- **Core finding: No statistically significant increase in commit-based activity after Copilot adoption**
- Copilot adopters were already more active before adoption (self-selection bias)
- Weak correlation (ρ≈0.17) between actual output changes and self-reported productivity gains
- Developers reported feeling more productive despite unchanged or declining commit metrics
- Copilot primarily helped with boilerplate, documentation, repetitive tasks

### HBR: "AI Doesn't Reduce Work — It Intensifies It" (Feb 2026)
- URL: https://hbr.org/2026/02/ai-doesnt-reduce-work-it-intensifies-it
- **Design:** 8-month ethnographic study at ~200-person US tech company, April–December, 40+ interviews
- **Three mechanisms of intensification:**
  1. **Task expansion** — workers absorb work that previously justified headcount (PMs write code, researchers do engineering)
  2. **Blurred work-life boundaries** — conversational AI makes work "feel like chatting"; work invades breaks, lunches, evenings
  3. **Multitasking acceleration** — managing multiple AI threads simultaneously; speed expectations rise organizationally
- Key quote: "You had thought that maybe you save some time, you can work less. But then really, you don't work less. You just work the same amount or even more."
- BCG: workers supervising multiple AI tools report 12% more mental fatigue — researchers call it "AI brain fry"
- Mike Manos (CTO, Dun & Bradstreet): "I got the eight hours to two hours, but now I can get 20 hours of work"

### HBR: "Overcoming the Organizational Barriers to AI Adoption" (Nov 2025)
- URL: https://hbr.org/2025/11/overcoming-the-organizational-barriers-to-ai-adoption
- **45% of executives** report ROI below expectations; only **10%** exceeded expectations
- **61% of employees** spent <5 hours learning about AI; **30% received no training**
- Chinese IT firm data: programmers **16–18% less likely** to recommend AI access to teammates

---

## PART 3: WHAT SUCCESSFUL PLAYERS UNDERSTAND (That Customers Don't Say Out Loud)

These are synthesized patterns from the research — things companies that capture AI value know, but don't frame as the sales problem:

### 1. The real product is workflow redesign, not the tool
The tool adoption is table stakes. McKinsey's #1 correlate with EBIT impact isn't the AI tool — it's **fundamental workflow redesign**. Bain puts it bluntly: coding is 25–35% of developer time. Speeding up coding while leaving everything else unchanged creates downstream congestion. The companies seeing 25–30% gains (Goldman Sachs, Netflix) redesigned the entire SDLC around AI. The rest got 10–15% on the margin and called it a pilot.

**What customers say:** "We need better AI tools."
**What they mean:** "We need someone to redesign how work flows so the tool gains don't get absorbed."
**What they don't say:** "We don't know how to redesign our organization."

### 2. Individual productivity gains are not company productivity gains — and the difference eats the ROI
Faros AI's data across 1,255 teams: high AI adoption teams complete 21% more tasks, merge 98% more PRs. PR review time increases 91%. Bugs per developer up 9%. PRs up 154% in size. Net company-level DORA/throughput impact: zero. The bottleneck just moved.

This is the Solow Paradox applied to AI — "you can see the AI everywhere except in the productivity statistics."

**What customers say:** "Developers are shipping more code."
**What they don't say:** "Code is getting reviewed more slowly and breaking more often."

### 3. The verification burden is an invisible AI tax — and it grows with adoption
Foxit/Sapio research: executives believe they save 4.6 hrs/week. They spend 4 hrs 20 min verifying. Net: 16 minutes. End users: save 3.6 hrs, spend 3 hrs 50 min verifying. Net: −14 minutes. Workday: 40% of time savings erased by rework. 77% of daily AI users review AI output as carefully as or more carefully than human work.

The more AI output enters the pipeline, the more review/verification load is imposed on humans downstream. Companies that don't track this see AI adoption numbers going up while throughput stays flat and don't understand why.

### 4. The executive/worker perception gap is not noise — it's a signal about who absorbs the cost
Section survey: >40% of executives claim 8+ hrs/week AI savings. Two-thirds of non-management workers report <2 hrs or zero. Workday: only 14% consistently get clear positive net outcomes. EY: 88% use AI, but 5% use it in ways that actually reshape their work.

The pattern: executives use AI for synthesis/summarization/communication tasks where they own the output. Workers use AI for task execution where they're accountable for the output — and they bear the verification cost. Executives measure their own time savings. Workers measure whether they can actually trust what they ship.

### 5. Trust is the real bottleneck — and it's not solved by making the AI more accurate
Stack Overflow 2025 (49,000 developers): trust in AI accuracy dropped from 40% to 29% year over year. Positive favorability dropped from 72% to 60%. 66% say they spend more time fixing flawed AI code. 75% would ask a human colleague for help over AI on high-stakes tasks.

More capability at the AI layer doesn't automatically increase trust. Trust is earned through consistent performance on tasks where the human can verify correctness without heroic effort. For most professional tasks, verification requires almost as much effort as doing the task directly.

### 6. The 5% vs 88% split is structural, not motivational
EY: 88% use AI for basic tasks; 5% use it in ways that reshape their work. BCG: only 1 in 4 frontline employees gets leadership support for AI adoption. Workday: fewer than 10% of orgs have updated job roles for AI.

**The structure that creates the 5%:** strong leadership modeling + training that goes beyond tool onboarding + roles explicitly redesigned to include AI as a core capability + measurement systems that track AI-enabled outcomes, not AI usage.

**The structure that produces the 88%:** tool rollout, optional training, no role redesign, no measurement change. Workers figure out how to use AI for tasks they already do, and it mostly helps at the margin.

---

## PART 4: THE 3 MARKET ASSUMPTIONS — AND WHAT WOULD MAKE THEM WRONG

### Assumption 1: AI adoption leads to productivity gains

**What the market believes:** If you get your team using AI tools, productivity will improve. The studies showing 14–55% gains on specific tasks prove the potential is there.

**Evidence the market cites:** GitHub's own research showing 55% faster task completion. BCG showing consultants completing 12.2% more tasks at 40% higher quality. Adecco: 1 hour/day saved at scale.

**What would have to be true for this to be wrong:**
- Productivity gains on individual tasks don't aggregate to organizational throughput (Faros: confirmed)
- The verification/rework burden offsets the gains before they reach deliverables (Workday, Foxit: confirmed)
- Adoption is concentrated in tasks where time saved doesn't map to value delivered (EY: the 88% basic use case)
- Selection effects: early adopters were already the highest performers (NAV IT study: confirmed)

**Current signals it might be wrong:** NBER: 80%+ of firms report no impact on employment or productivity over 3 years. PwC: 56% of CEOs report nothing out of AI. McKinsey: only 39% see any EBIT contribution. The individual task studies may be real and the organizational impact studies are also real — they measure different things.

---

### Assumption 2: More training and better tools will unlock the value

**What the market believes:** The reason companies aren't seeing ROI is that employees don't know how to use the tools, and the tools aren't good enough yet. Both problems are solvable with investment and time.

**Evidence the market cites:** BCG: leadership support moves employee positivity from 15% to 55%. EY: only 12% are adequately trained. The implied conclusion: close the training gap, get the value.

**What would have to be true for this to be wrong:**
- The bottleneck is organizational structure and incentive design, not skill (HBR: managers protect headcount because their authority depends on it; HBR intensification study: gains get reabsorbed into more work, not free time)
- Workers are rationally skeptical of tools that impose verification costs they bear personally (Foxit: the trust tax)
- The political resistance is structural, not skill-based: programmers who recommend AI access are less likely to do so because it undermines their colleagues' job security (Chinese IT firm data: 16–18% less likely)
- "Better tools" increases the rework surface area if the organizational system doesn't evolve to handle higher AI output volume

**Current signals it might be wrong:** Even well-trained users at well-resourced companies show the paradox. METR's study used experienced developers who knew the tools well. The issue isn't "not trained enough" — it's that the entire downstream system (review, testing, release, accountability) wasn't redesigned to absorb AI-accelerated output.

---

### Assumption 3: The productivity gains are real and the measurement is just lagging

**What the market believes:** There's always a lag between technology adoption and productivity statistics. The personal computer didn't show up in productivity data for years. AI will too — we just need to be patient.

**Evidence the market cites:** NBER firms forecast 1.4% productivity gain over next 3 years. Historical analogies (electricity, internet, PC). Controlled studies showing real task-level gains.

**What would have to be true for this to be wrong:**
- The task-level gains are real but structurally captured elsewhere (verification absorbed by workers; gains captured by managers in the form of increased output demands with no pay increase)
- AI intensification (HBR ethnographic study: more work, not less) means productivity statistics will reflect more output produced with the same or greater effort — not the same output with less effort
- The gains are real but accruing as competitive positioning (surviving the industry baseline) not measurable productivity improvement
- The "AI tax" of trust/verification may grow proportionally with AI capability — smarter AI makes more confident errors that are harder to detect

**Current signals it might be wrong:** Both the individual task gains AND the organizational non-impact seem robust across multiple methodologies and countries. UC Berkeley Haas ethnographic: workers feel busy and stretched despite AI. Workday: workers are using more time, not less. Fortune/Workday: "more work, not less" is the lived experience. The lag hypothesis is plausible but untested — and companies are acting on it as if it's confirmed.

---

## PART 5: CULTURE, PROCESS, AND MINDSET — HIGH vs. LOW VALUE ADOPTERS

### What High Performers Actually Do Differently (specific, not generic)

**They treat it as a system change, not a tool rollout**
- Goldman Sachs: integrated AI into their development platform AND fine-tuned it on internal codebases. Not just "here's Copilot."
- Netflix: redesigned review processes to handle higher PR volume before adopting AI at scale — they built the receiving system first
- McKinsey high performers: nearly 3x more likely to fundamentally redesign workflows end-to-end before measuring results

**They measure differently**
- Track AI-enabled outcomes (delivery cycle time, defect escape rate, time-to-review), not AI usage metrics (seats, tokens, acceptance rate)
- Workday: orgs with positive AI outcomes reinvest time savings into skills training — they have a redeployment policy, not just a usage policy
- BCG: high performers "implement better systems for tracking value creation from AI investments"

**They redesign the bottleneck, not just the fast part**
- Bain: coding = 25–35% of dev time. High performers redesigned testing, integration, and release simultaneously
- Faros: the PR review bottleneck grew 91% with AI adoption. High performers addressed this before it metastasized
- DORA 2025: AI amplifies existing org strengths and weaknesses — high performers fix the weakness before amplifying it

**They make the leadership commitment visible and specific**
- BCG: leadership support moves employee AI positivity from 15% to 55% — but only 1 in 4 frontline employees gets this
- McKinsey: high performers are 3x more likely to have senior leaders actively using AI and championing it (not just approving budget)
- What this looks like in practice: leaders share their own AI-assisted work in all-hands; leaders publicly model where AI helped and where it failed

**They update the job, not just the tool**
- Workday: fewer than 10% of orgs have updated most roles to reflect AI capabilities. High performers update job scope, success metrics, and accountability structures.
- EY: the 5% who use AI transformatively have roles that explicitly include AI-mediated work. The 88% have roles designed for pre-AI work, with AI bolted on.
- The signal: if the job description and performance review haven't changed, the tool adoption is cosmetic

### Low Performers — The Specific Patterns

- Grassroots, uncoordinated adoption: developers individually explore tools without shared standards, prompting norms, or output review processes
- Usage metrics as success metrics: measuring "% of developers using Copilot" or "acceptance rate" rather than delivery outcomes
- Pilot mode as permanent state: 42% of companies now abandon most AI initiatives before production (up from 17% one year ago)
- Verification cost externalized to individuals: each developer bears their own rework burden; no shared standards for what AI output is trustworthy enough to ship
- Change management as a one-time event: a launch announcement + 1-hour training, not ongoing adaptation of process and role

---

## PART 6: THE HIDDEN POLITICAL AND PERSONAL DYNAMICS

These are the things nobody puts in the survey response but that everyone in the building knows:

### 1. Middle managers are the veto point no one is talking about
The HBR study on organizational barriers names it clearly: "managers are the gatekeepers of AI adoption, yet their authority often depends on the size of their teams." A translation department leader who automates their team's core workflow eliminates the justification for their team — and their bonus.

This isn't irrational resistance. It's rational self-preservation. A manager who makes their 10-person team do the work of 3 people with AI has just made the case for 7 layoffs, which they're responsible for initiating, which their remaining team will resent them for.

The mechanism: managers slow-walk AI pilots, introduce endless requirements, find edge cases that "prove" the AI isn't ready, or simply don't promote usage. They don't say they're doing this. They say they're being responsible stewards of quality.

**Current data:** 42% of companies abandon most AI initiatives before production (up from 17% one year ago). That jump isn't explained by the technology — it's explained by the veto.

### 2. Developers hide AI use — but not for the reason you think
The narrative is "workers hide AI use because they're afraid of looking lazy." The Cornerstone/OnDemand data (1,000 US + 2,000 UK workers) tells a more precise story: the primary driver isn't shame — it's **training deficit**. Workers who don't know whether they're using AI correctly don't want to surface that uncertainty to their manager.

The AI hiding rates: 49% of Americans who use AI at work keep it to themselves (Laserfiche). 57% of US workers reluctant to disclose to manager/colleagues (CornerstoneOnDemand). Anthropic study: 69% report social stigma.

But the deeper dynamic for developers specifically: programmers at the Chinese IT firm studied were **16–18% less likely to recommend AI access to teammates**. They understood that demonstrating AI could do their colleagues' job was a social harm to their team, even if it was individually rational. That's not hiding — that's community protection.

### 3. The "AI Skill Threat" is real, and it's not about job loss — it's about identity
The dsl.pubpub.org research across 3,000+ engineers: "AI Skill Threat" = "fear, anxiety, and worry that current skills will quickly become obsolete." It's not "will I have a job?" It's "will being good at what I've spent a decade getting good at matter?"

Engineers with strong beliefs in "innate brilliance" (the developer-as-craftsperson identity) are most vulnerable. Learning cultures with psychological safety lower threat perception.

The identity dynamic: senior engineers have the most to lose from AI devaluing deep expertise. They're also the most influential in peer culture. Stack Overflow 2025: Faros data shows **higher AI skepticism among senior engineers than junior engineers**. This creates an adoption inversion — the engineers with the most organizational credibility are the ones least likely to model enthusiastic AI use.

### 4. "Workslop" is destroying team trust from the inside
CNBC introduced the term in September 2025: AI-generated work that "masquerades as good work but lacks the substance to meaningfully advance a task." ~40% originates from peers; at least 16% from supervisors.

The organizational impact: once a team has experienced workslop from a colleague, they review all AI-assisted output with higher scrutiny — regardless of source. This is rational (the Workday finding that 77% review AI output as carefully as human output). But it means AI adoption raises the review burden on the entire team, not just the individual using it.

This doesn't show up in productivity surveys. It shows up in culture — teams that feel less trusting of each other's work.

### 5. The "AI intensification" trap is invisible to the people creating it
HBR ethnographic study: executives don't experience the intensification — they benefit from it. "I got the eight hours to two hours, but now I can get 20 hours of work" (Mike Manos, Dun & Bradstreet CTO). From the CTO's perspective: AI delivered exactly what was promised. From the team's perspective: AI delivered more work with no change in compensation, head count, or recognition.

UC Berkeley Haas research: AI-enabled workers report "momentum and expanded capability" alongside "feeling busier, more stretched, or less able to fully disconnect." These are the same people — the dual experience is the point. Workers feel productive AND overextended simultaneously. The productivity shows up in metrics. The overextension shows up in burnout surveys and attrition 12 months later.

BCG data: workers supervising multiple AI tools report **12% more mental fatigue**. This is being labeled "AI brain fry" in the research literature. It's not in any standard engagement survey.

### 6. The compliance gap creates shadow AI and ungoverned risk
EY: 23–58% of workers (sector-dependent) use unauthorized AI tools despite employer provisions. Laserfiche: 46% of employees paste company information into public AI tools without knowing if content is sensitive. Only 1 in 3 organizations has clear AI policy and approved tools.

The political dynamic: the people creating policy (legal, IT, security) don't use the tools. The people using the tools (engineers, PMs, analysts) don't own the policy. Nobody in the middle is translating between them. The result is policy that's too restrictive to be followed, so it isn't.

---

## PART 7: SUPPLEMENTARY DATA POINTS AND QUOTES

- **OpenAI Enterprise data (2025):** "Frontier workers" (95th percentile adoption intensity) send 6x more messages than median. Coding: 17x gap. They report saving 10+ hours/week. (The 5% vs 88% again — same pattern, different data source.)

- **GitClear 2024:** AI-generated code has **41% higher churn rate** than human-written code — more frequent revisions, lower initial quality

- **Stack Overflow 2025 (49,000 developers):** 80% now use AI tools; 51% daily. Trust in AI accuracy: dropped from 40% to 29% YoY. Positive favorability: 72% → 60%. 66% spend more time fixing flawed AI code. 75% would ask a human colleague on high-stakes tasks. 64% don't view AI as a job threat (down from 68%).

- **Section AI (5,000 white-collar workers):** 40% said they'd never use AI again

- **Gartner (projected):** 40%+ of agentic AI projects will be canceled by 2027

- **DORA 2025:** "Greatest returns on AI investment come not from the tools themselves but from a strategic focus on the underlying organizational system"

- **LSE Business Review, Feb 2026:** "AI productivity gains should be measured in more than minutes saved" — argues that framing productivity as time savings systematically undercounts quality, learning, and strategic work value

- **San Francisco Fed, Feb 2026 (AI Moment paper):** Macro-level productivity gains from AI remain undetected in official statistics despite measurable firm-level adoption

---

## PART 8: SOURCE INDEX

| Source | URL | Date | Type |
|--------|-----|------|------|
| BFI Working Paper (Humlum & Vestergaard) | https://bfi.uchicago.edu/insights/the-adoption-of-chatgpt/ | 2024 | Academic |
| Adecco Global Workforce of the Future 2024 | https://www.adeccogroup.com/global-workforce-of-the-future-research-2024 | Oct 2024 | Survey |
| Foxit State of Document Intelligence | https://www.foxit.com/state-of-document-intelligence/ | Mar 2026 | Survey |
| METR RCT Study | https://metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study/ | Jul 2025 | RCT |
| NBER Firm Data on AI (w34836) | https://www.nber.org/papers/w34836 | 2026 | Academic |
| PwC 29th Global CEO Survey | https://fortune.com/2026/01/19/pwc-global-chairman-mohamed-kande-ai-nothing-basics-29th-ceo-survey-davos-world-economic-forum/ | Jan 2026 | Survey |
| McKinsey State of AI 2025 | https://www.mckinsey.com/capabilities/quantumblack/our-insights/the-state-of-ai-how-organizations-are-rewiring-to-capture-value | 2025 | Survey |
| Workday Beyond Productivity | https://newsroom.workday.com/2026-01-14-New-Workday-Research-Companies-Are-Leaving-AI-Gains-on-the-Table | Jan 2026 | Survey |
| EY Work Reimagined 2025 | https://www.ey.com/en_gl/newsroom/2025/11/ey-survey-reveals-companies-are-missing-out-on-up-to-40-percent-of-ai-productivity-gains-due-to-gaps-in-talent-strategy | Nov 2025 | Survey |
| BCG AI at Work 2025 | https://www.bcg.com/publications/2025/ai-at-work-momentum-builds-but-gaps-remain | Jun 2025 | Survey |
| Faros AI Productivity Paradox | https://www.faros.ai/blog/ai-software-engineering | 2025 | Analysis |
| Bain Technology Report 2025 | https://www.bain.com/insights/from-pilots-to-payoff-generative-ai-in-software-development-technology-report-2025/ | 2025 | Survey |
| DORA 2025 | https://dora.dev/dora-report-2025/ | 2025 | Survey |
| GitHub Copilot Longitudinal (NAV IT) | https://arxiv.org/pdf/2509.20353 | 2025 | Observational |
| HBR: AI Intensifies Work | https://hbr.org/2026/02/ai-doesnt-reduce-work-it-intensifies-it | Feb 2026 | Ethnographic |
| HBR: Organizational Barriers | https://hbr.org/2025/11/overcoming-the-organizational-barriers-to-ai-adoption | Nov 2025 | Research |
| dsl.pubpub.org: Developer Identity | https://dsl.pubpub.org/pub/the-new-dev/release/1 | 2025 | Research |
| Stack Overflow Developer Survey 2025 | https://stackoverflow.blog/2025/12/29/developers-remain-willing-but-reluctant-to-use-ai-the-2025-developer-survey-results-are-here/ | Dec 2025 | Survey |
| CNBC: Workslop | https://www.cnbc.com/2025/09/23/ai-generated-workslop-is-destroying-productivity-and-teams-researchers-say.html | Sep 2025 | News |
| CornerstoneOnDemand: Hidden AI | https://www.cornerstoneondemand.com/company/news-room/press-releases/hidden-ai-lack-of-training-keeps-ai-use-in-the-shadows-despite-ai-usage-encouragement-from-employers/ | Oct 2025 | Survey |
| Laserfiche: Shadow AI | https://securitytoday.com/articles/2025/08/18/survey-nearly-half-of-employees-hide-workplace-ai-use.aspx | Aug 2025 | Survey |
| Platformer: AI Productivity Paradox | https://www.platformer.news/ai-productivity-paradox-metr-pwc-workday/ | 2025/2026 | Analysis |
| Fortune: AI Productivity Paradox (Solow) | https://fortune.com/2026/02/17/ai-productivity-paradox-ceo-study-robert-solow-information-technology-age/ | Feb 2026 | News |
| Fortune: More Work Not Less | https://fortune.com/2026/03/10/ai-productivity-workers-workday-efficiency/ | Mar 2026 | News |

---

## PART 9: ADDITIONAL FINDINGS FROM PARALLEL RESEARCH

### Corrected BFI Study Title
The Inc.com study is more precisely titled **"Large Language Models, Small Labor Market Effects"** (not "The Adoption of ChatGPT," which was an earlier related working paper).
- Full PDF: https://bfi.uchicago.edu/wp-content/uploads/2024/04/BFI_WP_2024-50.pdf
- SSRN: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4807516
- Key additional detail: Workers reallocated **80%+ of time savings to additional work tasks** (editing AI output, adjusting assessments) — not to leisure. Only 3–7% of productivity gains translated to higher pay.

### HBS/BCG "Jagged Technological Frontier" Study (2023)
**Crucial concept missing from main file**
- URL: https://papers.ssrn.com/sol3/papers.cfm?abstract_id=4573321 | HBS: https://www.hbs.edu/faculty/Pages/item.aspx?num=64700
- Sample: 758 BCG consultants, RCT design
- Core finding: Within the AI capability boundary, consultants completed 12.2% more tasks, 25.1% faster, at 40% higher quality. For tasks **outside** the frontier, consultants using AI performed **19 percentage points worse** than those without.
- The frontier is invisible from the outside — there's no label on the tool saying "this task is outside AI's reliable capability zone"
- **Strategic implication:** Companies that map their jagged frontier before broad deployment capture gains. Companies that deploy uniformly hit the outside-frontier penalty unknowingly.

### BCG "Widening AI Value Gap" (September 2025)
- URL: https://www.bcg.com/publications/2025/are-you-generating-value-from-ai-the-widening-gap
- PDF: https://media-publications.bcg.com/The-Widening-AI-Value-Gap-Sept-2025.pdf
- Only **5% of companies** qualify as "future-built" on AI
- These 5% plan to spend 2x more than laggards
- They capture double the revenue improvement and 40% greater cost reduction
- **70% of potential AI value sits in core business redesign** (R&D, sales, manufacturing) — NOT in support function automation (HR, legal, admin), which is where most companies have focused
- Shared ownership between business and IT: future-built companies are 1.5x more likely to have this model

### Microsoft/LinkedIn 2024 Work Trend Index
- URL: https://www.microsoft.com/en-us/worklab/work-trend-index/ai-at-work-is-here-now-comes-the-hard-part
- Sample: 31,000 full-time workers across 31 markets
- **52% of AI users hide usage on important tasks**; 53% worry it makes them look replaceable
- **But also:** 66% of leaders say they wouldn't hire someone without AI skills
- Workers have correctly inferred demonstrated AI skill is valued — but can't communicate AI-assisted quality without appearing to hedge

### Two Additional Hidden Political Dynamics (from parallel research)

**Dynamic 6: The Experience-Authority Inversion**
AI tools disproportionately benefit less-experienced workers by providing scaffolding. This narrows the visible output gap between senior and junior workers. In orgs where authority derives from demonstrated superior output, this threatens senior employees' standing — not from replacement, but from junior work looking comparable.
- Faros AI: Higher AI adoption found among newer/less-experienced engineers; senior developers slower to adopt tools that commoditize their advantages
- HBR: "Hierarchy disruption — junior employees outperforming seniors undermines experience-based authority structures"
- The compounding dynamic: senior engineers are then asked to review AI-assisted junior work at volume (PR review time +91%, PR size +154%). Their bottleneck role becomes visible as a "productivity constraint" — creating organizational pressure on the people most capable of improving AI quality to do it faster on tasks they find professionally unsatisfying.

**Dynamic 7: The Expectation-Reality Misperception Loop**
Workers systematically believe AI is helping more than it is. The AI generation step *feels* fast. The overhead costs (prompt engineering, validation, context reconstruction, debugging) are not psychologically attributed to the AI. This creates a reinforcing illusion.
- METR: Developers predicted 24% speedup, estimated 20% speedup after the study, actual result: 19% slower. Misperception persisted even after experiencing the outcome.
- Organizational consequence: managers ask "is AI helping?" and workers say yes — because it genuinely feels like yes. When the company measures outcomes, there's no improvement. Executives conclude there's a measurement problem rather than an AI effectiveness problem.
- This is the mechanism behind the Fortune/NBER finding: ~90% of S&P 500 executives describe AI as positive in earnings calls; ~90% of those same companies show no productivity impact in the data.

### HBR "Most AI Initiatives Fail — 5Rs Framework"
- URL: https://hbr.org/2025/11/most-ai-initiatives-fail-this-5-part-framework-can-help
- Case data: Companies using the 5Rs framework (weekly operations reviews, biweekly executive committees, standardized architectures, accountability assigned to project sponsors from day one) reduced delivery times 50–60% compared to ad hoc AI projects
- Employee participation in tool selection → 3.5x higher adoption

### Additional Source URLs (from parallel research)
- BCG press release on leaders vs laggards: https://www.bcg.com/press/30september2025-ai-leaders-outpace-laggards-revenue-growth-cost-savings
- Deloitte AI ROI paradox: https://www.deloitte.com/global/en/issues/generative-ai/ai-roi-the-paradox-of-rising-investment-and-elusive-returns.html
- Deloitte State of AI Enterprise 2026: https://www.deloitte.com/us/en/what-we-do/capabilities/applied-artificial-intelligence/content/state-of-generative-ai-in-enterprise.html
- WEF "Proof over Promise" 2026: https://www.weforum.org/publications/proof-over-promise-insights-on-real-world-ai-adoption-from-2025-minds-organizations/
- MIT 2025 AI pilot failure study (Fortune): https://fortune.com/2025/08/18/mit-report-95-percent-generative-ai-pilots-at-companies-failing-cfo/
- California Management Review "Seven Myths About AI and Productivity": https://cmr.berkeley.edu/2025/10/seven-myths-about-ai-and-productivity-what-the-evidence-really-says/
- LSE Business Review "AI productivity measured beyond minutes": https://blogs.lse.ac.uk/businessreview/2026/02/18/ai-productivity-gains-should-be-measured-in-more-than-minutes-saved/
- SF Fed "AI Moment" paper (Feb 2026): https://www.frbsf.org/research-and-insights/publications/economic-letter/2026/02/ai-moment-possibilities-productivity-policy/
- HBR "The Last Mile Problem Slowing AI Transformation": https://hbr.org/2026/03/the-last-mile-problem-slowing-ai-transformation
- Medium: "The Great AI Reckoning — Mutiny of the Middle Managers": https://medium.com/@larrydelaneyjr/the-great-ai-reckoning-of-2026-part-3-the-mutiny-of-the-middle-managers-how-employee-resistance-08e6fb781076
