# Human Engagement Signals in Spec Text

**Date:** 2026-03-24
**Status:** Feature design, preliminary validation against AI-tagged ground truth

## Problem

LLM-scored spec quality (completeness, error states, acceptance criteria) does NOT predict rework outcomes. All quality tiers rework MORE than no-spec. The missing variable may be **human engagement** — did someone actually think about this spec, or is it an AI-generated artifact?

## Ground Truth

We have 1,126 AI-tagged PRs (identified by "Generated with Claude Code", "🤖", "CURSOR_AGENT", "coderabbit.ai" markers) and 8,691 non-tagged PRs across 35 repos. This gives us a validation set for feature development.

## Discovered Signals

### Strong signals (validated against AI-tagged ground truth)

| Signal | AI-tagged | Non-tagged | Ratio | Notes |
|--------|-----------|------------|-------|-------|
| **Typos/misspellings** | 0.4% | 2% | 5x | Strongest signal. Robots don't misspell. |
| **Casual language** (kinda, nope, WIP, btw, IIRC, fwiw) | 1% | 2% | 2x | Humans use informal shorthand |
| **@mentions of people** | 14% | 20% | 1.4x | Humans reference other humans. AI doesn't know who to tag. |

### Promising but needs refinement

| Signal | AI-tagged | Non-tagged | Ratio | Notes |
|--------|-----------|------------|-------|-------|
| **First person "I"** | 14% | 9% | 0.6x (inverted!) | AI mimics "I" but the content differs. Human: "I ran into", "I noticed". AI: "I updated", "I implemented". Need to distinguish narrating experience vs describing action. |

### Untested (to compute statistically)

**Humanness features:**
- Sentence length variance (burstiness) — humans write uneven lengths, AI is uniform
- Type-token ratio (vocabulary diversity) — humans use unusual words, slang, abbreviations
- Average word length — AI uses "correct" longer words
- Perplexity — AI text is "too predictable" when scored by same model family
- Substance-to-length ratio — AI specs are 3x longer (2,791 chars vs 930) but score the same on quality

**Thinking features:**
- Negative scope ("not doing X", "out of scope", "won't fix") — requires deliberate boundary-setting
- Open questions ("should we also...?", "?") — acknowledges uncertainty
- References to other PRs/issues (#number in body, not just title)
- Before/after or expected/actual descriptions — structured diagnostic thinking
- Alternatives considered ("chose X because Y", "option A vs B")
- Risk/concern language ("might break", "regression", "careful")
- Test plan specifics ("tested by running...", "verified that...")
- History/context ("we tried X before", "this broke last week", "per discussion")

**Structural features:**
- Has explicit test plan
- Body length vs number of substantive claims (padding detection)
- Changelog-style ("Updated X", "Added Y", "Removed Z") vs narrative-style

## Observed Patterns

### AI-generated spec characteristics
- 3x longer than human specs (2,791 chars vs 930 avg)
- Template-heavy ("This PR introduces...", "Key changes include...")
- No typos, no casual language
- Describes WHAT changed in third person
- Sometimes mimics thinking ("the root cause is...") but without personal experience narrative
- Self-tags: "Generated with Claude Code", "🤖", "CURSOR_AGENT"
- Bot author names: robobun, copilot-swe-agent, devin-ai-integration, denobot

### Human-engaged spec characteristics
- Shorter, denser
- Contains typos and casual abbreviations
- First person experience narrative ("I ran into this when...", "After debugging, I found...")
- References people (@mentions, "per Jane's suggestion")
- Acknowledges uncertainty ("I'm not sure if...", "should we also...?")
- Negative scope ("not doing X in this PR")
- Real-world context ("this broke in prod", "per Slack discussion")

### The "robobun problem"
Some AI PRs score high on "thinking" heuristics because they describe root cause analysis and causal chains. Example: Bun's robobun writes specs with detailed technical reasoning that LOOKS like human analysis but is tagged "🤖 Generated with Claude Code". The engagement signal needs to distinguish between AI mimicking reasoning and humans actually reasoning.

## Prior Research

- **Burstiness** — human writing has uneven sentence length distribution. AI is uniform.
- **Perplexity** — AI-generated text has lower perplexity when scored by same model family.
- **Vocabulary diversity** — humans use more unusual word choices.
- **Entropy patterns** — AI text has smoother token-level entropy.
- AIDev paper (A070): Agent PRs show higher description-to-diff semantic alignment (CodeBERT: 0.9356 vs 0.9285). Agents are better at describing what they did — but this doesn't mean the description reflects human thinking.

## The Prompt History Hypothesis

**Key insight from session:** The spec is the OUTPUT. The conversation that produced the spec is where the thinking happens. Two identical-looking specs could have wildly different origins:

1. Human thinks deeply, writes spec → good engagement
2. Human tells AI "write spec for X", accepts first draft → zero engagement, looks identical
3. Human and AI go 15 rounds, human pushes back and refines → high engagement, looks identical

The spec text cannot distinguish case 2 from case 3. The prompt history (conversation with the AI) could. But we can't access it from GitHub.

**Proxy signals we CAN measure:**
- Multiple commits before first review → author iterated
- Time between issue creation and PR creation → longer = more thinking
- PR body edited after creation (GitHub tracks this, we don't fetch it yet)
- Presence of CLAUDE.md / AGENTS.md / .cursorrules in the repo → investment in AI guidance
- AIDev paper finding: teams iterate on agent config files 20+ times (A066)

**Implication for the book:** The Verification Triangle may need a fourth dimension or qualifier: not just spec quality, but spec *provenance* — was this spec the product of thinking, or the product of delegation?

## Meta-Observation

This session itself demonstrates the thesis. See `meta-observation.md` for the full analysis. The full conversation transcript is at the session JSONL path in SESSION-STATE.md.

## Next Step

Compute ALL features (humanness + thinking + structural + statistical) on every cached spec. No LLM calls needed — pure text analysis. Then correlate each feature with rework% and escape% by quartile. Whatever separates high-escape from low-escape specs is what actually predicts outcomes. No hypothesis needed — let the data decide.
