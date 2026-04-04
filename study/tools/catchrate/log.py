"""Structured logging for CATCHRATE.

All modules use log() and warn() instead of print(file=sys.stderr).
Centralizes output format, enables quiet mode, and makes credential
filtering possible in one place.
"""

from __future__ import annotations

import sys

_quiet = False


def set_quiet(quiet: bool) -> None:
    """Enable/disable quiet mode. When quiet, data-warnings are suppressed."""
    global _quiet
    _quiet = quiet


def warn(message: str) -> None:
    """Log a [data-warning]. Suppressed in quiet mode."""
    if not _quiet:
        print(f"[data-warning] {message}", file=sys.stderr)


def log(tag: str, message: str) -> None:
    """Log a tagged message to stderr. Never suppressed."""
    print(f"[{tag}] {message}", file=sys.stderr)
