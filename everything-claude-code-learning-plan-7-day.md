# Everything Claude Code: 7-Day Fast-Track (For Active Builders)

Audience: developers already shipping daily who want fast, practical adoption.

Rule: use this on real work, not toy prompts.

## Day 1: Install Only the Core

1. Install common rules + your language rules.
2. Enable only essential commands:
   - `/plan`
   - `/tdd`
   - `/code-review`
   - `/verify`
   - `/eval`
3. Enable minimal tooling:
   - 3-5 plugins
   - <= 10 MCP servers
4. Set default model policy:
   - Sonnet default
   - Opus only for hard architecture/security

Deliverable:
1. One checklist in your notes: "minimum stack I actually run."

## Day 2: Force the Core Loop

Take one real feature and run:

1. `/plan`
2. `/tdd`
3. `/code-review`
4. `/verify full`

Log:
1. What failed first
2. What caught it
3. What rework was required

Deliverable:
1. One short postmortem: "where my old flow leaked."

## Day 3: Add Basic Evals

Pick one feature path and define 4 checks:

1. 2 capability evals
2. 2 regression evals

Run:
1. `/eval define <feature>`
2. `/eval check <feature>`
3. `/eval report <feature>`

Deliverable:
1. Eval file + first report with real pass/fail.

## Day 4: Context and Token Discipline

1. Disable unused MCPs/plugins for this project.
2. Add compaction rhythm:
   - compact at logical phase boundaries only
3. Run same task under:
   - old setup
   - tightened setup

Compare:
1. Time
2. Rework
3. Cost/token behavior

Deliverable:
1. Personal context policy ("what stays on/off by default").

## Day 5: Reuse What You Learned

Extract 2 patterns from this week:

1. `/learn-eval`
2. Save as reusable skills

Each pattern must include:
1. Problem trigger
2. Working fix
3. When to apply

Deliverable:
1. Two learned skills in your learned skills folder.

## Day 6: Controlled Orchestration

Use one medium task:

1. `/orchestrate feature "..."`
2. `/verify full`
3. `/eval check <feature>`

Then compare to your manual loop:
1. Better?
2. Same?
3. Worse?

Deliverable:
1. One decision note: "when orchestration is worth it."

## Day 7: Lock the Operating System

Finalize your personal standard:

1. Default command sequence
2. Required pre-merge checks
3. Escalation rules (when to use Opus, when to add human review)
4. Weekly metrics:
   - lead time
   - rework
   - defect escape
   - reviewer minutes per accepted change

Deliverable:
1. One-page "my AI delivery SOP."

## Fast-Track Success Criteria

By end of day 7, you should have:

1. One real feature shipped through the full loop.
2. One eval report with meaningful pass/fail.
3. At least two reusable learned skills.
4. A stable minimal setup (not tool sprawl).
5. A written SOP you will actually follow.

## If You Have No Human Reviewers

Use this fallback stack on every meaningful change:

1. `/code-review`
2. `/verify full`
3. `/eval check`
4. Manual 10-minute pre-merge smoke pass

No reviewer is not an excuse for no review.
