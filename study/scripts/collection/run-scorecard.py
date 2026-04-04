#!/usr/bin/env python3
"""Run OpenSSF Scorecard on all study repos.

Replaces our homegrown enforcement scoring with a peer-reviewed,
standardized tool used by Google/OpenSSF on 1M+ repos.

Usage:
    python run-scorecard.py                  # score all repos
    python run-scorecard.py --repo cli/cli   # score one repo

Output: data/scorecard-results.json
"""

import argparse
import json
import os
import subprocess
import time
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"
RESULTS_PATH = DATA_DIR / "scorecard-results.json"

# All study repos
REPOS = sorted(set(
    fp.stem.replace("prs-", "").replace("-", "/", 1)
    for fp in DATA_DIR.glob("prs-*.json")
    if "validation" not in fp.stem
))


def score_repo(repo: str) -> dict:
    """Run scorecard on a single repo."""
    token = os.environ.get("GITHUB_AUTH_TOKEN") or subprocess.run(
        ["gh", "auth", "token"], capture_output=True, text=True
    ).stdout.strip()

    env = {**os.environ, "GITHUB_AUTH_TOKEN": token}
    cmd = ["scorecard", f"--repo=github.com/{repo}", "--format=json"]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120, env=env)
        if result.returncode != 0:
            return {"repo": repo, "error": result.stderr.strip()[:200]}
        data = json.loads(result.stdout)
        # Flatten checks into a simple dict
        checks = {}
        for check in data.get("checks", []):
            checks[check["name"]] = check["score"]
        return {
            "repo": repo,
            "overall_score": data.get("score"),
            "checks": checks,
            "date": data.get("date"),
        }
    except subprocess.TimeoutExpired:
        return {"repo": repo, "error": "timeout"}
    except Exception as e:
        return {"repo": repo, "error": str(e)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", help="Score a single repo")
    args = parser.parse_args()

    # Load existing (resume support)
    existing = {}
    if RESULTS_PATH.exists():
        try:
            with open(RESULTS_PATH) as f:
                existing = json.load(f)
        except Exception:
            pass

    repos = [args.repo] if args.repo else REPOS
    to_score = [r for r in repos if r not in existing]

    print(f"Total repos: {len(repos)}")
    print(f"Already scored: {len(repos) - len(to_score)}")
    print(f"To score: {len(to_score)}")

    for i, repo in enumerate(to_score):
        result = score_repo(repo)
        existing[repo] = result

        score = result.get("overall_score", "ERR")
        checks = result.get("checks", {})
        branch = checks.get("Branch-Protection", "?")
        ci = checks.get("CI-Tests", "?")
        review = checks.get("Code-Review", "?")
        print(f"  [{i+1}/{len(to_score)}] {repo}: {score}/10  "
              f"(branch={branch} ci={ci} review={review})", flush=True)

        # Save after each
        tmp = RESULTS_PATH.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(existing, indent=2))
        tmp.replace(RESULTS_PATH)

        time.sleep(1)  # Be nice to the API

    print(f"\nDone. {len(existing)} repos scored.")
    print(f"Results: {RESULTS_PATH}")

    # Quick summary
    scored = [v for v in existing.values() if "error" not in v]
    if scored:
        scores = sorted(scored, key=lambda x: x.get("overall_score", 0), reverse=True)
        print(f"\nTop 10:")
        for s in scores[:10]:
            print(f"  {s['repo']:<40s} {s['overall_score']}/10")
        print(f"\nBottom 10:")
        for s in scores[-10:]:
            print(f"  {s['repo']:<40s} {s['overall_score']}/10")


if __name__ == "__main__":
    main()
