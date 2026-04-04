#!/usr/bin/env python3
"""Run PyDriller SZZ on study repos and compare to CatchRate.

Clones repos (shallow), runs SZZ to find bug-introducing commits,
maps results back to PRs, and compares with CatchRate + human labels.

Usage:
    python run-pydriller-szz.py                    # clone + analyze all
    python run-pydriller-szz.py --repo cli/cli      # one repo
    python run-pydriller-szz.py --analyze           # just analyze existing results
    python run-pydriller-szz.py --validate          # compare to human labels

Output: data/szz-results.json
"""

import argparse
import json
import os
import re
import subprocess
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from pydriller import Repository, Git

DATA_DIR = Path(__file__).resolve().parent / "data"
CLONE_DIR = Path(__file__).resolve().parent / "repos"
RESULTS_PATH = DATA_DIR / "szz-results.json"


def clone_repo(repo: str) -> Path:
    """Shallow clone a repo if not already cloned."""
    repo_dir = CLONE_DIR / repo.replace("/", "-")
    if repo_dir.exists():
        # Pull latest
        try:
            subprocess.run(
                ["git", "pull", "--ff-only"],
                cwd=str(repo_dir), capture_output=True, timeout=60
            )
        except Exception:
            pass
        return repo_dir

    CLONE_DIR.mkdir(parents=True, exist_ok=True)
    print(f"  Cloning {repo}...", flush=True)
    try:
        subprocess.run(
            ["git", "clone", "--depth=1000", f"https://github.com/{repo}.git",
             str(repo_dir)],
            capture_output=True, timeout=300,
        )
    except subprocess.TimeoutExpired:
        print(f"  Clone timeout for {repo}", flush=True)
        return repo_dir

    return repo_dir


def find_fix_commits(repo_dir: Path, since: datetime) -> list[dict]:
    """Find commits that are bug fixes (title starts with fix/patch/hotfix)."""
    fixes = []
    try:
        for commit in Repository(str(repo_dir), since=since).traverse_commits():
            msg = commit.msg.split("\n")[0].lower()
            if re.match(r"^(fix|patch|hotfix|bugfix|revert)", msg):
                fixes.append({
                    "hash": commit.hash,
                    "msg": commit.msg.split("\n")[0][:200],
                    "author": commit.author.name,
                    "date": commit.author_date.isoformat(),
                    "files": [m.filename for m in commit.modified_files],
                })
    except Exception as e:
        print(f"  Error traversing: {e}", flush=True)
    return fixes


def run_szz(repo_dir: Path, fix_commits: list[dict]) -> list[dict]:
    """Run SZZ on fix commits to find bug-introducing commits."""
    pairs = []
    git = Git(str(repo_dir))

    for i, fix in enumerate(fix_commits):
        try:
            # PyDriller's SZZ: for each fix commit, find which commits
            # last modified the lines that were changed in the fix
            buggy_commits = git.get_commits_last_modified_lines(
                git.get_commit(fix["hash"])
            )

            # buggy_commits is dict: {filepath: set(commit_hashes)}
            introducing_hashes = set()
            for filepath, hashes in buggy_commits.items():
                introducing_hashes.update(hashes)

            if introducing_hashes:
                # Get details of introducing commits
                for intro_hash in introducing_hashes:
                    try:
                        intro_commit = git.get_commit(intro_hash)
                        pairs.append({
                            "fix_hash": fix["hash"],
                            "fix_msg": fix["msg"],
                            "fix_date": fix["date"],
                            "fix_author": fix["author"],
                            "intro_hash": intro_hash,
                            "intro_msg": intro_commit.msg.split("\n")[0][:200],
                            "intro_date": intro_commit.author_date.isoformat(),
                            "intro_author": intro_commit.author.name,
                        })
                    except Exception:
                        pass

        except Exception as e:
            if i < 3:  # Only log first few errors
                print(f"  SZZ error on {fix['hash'][:8]}: {e}", flush=True)

    return pairs


def map_commits_to_prs(pairs: list[dict], repo: str) -> list[dict]:
    """Map SZZ commit pairs to PR numbers using merge_commit_sha from PR data."""
    slug = repo.replace("/", "-")
    prs_path = DATA_DIR / f"prs-{slug}.json"
    if not prs_path.exists():
        return []

    with open(prs_path) as f:
        prs = json.load(f)

    # Build commit → PR mapping
    # A PR's merge_commit_sha is the merge commit, but commits within the PR
    # are in the commits list
    commit_to_pr = {}
    for pr in prs:
        sha = pr.get("merge_commit_sha", "")
        if sha:
            commit_to_pr[sha] = pr.get("pr_number")
            # Also short hash
            commit_to_pr[sha[:7]] = pr.get("pr_number")

        for c in pr.get("commits", []):
            if isinstance(c, dict):
                csha = c.get("sha", "")
                if csha:
                    commit_to_pr[csha] = pr.get("pr_number")
                    commit_to_pr[csha[:7]] = pr.get("pr_number")

    # Map pairs
    mapped = []
    for pair in pairs:
        fix_pr = commit_to_pr.get(pair["fix_hash"]) or commit_to_pr.get(pair["fix_hash"][:7])
        intro_pr = commit_to_pr.get(pair["intro_hash"]) or commit_to_pr.get(pair["intro_hash"][:7])

        if fix_pr and intro_pr and fix_pr != intro_pr:
            mapped.append({
                **pair,
                "fix_pr": fix_pr,
                "intro_pr": intro_pr,
            })

    return mapped


def analyze_repo(repo: str) -> dict:
    """Clone, find fixes, run SZZ, map to PRs."""
    repo_dir = clone_repo(repo)
    if not repo_dir.exists():
        return {"repo": repo, "error": "clone failed"}

    since = datetime(2025, 9, 1, tzinfo=timezone.utc)  # ~6 months back

    print(f"  Finding fix commits...", flush=True)
    fixes = find_fix_commits(repo_dir, since)
    print(f"  Found {len(fixes)} fix commits", flush=True)

    if not fixes:
        return {
            "repo": repo,
            "fix_commits": 0,
            "szz_pairs": 0,
            "pr_mapped_pairs": 0,
            "pairs": [],
        }

    print(f"  Running SZZ on {len(fixes)} fixes...", flush=True)
    pairs = run_szz(repo_dir, fixes)
    print(f"  SZZ found {len(pairs)} bug-introducing pairs", flush=True)

    # Deduplicate by (fix_hash, intro_hash)
    seen = set()
    unique_pairs = []
    for p in pairs:
        key = (p["fix_hash"], p["intro_hash"])
        if key not in seen:
            seen.add(key)
            unique_pairs.append(p)

    print(f"  Mapping to PRs...", flush=True)
    mapped = map_commits_to_prs(unique_pairs, repo)
    print(f"  Mapped {len(mapped)} pairs to PRs", flush=True)

    # Deduplicate by (fix_pr, intro_pr)
    pr_seen = set()
    pr_pairs = []
    for p in mapped:
        key = (p["fix_pr"], p["intro_pr"])
        if key not in pr_seen:
            pr_seen.add(key)
            pr_pairs.append(p)

    return {
        "repo": repo,
        "fix_commits": len(fixes),
        "szz_pairs": len(unique_pairs),
        "pr_mapped_pairs": len(pr_pairs),
        "pairs": pr_pairs,
    }


def validate_against_human_labels():
    """Compare SZZ results to human ground truth."""
    if not RESULTS_PATH.exists():
        print("No SZZ results. Run without --validate first.")
        return

    with open(RESULTS_PATH) as f:
        szz_data = json.load(f)

    # Build set of SZZ-detected PR pairs
    szz_pairs = set()
    for repo_data in szz_data.values():
        if "error" in repo_data:
            continue
        repo = repo_data["repo"]
        for pair in repo_data.get("pairs", []):
            # SZZ says intro_pr introduced bug fixed by fix_pr
            szz_pairs.add(f"{repo}#{pair['intro_pr']}->{pair['fix_pr']}")

    print(f"Total SZZ PR pairs: {len(szz_pairs)}")

    # Load human labels
    labels_files = [
        (DATA_DIR / "human-validation-labels.json", DATA_DIR / "human-validation-sample.json", "labels"),
        (DATA_DIR / "human-validation-labels.json", DATA_DIR / "human-validation-sample-ext.json", "extension_labels"),
        (DATA_DIR / "human-validation-medium-labels.json", DATA_DIR / "human-validation-medium.json", "labels"),
    ]

    comparisons = []
    for labels_path, sample_path, labels_key in labels_files:
        if not labels_path.exists() or not sample_path.exists():
            continue
        with open(labels_path) as f:
            label_data = json.load(f)
        with open(sample_path) as f:
            pairs = json.load(f)

        for entry in label_data.get(labels_key, []):
            if entry["label"] == "unsure":
                continue
            idx = entry["pair"]
            if idx >= len(pairs):
                continue
            p = pairs[idx]
            key = f"{p['repo']}#{p['target_num']}->{p['source_num']}"
            human = entry["label"] == "yes"
            szz = key in szz_pairs
            comparisons.append({"key": key, "human": human, "szz": szz})

    if not comparisons:
        print("No overlapping pairs to compare")
        return

    N = len(comparisons)
    tp = sum(1 for c in comparisons if c["human"] and c["szz"])
    fp = sum(1 for c in comparisons if not c["human"] and c["szz"])
    fn = sum(1 for c in comparisons if c["human"] and not c["szz"])
    tn = sum(1 for c in comparisons if not c["human"] and not c["szz"])
    agree = tp + tn

    prec = tp / (tp + fp) if (tp + fp) else 0
    rec = tp / (tp + fn) if (tp + fn) else 0

    print(f"\n=== SZZ vs HUMAN GROUND TRUTH (N={N}) ===")
    print(f"Agreement: {agree}/{N} ({100*agree/N:.0f}%)")
    print(f"TP={tp} FP={fp} FN={fn} TN={tn}")
    print(f"Precision: {prec:.2f}  Recall: {rec:.2f}")

    # Also load CatchRate results for three-way comparison
    # CatchRate CONFIRMED+HIGH pairs
    cr_pairs = set()
    for fp_path in sorted(DATA_DIR.glob("catchrate-*.json")):
        slug = fp_path.stem.replace("catchrate-", "")
        repo = slug.replace("-", "/", 1)
        with open(fp_path) as f:
            cr = json.load(f)
        for pr in cr.get("prs", []):
            if not pr.get("escaped"):
                continue
            conf = pr.get("escape_confidence", "")
            if conf not in ("confirmed", "high"):
                continue
            target = pr["number"]
            reason = pr.get("escape_reason", "")
            m = re.search(r"#(\d+)", reason)
            if m:
                source = int(m.group(1))
                cr_pairs.add(f"{repo}#{target}->{source}")

    # Three-way
    print(f"\n=== THREE-WAY COMPARISON ===")
    print(f"CatchRate CONFIRMED+HIGH pairs: {len(cr_pairs)}")
    print(f"SZZ pairs: {len(szz_pairs)}")
    overlap = cr_pairs & szz_pairs
    print(f"Both agree: {len(overlap)}")
    cr_only = cr_pairs - szz_pairs
    szz_only = szz_pairs - cr_pairs
    print(f"CatchRate only: {len(cr_only)}")
    print(f"SZZ only: {len(szz_only)}")

    # On human-labeled pairs, what does each method get?
    print(f"\n=== ON HUMAN-LABELED PAIRS ===")
    for method_name, method_pairs in [("CatchRate C+H", cr_pairs), ("SZZ", szz_pairs), ("Either", cr_pairs | szz_pairs), ("Both", cr_pairs & szz_pairs)]:
        tp_m = sum(1 for c in comparisons if c["human"] and c["key"] in method_pairs)
        fp_m = sum(1 for c in comparisons if not c["human"] and c["key"] in method_pairs)
        fn_m = sum(1 for c in comparisons if c["human"] and c["key"] not in method_pairs)
        prec_m = tp_m / (tp_m + fp_m) if (tp_m + fp_m) else 0
        rec_m = tp_m / (tp_m + fn_m) if (tp_m + fn_m) else 0
        print(f"  {method_name:15s}: prec={prec_m:.0%} rec={rec_m:.0%} (TP={tp_m} FP={fp_m} FN={fn_m})")

    # Show SZZ-only catches that are true rework
    szz_unique_catches = [c for c in comparisons if c["human"] and c["szz"] and c["key"] not in cr_pairs]
    if szz_unique_catches:
        print(f"\nSZZ UNIQUE CATCHES (rework that CatchRate missed):")
        for c in szz_unique_catches:
            print(f"  {c['key']}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", help="Analyze a single repo")
    parser.add_argument("--analyze", action="store_true", help="Analyze existing results")
    parser.add_argument("--validate", action="store_true", help="Compare to human labels")
    args = parser.parse_args()

    if args.validate:
        validate_against_human_labels()
        return

    if args.analyze:
        if not RESULTS_PATH.exists():
            print("No results yet")
            return
        with open(RESULTS_PATH) as f:
            results = json.load(f)
        total_pairs = sum(r.get("pr_mapped_pairs", 0) for r in results.values() if "error" not in r)
        total_fixes = sum(r.get("fix_commits", 0) for r in results.values() if "error" not in r)
        print(f"Repos: {len(results)}")
        print(f"Fix commits: {total_fixes}")
        print(f"PR-mapped pairs: {total_pairs}")
        return

    # Load existing (resume)
    existing = {}
    if RESULTS_PATH.exists():
        try:
            with open(RESULTS_PATH) as f:
                existing = json.load(f)
        except Exception:
            pass

    # Get repo list
    if args.repo:
        repos = [args.repo]
    else:
        repos = sorted(set(
            fp.stem.replace("prs-", "").replace("-", "/", 1)
            for fp in DATA_DIR.glob("prs-*.json")
            if "validation" not in fp.stem
        ))

    to_process = [r for r in repos if r not in existing]
    print(f"Total repos: {len(repos)}")
    print(f"Already done: {len(repos) - len(to_process)}")
    print(f"To process: {len(to_process)}")

    for i, repo in enumerate(to_process):
        print(f"\n[{i+1}/{len(to_process)}] {repo}:", flush=True)
        result = analyze_repo(repo)
        existing[repo] = result

        # Save after each
        tmp = RESULTS_PATH.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(existing, indent=2, default=str))
        tmp.replace(RESULTS_PATH)

        time.sleep(0.5)

    print(f"\nDone. {len(existing)} repos analyzed.")

    # Summary
    total_pairs = sum(r.get("pr_mapped_pairs", 0) for r in existing.values() if "error" not in r)
    total_fixes = sum(r.get("fix_commits", 0) for r in existing.values() if "error" not in r)
    print(f"Fix commits: {total_fixes}")
    print(f"PR-mapped pairs: {total_pairs}")

    # Run validation automatically
    print()
    validate_against_human_labels()


if __name__ == "__main__":
    main()
