#!/usr/bin/env python3
"""Generate catchrate JSON from pre-fetched PR data.

Replaces: catchrate check --from-prs FILE --json OUTPUT

Usage:
    python -m tools.run_catchrate data/prs-owner-repo.json data/catchrate-owner-repo.json
    python -m tools.run_catchrate data/prs-owner-repo.json  # prints to stdout
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add study/ to path so tools.* imports work
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.signals.sources.file import fetch_changes
from tools.catchrate.convert import merged_changes_to_prdata
from tools.catchrate.classify import classify_all
from tools.catchrate.rework import detect_escapes
from tools.catchrate.aggregate import compute_rates, compute_effectiveness
from tools.catchrate.models import AnalysisConfig, CatchrateResult
from tools.catchrate.report import render_json


def run(prs_path: str, output_path: str | None = None, lookback: int = 365, window_days: int = 14) -> dict:
    """Run the full catchrate pipeline on a prs-*.json file."""
    # Load and convert
    changes = fetch_changes(prs_path)
    if not changes:
        print(f"No changes found in {prs_path}", file=sys.stderr)
        return {}

    pr_data_list = merged_changes_to_prdata(changes)
    repo = changes[0].repo or "unknown/repo"
    now = datetime.now(timezone.utc)

    # Classify
    config = AnalysisConfig(window_days=window_days)
    classifications = classify_all(
        pr_data_list,
        window_days=config.window_days,
        include_bots=False,
        include_deps=False,
        now=now,
    )

    # Detect escapes
    classifications = detect_escapes(
        classifications,
        window_days=config.window_days,
    )

    # Compute rates and effectiveness
    rates = compute_rates(classifications)
    effectiveness = compute_effectiveness(classifications)

    # Build result
    result = CatchrateResult(
        repo=repo,
        lookback_days=lookback,
        window_days=window_days,
        rates=rates,
        classifications=classifications,
        effectiveness=effectiveness,
    )

    # Render JSON
    json_str = render_json(result)
    output = json.loads(json_str)

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
