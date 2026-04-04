"""Detect escapes: reverts, fix-follow-ups, ticket cross-references."""

from __future__ import annotations

import fnmatch
import re
from collections import Counter, defaultdict
from dataclasses import replace
from datetime import datetime

from tools.signals import (
    compute_file_overlap as _shared_file_overlap,
)
from tools.signals import (
    is_dependency_change,
    is_fix_message,
    is_revert_message,
)

from tools.catchrate.bots import is_bot
from tools.catchrate.dateutil import is_within_window, parse_iso_datetime
from tools.catchrate.log import log, warn
from tools.catchrate.models import Classification, ClassificationType, EscapeConfidence

CT = ClassificationType

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# SHA extraction from revert body — kept here because the shared package
# does not expose a dedicated function for "This reverts commit <sha>".
REVERT_BODY = re.compile(r"This reverts commit ([0-9a-f]{7,40})", re.IGNORECASE)

# CatchRate uses first-match-only ticket detection (spec: auto-detect tries
# patterns in order, uses first match).  The shared package's
# extract_ticket_ids collects from ALL patterns, so we keep our own list.
TICKET_PATTERNS = [
    re.compile(r"(?<!\w)#(\d+)\b"),  # GitHub issue (word boundary to avoid foo#123)
    re.compile(r"\b([A-Z][A-Z0-9]+-\d+)\b"),  # Jira-style
    re.compile(r"\b([A-Z][A-Z0-9]+-[a-z0-9]+)\b"),  # Linear-style
]

FILE_OVERLAP_THRESHOLD = 0.75  # Raised from 0.50 — human validation showed 18% precision at 50%
HIGH_TOUCH_THRESHOLD = 10  # Files touched by >10 PRs are auto-excluded

# Files that are touched by nearly every PR and tell you nothing about
# whether two PRs are related. Validated against 26K PRs across 43 repos.
ALWAYS_EXCLUDED_PATTERNS = [
    # Lock files / dependency manifests
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "Cargo.lock",
    "go.sum",
    "uv.lock",
    "poetry.lock",
    "Gemfile.lock",
    "composer.lock",
    # Package metadata (touched by every dep bump or version change)
    "package.json",
    "Cargo.toml",
    "go.mod",
    "pyproject.toml",
    "setup.py",
    "setup.cfg",
    "Gemfile",
    "composer.json",
    "pom.xml",
    "build.gradle",
    "build.gradle.kts",
    # Changelogs and version files
    "CHANGELOG.md",
    "CHANGES.md",
    "HISTORY.md",
    "VERSION",
    "version.py",
    "version.ts",
    "version.js",
    # Config noise
    ".gitignore",
    "tsconfig.json",
    "pnpm-workspace.yaml",
    # Generated / localization files
    "*.snap",
    "*.snapshot",
    "en.json",
    "common.json",
    # CI workflows (touched by many unrelated PRs)
    ".github/workflows/ci.yml",
    ".github/workflows/release.yml",
]

# Backport / cherry-pick detection — these reference the original PR but
# are not rework (same fix applied to a different branch).
# Validated on 100 human-labeled HIGH pairs: ports account for 12/36 FPs.
BACKPORT_PATTERNS = re.compile(
    r"backport|cherry[- ]?pick|"
    r"(?:core[- ]?2|release/core)[- ](?:port|version)|"
    r"\bport\s+of\b|"
    r"\bported?\s+(?:to|from|into)\b|"
    r"\bcore\s*2\s*(?:port|version)\b",
    re.IGNORECASE,
)

# Release PR detection — automated PRs that bundle multiple PRs into a
# release, not actual rework.
RELEASE_PATTERNS = re.compile(
    r"^(?:chore|release)\s*[:(].*(?:v?\d+\.\d+|release)|"
    r"^(?:Release|Prepare)\s+v?\d+\.\d+|"
    r"^v\d+\.\d+\.\d+|"
    r"^Patch\s+v?\d+\.\d+",
    re.IGNORECASE,
)

# CI/build fix detection — machine catches where the infrastructure caught
# the problem before users were affected. CI breaking IS the catch mechanism:
# nothing ships to users, someone fixes it, system worked as designed.
#
# Definition: if CI/tests/linting broke and that's what triggered the fix,
# it's a machine catch, not an escape. The only true escape is when
# something gets past ALL gates and affects users.
#
# Validated on 126 human-labeled HIGH pairs.
# Title patterns:
CI_FIX_TITLE_PATTERNS = re.compile(
    r"fix\s*\(?ci\)?[:/\s]|"
    r"fix\s*\(?build\)?[:/\s]|"
    r"fix\s*\(?e2e\)?[:/\s]|"
    r"fix\s*\(?lint\)?[:/\s]|"
    r"fix\s+(?:flaky|flakey|failing|broken|intermittent|unstable)\s+(?:test|e2e|spec|ci|build)|"
    r"fix\s+(?:test|e2e|ci|build)\s+(?:fail|flak|break|error)|"
    r"fix\s+(?:type|typescript|tsc)\s+error|"
    r"fix\s+fuzz\s+test|"
    r"make\s+.*tests?\s+deterministic",
    re.IGNORECASE,
)
# Body patterns (checked against first 500 chars):
CI_FIX_BODY_PATTERNS = re.compile(
    r"(?:ci|build|test|e2e|fuzz|lint|tsc|typescript)\s+(?:fail|broke|broken|error|crash)|"
    r"(?:fail|broke|broken)\s+(?:ci|build|test|e2e|compilation)|"
    r"fix(?:es|ing)?\s+(?:ci|build|test|e2e)\s+(?:fail|error|break)|"
    r"(?:test|spec|e2e)s?\s+(?:are|were|was)\s+(?:fail|break|flak)|"
    r"delimiter\s+bug\s+in\s+.*\.yml",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


# ReDoS mitigation: truncate input before applying user-supplied patterns
# and apply a timeout via signal alarm (Unix) or threading (cross-platform).
_MAX_PATTERN_INPUT_LEN = 10000
_REGEX_TIMEOUT_SECS = 2


def _safe_findall(pattern: re.Pattern, text: str) -> list[str]:
    """Run pattern.findall with a timeout to guard against catastrophic backtracking."""
    import concurrent.futures

    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(pattern.findall, text)
        try:
            return future.result(timeout=_REGEX_TIMEOUT_SECS)
        except concurrent.futures.TimeoutError:
            log(
                "ticket-pattern-timeout",
                f"--ticket-pattern timed out after "
                f"{_REGEX_TIMEOUT_SECS}s — possible catastrophic backtracking. "
                "Falling back to auto-detection.",
            )
            return []


def _extract_tickets(text: str, custom_pattern: re.Pattern | None = None) -> set[str]:
    """Extract ticket IDs from text."""
    if custom_pattern:
        # Mitigate ReDoS risk from user-supplied --ticket-pattern by
        # truncating excessively long input and applying a timeout.
        truncated = text[:_MAX_PATTERN_INPUT_LEN] if len(text) > _MAX_PATTERN_INPUT_LEN else text
        return set(_safe_findall(custom_pattern, truncated))

    tickets: set[str] = set()
    for pattern in TICKET_PATTERNS:
        found = pattern.findall(text)
        if found:
            tickets.update(found)
            break  # Use first matching pattern type only (spec detection order)
    return tickets


def _compute_file_overlap(
    candidate_files: list[str],
    reference_files: list[str],
    excluded_files: set[str],
) -> float:
    """Compute fraction of candidate's files that overlap with reference.

    Uses "% of candidate" direction: answers "is this fix entirely about
    the original change?" A surgical 1-file fix to a 50-file PR scores
    100% because the fix is fully contained in the original's file set.

    Delegates to delivery_gap_signals.compute_file_overlap after filtering
    out excluded files (high-touch / ignore-glob files).
    """
    cand = {f for f in candidate_files if f not in excluded_files and not _is_noise_file(f)}
    ref = {f for f in reference_files if f not in excluded_files and not _is_noise_file(f)}

    if not cand:
        return 0.0

    result: float = _shared_file_overlap(ref, cand)
    return result


def _is_not_escape(fix: Classification, original: Classification) -> bool:
    """Detect false positives: things that reference PR A but aren't escapes.

    Returns True if this pair should be EXCLUDED from escape detection.

    Validated on 100 human-labeled HIGH pairs (36 false positives):
      - Ports/backports: 12/36 (title/body keywords + near-identical titles)
      - Same-title cherry-picks: 4/36 (title with (#NNN) suffix)
      - CI/machine catches: 6/36 (infrastructure caught it, not an escape)
      - Release bundling: from prior validation round
    These filters remove 22/36 false positives, raising precision from 64% to ~77%.
    """
    fix_title = fix.title
    fix_body = fix.body

    # --- Backport / cherry-pick ---
    if BACKPORT_PATTERNS.search(fix_title) or BACKPORT_PATTERNS.search(fix_body[:500]):
        return True

    # Near-identical titles suggest a port to another branch/package
    # e.g. "fix(clerk-js): foo" and "fix(clerk-js): foo (#7857)"
    # Also catches VSCode pattern: "fix #290501" → "fix #290501 (#291876)"
    def _normalize_title(t: str) -> str:
        t = re.sub(r"\s*\(#\d+\)\s*$", "", t).strip()
        # Strip package scope differences like (clerk-js) vs (ui)
        t = re.sub(r"\([^)]+\):\s*", "", t).strip()
        return t.lower()

    if _normalize_title(fix_title) == _normalize_title(original.title):
        return True

    # --- Release bundling ---
    if RELEASE_PATTERNS.search(fix_title):
        return True

    # --- CI / machine catch ---
    # If the fix PR is specifically fixing CI/build/tests, the infrastructure
    # caught the problem. This is the system working, not an escape.
    if CI_FIX_TITLE_PATTERNS.search(fix_title):
        return True

    return bool(CI_FIX_BODY_PATTERNS.search(fix_body[:500]))


def _is_noise_file(filename: str) -> bool:
    """Check if a file is infrastructure noise that shouldn't count for overlap."""
    basename = filename.rsplit("/", 1)[-1] if "/" in filename else filename
    for pat in ALWAYS_EXCLUDED_PATTERNS:
        if fnmatch.fnmatch(basename, pat) or fnmatch.fnmatch(filename, pat):
            return True
    return False


def _matches_ignore_glob(filename: str, patterns: list[str]) -> bool:
    """Check if a filename matches any of the ignore glob patterns."""
    return any(fnmatch.fnmatch(filename, pat) for pat in patterns)


def _find_high_touch_files(
    classifications: list[Classification],
    ignore_patterns: list[str] | None = None,
    verbose: bool = False,
) -> set[str]:
    """Find files touched by more than HIGH_TOUCH_THRESHOLD PRs."""
    file_counter: Counter[str] = Counter()
    for c in classifications:
        for f in c.files:
            file_counter[f] += 1

    excluded = set()
    for f, count in file_counter.items():
        if count > HIGH_TOUCH_THRESHOLD:
            excluded.add(f)
            if verbose:
                warn(f"Auto-excluded from overlap: {f} (touched by {count} PRs)")

    # Also add files matching ignore patterns
    if ignore_patterns:
        all_files = set()
        for c in classifications:
            all_files.update(c.files)
        for f in all_files:
            if _matches_ignore_glob(f, ignore_patterns):
                excluded.add(f)

    return excluded


# ---------------------------------------------------------------------------
# Revert detection
# ---------------------------------------------------------------------------


def _detect_reverts(
    classifications: list[Classification],
    window_days: int = 14,
) -> dict[int, tuple[str, bool]]:
    """Detect PRs that were reverted.

    Returns {original_pr_number: (reason, is_bot_revert)}.
    Bot-authored reverts are machine catches (automated rollback), not escapes.
    Human-authored reverts are escapes (nothing caught it automatically).
    """

    escapes: dict[int, tuple[str, bool]] = {}

    # Build indexes for O(1) lookups
    by_number: dict[int, Classification] = {c.number: c for c in classifications}
    by_title: dict[str, list[Classification]] = {}
    by_commit_sha: dict[str, Classification] = {}
    merged_times: dict[int, datetime] = {}
    for c in classifications:
        stripped = c.title.strip()
        by_title.setdefault(stripped, []).append(c)
        for sha in c.commits:
            by_commit_sha[sha] = c
        if c.merged_at:
            t = parse_iso_datetime(c.merged_at, context=f"PR #{c.number} merged_at")
            if t is not None:
                merged_times[c.number] = t

    def _within_window(revert_num: int, original_num: int) -> bool:
        """Check if revert PR was merged within window_days of original."""
        revert_time = merged_times.get(revert_num)
        orig_time = merged_times.get(original_num)
        if revert_time is None or orig_time is None:
            return False
        return is_within_window(orig_time, revert_time, window_days)

    for c in classifications:
        # Check if this PR is a revert
        is_revert_title = is_revert_message(c.title)
        body_match = REVERT_BODY.search(c.body)
        is_revert_body = bool(body_match)

        if not (is_revert_title or is_revert_body):
            continue

        matched = False

        # Match by explicit PR reference: "Revert #123"
        # Use a stricter pattern: only match #N that directly follows "Revert"
        pr_ref = re.search(r"[Rr]evert\s+#(\d+)", c.title)
        if pr_ref:
            reverted_num = int(pr_ref.group(1))
            if reverted_num in by_number and _within_window(c.number, reverted_num):
                escapes[reverted_num] = (f"reverted by #{c.number}", is_bot(c.author))
                matched = True

        # Check by title match: "Revert "Original PR title""
        # Use greedy capture (.+) to handle nested quotes in revert-of-revert
        # titles like: Revert "Revert "Add feature X""
        if not matched:
            title_match = re.search(r'[Rr]evert\s+"(.+)"', c.title)
            if title_match:
                original_title = title_match.group(1).strip()
                candidates = by_title.get(original_title, [])
                for other in candidates:
                    if other.number != c.number and _within_window(c.number, other.number):
                        escapes[other.number] = (f"reverted by #{c.number}", is_bot(c.author))
                        matched = True

        # When REVERT_BODY matches, extract the SHA and find the
        # original PR whose commits list contains that SHA.
        if body_match and not matched:
            reverted_sha = body_match.group(1)
            original = by_commit_sha.get(reverted_sha)
            if original is None:
                # Prefix match fallback — prefer longest overlap to avoid
                # ambiguous matches when multiple PRs share a short prefix.
                best_match: Classification | None = None
                best_prefix_len = 0
                for sha, candidate in by_commit_sha.items():
                    shorter = min(len(sha), len(reverted_sha))
                    if shorter < 7:
                        continue
                    if sha.startswith(reverted_sha) or reverted_sha.startswith(sha):
                        # Compute actual shared prefix length
                        shared = 0
                        for a, b in zip(sha, reverted_sha, strict=False):
                            if a != b:
                                break
                            shared += 1
                        if shared > best_prefix_len:
                            best_prefix_len = shared
                            best_match = candidate
                original = best_match
            if (
                original is not None
                and original.number != c.number
                and _within_window(c.number, original.number)
            ):
                escapes[original.number] = (f"reverted by #{c.number}", is_bot(c.author))

    return escapes


# ---------------------------------------------------------------------------
# Fix-follow-up detection
# ---------------------------------------------------------------------------


def _detect_fix_followups(
    classifications: list[Classification],
    excluded_files: set[str],
    window_days: int = 14,
    ticket_pattern: re.Pattern | None = None,
    verbose: bool = False,
) -> dict[int, tuple[str, EscapeConfidence]]:
    """Detect PRs that had fix follow-ups with confidence tiers.

    Returns {original_pr_number: (reason, confidence)}.

    Confidence tiers (from validation on 99 labeled pairs):
      HIGH:   Fix PR explicitly references target PR number in title/body.
              ~84% precision (19% of true fixes have this, 3% of false positives).
      MEDIUM: Same author + within 3 days + file overlap. Or ticket match.
              ~60% estimated precision.
      LOW:    File overlap only, different authors or >3 days apart.
              ~37% precision (the old CatchRate default).
    """

    # Result: {target_pr_number: (reason, confidence)}
    # Higher confidence wins if a PR is flagged by multiple signals.
    escapes: dict[int, tuple[str, EscapeConfidence]] = {}
    ec = EscapeConfidence

    def _update(target_num: int, reason: str, confidence: EscapeConfidence) -> None:
        """Update escape, keeping the highest confidence."""
        tier_rank = {ec.CONFIRMED: 4, ec.HIGH: 3, ec.MEDIUM: 2, ec.LOW: 1}
        existing = escapes.get(target_num)
        if existing is None or tier_rank[confidence] > tier_rank[existing[1]]:
            escapes[target_num] = (reason, confidence)

    # Find all fix PRs — exclude reverts (handled separately) and dep bumps.
    fix_prs = [
        c
        for c in classifications
        if is_fix_message(c.title)
        and not is_revert_message(c.title)
        and not is_dependency_change(c.title, c.author, c.files)
        and c.classification != CT.PENDING
    ]

    # Dependency PRs to skip as targets.
    dep_pr_numbers = {
        c.number for c in classifications if is_dependency_change(c.title, c.author, c.files)
    }

    # Build indexes
    merged_prs = [c for c in classifications if c.merged_at and c.classification != CT.PENDING]
    ticket_index: dict[str, list[Classification]] = defaultdict(list)
    file_index: dict[str, list[Classification]] = defaultdict(list)
    merged_times: dict[int, datetime] = {}
    by_number: dict[int, Classification] = {}

    for pr in merged_prs:
        by_number[pr.number] = pr
        if not pr.merged_at:
            continue
        t = parse_iso_datetime(pr.merged_at, context=f"PR #{pr.number} merged_at")
        if t is None:
            continue
        merged_times[pr.number] = t
        text = f"{pr.title} {pr.body}"
        for ticket in _extract_tickets(text, ticket_pattern):
            ticket_index[ticket].append(pr)
        for f in pr.files:
            if f not in excluded_files and not _is_noise_file(f):
                file_index[f].append(pr)

    for fix in fix_prs:
        fix_time = merged_times.get(fix.number)
        if fix_time is None:
            continue

        fix_text = f"{fix.title} {fix.body}"

        # --- TIER 2 (HIGH): Fix PR explicitly references a target PR number ---
        # Look for #NNN in the fix title/body
        pr_refs = re.findall(r"#(\d+)", fix_text)
        for ref_str in pr_refs:
            ref_num = int(ref_str)
            if ref_num == fix.number or ref_num in dep_pr_numbers:
                continue
            original = by_number.get(ref_num)
            if original is None:
                continue
            orig_time = merged_times.get(ref_num)
            if orig_time is None:
                continue
            if not is_within_window(orig_time, fix_time, window_days):
                continue
            # Skip backports and release PRs (validated: removes 71% of HIGH FPs)
            if _is_not_escape(fix, original):
                continue
            _update(ref_num, f"fix: #{fix.number} (explicit PR ref)", ec.HIGH)

        # --- Collect file-overlap candidates ---
        candidates_by_file: set[int] = set()
        for f in fix.files:
            if f not in excluded_files:
                for cand in file_index.get(f, []):
                    candidates_by_file.add(cand.number)

        for cand_num in candidates_by_file:
            if cand_num == fix.number or cand_num in dep_pr_numbers:
                continue
            original = by_number.get(cand_num)
            if original is None:
                continue
            orig_time = merged_times.get(cand_num)
            if orig_time is None:
                continue
            if not is_within_window(orig_time, fix_time, window_days):
                continue
            # Skip backports and release PRs
            if _is_not_escape(fix, original):
                continue
            overlap = _compute_file_overlap(fix.files, original.files, excluded_files)
            if overlap < FILE_OVERLAP_THRESHOLD:
                continue

            # Compute time delta in days
            days_delta = abs((fix_time - orig_time).total_seconds()) / 86400

            # --- TIER 3 (MEDIUM): Same author + close in time ---
            same_author = fix.author == original.author
            close_in_time = days_delta <= 3

            if same_author and close_in_time:
                _update(
                    cand_num,
                    f"fix: #{fix.number} (same author, {days_delta:.0f}d)",
                    ec.MEDIUM,
                )
            else:
                # --- TIER 4 (LOW): File overlap only ---
                _update(
                    cand_num,
                    f"fix: #{fix.number} (file overlap only, {days_delta:.0f}d)",
                    ec.LOW,
                )

        # --- Ticket cross-reference → MEDIUM confidence ---
        fix_tickets = _extract_tickets(fix_text, ticket_pattern)
        if fix_tickets:
            seen: set[int] = set()
            for ticket in fix_tickets:
                for original in ticket_index.get(ticket, []):
                    if original.number == fix.number or original.number in seen:
                        continue
                    if is_fix_message(original.title) and not is_revert_message(original.title):
                        continue
                    seen.add(original.number)
                    orig_time = merged_times.get(original.number)
                    if orig_time is None:
                        continue
                    if not is_within_window(orig_time, fix_time, window_days):
                        continue
                    if _is_not_escape(fix, original):
                        continue
                    _update(
                        original.number,
                        f"fix: #{fix.number} (ticket match)",
                        ec.MEDIUM,
                    )

    return escapes


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def detect_escapes(
    classifications: list[Classification],
    window_days: int = 14,
    ignore_files: list[str] | None = None,
    ticket_pattern: str | None = None,
    verbose: bool = False,
) -> list[Classification]:
    """Detect escapes and return updated classifications.

    Returns a new list — the original classifications are not mutated.
    """
    custom_pattern = None
    if ticket_pattern:
        # ReDoS mitigation: compile is wrapped in try/except, input is
        # truncated to _MAX_PATTERN_INPUT_LEN in _extract_tickets, and
        # _safe_findall applies a timeout to catch catastrophic backtracking.
        try:
            custom_pattern = re.compile(ticket_pattern)
        except re.error as exc:
            log("invalid-ticket-pattern", f"Cannot compile --ticket-pattern: {exc}")
            # Fall back to auto-detection
            custom_pattern = None

    # Find high-touch files to exclude
    excluded_files = _find_high_touch_files(
        classifications,
        ignore_patterns=ignore_files,
        verbose=verbose,
    )

    # Detect reverts
    revert_escapes = _detect_reverts(classifications, window_days=window_days)

    # Detect fix follow-ups (now returns confidence tiers)
    fix_escapes = _detect_fix_followups(
        classifications,
        excluded_files,
        window_days=window_days,
        ticket_pattern=custom_pattern,
        verbose=verbose,
    )

    # Merge: reverts are CONFIRMED confidence, fix-followups have their own tiers.
    # Reverts override fix reasons.
    # MEDIUM and LOW tiers are disabled — human validation on 90 labeled pairs
    # showed 30% and 17% precision respectively. Only CONFIRMED (100%) and
    # HIGH (80%) are reliable enough for the escape signal.
    all_escapes: dict[int, tuple[str, EscapeConfidence]] = {}
    for num, (reason, confidence) in fix_escapes.items():
        if confidence in (EscapeConfidence.MEDIUM, EscapeConfidence.LOW):
            continue
        all_escapes[num] = (reason, confidence)
    for num, (reason, is_bot_revert) in revert_escapes.items():
        if is_bot_revert:
            # Bot-authored reverts are automated rollbacks (machine catch),
            # not escapes. The infrastructure caught the problem.
            continue
        all_escapes[num] = (reason, EscapeConfidence.CONFIRMED)

    # Build new list — replace escaped PRs with updated copies.
    # Skip ungated and pending PRs (spec says they are excluded
    # from classification / not yet classifiable).
    result: list[Classification] = []
    for c in classifications:
        if c.number in all_escapes and c.classification not in (CT.UNGATED, CT.PENDING):
            reason, confidence = all_escapes[c.number]
            result.append(
                replace(
                    c,
                    classification=CT.ESCAPE,
                    escaped=True,
                    escape_reason=reason,
                    escape_confidence=confidence,
                )
            )
        else:
            result.append(c)

    return result
