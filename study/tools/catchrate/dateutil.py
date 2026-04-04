"""Shared ISO-8601 datetime parsing and time window utilities for CATCHRATE."""

from __future__ import annotations

from datetime import datetime, timedelta

from tools.catchrate.log import warn


def parse_iso_datetime(value: str, context: str = "") -> datetime | None:
    """Parse an ISO-8601 datetime string, handling the Z suffix.

    Returns None on empty/invalid input and logs a [data-warning] with the
    context string when parsing fails.
    """
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        ctx = f" ({context})" if context else ""
        warn(f'Could not parse datetime "{value}"{ctx}.')
        return None


def is_within_window(reference: datetime, event: datetime, window_days: int) -> bool:
    """Check if event occurred within window_days after reference.

    Uses continuous timedelta comparison (not .days truncation) for
    consistent boundary behavior across all callers.
    Both datetimes must be timezone-aware or both naive.
    """
    if (reference.tzinfo is None) != (event.tzinfo is None):
        raise TypeError(
            "Cannot compare tz-aware and tz-naive datetimes in "
            "is_within_window. Both must be tz-aware or both naive."
        )
    delta = event - reference
    return timedelta(0) <= delta <= timedelta(days=window_days)
