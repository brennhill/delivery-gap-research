#!/usr/bin/env python3
"""Aggregate UPFRONT and CATCHRATE JSON outputs into summary tables.

Reads JSON files from data/ and produces:
  - results/summary.json        — cross-repo aggregate statistics
  - results/per-repo-summary.csv
  - results/per-pr-detail.csv
  - results/complexity-bucketed.csv
  - results/cross-repo-hypotheses.csv

Usage:
    python aggregate.py
"""

from __future__ import annotations

import csv
import json
import statistics
import sys
from pathlib import Path

STUDY_DIR = Path(__file__).resolve().parent
DATA_DIR = STUDY_DIR / "data"
RESULTS_DIR = STUDY_DIR / "results"

# Repo metadata derived from runner.py's REPOS list (single source of truth)
from runner import REPOS as _RUNNER_REPOS

REPO_META: dict[str, dict[str, str]] = {
    r["repo"]: {"lang": r["lang"], "tier": r["tier"]}
    for r in _RUNNER_REPOS
}


def _slug(repo: str) -> str:
    return repo.replace("/", "-")


def _safe_pct(num: float | None, digits: int = 1) -> str:
    if num is None:
        return ""
    return f"{num * 100:.{digits}f}"


def _safe_float(val: float | None, digits: int = 1) -> str:
    if val is None:
        return ""
    return f"{val:.{digits}f}"


def _median(values: list[float]) -> float | None:
    if not values:
        return None
    return statistics.median(values)


# ── Loaders ──────────────────────────────────────────────────────────────


def load_spec_signals(repo: str) -> dict | None:
    path = DATA_DIR / f"spec-signals-{_slug(repo)}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        print(f"Warning: could not load {path}: {e}", file=sys.stderr)
        return None


def load_catchrate(repo: str) -> dict | None:
    path = DATA_DIR / f"catchrate-{_slug(repo)}.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        print(f"Warning: could not load {path}: {e}", file=sys.stderr)
        return None


# ── Per-repo summary row ─────────────────────────────────────────────────


def build_repo_row(repo: str, spec_signals: dict | None, catchrate: dict | None) -> dict:
    """Build one row for per-repo-summary.csv."""
    meta = REPO_META.get(repo, {"lang": "unknown", "tier": "?"})
    row: dict = {
        "repo": repo,
        "language": meta["lang"],
        "tier": meta["tier"],
        "spec_coverage_pct": None,
        "machine_catch_rate_pct": None,
        "human_save_rate_pct": None,
        "escape_rate_pct": None,
        "median_review_cycles": None,
        "median_ttm_hours": None,
        "rework_rate_specd": None,
        "rework_rate_unspecd": None,
    }

    if spec_signals:
        cov = spec_signals.get("coverage", {})
        row["spec_coverage_pct"] = cov.get("coverage_pct")

        eff = spec_signals.get("effectiveness", {})
        row["rework_rate_specd"] = eff.get("specd_rework_rate")
        row["rework_rate_unspecd"] = eff.get("unspecd_rework_rate")

    if catchrate:
        row["machine_catch_rate_pct"] = catchrate.get("machine_catch_rate")
        row["human_save_rate_pct"] = catchrate.get("human_save_rate")
        row["escape_rate_pct"] = catchrate.get("escape_rate")

        eff = catchrate.get("effectiveness", {})
        row["median_review_cycles"] = eff.get("median_review_cycles")
        row["median_ttm_hours"] = eff.get("median_ttm_hours")

    return row


# ── Per-PR detail rows ───────────────────────────────────────────────────


def build_pr_rows(repo: str, spec_signals: dict | None, catchrate: dict | None) -> list[dict]:
    """Build per-PR rows combining UPFRONT and CATCHRATE data."""
    rows: list[dict] = []

    # Build lookup of UPFRONT spec classifications by PR number
    specd_map: dict[int, bool] = {}
    if spec_signals:
        for pr in spec_signals.get("coverage", {}).get("prs", []):
            num = pr.get("number")
            if num is not None:
                specd_map[num] = pr.get("specd", False)

    # Build lookup of UPFRONT rework signals by target PR
    rework_targets: set[int] = set()
    if spec_signals:
        for sig in spec_signals.get("effectiveness", {}).get("signals", []):
            target = sig.get("target")
            if target is not None:
                rework_targets.add(target)

    # Use CATCHRATE PR-level data as the primary source (it has classification,
    # lines_changed, size_bucket, review_cycles, TTM)
    if catchrate:
        for pr in catchrate.get("prs", []):
            num = pr.get("number")
            specd = specd_map.get(num)  # None if UPFRONT data missing for this PR
            rows.append({
                "repo": repo,
                "pr_number": num,
                "title": pr.get("title", ""),
                "specd": _bool_str(specd),
                "classification": pr.get("classification", ""),
                "lines_changed": pr.get("lines_changed"),
                "size_bucket": pr.get("size_bucket", ""),
                "review_cycles": pr.get("review_cycles"),
                "ttm_hours": pr.get("time_to_merge_hours"),
                "rework": "yes" if num in rework_targets else "no",
                "merged_at": pr.get("merged_at", ""),
            })
    elif spec_signals:
        # Fallback: use UPFRONT PRs if no CATCHRATE data
        for pr in spec_signals.get("coverage", {}).get("prs", []):
            num = pr.get("number")
            rows.append({
                "repo": repo,
                "pr_number": num,
                "title": pr.get("title", ""),
                "specd": _bool_str(pr.get("specd")),
                "classification": "",
                "lines_changed": None,
                "size_bucket": "",
                "review_cycles": None,
                "ttm_hours": None,
                "rework": "yes" if num in rework_targets else "no",
                "merged_at": pr.get("merged_at", ""),
            })

    return rows


def _bool_str(val: bool | None) -> str:
    if val is None:
        return ""
    return "yes" if val else "no"


# ── Complexity-bucketed rows ─────────────────────────────────────────────


def build_complexity_rows(
    repo: str,
    spec_signals: dict | None,
    catchrate: dict | None,
) -> list[dict]:
    """Build per-(repo, size_bucket, spec_status) rows with aggregates.

    Uses CATCHRATE PR data for size buckets and review metrics,
    cross-referenced with UPFRONT spec classification.
    """
    if not catchrate:
        return []

    # Build spec lookup from UPFRONT
    specd_map: dict[int, bool] = {}
    if spec_signals:
        for pr in spec_signals.get("coverage", {}).get("prs", []):
            num = pr.get("number")
            if num is not None:
                specd_map[num] = pr.get("specd", False)

    # Build rework lookup from UPFRONT
    rework_targets: set[int] = set()
    if spec_signals:
        for sig in spec_signals.get("effectiveness", {}).get("signals", []):
            target = sig.get("target")
            if target is not None:
                rework_targets.add(target)

    # Group PRs by (size_bucket, spec_status)
    groups: dict[tuple[str, str], list[dict]] = {}
    for pr in catchrate.get("prs", []):
        num = pr.get("number")
        bucket = pr.get("size_bucket", "unknown")
        specd = specd_map.get(num)
        spec_status = "specd" if specd else ("unspecd" if specd is not None else "unknown")

        key = (bucket, spec_status)
        if key not in groups:
            groups[key] = []
        groups[key].append({
            "rework": num in rework_targets,
            "review_cycles": pr.get("review_cycles"),
            "ttm_hours": pr.get("time_to_merge_hours"),
        })

    rows: list[dict] = []
    for (bucket, spec_status), prs in sorted(groups.items()):
        count = len(prs)
        rework_count = sum(1 for p in prs if p["rework"])
        rework_rate = rework_count / count if count > 0 else None

        cycles = [p["review_cycles"] for p in prs if p["review_cycles"] is not None]
        ttms = [p["ttm_hours"] for p in prs if p["ttm_hours"] is not None]

        rows.append({
            "repo": repo,
            "size_bucket": bucket,
            "spec_status": spec_status,
            "count": count,
            "rework_count": rework_count,
            "rework_rate": rework_rate,
            "median_review_cycles": _median(cycles),
            "median_ttm_hours": _median(ttms),
        })

    return rows


# ── Cross-repo hypothesis testing ────────────────────────────────────────


def build_hypothesis_rows(all_complexity: list[dict]) -> list[dict]:
    """Test four hypotheses within each size bucket across all repos.

    Hypotheses (from the SSRN paper):
    H1: Spec'd PRs have lower rework rates than unspec'd PRs
    H2: The rework gap widens with complexity (larger PRs)
    H3: Spec'd PRs have fewer review cycles
    H4: Spec'd PRs have shorter time-to-merge
    """
    # Group by size_bucket across all repos
    bucket_data: dict[str, dict[str, list[dict]]] = {}
    for row in all_complexity:
        bucket = row["size_bucket"]
        spec_status = row["spec_status"]
        if spec_status not in ("specd", "unspecd"):
            continue
        if bucket not in bucket_data:
            bucket_data[bucket] = {"specd": [], "unspecd": []}
        bucket_data[bucket][spec_status].append(row)

    rows: list[dict] = []
    bucket_rework_deltas: dict[str, float | None] = {}

    for bucket in ["small", "medium", "large"]:
        if bucket not in bucket_data:
            rows.append({
                "size_bucket": bucket,
                "hypothesis": "H1-H4",
                "specd_repos": 0,
                "unspecd_repos": 0,
                "specd_total_prs": 0,
                "unspecd_total_prs": 0,
                "specd_rework_rate": None,
                "unspecd_rework_rate": None,
                "rework_delta_pp": None,
                "specd_median_review_cycles": None,
                "unspecd_median_review_cycles": None,
                "specd_median_ttm_hours": None,
                "unspecd_median_ttm_hours": None,
            })
            bucket_rework_deltas[bucket] = None
            continue

        bd = bucket_data[bucket]
        specd_rows = bd.get("specd", [])
        unspecd_rows = bd.get("unspecd", [])

        specd_total = sum(r["count"] for r in specd_rows)
        unspecd_total = sum(r["count"] for r in unspecd_rows)

        specd_rework_total = sum(r["rework_count"] for r in specd_rows)
        unspecd_rework_total = sum(r["rework_count"] for r in unspecd_rows)

        specd_rework_rate = specd_rework_total / specd_total if specd_total > 0 else None
        unspecd_rework_rate = unspecd_rework_total / unspecd_total if unspecd_total > 0 else None

        if specd_rework_rate is not None and unspecd_rework_rate is not None:
            delta = (specd_rework_rate - unspecd_rework_rate) * 100
        else:
            delta = None
        bucket_rework_deltas[bucket] = delta

        # Aggregate review cycles and TTM across repos
        specd_cycles = [r["median_review_cycles"] for r in specd_rows
                        if r["median_review_cycles"] is not None]
        unspecd_cycles = [r["median_review_cycles"] for r in unspecd_rows
                          if r["median_review_cycles"] is not None]
        specd_ttm = [r["median_ttm_hours"] for r in specd_rows
                     if r["median_ttm_hours"] is not None]
        unspecd_ttm = [r["median_ttm_hours"] for r in unspecd_rows
                       if r["median_ttm_hours"] is not None]

        rows.append({
            "size_bucket": bucket,
            "hypothesis": "H1: rework, H3: reviews, H4: TTM",
            "specd_repos": len(specd_rows),
            "unspecd_repos": len(unspecd_rows),
            "specd_total_prs": specd_total,
            "unspecd_total_prs": unspecd_total,
            "specd_rework_rate": specd_rework_rate,
            "unspecd_rework_rate": unspecd_rework_rate,
            "rework_delta_pp": delta,
            "specd_median_review_cycles": _median(specd_cycles),
            "unspecd_median_review_cycles": _median(unspecd_cycles),
            "specd_median_ttm_hours": _median(specd_ttm),
            "unspecd_median_ttm_hours": _median(unspecd_ttm),
        })

    # H2: does the rework gap widen with complexity?
    small_d = bucket_rework_deltas.get("small")
    medium_d = bucket_rework_deltas.get("medium")
    large_d = bucket_rework_deltas.get("large")

    h2_supported = "insufficient data"
    if small_d is not None and medium_d is not None and large_d is not None:
        # Gap widens means abs(delta) increases from small to large
        if abs(small_d) <= abs(medium_d) <= abs(large_d):
            h2_supported = "supported"
        else:
            h2_supported = "not supported"

    rows.append({
        "size_bucket": "all",
        "hypothesis": "H2: gap widens with complexity",
        "specd_repos": "",
        "unspecd_repos": "",
        "specd_total_prs": "",
        "unspecd_total_prs": "",
        "specd_rework_rate": "",
        "unspecd_rework_rate": "",
        "rework_delta_pp": h2_supported,
        "specd_median_review_cycles": f"small={_safe_float(small_d)}pp",
        "unspecd_median_review_cycles": f"medium={_safe_float(medium_d)}pp",
        "specd_median_ttm_hours": f"large={_safe_float(large_d)}pp",
        "unspecd_median_ttm_hours": "",
    })

    return rows


# ── Summary JSON ─────────────────────────────────────────────────────────


def build_summary(repo_rows: list[dict], all_pr_rows: list[dict]) -> dict:
    """Build cross-repo summary statistics."""
    n = len(repo_rows)
    if n == 0:
        return {"error": "no data loaded"}

    def _agg(key: str) -> dict:
        vals = [r[key] for r in repo_rows if r[key] is not None]
        if not vals:
            return {"count": 0, "mean": None, "median": None, "min": None, "max": None}
        return {
            "count": len(vals),
            "mean": round(statistics.mean(vals), 4),
            "median": round(statistics.median(vals), 4),
            "min": round(min(vals), 4),
            "max": round(max(vals), 4),
        }

    total_prs = len(all_pr_rows)
    specd_prs = sum(1 for r in all_pr_rows if r["specd"] == "yes")
    unspecd_prs = sum(1 for r in all_pr_rows if r["specd"] == "no")
    rework_prs = sum(1 for r in all_pr_rows if r["rework"] == "yes")

    return {
        "repos_analyzed": n,
        "total_prs": total_prs,
        "specd_prs": specd_prs,
        "unspecd_prs": unspecd_prs,
        "rework_prs": rework_prs,
        "cross_repo_aggregates": {
            "spec_coverage_pct": _agg("spec_coverage_pct"),
            "machine_catch_rate": _agg("machine_catch_rate_pct"),
            "human_save_rate": _agg("human_save_rate_pct"),
            "escape_rate": _agg("escape_rate_pct"),
            "median_review_cycles": _agg("median_review_cycles"),
            "median_ttm_hours": _agg("median_ttm_hours"),
            "rework_rate_specd": _agg("rework_rate_specd"),
            "rework_rate_unspecd": _agg("rework_rate_unspecd"),
        },
    }


# ── CSV writers ──────────────────────────────────────────────────────────


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    print(f"  Wrote {path} ({len(rows)} rows)")


# ── Main ─────────────────────────────────────────────────────────────────


def main() -> None:
    if not DATA_DIR.exists():
        print(f"Error: data directory not found: {DATA_DIR}", file=sys.stderr)
        print("Run runner.py first to collect data.", file=sys.stderr)
        sys.exit(1)

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    repos = list(REPO_META.keys())
    loaded = 0

    all_repo_rows: list[dict] = []
    all_pr_rows: list[dict] = []
    all_complexity_rows: list[dict] = []

    for repo in repos:
        spec_signals = load_spec_signals(repo)
        catchrate = load_catchrate(repo)

        if spec_signals is None and catchrate is None:
            print(f"  Skipping {repo} (no data files found)")
            continue

        loaded += 1
        print(f"  Loading {repo}...")

        all_repo_rows.append(build_repo_row(repo, spec_signals, catchrate))
        all_pr_rows.extend(build_pr_rows(repo, spec_signals, catchrate))
        all_complexity_rows.extend(build_complexity_rows(repo, spec_signals, catchrate))

    if loaded == 0:
        print("No data files found. Run runner.py first.", file=sys.stderr)
        sys.exit(1)

    print(f"\nLoaded data for {loaded}/{len(repos)} repos.\n")

    # 1. Per-repo summary CSV
    write_csv(
        RESULTS_DIR / "per-repo-summary.csv",
        all_repo_rows,
        [
            "repo", "language", "tier",
            "spec_coverage_pct",
            "machine_catch_rate_pct", "human_save_rate_pct", "escape_rate_pct",
            "median_review_cycles", "median_ttm_hours",
            "rework_rate_specd", "rework_rate_unspecd",
        ],
    )

    # 2. Per-PR detail CSV
    write_csv(
        RESULTS_DIR / "per-pr-detail.csv",
        all_pr_rows,
        [
            "repo", "pr_number", "title", "specd", "classification",
            "lines_changed", "size_bucket", "review_cycles", "ttm_hours",
            "rework", "merged_at",
        ],
    )

    # 3. Complexity-bucketed CSV
    write_csv(
        RESULTS_DIR / "complexity-bucketed.csv",
        all_complexity_rows,
        [
            "repo", "size_bucket", "spec_status", "count", "rework_count",
            "rework_rate", "median_review_cycles", "median_ttm_hours",
        ],
    )

    # 4. Cross-repo hypotheses CSV
    hypothesis_rows = build_hypothesis_rows(all_complexity_rows)
    write_csv(
        RESULTS_DIR / "cross-repo-hypotheses.csv",
        hypothesis_rows,
        [
            "size_bucket", "hypothesis",
            "specd_repos", "unspecd_repos",
            "specd_total_prs", "unspecd_total_prs",
            "specd_rework_rate", "unspecd_rework_rate", "rework_delta_pp",
            "specd_median_review_cycles", "unspecd_median_review_cycles",
            "specd_median_ttm_hours", "unspecd_median_ttm_hours",
        ],
    )

    # 5. Summary JSON
    summary = build_summary(all_repo_rows, all_pr_rows)
    summary_path = RESULTS_DIR / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"  Wrote {summary_path}")

    print("\nDone.")


if __name__ == "__main__":
    main()
