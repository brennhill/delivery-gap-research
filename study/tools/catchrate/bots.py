"""Unified bot-detection logic for CATCHRATE."""

from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from tools.catchrate.models import PRDataLike as PRData

# Exact bot login matches (case-insensitive).
# Uses exact match to avoid false positives on human usernames
# containing bot-like substrings (e.g., "stalehouse").
BOT_LOGINS = frozenset(
    {
        "dependabot",
        "renovate",
        "greenkeeper",
        "depfu",
        "snyk-bot",
        "imgbot",
        "allcontributors",
        "dependabot-preview",
        "renovate-bot",
        "stale",
        "stale-bot",
        "auto-close",
        "auto-close-bot",
    }
)

BUILTIN_LLM_REVIEWERS = frozenset(
    {
        "copilot",
        "github-copilot",
        "coderabbitai",
        "codium-ai",
        "sourcery-ai",
        "ellipsis-dev",
        "greptile-bot",
    }
)


def is_bot(login: str, user_type: str | None = None) -> bool:
    """Return True if the user is a bot based on login and/or user type.

    Uses exact login matching (case-insensitive) plus [bot] suffix detection.
    """
    if user_type == "Bot":
        return True
    login_lower = login.lower()
    if login_lower.endswith("[bot]"):
        return True
    return login_lower in BOT_LOGINS


def build_llm_reviewer_set(custom: set[str] | None = None) -> frozenset[str]:
    """Build the combined LLM reviewer set once. Call at the top of a run."""
    if not custom:
        return BUILTIN_LLM_REVIEWERS
    return BUILTIN_LLM_REVIEWERS | frozenset(r.lower() for r in custom)


def is_bot_reviewer(
    reviewer: Mapping[str, Any],
    llm_reviewers: set[str] | frozenset[str] | None = None,
) -> bool:
    """Return True if reviewer is non-human (Bot type or LLM reviewer).

    For best performance, pass a pre-built set from build_llm_reviewer_set()
    instead of raw custom logins.
    """
    user = reviewer.get("user", {}) or {}
    user_type = user.get("type", "User")
    login = (user.get("login", "") or "").lower()

    if user_type == "Bot":
        return True

    # If caller already passed a combined set, use it directly
    if llm_reviewers is not None:
        return login in llm_reviewers

    return login in BUILTIN_LLM_REVIEWERS


def is_bot_author(pr: PRData) -> bool:
    """Return True if the PR author is a bot."""
    return is_bot(pr.author, pr.author_type)
