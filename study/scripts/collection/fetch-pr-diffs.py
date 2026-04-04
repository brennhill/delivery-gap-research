#!/usr/bin/env python3
"""Fetch PR diff hunks for MEDIUM confidence pairs.

Gets patch data from GitHub API to enable function-level overlap analysis.
Extracts function names from @@ hunk headers.

Usage:
    python fetch-pr-diffs.py              # fetch all MEDIUM pair diffs
    python fetch-pr-diffs.py --all-tiers  # fetch for all escaped pairs

Output: data/pr-diffs.json
"""

import argparse
import json
import re
import subprocess
import time
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"
DIFFS_PATH = DATA_DIR / "pr-diffs.json"


def fetch_pr_files(repo: str, pr_number: int) -> list[dict]:
    """Fetch file-level diff info for a PR via gh CLI."""
    cmd = [
        "gh", "api",
        f"repos/{repo}/pulls/{pr_number}/files",
        "--paginate",
        "--jq", """[.[] | {
            filename: .filename,
            status: .status,
            additions: .additions,
            deletions: .deletions,
            patch: .patch
        }]""",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            return [{"error": result.stderr.strip()[:200]}]
        # gh --paginate with --jq outputs multiple JSON arrays, one per page
        # Merge them
        files = []
        for line in result.stdout.strip().split("\n"):
            if line.strip():
                files.extend(json.loads(line))
        return files
    except subprocess.TimeoutExpired:
        return [{"error": "timeout"}]
    except Exception as e:
        return [{"error": str(e)}]


def extract_functions_from_patch(patch: str) -> list[str]:
    """Extract function/method names from @@ hunk headers.

    Git includes the enclosing function name after the @@ line range.
    e.g.: @@ -10,5 +10,7 @@ def process_payment(amount):
    """
    if not patch:
        return []
    functions = []
    for m in re.finditer(r"@@ .+? @@\s*(.*)", patch):
        context = m.group(1).strip()
        if not context:
            continue
        # Extract function/method name from common patterns
        # Python: def foo(, class Foo:
        # JS/TS: function foo(, const foo =, async foo(, export function
        # Go: func (r *Receiver) Method(, func Function(
        # Rust: fn function_name(, pub fn, impl Struct
        # Java/C#: public void method(, private int foo(
        # C/C++: type function_name(
        func_match = re.search(
            r"(?:def |function |fn |func |(?:public|private|protected|static|async|export)\s+)*"
            r"(?:(?:const|let|var)\s+)?"
            r"([a-zA-Z_]\w*)\s*[\(:{]",
            context,
        )
        if func_match:
            functions.append(func_match.group(1))
        else:
            # Fall back to the raw context line
            functions.append(context[:80])
    return functions


def extract_diff_summary(files: list[dict]) -> dict:
    """Summarize diff: files, functions touched, line ranges."""
    if not files or (len(files) == 1 and "error" in files[0]):
        return {"error": files[0].get("error", "unknown") if files else "empty"}

    summary = {
        "files": [],
        "functions_by_file": {},
        "total_additions": 0,
        "total_deletions": 0,
    }

    for f in files:
        if "error" in f:
            continue
        filename = f.get("filename", "")
        summary["files"].append(filename)
        summary["total_additions"] += f.get("additions", 0)
        summary["total_deletions"] += f.get("deletions", 0)

        patch = f.get("patch", "")
        if patch:
            functions = extract_functions_from_patch(patch)
            if functions:
                summary["functions_by_file"][filename] = functions

    return summary


def compute_function_overlap(target_diff: dict, source_diff: dict) -> dict:
    """Compute function-level overlap between two PRs."""
    if "error" in target_diff or "error" in source_diff:
        return {"error": "missing diff data"}

    target_funcs = set()
    source_funcs = set()

    for filename, funcs in target_diff.get("functions_by_file", {}).items():
        for func in funcs:
            target_funcs.add(f"{filename}::{func}")

    for filename, funcs in source_diff.get("functions_by_file", {}).items():
        for func in funcs:
            source_funcs.add(f"{filename}::{func}")

    overlap = target_funcs & source_funcs
    file_overlap = set(target_diff.get("files", [])) & set(source_diff.get("files", []))

    return {
        "file_overlap_count": len(file_overlap),
        "function_overlap_count": len(overlap),
        "overlapping_functions": sorted(overlap),
        "target_function_count": len(target_funcs),
        "source_function_count": len(source_funcs),
        "function_overlap_pct": len(overlap) / len(source_funcs) if source_funcs else 0,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--all-tiers", action="store_true",
                        help="Fetch diffs for all tiers, not just MEDIUM")
    args = parser.parse_args()

    # Load existing results (resume support)
    existing = {}
    if DIFFS_PATH.exists():
        try:
            with open(DIFFS_PATH) as f:
                existing = json.load(f)
        except Exception:
            pass

    # Collect PRs to fetch
    prs_to_fetch = set()  # "repo#number"
    pairs = []  # (repo, target, source, confidence)

    for fp in sorted(DATA_DIR.glob("catchrate-*.json")):
        slug = fp.stem.replace("catchrate-", "")
        repo = slug.replace("-", "/", 1)
        with open(fp) as f:
            cr = json.load(f)
        for pr in cr.get("prs", []):
            if not pr.get("escaped"):
                continue
            conf = pr.get("escape_confidence", "")
            if not args.all_tiers and conf != "medium":
                continue
            target_num = pr["number"]
            reason = pr.get("escape_reason", "")
            m = re.search(r"#(\d+)", reason)
            if not m:
                continue
            source_num = int(m.group(1))
            pairs.append((repo, target_num, source_num, conf))
            prs_to_fetch.add(f"{repo}#{target_num}")
            prs_to_fetch.add(f"{repo}#{source_num}")

    # Skip already fetched
    to_fetch = [k for k in prs_to_fetch if k not in existing.get("diffs", {})]
    print(f"Pairs: {len(pairs)}")
    print(f"Unique PRs: {len(prs_to_fetch)}")
    print(f"Already fetched: {len(prs_to_fetch) - len(to_fetch)}")
    print(f"To fetch: {len(to_fetch)}")

    if "diffs" not in existing:
        existing["diffs"] = {}

    # Fetch diffs
    for i, key in enumerate(sorted(to_fetch)):
        repo, num_str = key.rsplit("#", 1)
        pr_number = int(num_str)

        files = fetch_pr_files(repo, pr_number)
        summary = extract_diff_summary(files)
        existing["diffs"][key] = summary

        func_count = sum(len(v) for v in summary.get("functions_by_file", {}).values())
        status = f"{len(summary.get('files', []))} files, {func_count} functions"
        if "error" in summary:
            status = f"ERROR: {summary['error'][:60]}"
        print(f"  [{i+1}/{len(to_fetch)}] {key}: {status}", flush=True)

        # Save every 50
        if (i + 1) % 50 == 0 or i == len(to_fetch) - 1:
            tmp = DIFFS_PATH.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(existing, indent=2))
            tmp.replace(DIFFS_PATH)

        time.sleep(0.5)  # Stay well under rate limit

    # Compute function overlap for all pairs
    print(f"\nComputing function overlap for {len(pairs)} pairs...")
    overlaps = {}
    for repo, target, source, conf in pairs:
        target_diff = existing["diffs"].get(f"{repo}#{target}", {})
        source_diff = existing["diffs"].get(f"{repo}#{source}", {})
        overlap = compute_function_overlap(target_diff, source_diff)
        key = f"{repo}#{target}->{source}"
        overlaps[key] = {**overlap, "confidence": conf}

    existing["overlaps"] = overlaps

    # Save final
    tmp = DIFFS_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(existing, indent=2))
    tmp.replace(DIFFS_PATH)

    # Summary
    with_func_overlap = sum(1 for v in overlaps.values() if v.get("function_overlap_count", 0) > 0)
    without = sum(1 for v in overlaps.values() if v.get("function_overlap_count", 0) == 0 and "error" not in v)
    errors = sum(1 for v in overlaps.values() if "error" in v)
    print(f"\nResults:")
    print(f"  Function overlap: {with_func_overlap} pairs")
    print(f"  No function overlap: {without} pairs")
    print(f"  Errors: {errors} pairs")
    print(f"Saved to {DIFFS_PATH}")


if __name__ == "__main__":
    main()
