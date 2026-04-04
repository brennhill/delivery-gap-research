"""
Pure signal detection functions for delivery pipeline analysis.

These are stateless, testable functions that classify commit messages
and file paths. No I/O, no subprocess calls. Zero dependencies beyond
the Python standard library.

Shared by changeledger, CatchRate, and Upfront to ensure consistent
detection across the delivery-gap tool ecosystem.
"""

import re

# ── Ticket ID patterns ───────────────────────────────────────────────

TICKET_PATTERNS = [
    re.compile(r"[A-Z]{2,10}-\d+"),          # JIRA/Linear numeric: PROJ-123
    re.compile(r"(?<!\w)#(\d+)\b"),           # GitHub/GitLab issue: #123
    re.compile(r"(?:fixes|closes|resolves)\s+#(\d+)", re.IGNORECASE),
    re.compile(r"[A-Z]{2,10}-[a-z0-9]+"),     # Linear alphanumeric: ENG-abc123
]

# ── Fix detection ────────────────────────────────────────────────────

FIX_PATTERNS = re.compile(
    r"^(fix|hotfix|bugfix|patch|revert)[\s(:!/]",
    re.IGNORECASE | re.MULTILINE,
)

# ── Revert detection ────────────────────────────────────────────────

REVERT_PATTERN = re.compile(
    r'revert\s+"?(.+?)"?\s*$|^Revert\s+"(.+?)"|This reverts commit ([0-9a-f]{7,40})',
    re.IGNORECASE | re.MULTILINE,
)

FIXES_TRAILER = re.compile(r"^Fixes:\s+([0-9a-f]{7,40})", re.MULTILINE)

REVERT_PR_PATTERN = re.compile(
    r"(?:revert(?:s|ed|ing)?)\s+#(\d+)",
    re.IGNORECASE,
)

# ── Dependency / chore detection ─────────────────────────────────────

_DEP_TITLE_PATTERNS = re.compile(
    r"^bump\s|"
    r"^upgrade\s+(?:go|node|python|ruby|java|rust|elixir|swift)\b|"
    r"^(?:update|upgrade)\s+(?:vendored\s+)?(?:depend|google\.|golang\.|github\.com/|@|npm|pip|cargo|gem)|"
    r"\b(?:dependabot|renovate|auto.?merge)\b|"
    r"^chore\(deps\)|^build\(deps\)",
    re.IGNORECASE,
)

_DEP_AUTHORS = {
    "dependabot[bot]", "renovate[bot]", "dependabot", "renovate",
    "greenkeeper[bot]", "snyk-bot", "depfu[bot]",
}

LOCK_FILES = {
    "go.sum", "go.mod", "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    "Cargo.lock", "Gemfile.lock", "poetry.lock", "Pipfile.lock",
    "composer.lock", "requirements.txt", "shrinkwrap.yaml",
}


def is_dependency_change(
    title: str,
    author: str = "",
    files: list[str] | None = None,
) -> bool:
    """Return True if the change is a dependency bump or automated cherry pick.

    Detection uses three signals (any one is sufficient):
    1. Title matches dependency/bump/upgrade patterns
    2. Author is a known dependency bot
    3. All changed files are lock/manifest files
    """
    if _DEP_TITLE_PATTERNS.search(title):
        return True
    if author.lower() in _DEP_AUTHORS:
        return True
    if files:
        basenames = {f.split("/")[-1] if "/" in f else f for f in files}
        if basenames and basenames.issubset(LOCK_FILES):
            return True
    return False


# ── File classification ──────────────────────────────────────────────

IGNORE_FILES = {
    "README.md", "CHANGELOG.md", "CHANGES.md", "HISTORY.md",
    "package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml",
    "Cargo.lock", "go.sum", "Gemfile.lock", "poetry.lock",
    "requirements.txt", "Pipfile.lock",
    ".gitignore", ".eslintrc.js", ".eslintrc.json", ".prettierrc",
    "tsconfig.json", "jest.config.js", "jest.config.ts",
    "Makefile", "Dockerfile", "docker-compose.yml",
}

IGNORE_DIR_PATTERNS = re.compile(
    r"(^\.github/|^docs/|^\.vscode/|\.lock$|\.sum$)",
    re.IGNORECASE,
)

# ── PR number extraction ────────────────────────────────────────────

_MERGE_PR_PATTERN = re.compile(r"^Merge pull request #(\d+)\b")
_SQUASH_PR_PATTERN = re.compile(r"\(#(\d+)\)\s*$")


# ── Pure functions ───────────────────────────────────────────────────

def is_source_file(path: str) -> bool:
    """Return True if the path is a source file (not config, docs, or lockfile)."""
    basename = path.split("/")[-1] if "/" in path else path
    if basename in IGNORE_FILES:
        return False
    return not IGNORE_DIR_PATTERNS.search(path)


def extract_ticket_ids(text: str) -> set[str]:
    """Extract normalized ticket IDs from a commit message or PR body.

    Returns a set of normalized IDs: JIRA keys uppercased (PROJ-123),
    GitHub issues prefixed with # (#123).
    """
    ids: set[str] = set()
    for pattern in TICKET_PATTERNS:
        for match in pattern.finditer(text):
            captured = match.group(1) if pattern.groups and match.group(1) else match.group(0)
            normalized = captured.upper()
            if normalized.isdigit():
                normalized = f"#{normalized}"
            ids.add(normalized)
    return ids


def is_fix_message(text: str) -> bool:
    """Return True if the text starts with a fix/bugfix/hotfix/patch prefix."""
    return bool(FIX_PATTERNS.search(text))


def extract_fixes_sha(text: str) -> str | None:
    """Extract SHA from a 'Fixes: <sha>' trailer in commit message."""
    m = FIXES_TRAILER.search(text)
    return m.group(1) if m else None


def is_revert_message(text: str) -> bool:
    """Return True if the text matches a revert pattern."""
    return bool(REVERT_PATTERN.search(text))


def extract_revert_pr_numbers(text: str) -> set[int]:
    """Extract PR numbers from revert messages (e.g., 'Revert #42', 'Reverts #42')."""
    return {int(m.group(1)) for m in REVERT_PR_PATTERN.finditer(text)}


def extract_pr_number_from_subject(subject: str) -> int | None:
    """Extract PR number from a git merge commit subject.

    Handles two common GitHub merge strategies:
    - Merge commit: "Merge pull request #42 from owner/branch"
    - Squash merge: "feat: add thing (#42)"
    """
    m = _MERGE_PR_PATTERN.search(subject)
    if m:
        return int(m.group(1))
    m = _SQUASH_PR_PATTERN.search(subject)
    if m:
        return int(m.group(1))
    return None


def compute_file_overlap(files_a: set[str], files_b: set[str]) -> float:
    """Compute file overlap ratio: len(intersection) / len(files_b).

    Uses % of candidate (files_b) as denominator — catches surgical fixes
    to large PRs. Returns 0.0 if files_b is empty.
    """
    if not files_b:
        return 0.0
    overlap = files_a & files_b
    return len(overlap) / len(files_b)
