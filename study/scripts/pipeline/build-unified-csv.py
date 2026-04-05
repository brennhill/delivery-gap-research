#!/usr/bin/env python3
"""Build a unified CSV with one row per PR across all repos.

Joins: PR data + spec-signals coverage + CATCHRATE classification + workflow tags + quality scores + rework signals.

Output: data/unified-prs.csv
"""

import csv
import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


def load_json(path):
    try:
        return json.loads(path.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def build_rows():
    slugs = sorted(
        p.stem.replace("prs-", "")
        for p in DATA_DIR.glob("prs-*.json")
    )

    all_rows = []

    for slug in slugs:
        prs = load_json(DATA_DIR / f"prs-{slug}.json")
        if not prs:
            continue

        spec_signals = load_json(DATA_DIR / f"spec-signals-{slug}.json")
        catchrate = load_json(DATA_DIR / f"catchrate-{slug}.json")
        workflow = load_json(DATA_DIR / f"workflow-{slug}.json")
        quality_data = load_json(DATA_DIR / f"spec-quality-{slug}.json")

        # Index spec_signals coverage by number
        cov_by_num = {}
        if spec_signals:
            for p in spec_signals.get("coverage", {}).get("prs", []):
                cov_by_num[p["number"]] = p

        # Index catchrate by number
        cr_by_num = {}
        if catchrate:
            for p in catchrate.get("prs", []):
                cr_by_num[p["number"]] = p

        # Index workflow tags by PR number
        wf_by_num = {}
        if workflow:
            for tag in workflow.get("pr_tags", []):
                wf_by_num[tag["pr_number"]] = tag

        # Index quality scores by pr_number (within same repo file, repo is implicit)
        q_by_num = {}
        if quality_data:
            for r in quality_data:
                if "error" not in r and "_script_error" not in r and "_parse_error" not in r:
                    q_by_num[r["pr_number"]] = r

        # Rework signals: which target PRs were reworked + type
        reworked_targets = set()
        rework_type = {}  # pr_number -> 'alignment' or 'implementation'
        pr_files = {pr["pr_number"]: pr.get("files", []) for pr in prs}

        if spec_signals:
            for s in spec_signals.get("effectiveness", {}).get("signals", []):
                target = int(s["target"])
                source = int(s["source"])
                reworked_targets.add(target)

                overlap = s.get("overlapping_files", [])
                sf = pr_files.get(source, [])
                tf = pr_files.get(target, [])
                total = len(set(sf) | set(tf))
                if total > 0:
                    ratio = len(overlap) / total
                    new_type = "implementation" if ratio >= 0.5 else "alignment"
                    # Keep the highest-overlap classification if multiple signals
                    if target not in rework_type or new_type == "implementation":
                        rework_type[target] = new_type

        # Build rows
        repo_name = prs[0].get("repo", slug.replace("-", "/", 1)) if prs else slug
        tier = _get_tier(slug)

        for pr in prs:
            num = pr["pr_number"]
            title = pr["title"]

            cov = cov_by_num.get(num, {})
            cr = cr_by_num.get(num, {})
            wf = wf_by_num.get(num, {})
            q = q_by_num.get(num, {})

            row = {
                # Identity
                "repo": repo_name,
                "tier": tier,
                "pr_number": num,
                "title": title,
                "author": pr.get("author", ""),
                "merged_at": pr.get("merged_at", ""),

                # Size
                "additions": pr.get("additions", 0),
                "deletions": pr.get("deletions", 0),
                "lines_changed": cr.get("lines_changed", 0),
                "size_bucket": cr.get("size_bucket", ""),
                "files_count": len(pr.get("files", [])),

                # Spec coverage
                "specd": cov.get("specd", False),
                "spec_source": cov.get("spec_source", ""),

                # Catchrate
                "classification": cr.get("classification", ""),
                "ci_status": cr.get("ci_status", ""),
                "review_modified": cr.get("review_modified", False),
                "escaped": cr.get("escaped", False),
                "review_cycles": cr.get("review_cycles", 0),
                "time_to_merge_hours": cr.get("time_to_merge_hours", 0),

                # Workflow
                "approval_mechanism": wf.get("approval_mechanism", ""),
                "workflow_type": wf.get("active_workflow_type", ""),

                # Rework
                "reworked": num in reworked_targets,
                "rework_type": rework_type.get(num, ""),

                # Quality scores (LLM)
                "q_overall": q.get("overall", ""),
                "q_outcome_clarity": q.get("outcome_clarity", ""),
                "q_error_states": q.get("error_states", ""),
                "q_scope_boundaries": q.get("scope_boundaries", ""),
                "q_acceptance_criteria": q.get("acceptance_criteria", ""),
                "q_data_contracts": q.get("data_contracts", ""),
                "q_dependency_context": q.get("dependency_context", ""),
                "q_behavioral_specificity": q.get("behavioral_specificity", ""),
                "q_change_type": q.get("change_type", ""),
                "q_spec_length_signal": q.get("spec_length_signal", ""),
            }
            all_rows.append(row)

    return all_rows


def _get_tier(slug):
    """Get tier from runner.py's REPOS list (single source of truth)."""
    from runner import REPOS
    tier_map = {r["repo"].replace("/", "-"): r["tier"] for r in REPOS}
    return tier_map.get(slug, "?")


def main():
    rows = build_rows()
    if not rows:
        print("No data found")
        return

    out_path = DATA_DIR / "unified-prs.csv"
    fieldnames = list(rows[0].keys())

    tmp_path = out_path.with_suffix('.csv.tmp')
    with open(tmp_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    tmp_path.replace(out_path)

    print(f"Wrote {len(rows)} rows to {out_path}")

    # Summary
    repos = set(r["repo"] for r in rows)
    specd = sum(1 for r in rows if r["specd"])
    scored = sum(1 for r in rows if r["q_overall"] != "")
    reworked = sum(1 for r in rows if r["reworked"])
    print(f"Repos: {len(repos)}")
    print(f"Spec'd: {specd}/{len(rows)} ({specd/len(rows)*100:.0f}%)")
    print(f"Quality scored: {scored}")
    print(f"Reworked: {reworked}")


if __name__ == "__main__":
    main()
