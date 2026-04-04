# Everything Claude Code: Solo Learning Plan

This plan distills the repo into a practical sequence for one developer learning by doing.

Goal: pick a minimal toolset, use it on real tasks, and build basic eval discipline.

## What to Learn (and in what order)

1. Core workflow: `plan -> tdd -> code-review -> verify`
2. Basic evals: define, run, report, iterate
3. Context discipline: MCP/plugin minimization, compaction, model choice
4. Reuse loop: extract patterns into skills (`learn` / `learn-eval`)
5. Scaling pattern: orchestrate multi-agent flow only after basics work

## Minimal Starter Stack (Do Not Install Everything)

1. Install one language ruleset + common rules only.
2. Start with these commands: `/plan`, `/tdd`, `/code-review`, `/verify`, `/eval`.
3. Enable only 3-5 plugins and <= 10 MCP servers.
4. Default model to Sonnet; escalate to Opus only for hard reasoning/security work.
5. Use one practice project that is real enough to break.

## 30-Day Sequence

## Week 1: Foundation and Habits

Objective: stop ad-hoc prompting and run a repeatable delivery loop.

1. Read in order:
   - `README.md` quick start + key concepts
   - `the-shortform-guide.md`
   - `rules/README.md`
2. Install:
   - common rules + your language rules
   - 2 hooks max (`format/typecheck`, `console.log warning`)
3. Run 3 small tasks through:
   - `/plan`
   - `/tdd`
   - `/code-review`
   - `/verify`
4. Track for each task:
   - what failed first
   - what catch mechanism found it (test/review/verify)
   - what you had to redo

Deliverable by end of week:
1. One-page personal workflow note with your exact command order.
2. One short list of "never skip" checks.

## Week 2: Basic Evals (Anti-Suck Layer)

Objective: define evals explicitly instead of relying on "looks good."

1. Read:
   - `commands/eval.md`
   - `commands/learn-eval.md`
   - `the-longform-guide.md` section "Verification Loops and Evals"
2. Pick one feature and create:
   - 2 capability evals
   - 2 regression evals
3. Run:
   - `/eval define <feature>`
   - `/eval check <feature>`
   - `/eval report <feature>`
4. Improve until:
   - capability checks are stable
   - regression checks are deterministic

Deliverable by end of week:
1. One eval definition file.
2. One eval report with pass/fail history and notes.

## Week 3: Context and Cost Control

Objective: improve quality per token, not just output speed.

1. Read:
   - `the-longform-guide.md` sections:
     - context/memory management
     - token optimization
     - parallelization
2. Apply:
   - disable unused MCPs for the project
   - test one compacting rhythm (`/compact` at logical breakpoints)
   - set model defaults and escalation rules
3. Do the same task twice:
   - baseline (your current way)
   - optimized context/tool setup
4. Compare:
   - time to completion
   - rework required
   - token/cost behavior

Deliverable by end of week:
1. Personal "tool enablement policy" (what stays enabled by default).
2. Model routing cheat sheet (when Haiku/Sonnet/Opus).

## Week 4: Reuse and Scale

Objective: stop re-solving the same problems every session.

1. Read:
   - `commands/learn.md`
   - `commands/learn-eval.md`
   - `commands/orchestrate.md`
2. Extract 3 learned patterns into reusable skills.
3. Run one medium feature with:
   - `/orchestrate feature...`
   - then `/verify full`
4. Compare orchestration vs your normal sequential loop.

Deliverable by end of week:
1. Three reusable learned skills.
2. One orchestration report and one "was this worth it?" note.

## What "Good" Looks Like by Day 30

1. You have a stable command sequence you actually follow.
2. You can define and run basic evals without hand-waving.
3. You keep tool/context scope tight instead of enabling everything.
4. You can show 2-3 concrete examples where eval/review caught real issues.
5. You have at least 3 reusable patterns saved from your own sessions.

## Solo Review Model (If You Do Not Have Human Reviewers)

You still need review; you just cannot pretend "no reviewer" means "no risk."

Use this stack:
1. AI reviewer pass: `/code-review`
2. Deterministic verification: `/verify`
3. Eval pass for capability + regression: `/eval check`
4. Weekly manual audit of one merged change: "what slipped and why?"

If all four are skipped, confidence is fake.

## Weekly Reflection Prompts

1. What did the loop catch that your intuition missed?
2. Which checks are noisy and need tightening?
3. Which step consumed most time with least value?
4. What should be turned into a reusable skill now?

## Recommended Reading Order in the Repo

1. `README.md`
2. `the-shortform-guide.md`
3. `rules/README.md`
4. `commands/plan.md`
5. `commands/tdd.md`
6. `commands/code-review.md`
7. `commands/verify.md`
8. `commands/eval.md`
9. `commands/learn-eval.md`
10. `the-longform-guide.md`
11. `commands/orchestrate.md`

## Keep It Practical

Do not "study the system" for weeks before shipping anything.

Run the loop on real work immediately, then tighten based on evidence.
