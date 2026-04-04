#!/usr/bin/env python3
"""Generate spec-signals JSON from pre-fetched PR data.

Replaces: upfront report --from-prs FILE --json OUTPUT

Usage:
    python -m tools.run_spec_signals data/prs-owner-repo.json data/spec-signals-owner-repo.json
    python -m tools.run_spec_signals data/prs-owner-repo.json  # prints to stdout
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from dataclasses import asdict
from pathlib import Path

# Add study/ to path so tools.* imports work
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.signals.sources.file import fetch_changes
from tools.spec_signals.merged_change_adapter import convert_merged_changes
from tools.spec_signals.coverage import run_coverage
from tools.spec_signals.effectiveness import (
    PRMetadata,
    compute_complexity_buckets,
    compute_effectiveness,
    compute_friction,
    detect_rework_prs,
)
from tools.spec_signals.quality import score_classifications


def run(prs_path: str, output_path: str | None = None, lookback_days: int = 365, rework_window: int = 14) -> dict:
    """Run the full spec-signals pipeline on a prs-*.json file."""
    # Load and convert
    changes = fetch_changes(prs_path)
    prs = convert_merged_changes(changes)
    repo = changes[0].repo if changes else None

    # Coverage: classify each PR as spec'd or not
    classifications = run_coverage(prs=prs, include_bots=False, include_deps=False)

    # Quality: heuristic scoring of spec'd PRs
    quality_results = score_classifications(classifications)

    # Effectiveness: detect rework signals
    signals = detect_rework_prs(prs, rework_window_days=rework_window)
    result = compute_effectiveness(classifications, signals)

    # Friction and complexity (optional enrichment)
    rework_targets = {s.target_id for s in signals}
    cls_map = {c.change_id: c.specd for c in classifications}
    pr_data = [
        PRMetadata(
            number=pr.number,
            specd=cls_map.get(str(pr.number), False),
            review_count=pr.review_count,
            created_at=pr.created_at,
            merged_at=pr.merged_at,
            lines=pr.additions + pr.deletions,
            reworked=str(pr.number) in rework_targets,
        )
        for pr in prs
        if pr.created_at is not None
    ]
    complexity = compute_complexity_buckets(pr_data)

    # Coverage summary
    total = len(classifications)
    specd = sum(1 for c in classifications if c.specd)
    pct = round(specd / total * 100) if total > 0 else 0

    # Quality summary
    if quality_results:
        scores = [qs.overall for _, qs in quality_results]
        avg_score = round(sum(scores) / len(scores))
        verdicts = dict(Counter(qs.verdict for _, qs in quality_results))
    else:
        avg_score = 0
        verdicts = {}

    # Serialize complexity buckets
    by_complexity = {}
    if complexity:
        for bucket_name, bucket in complexity.items():
            by_complexity[bucket_name] = {
                "specd_rework_rate": bucket.specd_rework_rate,
                "unspecd_rework_rate": bucket.unspecd_rework_rate,
                "specd_count": bucket.specd_count,
                "unspecd_count": bucket.unspecd_count,
            }

    # Build output (same format as upfront report --json)
    output = {
        "repo": repo,
        "lookback_days": lookback_days,
        "rework_window_days": rework_window,
        "coverage": {
            "coverage_pct": pct,
            "total_prs": total,
            "specd_prs": specd,
            "prs": [
                {
                    "number": c.pr_number,
                    "sha": c.commit_sha,
                    "title": c.title,
                    "specd": c.specd,
                    "spec_source": c.spec_source,
                    "merged_at": c.merged_at,
                }
                for c in classifications
            ],
        },
        "quality": {
            "mode": "heuristic",
            "average_score": avg_score,
            "verdicts": verdicts,
            "specs": [
                {
                    "pr_number": cls.pr_number,
                    "format": qs.format_detected,
                    "completeness": qs.completeness,
                    "ambiguity": qs.ambiguity,
                    "testability": qs.testability,
                    "consistency": qs.consistency,
                    "overall": qs.overall,
                    "verdict": qs.verdict,
                    "issues": [asdict(i) for i in qs.issues],
                    "warnings": qs.warnings,
                }
                for cls, qs in quality_results
            ],
        },
        "effectiveness": {
            "specd_rework_rate": result.specd_rework_rate,
            "unspecd_rework_rate": result.unspecd_rework_rate,
            "delta": result.delta,
            "specd_sample_size": result.specd_sample_size,
            "unspecd_sample_size": result.unspecd_sample_size,
            "significance": result.significance,
            "signals": [
                {
                    "type": s.type,
                    "source": s.source_id,
                    "target": s.target_id,
                    "classification": s.classification,
                    "overlapping_files": s.overlapping_files,
                }
                for s in result.signals
            ],
            "by_complexity": by_complexity,
        },
    }

    if output_path:
        Path(output_path).write_text(json.dumps(output, indent=2), encoding="utf-8")
        print(f"Wrote {output_path}", file=sys.stderr)

    return output


def main():
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <prs-*.json> [output.json]", file=sys.stderr)
        sys.exit(1)

    prs_path = sys.argv[1]
    output_path = sys.argv[2] if len(sys.argv) > 2 else None
    result = run(prs_path, output_path)

    if not output_path:
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
