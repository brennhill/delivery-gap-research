"""Spec quality scoring — completeness, ambiguity, testability, consistency.

Two entry points: file mode (single spec file) and repo mode (SpecClassification list).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tools.spec_signals.models import SpecClassification

# --- Vague terms (from SPEC.md, full list) ---

VAGUE_TERMS = [
    "appropriate",
    "appropriately",
    "fast",
    "fast enough",
    "user-friendly",
    "properly",
    "correctly",
    "reasonable",
    "as needed",
    "as appropriate",
    "etc.",
    "and so on",
    "handle errors",
    "handle gracefully",
    "should work",
    "simple",
    "easy",
    "intuitive",
    "flexible",
    "robust",
    "scalable",
    "secure",
    "efficient",
    "performant",
    "clean",
    "modular",
    "maintainable",
    "good",
    "better",
    "best practice",
    "industry standard",
    "state of the art",
    "when possible",
    "if applicable",
    "as much as possible",
    "adequate",
    "sufficient",
    "normal",
    "typical",
    "usual",
    "seamless",
    "seamlessly",
    "real-time",
    "comprehensive",
    "modern",
    "lightweight",
    "minimize",
    "optimize",
    "transparent",
    "transparently",
    "elegant",
]

_vague_pattern = "|".join(re.escape(t) for t in sorted(VAGUE_TERMS, key=len, reverse=True))
VAGUE_RE = re.compile(rf"\b({_vague_pattern})\b", re.IGNORECASE)

# If the same line has a concrete measurement, the vague term is contextually precise — skip it
_PRECISE_LINE_RE = re.compile(
    r"\d+\s*(?:ms|s|sec|min|hour|hr|day|%|req|MB|GB|KB)\b|\bat\s+(?:most|least)\s+\d|\bunder\s+\d|\b(?:p95|p99|p50)\b",
    re.IGNORECASE,
)

# --- Format detection ---

EXPECTED_SECTIONS: dict[str, list[str]] = {
    "spec-kit": ["acceptance criteria", "edge cases", "key entities", "constraints"],
    "kiro": ["acceptance criteria", "constraints", "data model"],
    "openspec": ["acceptance criteria", "scope"],
    "delivery-gap": [
        "acceptance criteria",
        "constraints",
        "scope boundaries",
        "context anchors",
        "key entities",
        "error contract",
        "edge cases",
        "style rules",
    ],
    "ml-research": ["research direction", "success metric", "constraints"],
    "rfc": ["acceptance criteria", "constraints", "scope"],
    "freeform": ["acceptance criteria", "scope"],
}

# ML research optional sections — added to numerator/denominator only if detected
ML_RESEARCH_OPTIONAL_SECTIONS: list[str] = [
    "data specification",
    "techniques",
    "experimentation plan",
    "human-in-the-loop",
    "infrastructure",
    "monitoring",
    "cost",
    "integration points",
]

# --- Format detection patterns (pre-compiled) ---

_FR_RE = re.compile(r"\bFR-\d{3}\b")
_SC_RE = re.compile(r"\bSC-\d{3}\b")
_KIRO_RE = re.compile(r"\bTHE\s+SYSTEM\s+SHALL\b")
_OPENSPEC_RE = re.compile(r"(?:ADDED|MODIFIED)\s+Requirements")
_CONSTRAINTS_RE = re.compile(r"^##\s*(?:\d+\)\s*)?(?:Constraints|Non-negotiable)", re.MULTILINE | re.IGNORECASE)
_AC_SIGNAL_RE = re.compile(
    r"(?:^##\s*(?:\d+\)\s*)?Acceptance\s+criteria|Contract\s+check:|Invariant\s+check:|Policy\s+check:)",
    re.MULTILINE | re.IGNORECASE,
)
_MOTIVATION_RE = re.compile(r"^##\s*Motivation", re.MULTILINE)
_ALTERNATIVES_RE = re.compile(r"^##\s*Alternatives\s+Considered", re.MULTILINE)
_DECISION_RE = re.compile(r"^##\s*Decision", re.MULTILINE)
_CONTRACT_AC_RE = re.compile(r"(?:contract|invariant|policy)\s+check:\s*(.+?)(?:\n|$)", re.IGNORECASE)

# ML research format detection
_ML_RESEARCH_DIRECTION_RE = re.compile(
    r"^##\s*(?:\d+\)\s*)?Research\s+Direction", re.MULTILINE | re.IGNORECASE
)
_ML_SUCCESS_METRIC_RE = re.compile(
    r"^##\s*(?:\d+\)\s*)?Success\s+Metric", re.MULTILINE | re.IGNORECASE
)

# --- Markdown stripping ---

# Strip inline markdown formatting so regexes match plain keywords
# Process most-specific first (***) to avoid mismatched delimiters
_MD_TRIPLE_RE = re.compile(r"(\*{3}|_{3})(.+?)\1")
_MD_DOUBLE_RE = re.compile(r"(\*{2}|_{2})(.+?)\1")
_MD_SINGLE_RE = re.compile(r"(\*|_)(.+?)\1")
_MD_BACKTICK_RE = re.compile(r"`([^`]+)`")


def _strip_markdown_inline(text: str) -> str:
    """Strip bold, italic, and backtick formatting, preserving content.

    ***bold-italic*** → bold-italic, **Given** → Given, `MUST` → MUST.
    Processes most-specific delimiters first to handle nesting correctly.
    """
    text = _MD_TRIPLE_RE.sub(r"\2", text)
    text = _MD_DOUBLE_RE.sub(r"\2", text)
    text = _MD_SINGLE_RE.sub(r"\2", text)
    text = _MD_BACKTICK_RE.sub(r"\1", text)
    return text


# Section detection patterns — used to find section boundaries
SECTION_HEADERS: dict[str, re.Pattern] = {
    "acceptance criteria": re.compile(
        r"(?:^##\s*(?:\d+\)\s*)?acceptance\s+(?:criteria|scenarios)|given\s.+?when\s.+?then\s|when\s.+?then\s|the\s+system\s+shall\b|contract\s*check:|invariant\s*check:|policy\s*check:)",
        re.IGNORECASE | re.MULTILINE,
    ),
    "edge cases": re.compile(
        r"(?:^##\s*(?:\d+\)\s*)?edge\s+cases|what\s+happens\s+when\b)", re.IGNORECASE | re.MULTILINE
    ),
    "constraints": re.compile(r"(?:^##\s*(?:\d+\)\s*)?(?:constraints|non-negotiable))", re.IGNORECASE | re.MULTILINE),
    "scope boundaries": re.compile(
        r"(?:^##\s*(?:\d+\)\s*)?(?:(?:out\s+of\s+)?scope|scope\s+boundaries))", re.IGNORECASE | re.MULTILINE
    ),
    "scope": re.compile(r"(?:^##\s*(?:\d+\)\s*)?(?:out\s+of\s+)?scope)", re.IGNORECASE | re.MULTILINE),
    "context anchors": re.compile(
        r"(?:^##\s*(?:\d+\)\s*)?(?:model\s+anchors|context\s+anchors)|follow\s+the\s+pattern\s+in\s|use\s+the\s+\w+\s+(?:class|function|module)\s+from\s|src/\S+\.(?:py|ts|js|go|rs)\b)",
        re.IGNORECASE | re.MULTILINE,
    ),
    "i/o contracts": re.compile(
        r"(?:request\s*:|response\s*:|POST\s+/|GET\s+/|PUT\s+/|DELETE\s+/|returns?\s+\d{3}\b)",
        re.IGNORECASE,
    ),
    "error contract": re.compile(
        r'(?:error\s+(?:response|contract|shape|code)|all\s+errors\s+return|"error"\s*:)',
        re.IGNORECASE,
    ),
    "side effects": re.compile(
        r"(?:emit\s+\w+\s*event|send\s+(?:email|notification)|log\s+to\s+audit|message\s+queue|webhook)",
        re.IGNORECASE,
    ),
    "state transitions": re.compile(
        r"(?:→|->|states?\s*:|terminal\s+state|(?:DRAFT|PENDING|ACTIVE|COMPLETED|CANCELLED)\s*(?:→|->))",
        re.IGNORECASE,
    ),
    "data model": re.compile(
        r"(?:^##\s*(?:key\s+)?entit|^##\s*data\s+model|schema\s*:|fields?\s*:|type\s*:\s*(?:string|int|bool))",
        re.IGNORECASE | re.MULTILINE,
    ),
    "key entities": re.compile(
        r"(?:^##\s*(?:\d+\)\s*)?(?:key\s+)?entit|^##\s*(?:\d+\)\s*)?data\s+model)", re.IGNORECASE | re.MULTILINE
    ),
    "style rules": re.compile(
        r"(?:^##\s*(?:\d+\)\s*)?style\s+and\s+architecture|module\s+boundar|error\/logging\s+convention)",
        re.IGNORECASE | re.MULTILINE,
    ),
    # ML research sections
    "research direction": re.compile(
        r"(?:^##\s*(?:\d+\)\s*)?research\s+direction|hypothesis\s*:)",
        re.IGNORECASE | re.MULTILINE,
    ),
    "success metric": re.compile(
        r"(?:^##\s*(?:\d+\)\s*)?success\s+metric|primary\s+metric\s*:|evaluation\s+method\s*:)",
        re.IGNORECASE | re.MULTILINE,
    ),
    "data specification": re.compile(
        r"(?:^##\s*(?:\d+\)\s*)?data\s+specification|training\s+data\s*:|validation\s+data\s*:|feature\s+engineering\s*:)",
        re.IGNORECASE | re.MULTILINE,
    ),
    "techniques": re.compile(
        r"(?:^##\s*(?:\d+\)\s*)?techniques|model\s+architecture\s*:|algorithm\s+choice|baseline\s+to\s+beat\s*:)",
        re.IGNORECASE | re.MULTILINE,
    ),
    "experimentation plan": re.compile(
        r"(?:^##\s*(?:\d+\)\s*)?experimentation\s+plan|offline\s+eval|a/b\s+test\s+design|iteration\s+strategy\s*:)",
        re.IGNORECASE | re.MULTILINE,
    ),
    "human-in-the-loop": re.compile(
        r"(?:^##\s*(?:\d+\)\s*)?human.in.the.loop|escalation\s+criteria\s*:|go/no.go\s+decision)",
        re.IGNORECASE | re.MULTILINE,
    ),
    "infrastructure": re.compile(
        r"(?:^##\s*(?:\d+\)\s*)?infrastructure|hardware\s+requirements?\s*:|deployment\s+environment\s*:)",
        re.IGNORECASE | re.MULTILINE,
    ),
    "monitoring": re.compile(
        r"(?:^##\s*(?:\d+\)\s*)?monitoring|model\s+drift|data\s+quality\s+alert|performance\s+regression\s+threshold)",
        re.IGNORECASE | re.MULTILINE,
    ),
    "cost": re.compile(
        r"(?:^##\s*(?:\d+\)\s*)?cost|compute\s+cost\s*:|budget\s+cap\s*:)",
        re.IGNORECASE | re.MULTILINE,
    ),
    "integration points": re.compile(
        r"(?:^##\s*(?:\d+\)\s*)?integration\s+points|upstream\s+data\s+dependenc|downstream\s+consumer)",
        re.IGNORECASE | re.MULTILINE,
    ),
}

HIGH_IMPACT = {
    "acceptance criteria",
    "edge cases",
    "constraints",
    "scope boundaries",
    "scope",
    "context anchors",
    "key entities",
    "i/o contracts",
    "error contract",
    "style rules",
}
MEDIUM_IMPACT = {"side effects", "state transitions", "data model"}


# Pre-compiled keyword patterns for section impact classification
def _compile_section_keywords(names: set[str]) -> dict[str, list[re.Pattern[str]]]:
    """Compile word-boundary patterns for significant keywords (3+ chars) per section name."""
    result: dict[str, list[re.Pattern[str]]] = {}
    for name in names:
        keywords = [kw for kw in name.split() if len(kw) > 2]
        result[name] = [re.compile(rf"\b{re.escape(kw)}\b", re.IGNORECASE) for kw in keywords]
    return result


_HIGH_IMPACT_KW = _compile_section_keywords(HIGH_IMPACT)
_MEDIUM_IMPACT_KW = _compile_section_keywords(MEDIUM_IMPACT)

# Sections that are NOT scored (human-only context)
HUMAN_SECTIONS_RE = re.compile(
    r"^##\s*(?:\d+\)\s*)?(?:context|problem|why\s+now|expected\s+outcomes?|priorit|alternatives?\s+considered|motivation|roadmap|ownership|rollback|success\s+criteria|research\s+direction|human.in.the.loop|cost)",
    re.IGNORECASE | re.MULTILINE,
)

# Goal extraction
HEADING_GOAL_RE = re.compile(r"^##\s*(?:Goals?|Requirements?|Features?)\s*$", re.IGNORECASE | re.MULTILINE)
# Match Given/When/Then or When/Then (markdown stripped before matching)
GWT_RE = re.compile(
    r"(?:given\s.+?when\s.+?then\s.+?|when\s.+?then\s.+?)(?:\n|$)",
    re.IGNORECASE,
)


@dataclass
class Issue:
    line: int
    type: str  # ambiguity, testability, consistency, completeness
    term: str
    suggestion: str


@dataclass
class QualityScore:
    completeness: int
    ambiguity: int
    testability: int
    consistency: int
    overall: int
    verdict: str  # PASS, REVIEW, REWRITE
    format_detected: str
    issues: list[Issue] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    sections_found: list[str] = field(default_factory=list)
    sections_expected: list[str] = field(default_factory=list)


def detect_format(text: str, search_dirs: list[Path] | None = None) -> str:
    """Detect spec format from content and directory signals."""
    if search_dirs:
        for d in search_dirs:
            if (d / ".specify").is_dir():
                return "spec-kit"
            if (d / ".kiro" / "specs").is_dir():
                return "kiro"
            if (d / ".openspec").is_dir():
                return "openspec"

    if _FR_RE.search(text) and _SC_RE.search(text):
        return "spec-kit"

    if _KIRO_RE.search(text):
        return "kiro"

    if _OPENSPEC_RE.search(text):
        return "openspec"

    if _CONSTRAINTS_RE.search(text) and _AC_SIGNAL_RE.search(text):
        return "delivery-gap"

    if _ML_RESEARCH_DIRECTION_RE.search(text) and _ML_SUCCESS_METRIC_RE.search(text):
        return "ml-research"

    rfc_signals = sum(
        [
            bool(_MOTIVATION_RE.search(text)),
            bool(_ALTERNATIVES_RE.search(text)),
            bool(_DECISION_RE.search(text)),
        ]
    )
    if rfc_signals >= 2:
        return "rfc"

    return "freeform"


def _find_search_dirs(file_path: Path) -> list[Path]:
    """Find directories to check for format signals, up to git root or 3 levels."""
    dirs = []
    current = file_path.parent.resolve()
    for _ in range(4):
        dirs.append(current)
        if (current / ".git").exists():
            break
        parent = current.parent
        if parent == current:
            break
        current = parent
    return dirs


def _build_line_impact_map(text: str) -> dict[int, str]:
    """Pre-compute a line-number-to-impact-level map.

    Single pass over the text — O(lines), not O(lines * matches).
    """
    lines = text.splitlines()
    impact_map: dict[int, str] = {}
    current_impact = "high"  # default before any header

    for i, line in enumerate(lines):
        if re.match(r"^##\s", line):
            # Check if human-only section
            if HUMAN_SECTIONS_RE.match(line):
                current_impact = "none"
            else:
                header_lower = line.lower()
                # Match full section name or ALL significant keywords as whole words
                matched = False
                for section_name, patterns in _HIGH_IMPACT_KW.items():
                    if section_name in header_lower or (patterns and all(p.search(header_lower) for p in patterns)):
                        current_impact = "high"
                        matched = True
                        break
                if not matched:
                    for section_name, patterns in _MEDIUM_IMPACT_KW.items():
                        if section_name in header_lower or (patterns and all(p.search(header_lower) for p in patterns)):
                            current_impact = "medium"
                            matched = True
                            break
                if not matched:
                    current_impact = "high"  # default for unknown scored sections
        # 1-indexed line numbers
        impact_map[i + 1] = current_impact

    return impact_map


def _find_sections(text: str) -> list[str]:
    """Identify which scored sections are present."""
    found = []
    for name, pattern in SECTION_HEADERS.items():
        if pattern.search(text) and name not in found:
            found.append(name)
    return found


def _score_completeness(
    sections_found: list[str],
    expected: list[str],
    optional: list[str] | None = None,
) -> tuple[int, list[Issue], list[str]]:
    """Score completeness. Returns (score, issues, effective_expected).

    Required sections always count in the denominator.
    Optional sections are added to numerator and denominator only if detected.
    The effective_expected list is returned for reporting.
    """
    if not expected:
        return 100, [], []

    # Start with required sections
    effective = list(expected)

    # Add optional sections that are actually present
    if optional:
        for s in optional:
            if s in sections_found:
                effective.append(s)

    present = sum(1 for s in effective if s in sections_found)
    score = round(present / len(effective) * 100)
    issues = []
    for s in effective:
        if s not in sections_found:
            issues.append(
                Issue(
                    line=0,
                    type="completeness",
                    term=s,
                    suggestion=f"Missing expected section: {s}",
                )
            )
    return score, issues, effective


def _score_ambiguity(text: str) -> tuple[int, list[Issue]]:
    """Score ambiguity — normalized by spec length, with per-line impact classification."""
    issues = []
    high_count = 0
    medium_count = 0

    # Pre-compute impact map once (O(lines)), not per-match
    impact_map = _build_line_impact_map(text)

    for i, line in enumerate(text.splitlines(), 1):
        for match in VAGUE_RE.finditer(line):
            impact = impact_map.get(i, "high")
            if impact == "none":
                continue  # skip terms in human-only sections
            # Skip if the same line has a concrete measurement
            if _PRECISE_LINE_RE.search(line):
                continue
            if impact == "high":
                high_count += 1
            else:
                medium_count += 1
            issues.append(
                Issue(
                    line=i,
                    type="ambiguity",
                    term=match.group(),
                    suggestion=f"Replace '{match.group()}' with a specific, measurable term",
                )
            )

    raw_deductions = (5 * high_count) + (3 * medium_count)
    words = len(text.split())

    # For very short specs (<50 words), apply a penalty rather than the floor
    if words < 50 and (high_count + medium_count) > 0:
        vague_ratio = (high_count + medium_count) / max(words, 1)
        score = max(0, round(100 - vague_ratio * 500))
    else:
        words_capped = max(words, 100)
        deductions_per_100 = (raw_deductions / words_capped) * 100
        score = max(0, round(100 - deductions_per_100))

    return score, issues


_GOAL_STRONG_RE = re.compile(r"\b(?:MUST|SHALL)\b")
_GOAL_WEAK_RE = re.compile(r"\b(?:SHOULD|will)\b")
_GOAL_SKIP_RE = re.compile(r"(?:Note|See|For|The |This |That |If |When )", re.IGNORECASE)
_NEXT_HEADING_RE = re.compile(r"^##\s", re.MULTILINE)


def _extract_goals(text: str) -> list[str]:
    """Extract goals from spec text in a single pass over lines.

    Priority: MUST/SHALL > heading-based goals > SHOULD/will > bullet requirements.
    """
    goals: list[str] = []
    seen: set[str] = set()

    def _add(goal: str) -> None:
        goal = goal.strip().lstrip("-* ")
        if goal and len(goal) > 10 and goal not in seen:
            seen.add(goal)
            goals.append(goal)

    # Collect lines from Goals/Requirements/Features heading sections
    for heading_match in HEADING_GOAL_RE.finditer(text):
        start = heading_match.end()
        next_heading = _NEXT_HEADING_RE.search(text[start:])
        section_end = start + next_heading.start() if next_heading else len(text)
        for line in text[start:section_end].splitlines():
            _add(line)

    # Single pass: classify each line by signal strength
    strong_goals: list[str] = []
    weak_goals: list[str] = []
    bullet_goals: list[str] = []

    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or len(stripped) <= 10:
            continue
        if _GOAL_STRONG_RE.search(line):
            strong_goals.append(line)
        elif _GOAL_WEAK_RE.search(line):
            weak_goals.append(line)
        elif re.match(r"\s*[-*]\s+.{15,}", line) and not _GOAL_SKIP_RE.match(stripped.lstrip("-* ")):
            bullet_goals.append(stripped.lstrip("-* ").strip())

    # Add strong goals (MUST/SHALL)
    for g in strong_goals:
        _add(g)

    # Always add SHOULD/will goals (not just when MUST is absent)
    for g in weak_goals:
        _add(g)

    # Bullet goals only as fallback when no keyword-based goals found
    if not goals:
        for g in bullet_goals:
            _add(g)

    return goals


_ML_THRESHOLD_RE = re.compile(
    r"(?:[<>=!]=?\s*\d+\.?\d*|threshold|at\s+(?:most|least)\s+\d|under\s+\d|above\s+\d|below\s+\d)",
    re.IGNORECASE,
)
_ML_EVAL_METHOD_RE = re.compile(
    r"(?:offline\s+eval|a/b\s+test|human\s+eval|held.out\s+set|validation\s+set|eval\s+set|test\s+set)",
    re.IGNORECASE,
)
_ML_REPRODUCIBLE_RE = re.compile(
    r"(?:seed\s*[=:]\s*\d+|fixed\s+seed|deterministic|reproducib)",
    re.IGNORECASE,
)


def _score_testability_ml(text: str) -> tuple[int, list[Issue]]:
    """ML-specific testability: measurable thresholds, evaluation method, reproducibility."""
    issues: list[Issue] = []
    checks = 0
    passed = 0

    # Check 1: Success metric has a measurable threshold
    checks += 1
    if _ML_THRESHOLD_RE.search(text):
        passed += 1
    else:
        issues.append(Issue(
            line=0,
            type="testability",
            term="success metric",
            suggestion="Add a measurable threshold (e.g., 'val_bpb < 1.05') so success/failure is unambiguous",
        ))

    # Check 2: Evaluation method specified
    checks += 1
    if _ML_EVAL_METHOD_RE.search(text):
        passed += 1
    else:
        issues.append(Issue(
            line=0,
            type="testability",
            term="evaluation method",
            suggestion="Specify the evaluation method (offline eval, A/B test, human eval) and the eval dataset",
        ))

    # Check 3: Reproducibility signal (optional — adds to score but doesn't penalize)
    if _ML_REPRODUCIBLE_RE.search(text):
        checks += 1
        passed += 1

    score = round(passed / checks * 100) if checks else 0
    return score, issues


def _score_testability_swe(text: str, gwt_matches: list[re.Match]) -> tuple[int, list[Issue]]:
    """SWE testability: goals matched against GWT acceptance criteria."""
    goals = _extract_goals(text)
    if not goals:
        return 0, [
            Issue(
                line=0,
                type="testability",
                term="(no goals found)",
                suggestion="No goals, requirements, or MUST statements found. Testability cannot be scored.",
            )
        ]
    has_testable_criteria = len(gwt_matches) > 0 or bool(
        re.search(
            r"(?:returns?\s+\d{3}|exit\s+code\s+\d|score\s+(?:is|equals|=)\s+\d)",
            text,
            re.IGNORECASE,
        )
    )

    # Pre-compute GWT word sets once (not per-goal)
    gwt_word_sets = [set(re.findall(r"\w{4,}", gwt.group().lower())) for gwt in gwt_matches]

    covered = 0
    issues = []
    for goal in goals:
        goal_words = set(re.findall(r"\w{4,}", goal.lower()))
        matched = False
        for gwt_words in gwt_word_sets:
            if len(goal_words & gwt_words) >= 3:
                matched = True
                break
        if (
            not matched
            and has_testable_criteria
            and (re.search(r"\b\d+\b", goal) or re.search(r"exit\s+code|returns?\b", goal, re.IGNORECASE))
        ):
            matched = True
        if matched:
            covered += 1
        else:
            issues.append(
                Issue(
                    line=0,
                    type="testability",
                    term=goal[:80],
                    suggestion=f"Goal without test: '{goal[:60]}{'...' if len(goal) > 60 else ''}' — add a Given/When/Then criterion",
                )
            )

    score = round(covered / len(goals) * 100) if goals else 0
    return score, issues


def _score_testability(text: str, gwt_matches: list[re.Match], fmt: str = "freeform") -> tuple[int, list[Issue]]:
    """Dispatch testability scoring by format."""
    if fmt == "ml-research":
        return _score_testability_ml(text)
    return _score_testability_swe(text, gwt_matches)


def _score_consistency(text: str, gwt_matches: list[re.Match]) -> tuple[int, list[Issue]]:
    issues = []
    contradictions = 0

    scope_exclusions = re.findall(
        r"(?:out\s+of\s+scope|does\s+not|not\s+(?:part\s+of|included))\s*[:\-]?\s*(.+?)(?:\n|$)",
        text,
        re.IGNORECASE,
    )
    gwt_word_sets = [set(re.findall(r"\w{4,}", gwt.group().lower())) for gwt in gwt_matches]

    # Also check contract/invariant/policy check lines (delivery-gap AC format)
    contract_word_sets = [set(re.findall(r"\w{4,}", m.group(1).lower())) for m in _CONTRACT_AC_RE.finditer(text)]
    all_ac_word_sets = gwt_word_sets + contract_word_sets

    for exclusion in scope_exclusions:
        keywords = set(re.findall(r"\w{4,}", exclusion.lower()))
        if len(keywords) < 2:
            continue
        for ac_words in all_ac_word_sets:
            overlap = keywords & ac_words
            if len(overlap) >= 2:
                contradictions += 1
                issues.append(
                    Issue(
                        line=0,
                        type="consistency",
                        term=f"Scope excludes '{exclusion.strip()[:50]}'",
                        suggestion=f"But acceptance criteria reference: {', '.join(sorted(overlap)[:3])}",
                    )
                )
                break

    score = max(0, 100 - (25 * contradictions))
    return score, issues


def _generate_warnings(sections_found: list[str]) -> list[str]:
    warnings = []
    checks = {
        "context anchors": "No context anchors — AI will invent its own architecture",
        "i/o contracts": "No I/O contracts — AI will invent API shapes",
        "side effects": "No side effects listed — AI may miss integrations",
        "error contract": "No error contract — AI will invent error shapes per function",
        "state transitions": "No state transitions — AI may allow invalid transitions",
        "style rules": "No style/architecture rules — AI may violate module boundaries or conventions",
    }
    for section, warning in checks.items():
        if section not in sections_found:
            warnings.append(warning)
    return warnings


def score_text(
    text: str,
    format_override: str | None = None,
    file_path: Path | None = None,
) -> QualityScore:
    """Score a spec text. Core scoring engine used by both entry points."""
    if not text.strip():
        return QualityScore(
            completeness=0,
            ambiguity=0,
            testability=0,
            consistency=0,
            overall=0,
            verdict="REWRITE",
            format_detected="freeform",
            warnings=["No scorable content found. This file does not appear to be a specification."],
        )

    # Strip markdown inline formatting for keyword matching (G/W/T, MUST, etc.)
    # Keep original text for ambiguity scoring (needs accurate line numbers)
    stripped = _strip_markdown_inline(text)

    search_dirs = _find_search_dirs(file_path) if file_path else None
    fmt = format_override or detect_format(stripped, search_dirs)
    expected = EXPECTED_SECTIONS.get(fmt, EXPECTED_SECTIONS["freeform"])

    sections_found = _find_sections(stripped)

    optional = ML_RESEARCH_OPTIONAL_SECTIONS if fmt == "ml-research" else None
    completeness, comp_issues, effective_expected = _score_completeness(sections_found, expected, optional)
    ambiguity, amb_issues = _score_ambiguity(text)  # original text for line numbers
    # Compute GWT matches once, share between testability and consistency
    gwt_matches = list(GWT_RE.finditer(stripped))
    testability, test_issues = _score_testability(stripped, gwt_matches, fmt)
    consistency, cons_issues = _score_consistency(stripped, gwt_matches)

    overall = round(completeness * 0.30 + ambiguity * 0.30 + testability * 0.25 + consistency * 0.15)

    missing_high = [s for s in effective_expected if s in HIGH_IMPACT and s not in sections_found]
    if overall >= 70 and not missing_high:
        verdict = "PASS"
    elif overall < 40 or len(missing_high) >= 3:
        verdict = "REWRITE"
    else:
        verdict = "REVIEW"

    all_issues = comp_issues + amb_issues + test_issues + cons_issues
    warnings = _generate_warnings(sections_found)

    return QualityScore(
        completeness=completeness,
        ambiguity=ambiguity,
        testability=testability,
        consistency=consistency,
        overall=overall,
        verdict=verdict,
        format_detected=fmt,
        issues=all_issues,
        warnings=warnings,
        sections_found=sections_found,
        sections_expected=effective_expected,
    )


def score_file(file_path: str | Path, format_override: str | None = None) -> QualityScore:
    """File mode — score a single spec file."""
    path = Path(file_path)
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        return QualityScore(
            completeness=0,
            ambiguity=0,
            testability=0,
            consistency=0,
            overall=0,
            verdict="REWRITE",
            format_detected="freeform",
            warnings=[f"Could not read file: {e}"],
        )
    return score_text(text, format_override=format_override, file_path=path)


def score_classifications(
    classifications: list[SpecClassification],
    format_override: str | None = None,
) -> list[tuple[SpecClassification, QualityScore]]:
    """Repo mode — score all spec'd PRs from coverage results."""
    results = []
    for cls in classifications:
        if cls.specd and cls.spec_content:
            score = score_text(cls.spec_content, format_override=format_override)
            results.append((cls, score))
    return results
