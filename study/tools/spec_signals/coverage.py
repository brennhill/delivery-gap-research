"""Spec link detection and classification.

Classifies PRs/commits as spec'd or unspec'd based on regex patterns.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from tools.signals import extract_ticket_ids

from tools.spec_signals.models import SpecClassification

if TYPE_CHECKING:
    from tools.spec_signals.models import Commit, PullRequest

# Upfront-specific: false positives to exclude from shared ticket extraction
_TICKET_FALSE_POSITIVES = {
    "UTF",
    "SHA",
    "TLS",
    "SSL",
    "HTTP",
    "TCP",
    "UDP",
    "ISO",
    "RFC",
    "IEEE",
    "AES",
    "RSA",
    "CWE",
    "CVE",
}

# URL pattern
URL_RE = re.compile(r"https?://\S+")

# PR template section headers
SECTION_RE = re.compile(
    r"^##\s*(?:Spec|Requirements|Acceptance\s+Criteria)",
    re.MULTILINE | re.IGNORECASE,
)

# Placeholder content — single source of truth
PLACEHOLDERS = {
    "tbd",
    "todo",
    "n/a",
    "na",
    "none",
    "yes",
    "done",
    "see above",
    "[fill in]",
    "fill in",
    "placeholder",
}
# Full-line match for placeholder variations
PLACEHOLDER_RE = re.compile(
    r"^\s*(?:" + "|".join(re.escape(p) for p in sorted(PLACEHOLDERS, key=len, reverse=True)) + r")\s*$",
    re.IGNORECASE,
)

MIN_WORDS = 20

_MARKDOWN_HEADER_RE = re.compile(r"^#{1,6}\s")
_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)


def _strip_markdown_headers(text: str) -> str:
    """Remove markdown headers (lines matching ^#{1,6} ), leaving content."""
    lines = []
    for line in text.splitlines():
        if _MARKDOWN_HEADER_RE.match(line):
            continue
        lines.append(line)
    return "\n".join(lines)


def _is_placeholder_only(text: str) -> bool:
    """Check if text is just placeholder content."""
    stripped = text.strip().lower()
    if stripped in PLACEHOLDERS:
        return True
    content_lines = [ln.strip().lower() for ln in text.splitlines() if ln.strip()]
    if not content_lines:
        return True
    return all(ln in PLACEHOLDERS or PLACEHOLDER_RE.fullmatch(ln) for ln in content_lines)


_SPEC_URL_RE = re.compile(
    r"(?:notion\.so|notion\.site|confluence|atlassian\.net|docs\.google\.com|linear\.app|jira|shortcut\.com|github\.com/[^/]+/[^/]+/issues/)",
    re.IGNORECASE,
)


def _is_spec_url(url: str) -> bool:
    """Check if URL points to a known spec-hosting domain."""
    return bool(_SPEC_URL_RE.search(url))


def _has_section_content(body: str) -> tuple[bool, str | None]:
    """Check if PR body has a filled-in spec/requirements section."""
    match = SECTION_RE.search(body)
    if not match:
        return False, None

    start = match.end()
    next_header = re.search(r"^##\s", body[start:], re.MULTILINE)
    section_content = body[start : start + next_header.start()] if next_header else body[start:]

    content = _strip_markdown_headers(section_content).strip()
    content = _HTML_COMMENT_RE.sub("", content).strip()  # strip HTML comments before counting
    if not content or _is_placeholder_only(content):
        return False, None

    word_count = len(content.split())
    if word_count < MIN_WORDS:
        return False, None

    return True, "template section"


def _detect_spec_source(text: str, check_sections: bool = False) -> tuple[bool, str | None]:
    """Shared spec detection logic. Returns (specd, spec_source).

    Used by both classify_pr and classify_commit to avoid duplication.
    """
    if not text.strip() or text.strip().lower() in {"no description provided", ""}:
        return False, None

    # Check for filled template sections (PR mode only)
    if check_sections:
        has_section, source = _has_section_content(text)
        if has_section:
            return True, source

    # Check for ticket IDs (shared package), excluding Upfront-specific false positives.
    # Bare #NNN refs are too noisy — only accept them when the shared package found
    # them via a context keyword (fixes/closes/resolves).  Project-key tickets
    # (PROJ-123) are accepted unconditionally after false-positive filtering.
    ticket_ids = extract_ticket_ids(text)
    _CONTEXT_KW_RE = re.compile(
        r"(?:fix|fixes|closed?|closes|resolves?|references|refs|related?\s+to)\s+#(\d+)",
        re.IGNORECASE,
    )
    contextual_nums = {m.group(1) for m in _CONTEXT_KW_RE.finditer(text)}
    for tid in sorted(ticket_ids):
        if tid.startswith("#"):
            # Only accept GitHub-style #NNN when it appeared with a context keyword
            num = tid.lstrip("#")
            if num not in contextual_nums:
                continue
        elif "-" in tid:
            prefix = tid.split("-")[0]
            if prefix in _TICKET_FALSE_POSITIVES:
                continue
        return True, tid

    # Check for URLs to known spec-hosting domains
    for url_match in URL_RE.finditer(text):
        if _is_spec_url(url_match.group()):
            return True, url_match.group()

    return False, None


def classify_pr(pr: PullRequest) -> SpecClassification:
    """Classify a single PR as spec'd or unspec'd.

    Checks body first (template sections, tickets, URLs), then falls back
    to title for ticket IDs (many teams put PROJ-123 in the title only).
    """
    body = pr.body or ""
    merged_at = pr.merged_at.isoformat() if pr.merged_at else ""
    specd, spec_source = _detect_spec_source(body, check_sections=True)
    if not specd:
        # Fall back to title for ticket IDs
        specd, spec_source = _detect_spec_source(pr.title, check_sections=False)
    return SpecClassification(
        pr_number=pr.number,
        commit_sha=None,
        title=pr.title,
        specd=specd,
        spec_source=spec_source,
        spec_content=body,
        merged_at=merged_at,
    )


def classify_commit(commit: Commit) -> SpecClassification:
    """Classify a commit as spec'd or unspec'd (git-only mode)."""
    message = commit.message or ""
    first_line = message.split("\n")[0]
    specd, spec_source = _detect_spec_source(message, check_sections=False)
    return SpecClassification(
        pr_number=None,
        commit_sha=commit.sha,
        title=first_line,
        specd=specd,
        spec_source=spec_source,
        spec_content=message,
        merged_at=commit.date.isoformat(),
    )


def run_coverage(
    prs: list[PullRequest] | None = None,
    commits: list[Commit] | None = None,
    include_bots: bool = False,
    include_deps: bool = False,
) -> list[SpecClassification]:
    """Classify all PRs or commits and return classifications."""
    if prs is not None:
        from tools.signals import is_dependency_change

        def is_bot_author(pr: PullRequest) -> bool:
            return pr.author.endswith("[bot]")

        results = []
        for pr in prs:
            if not include_bots and is_bot_author(pr):
                continue
            if not include_deps and is_dependency_change(
                pr.title, pr.author, [f.path if hasattr(f, 'path') else f for f in (pr.files or [])],
            ):
                continue
            results.append(classify_pr(pr))
        return results

    if commits is not None:
        return [classify_commit(c) for c in commits]

    return []
