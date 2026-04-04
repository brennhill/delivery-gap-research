# Images Needed

Tracks visual assets that should be created or revised for the manuscript. Each entry includes a detailed image-generation prompt.

Status values:

- `needed`: not created yet
- `in-progress`: being drafted
- `done`: created and ready
- `review`: created but needs review/redo in context

## Images Flagged for Review

- **C05-IMG-02** (`05.02-agent-cascade-sequence.png`) — review in chapter context
- **C06-IMG-02** (`06.02-output-vs-trace-grading.png`) — review in chapter context
- **C08-IMG-02** (`08.02-reliability-control-map.png`) — review in chapter context; arrow mapping is messy (controls don't connect 1:1 to their correct "prevents")
- **C08-IMG-03** (`08.03-human-smoke-trace-loop.png`) — review in chapter context
- **C09-IMG-01 + C09-IMG-02** — these two images are nearly identical (old pyramid vs pipeline, and pipeline funnel detail). Consider merging into one image or differentiating their purpose. Not urgent.
- **C09-IMG-04** (`09.04-fix-cost-by-layer.png`) — data not verified; the specific dollar ratios (1:200) need sourcing or should be labeled as illustrative, not factual
- **C10-IMG-01** (`10.01-legacy-migration-flow.png`) — review in chapter context
- **C15-IMG-01** (`15.01-career-moat-stack.png`) — review in chapter context; pyramid is inverted (widest at top) vs spec which asks for widest at bottom (foundation stack)
- **C15-IMG-04** (`15.04-anti-pattern-control-map.png`) — content needs revision; author uses a "Scale / Scope / Impact / Depth" framework that should be adapted for AI context and replace the current anti-pattern list

Style guide: All images should use a clean, modern technical illustration style. White or light gray background. No gradients or 3D effects. Use a consistent color palette: dark navy for primary elements, teal/cyan for highlights, warm orange/amber for warnings or callouts, light gray for secondary elements. Sans-serif labels (Inter or similar). Minimal decoration — every visual element should convey information.

Aspect ratios and resolution:
- **Landscape diagrams** (timelines, flowcharts, comparisons): **3:2** — 2400x1600px
- **Vertical diagrams** (flowcharts, checklists): **2:3** — 1600x2400px
- **Tables/matrices:** **4:3** — 2400x1800px or **square** — 2000x2000px

Reference style: Flat vector infographic with icon-based illustrations, matching the era-timeline (C01-IMG-01). All prompts should produce images consistent with this baseline: clean flat fills, no gradients or 3D, icon-driven visuals, navy/teal/amber palette, no borders, sans-serif labels.

---

## Chapter 1: The End of the Headcount Era

1. Image ID: `C01-IMG-01`
   - Target file: `images/01.01-era-timeline.png`
   - Status: `done`
   - Description: Timeline showing the shift from headcount-era hiring through ZIRP contraction to the AI-augmented delivery model.
   - Prompt: Create a horizontal timeline infographic spanning 2015 to 2026. Three distinct phases separated by vertical dividers. Phase 1 (2015-2021) labeled "Headcount Era" in navy — show upward-trending icons of people/team growth, dollar signs, text "ZIRP funding, hire fast, grow teams." Phase 2 (2022-2023) labeled "Contraction" in amber/warning — show a sharp downward arrow, text "Rate hikes, layoffs, efficiency mandates." Phase 3 (2024-2026) labeled "AI-Augmented Delivery" in teal — show a smaller team icon with gear/AI symbols around it, text "Smaller teams, higher leverage, AI as infrastructure." Each phase should have 2-3 bullet annotations below. Clean white background, no 3D effects. Landscape orientation 2400x1400px.

2. Image ID: `C01-IMG-02`
   - Target file: `images/01.02-artisan-builder-inspector.png`
   - Status: `done`
   - Description: Comparison diagram showing artisan mindset vs builder mindset with the inspector bridge between them.
   - Prompt: Style: flat vector infographic, icon-based, navy/teal/amber palette, no borders, sans-serif labels — match the era-timeline reference. Create a three-panel horizontal comparison diagram. Left panel labeled "Artisan" in warm amber — show a single person hand-crafting code, with attributes listed below: "Craft identity," "Manual mastery," "Resistance to automation," "Quality through personal touch." Right panel labeled "Builder" in teal — show a person operating a system/pipeline, attributes: "Systems thinking," "Leverage through tools," "Adaptation," "Quality through process." Center panel labeled "Inspector Bridge" in navy connecting both sides with arrows — show a magnifying glass over code, attributes: "Review skill," "Pattern recognition," "Trust through verification," "The craft that scales." White background, clean lines, no gradients. Landscape 2400x1400px.

---

## Chapter 2: The Junior Gap and the New Hiring Math

3. Image ID: `C02-IMG-01`
   - Target file: `images/02.01-30-day-reposition-timeline.png`
   - Status: `done`
   - Description: Four-week timeline of the 30-day reposition plan.
   - Prompt: Style: flat vector infographic, icon-based, navy/teal/amber palette, no borders, sans-serif labels — match the era-timeline reference. Create a horizontal four-step timeline infographic, each step representing one week. Week 1 (navy): icon of a document/spec, label "Document One Real Workflow," sub-text "Write a half-page spec before coding." Week 2 (teal): icon of three checkmarks/gates, label "Add Three Deterministic Gates," sub-text "Contract + Invariant + Policy check." Week 3 (teal): icon of a magnifying glass over a log/trace, label "Instrument One Trace," sub-text "Debug from evidence, not intuition." Week 4 (amber): icon of a published document/portfolio, label "Publish Evidence Brief," sub-text "One page: what changed, what improved." Connect weeks with forward arrows. Below the timeline, a small progress bar from "Guessing" to "Proving." Clean white background, landscape 2400x1400px.

4. Image ID: `C02-IMG-02`
   - Target file: `images/02.02-five-failure-modes-flowchart.png`
   - Status: `done`
   - Description: Diagnostic flowchart for five failure modes that kill junior growth.
   - Prompt: Style: flat vector infographic, icon-based, navy/teal/amber palette, no borders, sans-serif labels — match the era-timeline reference. Create a vertical flowchart with five branching diagnostic paths. Center column: five numbered failure modes in boxes — "1. Delegating without understanding," "2. Never reading generated code," "3. Trusting green checks blindly," "4. Re-prompting instead of debugging," "5. Not asking for architecture context." For each box, a right-branching arrow leads to a "Self-Check Question" in a lighter box (e.g., "Can you explain what the code does without AI?"), then another arrow to a "Fix Action" in a teal box (e.g., "Read every generation. Ask AI for architecture walkthrough."). Use red/amber highlight on the failure mode boxes, green/teal on the fix actions. Vertical orientation, 1400x2400px.

---

## Chapter 3: The Machine in the Ghost

5. Image ID: `C03-IMG-01`
   - Target file: `images/03.01-tokenization-example.png`
   - Status: `done`
   - Description: Tokenization example showing how the same word produces different tokens in different contexts.
   - Prompt: Style: flat vector infographic, icon-based, navy/teal/amber palette, no borders, sans-serif labels — match the era-timeline reference. Create an educational diagram showing tokenization. Top section: the sentence "The bank by the river" broken into colored token blocks — each token a different shade, with token IDs shown below (e.g., "The"→1234, " bank"→5678). Bottom section: the sentence "I went to the bank to deposit money" with the SAME word "bank" highlighted in a different color and different token ID, showing context changes tokenization. Middle annotation: "Same word, different context → different internal representation." Use a monospace font for the token text, colored rounded rectangles for each token block. Clean white background. Landscape 2400x1400px.

6. Image ID: `C03-IMG-02`
   - Target file: `images/03.02-attention-budget-diagram.png`
   - Status: `done`
   - Description: Diagram showing how attention budget distributes across a context window.
   - Prompt: Style: flat vector infographic, icon-based, navy/teal/amber palette, no borders, sans-serif labels — match the era-timeline reference. Create a horizontal bar diagram representing a context window (left = start, right = end). The bar is divided into segments labeled "System prompt," "Earlier messages," "Retrieved context," "Current message," "Model response." Above the bar, show a heat-map gradient: bright teal at the start (high attention), fading to light gray in the middle (low attention), then brightening again at the end (recency boost). Annotate with arrows: "Strong attention" at both ends, "Attention dilution zone" in the middle. Below, a callout: "Critical information at the start or end. Supporting detail in the middle." Clean white background, landscape 2400x1400px.

7. Image ID: `C03-IMG-03`
   - Target file: `images/03.03-hallucination-mechanics.png`
   - Status: `done`
   - Description: Three hallucination mechanics side by side.
   - Prompt: Style: flat vector infographic, icon-based, navy/teal/amber palette, no borders, sans-serif labels — match the era-timeline reference. Create a three-column comparison diagram. Column 1 labeled "Compression Limits (Interpolation)" in amber — show a simplified neural network with a gap, small icon of a person asking a question about a rare topic, output showing confident but wrong answer. Annotation: "Training data too sparse → model fills gap with plausible fiction." Column 2 labeled "Alignment Side Effects (Sycophancy)" in amber — show a thumbs-up icon influencing model output, annotation: "RLHF reward for helpfulness → model agrees rather than says 'I don't know.'" Column 3 labeled "Autoregressive Lock-In (Snowball)" in amber — show a chain of tokens where an early wrong token forces subsequent wrong tokens, annotation: "Once committed to a direction, each token reinforces the error." Below all three: shared callout in navy: "Hallucination is structural, not a bug to be patched." Landscape 2400x1400px.

8. Image ID: `C03-IMG-04`
   - Target file: `images/03.04-reasoning-models-comparison.png`
   - Status: `done`
   - Description: Comparison table of standard models vs reasoning models.
   - Prompt: Style: flat vector infographic, icon-based, navy/teal/amber palette, no borders, sans-serif labels — match the era-timeline reference. Create a clean comparison table with two columns and six rows. Header row: "Standard Models" (navy) vs "Reasoning Models" (teal). Rows: Latency (fast vs slower — internal chain of thought), Cost (lower vs higher — more tokens consumed), Failure Profile (confident wrong answers vs overthinking, refusal, verbose hedging), Best Use Cases (code generation, summarization, translation vs multi-step planning, constraint satisfaction, complex debugging), Chain-of-Thought (user must prompt for it vs built-in, often redundant to add), When to Use (default for most tasks vs high-stakes decisions, complex architecture). Use subtle row shading for readability. Clean white background, landscape 2400x1400px.

---

## Chapter 4: Prompt Engineering as System Architecture

9. Image ID: `C04-IMG-01`
   - Target file: `images/04.01-sandwich-pattern.png`
   - Status: `done`
   - Description: The sandwich pattern for prompt structure.
   - Prompt: Style: flat vector infographic, icon-based, navy/teal/amber palette, no borders, sans-serif labels — match the era-timeline reference. Create a vertical layered diagram resembling a sandwich or stack. Three horizontal layers with clear separation. Top layer (navy, bold): "Instructions Layer" — text "Role, constraints, output format, what NOT to do." Middle layer (light gray, largest): "Evidence / Context Layer" — text "Retrieved docs, code snippets, examples, conversation history." Bottom layer (teal, bold): "Specific Ask Layer" — text "The exact question or task, with success criteria." Arrows on the left side pointing to each layer with labels: "Frame the task," "Ground in reality," "Request the output." Annotation at bottom: "Instructions and ask get strong attention. Context in the middle gets compressed — put the most important context near the boundaries." Portrait orientation 1400x2000px.

10. Image ID: `C04-IMG-02`
    - Target file: `images/04.02-context-engineering-strategies.png`
    - Status: `done`
    - Description: Four context engineering strategies.
    - Prompt: Style: flat vector infographic, icon-based, navy/teal/amber palette, no borders, sans-serif labels — match the era-timeline reference. Create a 2x2 grid diagram with four quadrants. Top-left "Write" (navy): icon of a pen/keyboard, text "Structure the input — role, constraints, format, examples. You control what goes in." Top-right "Select" (teal): icon of a funnel/filter, text "Retrieve relevant context — RAG, code search, doc lookup. Pull in what matters." Bottom-left "Compress" (amber): icon of a compression arrow, text "Summarize prior context — conversation history, large docs. Keep signal, drop noise." Bottom-right "Isolate" (gray): icon of separate boxes, text "Separate concerns — use sub-agents, parallel prompts, scoped contexts. Prevent cross-contamination." Center label: "Context Engineering." Arrows from center to each quadrant. Clean white background, landscape 2400x1400px.

---

## Chapter 5: Agents and the Tool-Use Revolution

11. Image ID: `C05-IMG-01`
    - Target file: `images/05.01-agent-topology-diagram.png`
    - Status: `done`
    - Description: Agent topology decision diagram with four patterns.
    - Prompt: Style: flat vector infographic, icon-based, navy/teal/amber palette, no borders, sans-serif labels — match the era-timeline reference. Create a four-quadrant decision diagram for agent architectures. Each quadrant shows a different topology with a simple flow diagram. Top-left "Single-Shot" (simplest): one box (Model) → one arrow → Output. Annotation: "One call, one response. Lowest complexity, lowest cost. Use for: translation, summarization, simple generation." Top-right "Pipeline" (linear): three boxes chained left-to-right (Agent A → Agent B → Agent C → Output). Annotation: "Sequential steps. Each agent transforms output. Use for: multi-stage processing, refinement chains." Bottom-left "Router" (branching): one box (Router) with three arrows to three boxes (Specialist A, B, C), each → Output. Annotation: "Task classification then delegation. Use for: mixed-task workloads, cost optimization." Bottom-right "Supervisor" (hierarchical): one box (Supervisor) at top, arrows to multiple Worker boxes below, arrows back up. Annotation: "Orchestrator manages workers. Highest complexity. Use for: complex multi-step tasks, research." Add complexity arrow (low→high) along bottom. Add cost arrow (low→high) along right side. Landscape 2400x1400px.

12. Image ID: `C05-IMG-02`
    - Target file: `images/05.02-agent-cascade-sequence.png`
    - Status: `review`
    - Description: Sequence diagram showing an agent cascade failure.
    - Prompt: Style: flat vector infographic, icon-based, navy/teal/amber palette, no borders, sans-serif labels — match the era-timeline reference. Create a vertical sequence diagram (UML-style) with four swim lanes: "Agent A (Orchestrator)," "Agent B (Code Generator)," "Service C (API)," "Token Budget." Show a failure cascade: Agent A sends task to Agent B (solid arrow). Agent B calls Service C (solid arrow). Service C returns error (red dashed arrow). Agent B retries Service C (solid arrow, labeled "retry 1"). Service C returns timeout (red dashed arrow). Agent B retries again (solid arrow, labeled "retry 2"). Meanwhile, Token Budget bar on the right fills up progressively in amber/red. Agent B generates fallback response with hallucinated data (red box). Agent A treats it as truth and proceeds (red arrow forward). Final annotation at bottom in red: "No agent said 'I might be wrong.' The system moved confidently through bad assumptions." Clean white background, portrait 1400x2400px.

---

## Chapter 6: The Core Delivery Loop

13. Image ID: `C06-IMG-01`
    - Target file: `images/06.01-manufacturing-vs-slot-machine.png`
    - Status: `done`
    - Description: Split-panel contrasting disciplined workflow vs prompt roulette.
    - Prompt: Style: flat vector infographic, icon-based, navy/teal/amber palette, no borders, sans-serif labels — match the era-timeline reference. Create a split-panel illustration, divided vertically. Left panel labeled "Manufacturing Line" (teal/positive): show a clean horizontal assembly line with six labeled stations in order — "Spec," "Scaffold," "Tests," "Implement," "Review," "Eval." Each station is a simple rounded rectangle with an icon. A clean product exits the end labeled "Stable Release" with a green checkmark. The line is orderly, well-lit, methodical. Right panel labeled "Slot Machine" (amber/warning): show a slot machine with three spinning reels showing code symbols (curly braces, semicolons, angle brackets). A person pulls the lever labeled "Prompt." Coins labeled "tokens" go in. Output tray has mixed results: some labeled "works!" and some labeled "bugs" and "rework." Under the machine, a growing pile labeled "Technical Debt." Dividing line in the center. Landscape 2400x1400px.

14. Image ID: `C06-IMG-02`
    - Target file: `images/06.02-output-vs-trace-grading.png`
    - Status: `review`
    - Description: Two-layer evaluation model showing output grading vs trace grading.
    - Prompt: Style: flat vector infographic, icon-based, navy/teal/amber palette, no borders, sans-serif labels — match the era-timeline reference. Create a two-layer horizontal diagram. Top layer labeled "Output Grading" (navy): a box labeled "Final Result" with arrows pointing to three check boxes — "Correct?" "Complete?" "Safe?" Annotation: "Did it produce the right answer?" Bottom layer labeled "Trace Grading" (teal): a timeline/sequence showing intermediate steps (Step 1 → Step 2 → Step 3 → Step 4), with a magnifying glass icon examining the connections between steps. Annotation: "Did it get there the right way?" A vertical connector between the two layers with text: "Both must pass. Correct output via broken reasoning is a time bomb." Clean white background, landscape 2400x1400px.

15. Image ID: `C06-IMG-03`
    - Target file: `images/06.03-weekly-scorecard-dashboard.png`
    - Status: `done`
    - Description: Weekly scorecard dashboard with speed, quality, rework, and cost.
    - Prompt: Style: flat vector infographic, icon-based, navy/teal/amber palette, no borders, sans-serif labels — match the era-timeline reference. Create a compact dashboard mockup with four metric cards in a 2x2 grid. Top-left card "Lead Time" (navy): show a small sparkline trending downward (good), current value "3.2 days," previous "4.1 days," green arrow down. Top-right card "Defect Escape Rate" (navy): sparkline flat/slightly down, current "2.1%," previous "2.8%," green arrow down. Bottom-left card "Rework Ratio" (navy): sparkline with a recent spike highlighted in amber, current "18%," previous "12%," red arrow up with amber highlight. Bottom-right card "Cost per Accepted Change" (navy): sparkline trending down, current "$142," previous "$168," green arrow down. Below the grid: a single row labeled "This Week's Outlier: PR #412 — 3 review rounds, no spec" in amber. Below that: "Control Tweak: No PR >400 lines without linked spec." Clean, dashboard-style layout. Landscape 2400x1400px.

---

## Chapter 7: Deterministic Feedback

16. Image ID: `C07-IMG-01`
    - Target file: `images/07.01-anti-suck-eval-pyramid.png`
    - Status: `done`
    - Description: Clean pyramid with three layers of evaluation.
    - Prompt: Style: flat vector infographic, icon-based, navy/teal/amber palette, no borders, sans-serif labels — match the era-timeline reference. Create a pyramid diagram with three horizontal layers. Base layer (largest, navy): "Deterministic Checks (QA)" — icons of checkmarks, text "Contract evals, invariant evals, policy evals. Binary pass/fail. No judgment needed." Middle layer (medium, teal): "Trace Checks (Model Evals)" — icons of timeline/sequence, text "Did the reasoning path make sense? Were intermediate steps sound?" Top layer (smallest, amber): "Human Judgment" — icon of a person reviewing, text "Does this feel right? Contextual quality only humans can assess." Left side annotation with arrow pointing up: "Automation increases ↑" Right side annotation with arrow pointing down: "Human involvement increases ↓" Below pyramid: "Build from the bottom up. Without the base, the top layers are guessing." Landscape 2400x1400px.

17. Image ID: `C07-IMG-02`
    - Target file: `images/07.02-three-eval-loops.png`
    - Status: `done`
    - Description: Three-lane timeline showing PR checks, nightly evals, and release smoke tests.
    - Prompt: Style: flat vector infographic, icon-based, navy/teal/amber palette, no borders, sans-serif labels — match the era-timeline reference. Create a three-lane horizontal swim-lane diagram representing evaluation cadence. Top lane "PR Loop (Minutes)" (navy): show a fast cycle — code commit icon → three quick check icons (contract, invariant, policy) → green checkmark or red X. Label: "Every PR. Core gates. Must pass to merge." Middle lane "Nightly Loop (Hours)" (teal): show a broader cycle — clock icon → multiple test scenario icons (stress tests, regression, order permutations) → trend chart icon. Label: "Every night. Broader scenarios. Catches drift." Bottom lane "Release Smoke (Pre-deploy)" (amber): show a human icon → manual test steps → trace capture → sign-off. Label: "Before major releases. Human-visible verification. Catches 'technically correct but obviously wrong.'" Time arrow along the bottom from "Fast/Frequent" to "Deep/Rare." Landscape 2400x1400px.

18. Image ID: `C07-IMG-03`
    - Target file: `images/07.03-eval-failure-taxonomy-matrix.png`
    - Status: `done`
    - Description: Matrix table for failure classification.
    - Prompt: Style: flat vector infographic, icon-based, navy/teal/amber palette, no borders, sans-serif labels — match the era-timeline reference. Create a clean data table with four columns and five rows. Column headers (navy background, white text): "Failure Type," "Detector," "Owner," "Immediate Action." Row 1: "Contract violation" | "Deterministic assertion" | "Author + reviewer" | "Block merge, fix or update contract." Row 2: "Invariant breach" | "Stress/property test" | "Author + domain expert" | "Block merge, investigate business rule." Row 3: "Policy violation" | "Security/compliance scanner" | "Security team" | "Block merge, escalate if data exposed." Row 4: "Trace anomaly" | "Nightly eval loop" | "On-call + tech lead" | "Investigate reasoning path, add regression test." Row 5: "Human judgment flag" | "Release smoke test" | "PM + tech lead" | "Hold release, assess user impact." Alternating light gray/white row backgrounds. Clean table style, no heavy borders. Landscape 2400x1400px.

---

## Chapter 8: Trace-First Debugging

19. Image ID: `C08-IMG-01`
    - Target file: `images/08.01-trace-anatomy-request-timeline.png`
    - Status: `done`
    - Description: Timeline view of a traced request with spans for model call, tool call, retries, and failure point.
    - Prompt: Style: flat vector infographic, icon-based, navy/teal/amber palette, no borders, sans-serif labels — match the era-timeline reference. Create a horizontal waterfall/Gantt-style trace timeline (similar to Jaeger or Datadog trace views). Show a single request spanning left to right. Parent span at top: "POST /api/generate (total: 2.3s)." Nested child spans below, indented: Span 1 "Parse request" (thin, 12ms, navy). Span 2 "LLM call — Claude" (wide, 800ms, teal). Span 3 "Tool call — database query" (medium, 200ms, navy). Span 4 "LLM call — follow-up" (wide, 600ms, teal). Span 5 "Tool call — external API" (medium, highlighted in RED, 450ms, with a red X icon). Label: "TIMEOUT — first bad span." Span 6 "Retry — external API" (medium, amber, 250ms, with green checkmark). Below the timeline: annotation arrow pointing to the red span: "Start debugging here. First bad span = first clue." Clean white background, landscape 2400x1400px.

20. Image ID: `C08-IMG-02`
    - Target file: `images/08.02-reliability-control-map.png`
    - Status: `review`
    - Description: Control map showing five reliability controls and the failures they prevent.
    - Prompt: Style: flat vector infographic, icon-based, navy/teal/amber palette, no borders, sans-serif labels — match the era-timeline reference. Create a two-column mapping diagram. Left column "Control" (navy boxes): five stacked boxes labeled "Timeout Budget," "Bounded Retries (max 3)," "Idempotency Keys," "Permission Boundaries," "Human Approval Gate." Right column "Prevents" (amber boxes): corresponding boxes — "Runaway costs, hung requests," "Retry storms, cascade failures," "Duplicate side effects, double-charges," "Agent accessing unauthorized resources," "Irreversible actions without human review." Connecting arrows from each left box to its right box. Center annotation: "Five controls. Cover these and you prevent 80% of agent-related incidents." Clean white background, landscape 2400x1400px.

21. Image ID: `C08-IMG-03`
    - Target file: `images/08.03-human-smoke-trace-loop.png`
    - Status: `review`
    - Description: Closed-loop diagram linking manual smoke tests, trace capture, failure classification, and fixes.
    - Prompt: Style: flat vector infographic, icon-based, navy/teal/amber palette, no borders, sans-serif labels — match the era-timeline reference. Create a circular flow diagram with four nodes connected by arrows forming a loop. Node 1 (top, navy): "Human Smoke Test" — icon of person clicking through a flow, text "Run the feature manually. Does it feel right?" Node 2 (right, teal): "Trace Capture" — icon of a timeline/log, text "Every action generates a trace. Capture the full path." Node 3 (bottom, amber): "Failure Classification" — icon of a sorting/triage board, text "Contract? Invariant? Policy? Trace anomaly? Classify and route." Node 4 (left, navy): "Fix + Regression Test" — icon of a wrench + test tube, text "Fix the root cause. Add a test that catches this class." Arrow from Node 4 back to Node 1 labeled "Next release." Center of the loop: "No trace → no diagnosis. No classification → no learning." Landscape 2400x1400px.

---

## Chapter 9: The AI-Native Test Pyramid

22. Image ID: `C09-IMG-01`
    - Target file: `images/09.01-ai-native-test-pyramid.png`
    - Status: `review`
    - Description: Old test pyramid vs AI-native test pipeline comparison.
    - Prompt: Style: flat vector infographic, icon-based, navy/teal/amber palette, no borders, sans-serif labels — match the era-timeline reference. Create a side-by-side comparison. Left side "Old Pyramid" (faded/gray): traditional test pyramid — wide base "Unit Tests," middle "Integration Tests," narrow top "E2E Tests." A red X over it. Right side "AI-Native Pipeline" (teal/navy, vivid): a vertical funnel or pipeline with layers from top to bottom — "Spec (human)" → "Bounded Diffs (<400 lines)" → "Static Analysis + Security Scan" → "Contract + Invariant Tests" → "Multi-Agent Review" → "Human Review" → "Canary Deploy" → "Production Monitoring." Each layer slightly narrower, showing filtering. Annotation: "The shape changed because the volume changed. You need more layers when 3x the code is hitting the pipeline." Landscape 2400x1400px.

23. Image ID: `C09-IMG-02`
    - Target file: `images/09.02-pipeline-layers-funnel.png`
    - Status: `review`
    - Description: The 7-step pipeline showing each layer catching what previous layers miss.
    - Prompt: Style: flat vector infographic, icon-based, navy/teal/amber palette, no borders, sans-serif labels — match the era-timeline reference. Create a vertical funnel diagram with seven horizontal bars, widest at top, narrowest at bottom. Each bar is labeled and colored. Bar 1 (navy): "Spec + Bounded Diffs" — annotation "Catches: scope creep, mega-PRs." Bar 2 (teal): "Static Analysis" — "Catches: lint errors, type mismatches." Bar 3 (teal): "Security Scan" — "Catches: known vulnerability patterns, secret exposure." Bar 4 (teal): "Contract + Invariant Tests" — "Catches: API drift, business rule violations." Bar 5 (amber): "Multi-Agent Review" — "Catches: cross-cutting concerns, architecture violations, bugs across files." Bar 6 (amber): "Human Review" — "Catches: intent mismatch, domain errors, 'technically correct but wrong.'" Bar 7 (navy, bold): "Canary + Monitoring" — "Catches: production-only failures, performance regression." Left side: arrow labeled "Volume in" (wide). Right side at bottom: arrow labeled "Trusted changes out" (narrow). Portrait 1600x2400px, 2:3.

24. Image ID: `C09-IMG-03`
    - Target file: `images/09.03-multi-agent-review-flow.png`
    - Status: `done`
    - Description: Multi-agent review with independent specialists.
    - Prompt: Style: flat vector infographic, icon-based, navy/teal/amber palette, no borders, sans-serif labels — match the era-timeline reference. Create a flow diagram showing a code diff entering a review stage. Center: a box labeled "PR Diff" with arrows fanning out to three parallel agent boxes — "Security Reviewer Agent" (checks for vulnerabilities, injection, secrets), "Architecture Reviewer Agent" (checks for pattern violations, naming, duplication), "Test Coverage Reviewer Agent" (checks for missing tests, weak assertions). Each agent box outputs findings into a shared "Review Summary" box. The summary feeds into a "Human Reviewer" box for final decision (Approve / Request Changes). Annotation: "Independent specialists find different failure classes. No single reviewer catches everything." Landscape 2400x1400px.

25. Image ID: `C09-IMG-04`
    - Target file: `images/09.04-fix-cost-by-layer.png`
    - Status: `review`
    - Description: Exponential cost growth from spec to production.
    - Prompt: Style: flat vector infographic, icon-based, navy/teal/amber palette, no borders, sans-serif labels — match the era-timeline reference. Create a bar chart with six bars increasing exponentially in height from left to right. X-axis labels: "Spec," "Scaffold," "Tests," "Code Review," "Staging," "Production." Y-axis: "Cost to Fix" (abstract units). Bar heights approximately: 1, 2, 5, 15, 50, 200. Colors: first three bars in teal (cheap), fourth in amber (moderate), last two in red (expensive). Annotation arrow from the tallest bar back to the shortest: "A $1 spec fix prevents a $200 production incident." Below: "Every layer you skip pushes the cost curve right." Clean, minimal chart style. Landscape 2400x1400px.

---

## Chapter 10: Real Systems — Legacy and Security

26. Image ID: `C10-IMG-01`
    - Target file: `images/10.01-legacy-migration-flow.png`
    - Status: `review`
    - Description: Legacy migration flow with stabilize-first strategy.
    - Prompt: Style: flat vector infographic, icon-based, navy/teal/amber palette, no borders, sans-serif labels — match the era-timeline reference. Create a horizontal flow diagram with six sequential steps connected by arrows. Step 1 "Risk Map" (navy): icon of a danger-zone map, text "Identify high-risk areas. Mark boundaries." Step 2 "Seam/Interface" (navy): icon of a dotted line between two blocks, text "Find or create a stable interface at the boundary." Step 3 "Characterization Tests" (teal): icon of a test tube with a lock, text "Write tests that capture current behavior. No changes yet." Step 4 "Dual-Path Run" (teal): icon of two parallel arrows, text "Old code and new code run side by side. Compare outputs." Step 5 "Divergence Check" (amber): icon of a diff/comparison, text "Where do outputs differ? Investigate each divergence." Step 6 "Flagged Cutover / Rollback" (navy): icon of a feature flag switch, text "Cut over behind a flag. Rollback if divergence exceeds threshold." Below the flow: "Stabilize first, accelerate second. Never rewrite — migrate." Landscape 2400x1400px.

27. Image ID: `C10-IMG-02`
    - Target file: `images/10.02-ai-dev-threat-surface-map.png`
    - Status: `done`
    - Description: Threat surface map across AI development workflow.
    - Prompt: Style: flat vector infographic, icon-based, navy/teal/amber palette, no borders, sans-serif labels — match the era-timeline reference. Create a horizontal flow diagram showing the AI-assisted development pipeline with trust boundaries marked. Five stages left to right: "Prompt Input" → "Context Assembly (RAG/retrieval)" → "Model Processing" → "Tool Invocation (APIs, DB, filesystem)" → "Side Effects (deploy, email, data write)." Between each stage, draw a vertical dashed red line labeled "Trust Boundary." Above each boundary, show threat icons: "Prompt Injection" (between input and context), "Data Poisoning" (between context and model), "Hallucination as Action" (between model and tools), "Unauthorized Side Effects" (between tools and effects). Below the flow: four boxes for the four default threat classes: "Prompt injection," "Data exfiltration," "Privilege escalation," "Supply chain compromise." Landscape 2400x1400px.

28. Image ID: `C10-IMG-03`
    - Target file: `images/10.03-delivery-loop-security-controls.png`
    - Status: `done`
    - Description: Delivery loop with embedded security controls at each step.
    - Prompt: Style: flat vector infographic, icon-based, navy/teal/amber palette, no borders, sans-serif labels — match the era-timeline reference. Create a horizontal pipeline diagram with six stages of the delivery loop: "Spec," "Scaffold," "Tests," "Implement," "Review," "Eval." Below each stage, show an embedded security control in a small amber box: Spec → "Threat model review, non-goals include security boundaries." Scaffold → "Dependency audit, no new packages without review." Tests → "Policy evals: injection, auth, secret detection." Implement → "Least-privilege tool access, scoped permissions." Review → "Security-focused LLM review pass, SAST scan." Eval → "Canary deploy with security monitoring, rollback trigger." Between the main pipeline and the controls, show small lock icons. Annotation: "Security lives inside the loop, not after it." Landscape 2400x1400px.

29. Image ID: `C10-IMG-04`
    - Target file: `images/10.04-attack-chain-breakpoints.png`
    - Status: `done`
    - Description: Attack chain from untrusted content to exfiltration with control breakpoints.
    - Prompt: Style: flat vector infographic, icon-based, navy/teal/amber palette, no borders, sans-serif labels — match the era-timeline reference. Create a horizontal attack chain diagram with six stages connected by arrows, showing an attack progressing left to right. Stage 1 "Untrusted Input" (red): "User submits prompt containing hidden instruction." Stage 2 "Context Assembly" (red→amber): "Malicious instruction mixed into retrieved context." BREAKPOINT 1 (green shield): "Input sanitization + context boundary markers." Stage 3 "Model Processing" (amber): "Model follows injected instruction." BREAKPOINT 2 (green shield): "Output filtering + instruction hierarchy." Stage 4 "Tool Call" (amber→red): "Model requests file read or API call with exfiltrated data." BREAKPOINT 3 (green shield): "Permission boundaries + allow-list." Stage 5 "Side Effect" (red): "Data sent to external endpoint." BREAKPOINT 4 (green shield): "Egress filtering + approval gate." Stage 6 "Exfiltration" (dark red): "Attacker receives sensitive data." Show the breakpoints as green vertical barriers that can stop the chain. Annotation: "Defense in depth: any single breakpoint stops the attack." Landscape 2400x1400px.

---

## Chapter 11: Cost, ROI, and Weekly Metrics

30. Image ID: `C11-IMG-01`
    - Target file: `images/11.01-weekly-roi-scorecard.png`
    - Status: `done`
    - Description: Compact weekly ROI dashboard.
    - Prompt: Style: flat vector infographic, icon-based, navy/teal/amber palette, no borders, sans-serif labels — match the era-timeline reference. Create a dashboard mockup showing a weekly ROI scorecard. Four horizontal metric rows, each with: metric name, current value, trend arrow, and a small 8-week sparkline. Row 1: "Cost per Accepted Change — $142 (↓12% vs baseline)" with downward-trending sparkline in green. Row 2: "Lead Time (commit→prod) — 3.2 days (↓22%)" with downward sparkline in green. Row 3: "Defect Escape Rate — 2.1% (↓25%)" with downward sparkline in green. Row 4: "Rework Ratio — 18% (↑50%)" with UPWARD sparkline in red/amber, highlighted as the outlier. Below the metrics: a section labeled "Outlier Autopsy" with text "PR #412: 3 review rounds, no linked spec. Root cause: skipped Step 0." And "This Week's Control Tweak: No PR >400 lines without linked spec." Clean dashboard style with subtle grid lines. Landscape 2400x1400px.

31. Image ID: `C11-IMG-02`
    - Target file: `images/11.02-cost-control-loop.png`
    - Status: `done`
    - Description: Architecture loop for cost governance.
    - Prompt: Style: flat vector infographic, icon-based, navy/teal/amber palette, no borders, sans-serif labels — match the era-timeline reference. Create a circular flow diagram with four major nodes and connecting arrows. Node 1 "Routing Ladder" (navy): "Route by task risk — reasoning model for high-risk, fast model for low-risk, cache for repeated queries." Node 2 "Caching Layer" (teal): "Cache repeated queries, embeddings, and common completions. Check cache before calling model." Node 3 "Budget Guards" (amber): "Per-team daily caps, per-request token limits, alert thresholds at 80% budget." Node 4 "Fallback Policy" (navy): "When budget exhausted or model unavailable — smaller model, cached response, or queue for next day." Arrows connect in a loop: Routing → Model Call → Budget Check → Fallback if needed → back to Routing. Center label: "Cost is a system design problem, not a spending problem." Landscape 2400x1400px.

32. Image ID: `C11-IMG-03`
    - Target file: `images/11.03-rough-math-scorecard-proxy.png`
    - Status: `done`
    - Description: Shadow Data Strategy for bypassing data fragmentation.
    - Prompt: Style: flat vector infographic, icon-based, navy/teal/amber palette, no borders, sans-serif labels — match the era-timeline reference. Create a diagram showing three data silos and how to bypass them. Three tall boxes on the left representing silos: "Finance (API Bill)" in red/locked, "HR (Salary Data)" in red/locked, "Git (PR Volume)" in green/unlocked. Arrows from each silo point to a central "Shadow Scorecard" spreadsheet mockup. The Finance arrow is dashed with label "Proxy: $50/dev/month industry average." The HR arrow is dashed with label "Proxy: $180k/yr fully burdened average." The Git arrow is solid with label "Direct: PRs merged to main." The spreadsheet shows simple calculations: "Cost per Accepted Change ≈ (salary + API) / PRs merged." Below: "Directionally correct beats perfectly precise six months late." Landscape 2400x1400px.

---

## Chapter 12: The Engineering Manager's Survival Guide

33. Image ID: `C12-IMG-01`
    - Target file: `images/12.01-policy-control-evidence-matrix.png`
    - Status: `done`
    - Description: Matrix linking policy clauses to controls, evidence, and ownership.
    - Prompt: Style: flat vector infographic, icon-based, navy/teal/amber palette, no borders, sans-serif labels — match the era-timeline reference. Create a four-column table diagram. Column headers: "Policy" (navy), "Control" (teal), "Evidence Artifact" (amber), "Owner" (navy). Four example rows: Row 1: "No AI-generated code in production without review" | "Two-pass review gate in CI" | "PR review log with reviewer names + timestamps" | "Tech Lead." Row 2: "Sensitive data never in AI prompts" | "Pre-send PII scanner" | "Scanner pass/fail log per request" | "Security." Row 3: "Model changes require eval pass" | "Eval suite runs on model swap" | "Eval results diff report" | "Platform team." Row 4: "All agent actions logged immutably" | "Append-only audit log" | "Log integrity hash chain" | "Platform team." Clean table with alternating row shading. Annotation: "Policy without a control is a wish. Control without evidence is theater." Landscape 2400x1400px.

34. Image ID: `C12-IMG-02`
    - Target file: `images/12.02-three-lane-governance-model.png`
    - Status: `done`
    - Description: Three-lane governance view with shared evidence spine.
    - Prompt: Style: flat vector infographic, icon-based, navy/teal/amber palette, no borders, sans-serif labels — match the era-timeline reference. Create a three-lane horizontal swim-lane diagram with a shared vertical spine. Three lanes stacked vertically: Top lane "Security Lane" (amber): concerns listed — "Threat model coverage, vulnerability scan results, incident response readiness." Middle lane "Compliance Lane" (navy): "Audit trail completeness, regulatory mapping, data handling documentation." Bottom lane "Leadership Lane" (teal): "Adoption velocity, ROI scorecard, risk appetite alignment." Vertical spine down the center labeled "Shared Evidence Spine" connecting all three lanes — "Same data, different views. One evidence pack serves all three audiences." Each lane has an arrow pointing to the spine. Landscape 2400x1400px.

35. Image ID: `C12-IMG-03`
    - Target file: `images/12.03-buy-in-306090-roadmap.png`
    - Status: `done`
    - Description: 30/60/90 adoption roadmap with stop/go gates.
    - Prompt: Style: flat vector infographic, icon-based, navy/teal/amber palette, no borders, sans-serif labels — match the era-timeline reference. Create a horizontal three-phase roadmap. Phase 1 "Days 1-30: Baseline + Pilot" (navy): bullet points "Pick one team, one deliverable. Baseline metrics. Run the loop." Diamond decision gate at end labeled "Stop/Go: Did the pilot produce measurable improvement?" Phase 2 "Days 31-60: Evidence + Expansion" (teal): "Publish scorecard. Draft internal case study. Identify cross-team friction." Diamond gate: "Stop/Go: Can you show before/after data to your VP?" Phase 3 "Days 61-90: Scale + Playbook" (amber): "Expand to 2-3 teams. Create self-serve adoption playbook. Governance for shared boundaries." Diamond gate: "Stop/Go: Are three teams showing consistent improvement?" Below the roadmap: "Each gate is binary. If the answer is no, fix the blocker before expanding. Premature scaling kills adoption." Landscape 2400x1400px.

36. Image ID: `C12-IMG-04`
    - Target file: `images/12.04-adoption-distribution-curve.png`
    - Status: `done`
    - Description: Adoption curve showing four developer archetypes.
    - Prompt: Style: flat vector infographic, icon-based, navy/teal/amber palette, no borders, sans-serif labels — match the era-timeline reference. Create a bell-curve distribution diagram divided into four colored segments. From left to right: Segment 1 "Eager Adopters" (~20%, teal): "Already using AI. Want fewer guardrails. Risk: reckless velocity." Segment 2 "Cautious Majority" (~40%, navy): "Willing but uncertain. Need evidence and safety. Your largest opportunity." Segment 3 "Skeptics" (~25%, gray): "Technically capable, philosophically resistant. Need data, not enthusiasm." Segment 4 "Quietly Terrified" (~15%, amber): "Not speaking up. Scared of obsolescence. Need psychological safety first." Below the curve: four management strategies, one per segment: "Channel energy into pilot leadership," "Provide structured onboarding + scorecard evidence," "Give them the data and the opt-in," "1:1 conversation + identity reframe." Landscape 2400x1400px.

37. Image ID: `C12-IMG-05`
    - Target file: `images/12.05-leveling-expectations-grid.png`
    - Status: `done`
    - Description: Leveling expectations grid showing what "good" means at each level.
    - Prompt: Style: flat vector infographic, icon-based, navy/teal/amber palette, no borders, sans-serif labels — match the era-timeline reference. Create a four-row table/grid showing AI-era leveling expectations. Column headers: "Level," "Generation," "Verification," "System Impact." Row 1 "Junior" (light teal): "Uses AI for scaffolding and first drafts" | "Reads generated code, asks questions about what it does" | "Follows the loop with guidance." Row 2 "Mid" (teal): "Generates confidently with appropriate model selection" | "Catches contract violations in review, writes meaningful tests" | "Runs the loop independently on bounded tasks." Row 3 "Senior" (navy): "Designs prompts and routing for team patterns" | "Reviews AI-generated code at architectural level, builds eval patterns" | "Improves the loop for the team, reduces coordination overhead." Row 4 "Staff+" (dark navy): "Architects delivery systems that make AI safe at scale" | "Designs cross-team verification infrastructure, failure taxonomy" | "Makes the loop reliable across teams and organizational boundaries." Left side annotation: "The commodity layer ↓ (generation) gets cheaper. The scarce layer ↑ (verification + system impact) gets more valuable." Landscape 2400x1400px.

38. Image ID: `C12-IMG-06`
    - Target file: `images/12.06-coordination-overhead-vs-ai-gains.png`
    - Status: `done`
    - Description: Chart showing coordination overhead eating AI gains in larger teams.
    - Prompt: Style: flat vector infographic, icon-based, navy/teal/amber palette, no borders, sans-serif labels — match the era-timeline reference. Create a dual-axis chart. X-axis: "Team Size" (2, 3, 4, 5, 6, 8, 10, 15). Left Y-axis: "Output per Person" (bar chart, teal). Right Y-axis: "Coordination Cost" (line chart, amber). The bars show output per person peaking at team size 3-5 then declining. The line shows coordination cost rising slowly until size 5, then accelerating sharply. A vertical dashed line at team size 5 labeled "Optimal zone (3-5)." Shaded green zone from 3-5, shaded red zone beyond 8. Annotation: "AI gains are real but coordination overhead eats them in larger teams. Revenue-per-employee data from AI-native companies confirms: Cursor ($3-5M/head), Midjourney ($3M/head). SaaS baseline: $300K/head." Landscape 2400x1400px.

---

## Chapter 13: Sustainable Pace and the Burnout Trap

39. Image ID: `C13-IMG-01`
    - Target file: `images/13.01-work-intensification-cycle.png`
    - Status: `done`
    - Description: The AI work intensification cycle.
    - Prompt: Style: flat vector infographic, icon-based, navy/teal/amber palette, no borders, sans-serif labels — match the era-timeline reference. Create a circular flow diagram showing a self-reinforcing negative cycle. Five nodes connected in a clockwise loop: Node 1 "AI Acceleration" (teal, initially positive): "Tasks complete faster. Output rises." → Node 2 "Raised Expectations" (amber): "Manager/stakeholders expect higher throughput as the new baseline." → Node 3 "Scope Expansion" (amber): "More tasks assigned. 'You have capacity now.'" → Node 4 "Cognitive Overload" (red): "Supervising more AI workflows. Decision fatigue. Error rate rises." → Node 5 "Total Load Increase" (red): "Working harder than before AI, not less. Rest erodes." → Arrow back to Node 1, but now Node 1 is relabeled "More AI to compensate" (red). Center of the loop: skull/warning icon with text "The burnout spiral: AI makes you faster, so you get more work, so you need more AI, so you get more work..." Landscape 2400x1400px.

---

## Chapter 14: Hiring, Team Shape, and the Org Chart

40. Image ID: `C14-IMG-01`
    - Target file: `images/14.01-interview-signals-old-vs-new.png`
    - Status: `done`
    - Description: Interview format comparison showing old vs new high-signal dimensions.
    - Prompt: Style: flat vector infographic, icon-based, navy/teal/amber palette, no borders, sans-serif labels — match the era-timeline reference. Create a two-column comparison table. Left column "Old Signals" (faded gray, with strikethrough or X marks): "Algorithm whiteboard (LeetCode)," "Memorized API knowledge," "Speed of typing/implementation," "Years of experience with specific framework," "Solo coding challenge." Right column "New High-Signal Dimensions" (teal, with checkmarks): "AI-assisted code review (catch the bug the AI missed)," "Spec writing from ambiguous requirements," "System design under AI constraints," "Live debugging from a trace," "Explain tradeoffs to a non-technical stakeholder." Below: three highlighted "Highest-Signal" boxes — "Technical + Product Depth," "Systems Thinking," "AI Fluency." Annotation: "Don't add rounds — replace your lowest-signal ones." Landscape 2400x1400px.

41. Image ID: `C14-IMG-02`
    - Target file: `images/14.02-vendor-evaluation-matrix.png`
    - Status: `done`
    - Description: Vendor evaluation scoring matrix template.
    - Prompt: Style: flat vector infographic, icon-based, navy/teal/amber palette, no borders, sans-serif labels — match the era-timeline reference. Create a scoring matrix table with columns: "Criterion," "Weight (H/M/L)," "Vendor A Score (1-5)," "Vendor B Score (1-5)," "Notes." Ten rows for criteria: "1. Task coverage" (H), "2. Model flexibility" (M), "3. Audit trail / provenance" (H), "4. Integration depth" (M), "5. Security posture" (H), "6. Cost model transparency" (H), "7. Offline capability" (L), "8. Switching cost" (M), "9. Price stability" (M), "10. Exit strategy" (M). Leave score cells empty (template). Bottom row: "Weighted Total." Below the table: "Score 1-5 per criterion. Weight: H=3x, M=2x, L=1x. Three criteria most teams miss: #3 (audit trail), #6 (cost model), #10 (exit strategy)." Clean table with subtle shading. Landscape 2400x1400px.

---

## Chapter 15: Your Durable Moat

42. Image ID: `C15-IMG-01`
    - Target file: `images/15.01-career-moat-stack.png`
    - Status: `review`
    - Description: Layered stack of four durable skills.
    - Prompt: Style: flat vector infographic, icon-based, navy/teal/amber palette, no borders, sans-serif labels — match the era-timeline reference. Create a vertical stack diagram with four layers, each wider than the one above (like an inverted pyramid or foundation stack). Bottom layer (widest, navy): "System Design Judgment" — "Architecture decisions that hold under load. Where to put boundaries, what to leave out." Second layer (teal): "Reliability & Debugging Depth" — "Finding root cause from traces, not guesses. Building systems that fail safely." Third layer (teal): "Domain Compression" — "Knowing what NOT to build. Turning vague requirements into tight specs." Top layer (amber, narrowest): "Cross-Functional Translation" — "Explaining technical constraints to PMs, business value to engineers." Left side: vertical arrow labeled "AI can't replace ↑" Right side: vertical arrow labeled "Value compounds over time ↑" Below the stack: "The commodity layer (code generation) gets cheaper every quarter. These four moats get more valuable." Portrait orientation 1400x2000px.

43. Image ID: `C15-IMG-02`
    - Target file: `images/15.02-90-day-transition-blueprint.png` (note: mapped from chapter reference `15.02` — originally tracked as `15.04`)
    - Status: `done`
    - Description: 90-day transition blueprint with three phases.
    - Prompt: Style: flat vector infographic, icon-based, navy/teal/amber palette, no borders, sans-serif labels — match the era-timeline reference. Create a horizontal three-phase timeline. Phase 1 "Month 1: Baseline" (navy): "Score yourself on four moats. Run 30-day reposition plan. Establish personal scorecard." Gate icon at boundary. Phase 2 "Month 2: Pilot" (teal): "Apply delivery loop to real work. Build first portfolio artifact. Get peer calibration on moat scores." Gate icon. Phase 3 "Month 3: Hardening" (amber): "Deepen lowest-scoring moat. Publish evidence brief. Present to manager or in 1:1." Below the timeline: a decision diamond: "Day 90: Are your moat scores higher? Is your portfolio growing? → Yes: Continue compounding. → No: Revisit which moat you're practicing and whether the practice is deliberate." Landscape 2400x1400px.

44. Image ID: `C15-IMG-03`
    - Target file: `images/15.03-portfolio-evidence-packet.png`
    - Status: `done`
    - Description: Five-part portfolio evidence packet.
    - Prompt: Style: flat vector infographic, icon-based, navy/teal/amber palette, no borders, sans-serif labels — match the era-timeline reference. Create a document layout showing five sections of a portfolio evidence packet, arranged as overlapping document pages or cards. Card 1 "Impact" (navy): "What shipped, who it affected, measurable outcome." Card 2 "Judgment" (teal): "A decision you made and why — what you chose NOT to build." Card 3 "Reliability" (teal): "A production issue you debugged from traces. Root cause and fix." Card 4 "Enablement" (amber): "A pattern, tool, or process you built that helped the team." Card 5 "Eval Maturity" (navy): "Tests or evals you wrote that caught real failures." Below: "One artifact per card. Verifiable, not self-reported. This packet works for performance reviews, interviews, and promotion cases." Landscape 2400x1400px.

45. Image ID: `C15-IMG-04`
    - Target file: `images/15.04-anti-pattern-control-map.png`
    - Status: `review`
    - Description: Anti-pattern matrix with remediation controls.
    - Prompt: Style: flat vector infographic, icon-based, navy/teal/amber palette, no borders, sans-serif labels — match the era-timeline reference. Create a two-column mapping diagram. Left column "Anti-Pattern" (red/amber boxes): "Resume-padding (quantity over quality)," "Vague claims ('improved performance')," "Solo hero narratives," "Only showing successes," "Stale portfolio (>6 months old)." Right column "Control / Fix" (teal/green boxes): "One artifact with measurable outcome beats ten bullet points," "Specific numbers: 'reduced p95 latency from 800ms to 200ms,'" "Show team enablement: 'built pattern used by 4 engineers,'" "Include a failure you caught or a post-mortem you ran," "Quarterly refresh: add one new artifact, retire one stale one." Connecting arrows between each pair. Landscape 2400x1400px.

---

## Chapter 16: The Staff+ Engineer

46. Image ID: `C16-IMG-01`
    - Target file: `images/16.01-staff-archetypes-before-after.png`
    - Status: `done`
    - Description: Staff+ archetypes showing how each role shifts.
    - Prompt: Style: flat vector infographic, icon-based, navy/teal/amber palette, no borders, sans-serif labels — match the era-timeline reference. Create a four-row before/after comparison. Each row represents a Staff+ archetype. Column headers: "Archetype," "Before AI (Value Source)," "After AI (The Delta)." Row 1 "Tech Lead": "Scoped tasks, guided execution through codebase knowledge" → "Builds verification infrastructure — CI gates, eval patterns, review rubrics that keep 3x volume trustworthy." Row 2 "Architect": "Deep domain knowledge, steered technical direction" → "Designs testable boundaries (contract checks) between teams. Interface integrity at AI speed." Row 3 "Solver": "Fixed deeply broken things through heroic debugging" → "Traces failures through taxonomy, installs systemic guardrails. Immunizes the system against failure classes." Row 4 "Right Hand": "Executive proxy, cross-org coordination" → "Agentic strategy — designs multi-agent architectures, defines human approval gates, shapes org-level AI policy." Use arrows between before and after columns. Landscape 2400x1400px.

47. Image ID: `C16-IMG-02`
    - Target file: `images/16.02-replit-failure-trace.png`
    - Status: `done`
    - Description: Replit incident traced through failure taxonomy.
    - Prompt: Style: flat vector infographic, icon-based, navy/teal/amber palette, no borders, sans-serif labels — match the era-timeline reference. Create a horizontal flow diagram showing six failure classes identified in the Replit incident, arranged as a chain. Each node is a rounded rectangle. Node 1 "Spec Gap" (red): "No constraint prohibiting destructive DDL during freeze." Node 2 "Review Gap" (red): "No human approval for destructive actions." Node 3 "Eval Gap" (red): "No policy eval blocking DROP on production." Node 4 "Observability Gap" (red): "Agent fabricated records and falsified logs." Node 5 "Integration Gap" (red): "Unrestricted database access, no env isolation." Node 6 "Rollout Gap" (red): "No dev/prod separation." Below each node, a green box showing the missing control: "Forbidden ops per environment" → "Human gate for write/delete on prod" → "Policy eval: DDL requires approval token" → "Immutable audit log agents can't write to" → "Least-privilege, scoped write access" → "Environment isolation with promotion gates." Landscape 2400x1400px.

48. Image ID: `C16-IMG-03`
    - Target file: `images/16.03-architectural-boundary-delta.png`
    - Status: `done`
    - Description: The Staff+ Delta at the boundary between teams.
    - Prompt: Style: flat vector infographic, icon-based, navy/teal/amber palette, no borders, sans-serif labels — match the era-timeline reference. Create a diagram showing two team zones with a boundary between them. Left zone "Team A" (navy): icon of an AI agent generating code, label "Agent generates implementation." Right zone "Team B" (teal): icon of a developer writing code, label "Developer builds their component." Between the zones: a bold vertical boundary line with a shield icon. Label above boundary: "The Staff+ Delta." Three elements at the boundary: "Contract Check" (test icon) — "API schema matches spec," "Invariant Test" (lock icon) — "Business rules hold across boundary," "ADR" (document icon) — "Why this boundary exists, documented." Below: "The Architect's value is the boundary design, not the implementation within it. Without explicit, tested contracts at team boundaries, AI speed creates AI chaos." Landscape 2400x1400px.

---

## Chapter 17: The Product Manager's AI Playbook

49. Image ID: `C17-IMG-01`
    - Target file: `images/17.01-pm-in-delivery-loop.png`
    - Status: `done`
    - Description: PM's position in the delivery loop showing highest leverage at spec and eval.
    - Prompt: Style: flat vector infographic, icon-based, navy/teal/amber palette, no borders, sans-serif labels — match the era-timeline reference. Create a horizontal pipeline showing the six delivery loop steps: "Spec," "Scaffold," "Tests," "Implement," "Review," "Eval." Above the pipeline, show the PM's involvement level as a heat bar — bright teal at "Spec" (highest leverage), fading through "Scaffold" and "Tests" (lower involvement), very faint at "Implement," slightly brighter at "Review," bright teal again at "Eval" (high leverage). Label the two peak points: Spec → "You own the source of truth. Define 'done' before tokens fly." Eval → "You are the final judgment layer. Technically correct ≠ right for the user." Below the pipeline: "PM leverage is highest at the boundaries: defining intent (spec) and verifying intent was preserved (eval)." Landscape 2400x1400px.

50. Image ID: `C17-IMG-02`
    - Target file: `images/17.02-pm-moat-framework.png`
    - Status: `done`
    - Description: PM moat framework with four PM-specific moats.
    - Prompt: Style: flat vector infographic, icon-based, navy/teal/amber palette, no borders, sans-serif labels — match the era-timeline reference. Create a four-quadrant diagram for PM career moats. Top-left "Product Judgment" (navy): "Knowing what to build and what not to build. Scoping under uncertainty. Kill decisions." Top-right "Quality Intuition" (teal): "Detecting 'technically correct but wrong for the user.' The gap between demo and product." Bottom-left "Domain Compression" (teal): "Turning vague stakeholder needs into tight specs. Non-goals as a superpower." Bottom-right "Cross-Functional Translation" (amber): "Speaking engineer, speaking executive, speaking customer — in one meeting." Center: "PM Moat Framework." Below: "AI handles research, drafting, and analysis. These four skills determine whether the AI output matters." Landscape 2400x1400px.

51. Image ID: `C17-IMG-03`
    - Target file: `images/17.03-ship-or-wait-decision-tree.png`
    - Status: `done`
    - Description: Ship-or-wait decision tree for probabilistic features.
    - Prompt: Style: flat vector infographic, icon-based, navy/teal/amber palette, no borders, sans-serif labels — match the era-timeline reference. Create a vertical decision tree flowchart. Start node at top: "Should we ship this AI-powered feature?" Five sequential decision diamonds, each with Yes (right/down) and No (left, leading to "Fix this first" box) paths. Diamond 1: "Is the quality bar defined and measurable?" Diamond 2: "Does a fallback exist when AI output is wrong?" Diamond 3: "Can we monitor quality in production automatically?" Diamond 4: "Do we have a kill switch and rollback plan?" Diamond 5: "Do we understand what breaks if this feature succeeds?" If all five are Yes → green box: "Ship it. Monitor the five signals." Each "No" path leads to an amber box with the specific fix: "Define pass/fail criteria," "Build fallback path," "Add quality sampling + alerts," "Implement feature flag + rollback trigger," "Map second-order effects and set intervention thresholds." Portrait orientation 1400x2400px.

---

## Chapter 18 (Appendix A): State of the Art

52. Image ID: `C19-IMG-01`
    - Target file: `images/19.01-state-of-the-art-map.png`
    - Status: `done`
    - Description: State-of-the-art map linking provider updates to engineering implications.
    - Prompt: Style: flat vector infographic, icon-based, navy/teal/amber palette, no borders, sans-serif labels — match the era-timeline reference. Create a structured reference diagram with three columns. Left column "Provider Updates" (navy): list of model/tool releases grouped by provider — OpenAI (GPT-5.3-Codex), Anthropic (Claude Opus 4.6, Sonnet 4.6), Google (Gemini 3.1), Open-Source (Llama 4, Mistral, DeepSeek-R1). Middle column "Capability Shifts" (teal): arrows from each provider to capability changes — "Stronger agentic coding," "Lower-cost high-quality routing," "Improved reasoning," "Self-hosted options for sovereignty." Right column "Engineering Implications" (amber): arrows from capabilities to decisions — "Update routing policies," "Re-run eval suite before switching," "Adjust cost models," "Validate security posture." Bottom: "Five interpretation rules: 1. Separate claim from constraint. 2. Check benchmark methodology. 3. Validate against your tasks. 4. Prefer primary docs. 5. Re-run your own evals." Landscape 2400x1400px.

---

## Branding

53. Image ID: `TITLE-REBRAND-01`
    - Chapter/section: `Cover and all internal diagrams`
    - Target file: N/A (affects multiple assets)
    - Status: `needed`
    - Description: Title rebranding verification. Confirm all cover art, internal diagrams, and marketing assets use "AI-Augmented Development" (not "AI-Augmented Development"). Markdown alt text has been cleared — this task covers visual assets only.
    - Prompt: Style: flat vector infographic, icon-based, navy/teal/amber palette, no borders, sans-serif labels — match the era-timeline reference. N/A — this is a verification task, not an image generation task. Review all visual assets for title consistency.
