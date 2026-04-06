#!/usr/bin/env python3

"""Locked quality-tier thresholds for q_overall on the fixed master dataset."""

from math import isnan


LOCKED_TOP_QUARTILE_CUTOFF = 58.0
LOCKED_TOP_DECILE_CUTOFF = 66.0

BOTTOM_75 = "BOTTOM75"
TOP_25_ONLY = "TOP25_ONLY"
TOP_10 = "TOP10"
UNSCORED = "UNSCORED"

TIER_ORDER = [BOTTOM_75, TOP_25_ONLY, TOP_10]
TIER_DISPLAY = {
    BOTTOM_75: f"Bottom 75% (<{LOCKED_TOP_QUARTILE_CUTOFF:.0f})",
    TOP_25_ONLY: f"P75-P89 (>={LOCKED_TOP_QUARTILE_CUTOFF:.0f}, <{LOCKED_TOP_DECILE_CUTOFF:.0f})",
    TOP_10: f"Top 10% (>={LOCKED_TOP_DECILE_CUTOFF:.0f})",
}


def _is_missing(value) -> bool:
    if value is None:
        return True
    try:
        return isnan(value)
    except TypeError:
        return False


def is_top_quartile(score) -> bool:
    return not _is_missing(score) and float(score) >= LOCKED_TOP_QUARTILE_CUTOFF


def is_top_decile(score) -> bool:
    return not _is_missing(score) and float(score) >= LOCKED_TOP_DECILE_CUTOFF


def quality_tier(score):
    if _is_missing(score):
        return UNSCORED
    score = float(score)
    if score >= LOCKED_TOP_DECILE_CUTOFF:
        return TOP_10
    if score >= LOCKED_TOP_QUARTILE_CUTOFF:
        return TOP_25_ONLY
    return BOTTOM_75
