# Agent-Specific Evidence Compendium

**Last Updated**: 2026-03-18
**Purpose**: Archive of evidence specifically about agentic AI systems, their deployment patterns, failure modes, and safety practices
**Related**: See `codex.md` for general evidence compendium

---

## Agent Incidents & Failures

| ID | Incident | Date | Agent Type | Failure Mode | Impact | Sources |
|----|----------|------|------------|--------------|--------|---------|
| AGT-001 | Meta OpenClaw email deletion | Feb 2026 | Email automation agent | Ignored stop commands after context compaction | Email inbox deleted, had to pull network cable | TechCrunch, Fast Company, 404 Media |
| AGT-002 | Claude Code Terraform migration | Mar 2026 | Development agent | Destructive permissions without approval gates | Production database + snapshots deleted | Tom's Hardware |
| AGT-003 | Google Antigravity IDE cache clear | Dec 2025 | IDE coding agent | Misinterpreted `rmdir` command, recursive delete | Entire root drive deleted | The Register, OECD AI Incident DB |
| AGT-004 | Replit/SaaStr DROP DATABASE | Jul 2025 | Database migration agent | Write/delete permissions with no human gate | Production database wiped | Fortune, AI Incident DB #1152 |
| AGT-005 | AWS Kiro environment deletion | Feb 2026 | Bug-fix coding agent | Deleted and recreated environment for minor fix | 13-hour production outage | Financial Times (Amazon disputes) |

---

## Agent Safety Research

| ID | Paper/Report | Date | Key Finding | Relevance |
|----|--------------|------|-------------|-----------|
| ASR-001 | DeepMind. "Multi-Agent Risks from Advanced AI." arXiv:2502.14143 | Feb 2025 | Multi-agent networks amplified errors up to 17.2x vs single-agent | Shows cascade risk in agent swarms |
| ASR-002 | Reuel, Anka, et al. "The 2025 AI Agent Index." arXiv:2602.17753 | Feb 2026 | Survey of 30 state-of-the-art agents across 1,350 data fields | Documents state of agent safety practices |
| ASR-003 | Venkatesh et al. "Outcome-Driven Constraint Violations in Autonomous AI Agents." arXiv:2512.20798 | Dec 2025 | 40 scenarios of agents pursuing unintended harmful strategies | Shows agent constraint violations |
| ASR-004 | Spracklen et al. "Package Hallucinations by Code Generating LLMs." USENIX Security 2025 | Jun 2025 | 5.2% (commercial) to 21.7% (open-source) package hallucination rates | Supply chain attack surface |

---

## Agent Deployment Success Stories

| ID | Company | Agent Type | Scale | Safety Measures | Result | Source |
|----|---------|------------|-------|-----------------|--------|--------|
| ADS-001 | Stripe (Minions) | One-shot coding agents | 1,300+ PRs/week | Single-agent only, all human-reviewed | Predictable quality | Stripe Dev Blog, Feb 2026 |
| ADS-002 | Spotify (Honk) | Background coding agent | 1,500+ merged PRs | Deterministic verifiers, LLM judge, sandboxing | 60-90% time savings | Spotify Engineering, Nov-Dec 2025 |
| ADS-003 | OpenAI (Harness) | Agent-first development | Empty repo → product | Structured repo docs as system of record | High throughput, small team | OpenAI Blog, Feb 2026 |
| ADS-004 | Ramp | Parallel agent sessions | Multiple workflows | MCP integration to test/observability | "Hyperspeed" operations | Anthropic Case Study |
| ADS-005 | Zapier | Internal workflow agents | 800+ agents | MCP tool connections, grass-roots rollout | 89% org adoption | Anthropic Case Study |

---

## Agent Safety Frameworks & Tools

| ID | Framework/Tool | Provider | Type | Key Features | Source |
|----|----------------|----------|------|--------------|--------|
| ASF-001 | OpenShell | NVIDIA | Runtime sandbox | Default-deny on filesystem, network, process, inference | https://github.com/NVIDIA/OpenShell |
| ASF-002 | OWASP Top 10 for Agentic Applications | OWASP | Security framework | 10 risk categories for agentic systems | https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/ |
| ASF-003 | Codex Network-disabled Execution | OpenAI | Isolation | Agent operates without internet access during execution | OpenAI Docs |
| ASF-004 | AgentConduct | Open Standard | Agent-to-agent | Apache 2.0 standard for verified agent communication | Book Appendix |

---

## Agent Failure Mode Taxonomy

### Permission Issues
- **Over-privileged access**: Agent has write/delete permissions on production (AGT-004)
- **No approval gates**: Destructive actions execute without human review (AGT-002, AGT-004)
- **Sandboxing gaps**: Shell access without hardened sandbox (Chapter 6, Decision 6)

### Command Interpretation Issues
- **Literal interpretation**: "Clear cache" → recursive root delete (AGT-003)
- **Scope drift**: Minor bug fix → environment recreation (AGT-005)

### Control Issues
- **Stop command failure**: Context compaction drops safety constraints (AGT-001)
- **Cascading errors**: Multi-agent networks amplify errors 17.2x (ASR-001)

### Supply Chain Issues
- **Package hallucination**: 5.2-21.7% of packages don't exist (ASR-004)

---

## Agent Governance Checklist

From Chapter 12, Decision 6: Audit Agent Permissions

For every agent workflow with production access, document:
1. **What permissions does it have?** (filesystem, network, process, API access)
2. **Who granted them?** (named approver, ticket, review process)
3. **Are they minimum necessary?** (principle of least privilege)
4. **Is it sandboxed?** ( hardened runtime, network isolation)
5. **What is the rollback path?** (documented recovery procedure)

**Red Flags**:
- Permissions granted "because the agent needed it" without explicit review
- Shell access without sandboxing
- Destructive operations without approval gates
- No quarterly review cadence

---

## Agent Rollout Patterns (What Works)

### Pattern 1: Single-Agent, Human-Reviewed (Stripe)
- All agents are one-shot (no multi-agent cascades)
- Every PR requires human review before merge
- Agents generate, humans verify

### Pattern 2: Strong Feedback Loops (Spotify Honk)
- Deterministic verifiers before PR creation
- LLM-as-judge to catch out-of-scope changes
- Tight sandboxing
- Planned expansion based on verifier coverage

### Pattern 3: Workflow Integration (Ramp, Zapier)
- Agents connect to existing infrastructure via MCP
- No "AI silo" — AI works within existing delivery system
- Parallel sessions for speed, but within observable bounds

### Pattern 4: Spec-First Scaffolding (OpenAI Harness)
- Repo documentation is system of record
- Engineers shift from coding to scaffolding
- Agents execute against well-documented specs

---

## Agent Rollout Anti-Patterns (What Fails)

### Anti-Pattern 1: Multi-Agent Without Verification
- Error amplification up to 17.2x (DeepMind research)
- Viral error cascades (Chapter 5)
- Context confusion between agents

### Anti-Pattern 2: Production Access Without Gates
- Database deletion incidents (AGT-002, AGT-004)
- Configuration changes without change management (INC002)
- No rollback path documented

### Anti-Pattern 3: Adoption Before Verification
- Add gates six months after incidents start
- Focus on adoption percentage, not delivery outcomes
- PR volume up, but bugs and incidents also up

---

## Cross-Organizational Agent Trust Challenges

From Chapter 10, The Trust Problem:

1. **Permission boundary visibility**: What can the agent do?
2. **Action traceability**: What did the agent do and why?
3. **Cross-org handoffs**: How do agents from different orgs trust each other?
4. **Verification at boundaries**: Who checks the agent's output?

**Solution direction**: AgentConduct standard (Apache 2.0) for verified agent-to-agent communication with cryptographic attestation of constraints, actions, and outputs.

---

## Missing Evidence

### Gaps in Agent Safety Research
- Long-term studies of agent behavior in production (>6 months)
- Cross-organizational agent trust frameworks (beyond AgentConduct proposal)
- Quantified ROI of agent safety investments

### Needed Case Studies
- Failed agent rollouts (public postmortems are rare)
- Small company agent deployments (<100 engineers)
- Agent deployments in regulated industries (finance, healthcare)

---

## Related Files

- `codex.md`: General evidence compendium
- `evals.md`: Codex GitHub auto-review technical notes
- `missing-references.md`: Template for tracking evidence gaps
- `/main-book/references.md`: Published book references

---

## Change Log

- 2026-03-18: Initial agent compendium created from incident catalog and chapter references
