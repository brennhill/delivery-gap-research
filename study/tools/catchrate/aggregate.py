"""Rate computation and effectiveness aggregation for CATCHRATE."""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field

from tools.catchrate.models import Classification, ClassificationType

CT = ClassificationType


# ---------------------------------------------------------------------------
# Typed result containers
# ---------------------------------------------------------------------------


@dataclass
class Rates:
    """Typed result from compute_rates — replaces dict[str, Any]."""

    machine_catch_count: int
    human_save_count: int
    escape_count: int
    pending_count: int
    ungated_count: int
    classifiable_count: int
    total_prs: int
    machine_catch_rate: float
    human_save_rate: float
    escape_rate: float
    escapes: list[Classification] = field(default_factory=list)


@dataclass
class EffectivenessBucket:
    """Median effectiveness for a classification or size bucket."""

    median_review_cycles: float = 0.0
    median_ttm_hours: float = 0.0
    count: int = 0
    machine_catch_rate: float | None = None
    human_save_rate: float | None = None
    escape_rate: float | None = None


@dataclass
class Effectiveness:
    """Typed result from compute_effectiveness."""

    median_review_cycles: float
    median_ttm_hours: float
    by_classification: dict[ClassificationType, EffectivenessBucket] = field(default_factory=dict)
    by_size: dict[str, EffectivenessBucket] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Computation
# ---------------------------------------------------------------------------


def compute_rates(classifications: list[Classification]) -> Rates:
    """Compute the three core rates from classified PRs (single pass)."""
    counts: dict[str, int] = {
        CT.MACHINE_CATCH: 0,
        CT.HUMAN_SAVE: 0,
        CT.ESCAPE: 0,
        CT.PENDING: 0,
        CT.UNGATED: 0,
    }
    escapes: list[Classification] = []

    for c in classifications:
        counts[c.classification] += 1
        if c.classification == CT.ESCAPE:
            escapes.append(c)

    mc_count = counts[CT.MACHINE_CATCH]
    hs_count = counts[CT.HUMAN_SAVE]
    esc_count = counts[CT.ESCAPE]
    classifiable = mc_count + hs_count + esc_count

    if classifiable == 0:
        mc_rate = hs_rate = esc_rate = 0.0
    else:
        mc_rate = mc_count / classifiable
        hs_rate = hs_count / classifiable
        esc_rate = esc_count / classifiable

    return Rates(
        machine_catch_count=mc_count,
        human_save_count=hs_count,
        escape_count=esc_count,
        pending_count=counts[CT.PENDING],
        ungated_count=counts[CT.UNGATED],
        classifiable_count=classifiable,
        total_prs=len(classifications),
        machine_catch_rate=mc_rate,
        human_save_rate=hs_rate,
        escape_rate=esc_rate,
        escapes=escapes,
    )


def compute_effectiveness(
    classifications: list[Classification],
) -> Effectiveness:
    """Compute effectiveness signals: median review cycles and TTM."""

    def _median(values: list[float]) -> float:
        return statistics.median(values) if values else 0.0

    all_cycles: list[float] = []
    all_ttm: list[float] = []
    by_class: dict[str, dict[str, list[float]]] = {}
    by_size: dict[str, dict[str, list]] = {}

    for c in classifications:
        if c.classification in (CT.PENDING, CT.UNGATED):
            continue
        all_cycles.append(c.review_cycles)
        if c.time_to_merge_hours is not None:
            all_ttm.append(c.time_to_merge_hours)
        bucket = by_class.setdefault(c.classification, {"cycles": [], "ttm": []})
        bucket["cycles"].append(c.review_cycles)
        if c.time_to_merge_hours is not None:
            bucket["ttm"].append(c.time_to_merge_hours)
        size_bucket = by_size.setdefault(
            c.size_bucket, {"cycles": [], "ttm": [], "classifications": []}
        )
        size_bucket["cycles"].append(c.review_cycles)
        if c.time_to_merge_hours is not None:
            size_bucket["ttm"].append(c.time_to_merge_hours)
        size_bucket["classifications"].append(c.classification)

    by_classification: dict[ClassificationType, EffectivenessBucket] = {}
    for cls_name in (CT.MACHINE_CATCH, CT.HUMAN_SAVE, CT.ESCAPE):
        bucket = by_class.get(cls_name, {"cycles": [], "ttm": []})
        by_classification[cls_name] = EffectivenessBucket(
            median_review_cycles=_median(bucket["cycles"]),
            median_ttm_hours=round(_median(bucket["ttm"]), 1),
            count=len(bucket["cycles"]),
        )

    by_size_result: dict[str, EffectivenessBucket] = {}
    for size_name in ("small", "medium", "large"):
        bucket = by_size.get(size_name, {"cycles": [], "ttm": [], "classifications": []})
        cls_list = bucket["classifications"]
        n = len(cls_list)
        mc: float | None
        hs: float | None
        esc: float | None
        if n > 0:
            mc = sum(1 for x in cls_list if x == CT.MACHINE_CATCH) / n
            hs = sum(1 for x in cls_list if x == CT.HUMAN_SAVE) / n
            esc = sum(1 for x in cls_list if x == CT.ESCAPE) / n
        else:
            mc = hs = esc = None
        by_size_result[size_name] = EffectivenessBucket(
            count=n,
            median_review_cycles=_median(bucket["cycles"]),
            median_ttm_hours=round(_median(bucket["ttm"]), 1),
            machine_catch_rate=round(mc, 4) if mc is not None else None,
            human_save_rate=round(hs, 4) if hs is not None else None,
            escape_rate=round(esc, 4) if esc is not None else None,
        )

    return Effectiveness(
        median_review_cycles=_median(all_cycles),
        median_ttm_hours=round(_median(all_ttm), 1),
        by_classification=by_classification,
        by_size=by_size_result,
    )
