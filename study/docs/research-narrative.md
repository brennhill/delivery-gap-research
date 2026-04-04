# Research Narrative: How We Found What Actually Predicts Software Quality

**Date:** 2026-03-24/25
**Context:** 30-repo empirical study for "The Delivery Gap" book
**Format:** Chronological evolution of hypothesis → data → correction → new hypothesis

---

## Act 1: "Specs reduce rework" (the simple hypothesis)

**Starting assumption:** PRs with linked specs (issues, tickets) should have lower rework rates than PRs without specs. The Verification Triangle predicts that spec quality → better eval → less waste.

**What the data showed:** Across 10 repos, spec'd PRs rework MORE than unspec'd (13-16% vs 9.6%). The opposite of what we expected.

**First reaction:** This must be a complexity confound — harder tasks get specs AND get reworked more.

**Correction (human):** "Are we even scoring spec QUALITY?" We checked — the heuristic scorer gave every spec 44-45/100. Zero differentiation. We were treating a one-line Jira ticket the same as a detailed design doc.

**Pivot:** Built an LLM-based quality scorer with 7 dimensions. Scores now range 5-95. Real variation exists.

---

## Act 2: "Better specs reduce rework" (the refined hypothesis)

**What the data showed (n=472):** Quality gradient is flat or slightly inverted. HIGH quality specs rework at 16.1%, LOW at 13.3%. All tiers rework more than no-spec (9.6%).

**Six competing hypotheses emerged:**
- (a) Specs are useless
- (b) Specs create review friction (give reviewers something to reject against)
- (c) Specs raise the bar (catch problems that would have escaped)
- (d) Specs raise human save rate
- (e) "Yolo spec" — AI writes spec, human doesn't read it
- (f) "Wrong thing, well-specified" — clear spec for the wrong problem

**Key correction (human):** "You should try to DISPROVE the thesis, not prove it."

---

## Act 3: "Rework vs escape" (reframing what matters)

**The breakthrough:** Instead of asking "does spec quality reduce rework?" we asked "does spec quality shift WHERE defects are caught?"

**Rework = caught during review (before merge) = good.**
**Escape = missed entirely (after merge) = bad.**

**What the data showed (n=10,660):**
- Spec'd PRs: +0.9pp more rework, **-1.2pp fewer escapes**
- Specs shift defects from post-merge to pre-merge
- 17 of 29 repos show "shifted earlier" or "helps both"

**The thesis is supported, but not the way we expected.** Specs don't reduce rework — they increase it. But they reduce escapes. The rework IS the system working.

---

## Act 4: "Alignment failures" (a new failure mode)

**Discovery:** File overlap analysis between original PR and follow-up fix revealed two rework types:
- **Implementation fix** (≥50% file overlap): Built the right thing wrong
- **Alignment failure** (<50% file overlap): Built the wrong thing entirely

**What the data showed:**
- AI-tier repos: 63% alignment failures
- Traditional repos: 28% alignment failures
- Alignment failures have BETTER spec quality (+7pp) than implementation fixes

**The "wrong thing, well-specified" pattern is real.** AI writes a clear, detailed spec for the wrong thing. The spec is internally excellent but externally wrong.

**Key insight (human):** "There are humans who just won't write this stuff." The spec is the output — the conversation that produced it is where thinking happens.

---

## Act 5: "Detecting human engagement" (what actually matters)

**Approach:** Build both regex-based features (cheap, deterministic) and LLM-based formality scoring (nuanced, per-PR).

**What we expected to be human signals:**
- Organizational context (references to teams, deadlines, incidents)
- Reasoning quality (causal chains, tradeoffs, negation depth)
- Test plans and risk mentions

**What the data actually showed:**

| Feature | AI-tagged | Human | We expected |
|---------|-----------|-------|-------------|
| Risk mentions | 0.82 | 0.24 | Human signal → WRONG, AI is performatively careful |
| Test plans | 0.74 | 0.17 | Human signal → WRONG, AI fills template sections |
| Domain grounding | 1.48 | 0.66 | Human signal → WRONG, AI lists file paths from diff |
| Org context | 0.82 | 0.46 | Human signal → WRONG, regex matches code identifiers |
| **Typos** | 0.004 | 0.016 | ??? → **5x human signal** |
| **Questions** | 0.004 | 0.014 | ??? → **4x human signal** |
| **Casual language** | 0.004 | 0.005 | ??? → **1.5x human signal** |

**Key correction (human):** "These risk mentions are performative. Is it just template filler?" Yes — AI "test plans" are section headers; AI "risk mentions" are PR template checkboxes.

**Key correction (human):** "Where is the AI getting organizational context?" Checked the actual matching lines — our regex was matching `Compliance` the Ruby module as "compliance" the legal requirement. The AI wasn't faking org context; our patterns were wrong.

---

## Act 6: "Casual language is the best predictor" (the unexpected finding)

**The exploratory scan (51 features × 10,660 PRs):**

**Golden signal:** `casual` (kinda, btw, WIP, nope, IIRC)
- +12.3pp MORE rework
- -2.9pp FEWER escapes
- The person writing casually catches problems before they ship

**Other human signals that predict good outcomes:**
- `fp_experience` (first-person narrative): -7.1pp rework, -4.0pp escape
- `typos`: -5.8pp rework, -3.1pp escape
- `questions`: -4.5pp rework, -2.9pp escape

**Danger signals (false confidence):**
- `negations` (out of scope): -2.5pp rework but +1.8pp MORE escapes
- `domain_grounding` (file paths, service names): -1.3pp rework but +0.9pp more escapes

**Key insight (human):** "But casual language IS engagement." Yes. The person who writes "kinda" isn't performing. They're just talking. They're not writing a spec — they're explaining something to another human. That IS engagement. The formal signals (negation depth, causal chains, tradeoffs) are things AI can mimic. Typos, casual language, questions are things AI won't do.

---

## Act 7: "The spec is residue" (the reframe)

**Key insight (human):** "If we could examine the chats, we'd probably see more data."

The casual spec is the residue of thinking that already happened — in the person's head, in Slack, in the AI chat. The thinking was done before the PR was opened. The spec is just a note to the reviewer.

The polished AI spec is the opposite — the artifact looks thorough but no conversation preceded it. The "thinking" was generated, not lived.

**Proxy signals for pre-PR conversation (added to feature set):**
- Time PR was open (created → merged)
- Time to first human review
- Number of unique human reviewers
- Author self-reviews (responding to feedback = engaged)
- Bot review count

**What this means for the book:** The Verification Triangle measures whether the infrastructure EXISTS. But the real question is whether humans USE it. Engagement isn't "wrote a thorough spec." Engagement is "a human was actually here, thinking, and didn't bother to polish it."

---

## What Still Needs Testing

1. Do the pre-PR conversation proxy signals (time open, reviewer count) correlate with outcomes?
2. Does the formality scorer (LLM-based) predict escape rates within size buckets?
3. Can we access prompt history / chat logs for any repos?
4. Does the "mixed" classification (half-engaged) consistently produce the worst outcomes?
5. At what PR size does engagement start mattering? (Preliminary: medium PRs)

---

## Meta-Observation

This research narrative itself demonstrates the thesis. Every significant finding came from the human correcting the AI:
- "Are we even scoring quality?" → rebuilt scorer
- "Try to disprove it" → falsification framework
- "Where is the AI getting org context?" → found regex matching code identifiers
- "These plans are performative" → discovered AI is 3x more "responsible" than humans
- "Humans misspell" → strongest discriminator
- "That IS engagement" → the key insight

The AI provided speed (test hypotheses in seconds), breadth (check all 10,660 PRs), and execution (compute 51 features instantly). The human provided skepticism, domain knowledge, and redirection. Neither alone would have reached these findings.
