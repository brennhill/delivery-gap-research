#!/usr/bin/env python3

from __future__ import annotations

import numpy as np


def bonferroni_adjust(p_values):
    """Return Bonferroni-adjusted p-values for a family of tests."""
    p = np.asarray(p_values, dtype=float)
    adjusted = np.clip(p * len(p), 0.0, 1.0)
    return adjusted.tolist()


def benjamini_hochberg_qvalues(p_values):
    """Return Benjamini-Hochberg FDR q-values."""
    p = np.asarray(p_values, dtype=float)
    n = len(p)
    order = np.argsort(p)
    ranked = p[order]
    adjusted_ranked = ranked * n / np.arange(1, n + 1)
    adjusted_ranked = np.minimum.accumulate(adjusted_ranked[::-1])[::-1]
    adjusted_ranked = np.clip(adjusted_ranked, 0.0, 1.0)
    adjusted = np.empty_like(adjusted_ranked)
    adjusted[order] = adjusted_ranked
    return adjusted.tolist()
