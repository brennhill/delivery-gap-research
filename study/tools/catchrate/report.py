"""Terminal, JSON, HTML, CSV output for CATCHRATE."""

from __future__ import annotations

import csv
import html
import io
import json
import math
import sys
from typing import Any

from tools.catchrate.aggregate import Effectiveness, EffectivenessBucket
from tools.catchrate.log import log as _log
from tools.catchrate.models import CatchrateResult, ClassificationType

CT = ClassificationType


# ---------------------------------------------------------------------------
# Classification warnings
# ---------------------------------------------------------------------------


def emit_warnings(ctx: CatchrateResult) -> None:
    """Emit classification warnings to stderr."""
    rates = ctx.rates
    mc_rate = rates.machine_catch_rate
    hs_rate = rates.human_save_rate
    classifiable = rates.classifiable_count
    total = rates.total_prs
    ungated = rates.ungated_count
    pending = rates.pending_count

    # Rubber-stamping warning
    mc_is_one = math.isclose(mc_rate, 1.0, abs_tol=1e-9)
    hs_is_zero = math.isclose(hs_rate, 0.0, abs_tol=1e-9)
    if classifiable > 0 and mc_is_one and hs_is_zero:
        _log(
            "review-quality-warning",
            "100% machine catch rate with 0% human save rate.\n"
            "This could mean gates are excellent — or that code review "
            "is rubber-stamping.\nIf escape rate is also 0%, consider "
            "whether the lookback period is long enough to observe escapes.",
        )

    # Low gate coverage
    if total > 0 and ungated > 0:
        pct = ungated / total * 100
        if pct > 20:
            _log(
                "low-gate-coverage",
                f"{ungated}/{total} PRs ({pct:.0f}%) "
                "have no CI checks configured.\n"
                "These PRs are excluded from rates. Pipeline "
                "trustworthiness measurement is limited without "
                "gate coverage.",
            )

    # High pending rate
    if total > 0 and pending > 0:
        pct = pending / total * 100
        if pct > 50:
            _log(
                "high-pending-rate",
                f"{pending}/{total} PRs ({pct:.0f}%) "
                "are still in the observation window "
                "and not yet classifiable.\n"
                f"Rates are based on only {classifiable} PRs. "
                "Consider a longer lookback: --lookback 180.",
            )


# ---------------------------------------------------------------------------
# Terminal output
# ---------------------------------------------------------------------------


def render_terminal(ctx: CatchrateResult) -> str:
    """Render terminal output string."""
    rates = ctx.rates
    trend = ctx.trend

    lines: list[str] = []

    if ctx.partial:
        lines.append(
            "\u26a0 PARTIAL RESULTS \u2014 rate limited. "
            "Rates below may not reflect the full period.\n"
        )

    lines.append(
        f"Pipeline Trustworthiness: {ctx.repo} "
        f"({ctx.lookback_days} days, {ctx.window_days}-day window)\n"
    )

    classifiable = rates.classifiable_count
    mc = rates.machine_catch_count
    hs = rates.human_save_count
    esc = rates.escape_count
    mc_rate = rates.machine_catch_rate
    hs_rate = rates.human_save_rate
    esc_rate = rates.escape_rate

    def _fmt_rate(rate: float) -> str:
        return f"{rate * 100:.0f}%"

    def _trend_delta(key: str, current: float) -> str:
        if trend is None:
            return ""
        prev = trend.get(key)
        if prev is None:
            return ""
        delta = (current - prev) * 100
        sign = "+" if delta >= 0 else ""
        return f"  ({sign}{delta:.0f}pp)"

    mc_trend = _trend_delta("machine_catch_rate", mc_rate)
    hs_trend = _trend_delta("human_save_rate", hs_rate)
    esc_trend = _trend_delta("escape_rate", esc_rate)

    lines.append(
        f"  Machine catch rate:  {_fmt_rate(mc_rate):>4}  "
        f"({mc}/{classifiable})  "
        f"\u2014 gates + review got it right{mc_trend}"
    )
    lines.append(
        f"  Human save rate:     {_fmt_rate(hs_rate):>4}  "
        f"({hs}/{classifiable})  "
        f"\u2014 reviewers caught what gates missed{hs_trend}"
    )
    lines.append(
        f"  Escape rate:         {_fmt_rate(esc_rate):>4}  "
        f"({esc}/{classifiable})  "
        f"\u2014 nobody caught it{esc_trend}"
    )

    lines.append("")
    lines.append(
        f"  Pending:  {rates.pending_count} PRs "
        f"(< {ctx.window_days} days old, not yet classifiable)"
    )
    lines.append(f"  Ungated:  {rates.ungated_count} PRs (no CI checks configured)")

    # Escapes detail
    escapes = rates.escapes
    if escapes:
        lines.append("")
        lines.append("  Escapes:")
        for e in escapes:
            lines.append(f"    #{e.number}  {e.title}     {e.escape_reason}")

    # Discard rate
    discard = ctx.discard
    if discard is not None:
        lines.append("")
        rate_str = _fmt_rate(discard.discard_rate)
        lines.append(
            f"  Discard rate:  {rate_str}  "
            f"({discard.discarded_prs}/{discard.total_opened_prs})  "
            f"\u2014 PRs closed without merging"
        )

    # Effectiveness signals
    eff = ctx.effectiveness
    _empty = EffectivenessBucket()
    mc_eff = eff.by_classification.get(CT.MACHINE_CATCH, _empty)
    hs_eff = eff.by_classification.get(CT.HUMAN_SAVE, _empty)
    esc_eff = eff.by_classification.get(CT.ESCAPE, _empty)
    lines.append("")
    lines.append("  Effectiveness:")
    lines.append(
        f"    Median review cycles:  {eff.median_review_cycles:.0f}"
        f"  (machine_catch: {mc_eff.median_review_cycles:.0f},"
        f" human_save: {hs_eff.median_review_cycles:.0f},"
        f" escape: {esc_eff.median_review_cycles:.0f})"
    )
    lines.append(
        f"    Median time to merge:  {eff.median_ttm_hours:.0f}h"
        f"  (machine_catch: {mc_eff.median_ttm_hours:.0f}h,"
        f" human_save: {hs_eff.median_ttm_hours:.0f}h,"
        f" escape: {esc_eff.median_ttm_hours:.0f}h)"
    )

    # Effectiveness by size
    size_labels = [
        ("small", "Small  (<100 lines)"),
        ("medium", "Medium (100-499)"),
        ("large", "Large  (500+)"),
    ]
    has_any_size = any(eff.by_size.get(s, _empty).count > 0 for s, _ in size_labels)
    if has_any_size:
        lines.append("")
        lines.append("  Effectiveness by size:")
        for size_key, label in size_labels:
            s = eff.by_size.get(size_key, _empty)
            if s.count > 0:
                lines.append(
                    f"    {label}:   "
                    f"{s.median_review_cycles:.0f} review cycles, "
                    f"{s.median_ttm_hours:.0f}h TTM  "
                    f"({s.count} PRs)"
                )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# JSON output
# ---------------------------------------------------------------------------


def render_json(ctx: CatchrateResult) -> str:
    """Render JSON output string."""
    rates = ctx.rates
    classifications = ctx.classifications

    data: dict[str, Any] = {
        "repo": ctx.repo,
        "lookback_days": ctx.lookback_days,
        "window_days": ctx.window_days,
        "total_prs": rates.total_prs,
        "classifiable_prs": rates.classifiable_count,
        "pending_prs": rates.pending_count,
        "machine_catch_rate": round(rates.machine_catch_rate, 4),
        "human_save_rate": round(rates.human_save_rate, 4),
        "escape_rate": round(rates.escape_rate, 4),
        "ungated_prs": rates.ungated_count,
    }

    if ctx.partial:
        data["partial"] = True

    if ctx.no_discard:
        data["discard_rate"] = "disabled"
    elif ctx.discard is not None:
        data["discard_rate"] = round(ctx.discard.discard_rate, 4)
        data["discarded_prs"] = ctx.discard.discarded_prs
        data["total_opened_prs"] = ctx.discard.total_opened_prs
    else:
        # Discard was enabled but fetch failed — signal with null
        data["discard_rate"] = None

    data["prs"] = [
        {
            "number": c.number,
            "title": c.title,
            "classification": c.classification,
            "ci_status": c.ci_status,
            "review_modified": c.review_modified,
            "escaped": c.escaped,
            "escape_reason": c.escape_reason,
            "escape_confidence": c.escape_confidence.value if c.escape_confidence else None,
            "merged_at": c.merged_at,
            "review_cycles": c.review_cycles,
            "time_to_merge_hours": (
                round(c.time_to_merge_hours, 1) if c.time_to_merge_hours is not None else None
            ),
            "lines_changed": c.lines_changed,
            "size_bucket": c.size_bucket,
        }
        for c in classifications
    ]

    eff = ctx.effectiveness
    data["effectiveness"] = {
        "median_review_cycles": eff.median_review_cycles,
        "median_ttm_hours": eff.median_ttm_hours,
        "by_classification": {
            k.value: {
                "median_review_cycles": v.median_review_cycles,
                "median_ttm_hours": v.median_ttm_hours,
            }
            for k, v in eff.by_classification.items()
        },
        "by_size": {
            k: {
                "count": v.count,
                "median_review_cycles": v.median_review_cycles,
                "median_ttm_hours": v.median_ttm_hours,
                "machine_catch_rate": v.machine_catch_rate,
                "human_save_rate": v.human_save_rate,
                "escape_rate": v.escape_rate,
            }
            for k, v in eff.by_size.items()
        },
    }

    return json.dumps(data, indent=2)


# ---------------------------------------------------------------------------
# HTML output
# ---------------------------------------------------------------------------


def render_html(ctx: CatchrateResult) -> str:
    """Render HTML report string. All user content is escaped."""
    rates = ctx.rates
    classifications = ctx.classifications
    trend = ctx.trend
    discard = ctx.discard

    e = html.escape
    mc_rate = rates.machine_catch_rate
    hs_rate = rates.human_save_rate
    esc_rate = rates.escape_rate
    classifiable = rates.classifiable_count

    def pct(val: float) -> str:
        return f"{val * 100:.1f}%"

    def _trend_html(key: str, current: float) -> str:
        if trend is None:
            return ""
        prev = trend.get(key)
        if prev is None:
            return ""
        delta = (current - prev) * 100
        sign = "+" if delta >= 0 else ""
        if key == "machine_catch_rate":
            color = "green" if delta >= 0 else "red"
        elif key in ("human_save_rate", "escape_rate"):
            color = "green" if delta <= 0 else "red"
        else:
            color = "red"
        return f' <span style="color:{color}">({sign}{delta:.0f}pp)</span>'

    escapes_html = ""
    escapes = rates.escapes
    if escapes:
        rows = ""
        for esc in escapes:
            rows += (
                f"<tr><td>#{esc.number}</td>"
                f"<td>{e(esc.title)}</td>"
                f"<td>{e(esc.escape_reason)}</td></tr>\n"
            )
        escapes_html = f"""
    <h3>Escapes</h3>
    <table border="1" cellpadding="4" cellspacing="0">
      <tr><th>PR</th><th>Title</th><th>Reason</th></tr>
      {rows}
    </table>"""

    discard_html = ""
    if discard is not None:
        dr_pct = pct(discard.discard_rate)
        dr_n = f"{discard.discarded_prs}/{discard.total_opened_prs}"
        discard_html = f"""
    <h3>Discard Rate</h3>
    <p>{dr_pct} ({dr_n}) &mdash; PRs closed without merging</p>"""

    partial_html = ""
    if ctx.partial:
        partial_html = (
            '<p style="color:orange;font-weight:bold;">'
            "&#9888; PARTIAL RESULTS &mdash; rate limited.</p>"
        )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>CATCHRATE Report: {e(ctx.repo)}</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont,
        'Segoe UI', Roboto, sans-serif;
      max-width: 800px; margin: 40px auto;
      padding: 0 20px; color: #333;
    }}
    h1 {{ border-bottom: 2px solid #333; padding-bottom: 8px; }}
    .rate {{ font-size: 2em; font-weight: bold; margin: 0; }}
    .rate-label {{ color: #666; margin-bottom: 16px; }}
    .rates {{ display: flex; gap: 40px; margin: 20px 0; }}
    .rate-card {{ text-align: center; }}
    table {{ border-collapse: collapse; width: 100%; margin-top: 10px; }}
    th {{ background: #f5f5f5; text-align: left; }}
    td, th {{ padding: 6px 10px; }}
    .meta {{ color: #888; font-size: 0.9em; }}
  </style>
</head>
<body>
  <h1>Pipeline Trustworthiness: {e(ctx.repo)}</h1>
  <p class="meta">{ctx.lookback_days} days, {ctx.window_days}-day window |
    {classifiable} classifiable PRs</p>
  {partial_html}
  <div class="rates">
    <div class="rate-card">
      <p class="rate">{pct(mc_rate)}{_trend_html("machine_catch_rate", mc_rate)}</p>
      <p class="rate-label">Machine Catch Rate</p>
    </div>
    <div class="rate-card">
      <p class="rate">{pct(hs_rate)}{_trend_html("human_save_rate", hs_rate)}</p>
      <p class="rate-label">Human Save Rate</p>
    </div>
    <div class="rate-card">
      <p class="rate">{pct(esc_rate)}{_trend_html("escape_rate", esc_rate)}</p>
      <p class="rate-label">Escape Rate</p>
    </div>
  </div>

  <p>Pending: {rates.pending_count} PRs | Ungated: {rates.ungated_count} PRs</p>
  {escapes_html}
  {discard_html}

  <hr>
  <h3>PR Classifications</h3>
  <table border="1" cellpadding="4" cellspacing="0">
    <tr><th>PR</th><th>Title</th><th>Classification</th><th>CI Status</th><th>Merged</th></tr>
    {
        "".join(
            f"<tr><td>#{c.number}</td><td>{e(c.title)}</td><td>{e(c.classification)}</td>"
            f"<td>{e(c.ci_status)}</td><td>{e(c.merged_at or '')}</td></tr>"
            for c in classifications
        )
    }
  </table>

  {_render_html_effectiveness(ctx.effectiveness)}
  <footer style="margin-top:30px;color:#aaa;font-size:0.8em;">
    Generated by CATCHRATE
  </footer>
</body>
</html>"""


def _render_html_effectiveness(eff: Effectiveness) -> str:
    """Render effectiveness section for HTML report."""
    _empty = EffectivenessBucket()
    mc_eff = eff.by_classification.get(CT.MACHINE_CATCH, _empty)
    hs_eff = eff.by_classification.get(CT.HUMAN_SAVE, _empty)
    esc_eff = eff.by_classification.get(CT.ESCAPE, _empty)
    return f"""
  <hr>
  <h3>Effectiveness</h3>
  <table border="1" cellpadding="4" cellspacing="0">
    <tr><th>Metric</th><th>Overall</th><th>Machine Catch</th>
        <th>Human Save</th><th>Escape</th></tr>
    <tr><td>Median Review Cycles</td>
        <td>{eff.median_review_cycles:.0f}</td>
        <td>{mc_eff.median_review_cycles:.0f}</td>
        <td>{hs_eff.median_review_cycles:.0f}</td>
        <td>{esc_eff.median_review_cycles:.0f}</td></tr>
    <tr><td>Median TTM (hours)</td>
        <td>{eff.median_ttm_hours:.0f}</td>
        <td>{mc_eff.median_ttm_hours:.0f}</td>
        <td>{hs_eff.median_ttm_hours:.0f}</td>
        <td>{esc_eff.median_ttm_hours:.0f}</td></tr>
  </table>"""


# ---------------------------------------------------------------------------
# CSV output
# ---------------------------------------------------------------------------


def render_csv(ctx: CatchrateResult) -> str:
    """Render CSV output string."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "number",
            "title",
            "classification",
            "ci_status",
            "review_modified",
            "escaped",
            "escape_reason",
            "merged_at",
            "review_cycles",
            "time_to_merge_hours",
            "lines_changed",
            "size_bucket",
        ]
    )
    for c in ctx.classifications:
        writer.writerow(
            [
                c.number,
                c.title,
                c.classification,
                c.ci_status,
                c.review_modified,
                c.escaped,
                c.escape_reason,
                c.merged_at or "",
                c.review_cycles,
                round(c.time_to_merge_hours, 1) if c.time_to_merge_hours is not None else "",
                c.lines_changed,
                c.size_bucket,
            ]
        )
    return output.getvalue()


# ---------------------------------------------------------------------------
# Trend comparison
# ---------------------------------------------------------------------------


def render_trend(
    ctx: CatchrateResult,
    previous: dict[str, Any],
) -> str:
    """Render trend comparison string."""
    lines: list[str] = []
    lines.append(f"Trend comparison for {ctx.repo}:\n")

    rates = ctx.rates
    for current, prev_key, label in [
        (rates.machine_catch_rate, "machine_catch_rate", "Machine catch rate"),
        (rates.human_save_rate, "human_save_rate", "Human save rate"),
        (rates.escape_rate, "escape_rate", "Escape rate"),
    ]:
        prev = previous.get(prev_key, 0)
        delta = (current - prev) * 100
        sign = "+" if delta >= 0 else ""
        lines.append(
            f"  {label}: {prev * 100:.0f}% \u2192 {current * 100:.0f}% ({sign}{delta:.0f}pp)"
        )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Write helpers
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Renderer registry
# ---------------------------------------------------------------------------

# Maps format name → (renderer_function, file_extension).
# To add a new format, register it here — no changes needed in cli.py.
RENDERERS: dict[str, tuple[Any, str]] = {
    "json": (render_json, ".json"),
    "html": (render_html, ".html"),
    "csv": (render_csv, ".csv"),
}


def write_output(path: str, content: str) -> None:
    """Write content to a file, with error handling."""
    import os

    parent = os.path.dirname(os.path.abspath(path))
    if not os.path.isdir(parent):
        _log(
            "output-dir-missing",
            f'Cannot write to "{path}": directory "{parent}" does not exist.',
        )
        sys.exit(2)

    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
    except PermissionError:
        _log(
            "output-write-failed",
            f'Cannot write to "{path}": permission denied.\nCheck file permissions and try again.',
        )
        sys.exit(2)
