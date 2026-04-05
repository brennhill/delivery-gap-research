#!/usr/bin/env python3
"""Replicate all study results from source data.

Single command to reproduce every analysis in the paper:
    python3 replicate-results.py

This runs the full 11-step pipeline:
  1. Merge SZZ/JIT checkpoint files
  2. Build unified-prs.csv (merge PR data + spec signals + rework)
  3. Build master-prs.csv (join all features)
  4. Main analysis (H1-H5, within-author LPM)
  5. Subgroup robustness (human/AI, repo stratification, quality×AI)
  6. High-quality spec robustness (top-quartile, dose-response)
  7. Temporal robustness (recent 3 months, SDD era)
  8. Complexity stratification (top-20% by churn, entropy, JIT risk)
  9. Issue-linked robustness (GitHub issues as true specs)
  10. JIT features as primary controls
  11. Propensity score matching

All results are written to results/*.txt.
Source data in data/ is never modified.

Prerequisites:
    pip install pandas numpy statsmodels scipy

Optional (for spec quality scoring — not needed for replication):
    pip install anthropic
    export ANTHROPIC_API_KEY=...
    python3 scripts/scoring/score-specs.py
"""

import subprocess
import sys
from pathlib import Path

STUDY_DIR = Path(__file__).resolve().parent

def main():
    script = STUDY_DIR / "scripts" / "pipeline" / "run-all-analysis.sh"
    if not script.exists():
        print(f"Error: {script} not found", file=sys.stderr)
        sys.exit(1)

    print("=" * 70)
    print("REPLICATING: Does Spec-Driven Development Reduce Defects?")
    print("=" * 70)
    print(f"Study dir: {STUDY_DIR}")
    print(f"Results will be written to: {STUDY_DIR / 'results'}/*.txt")
    print()

    result = subprocess.run(
        ["bash", str(script)],
        cwd=str(STUDY_DIR),
    )

    if result.returncode != 0:
        print(f"\nPipeline failed with exit code {result.returncode}", file=sys.stderr)
        sys.exit(result.returncode)

    # Combine all result files into a single report
    results_dir = STUDY_DIR / "results"
    report_path = results_dir / "FULL-REPORT.txt"

    result_files = [
        "analysis-results.txt",
        "robustness-subgroups.txt",
        "robustness-highquality.txt",
        "robustness-temporal.txt",
        "robustness-complexity.txt",
        "robustness-issue-linked.txt",
        "primary-with-jit-controls.txt",
        "propensity-score-matching.txt",
    ]

    with open(report_path, "w") as report:
        report.write("=" * 70 + "\n")
        report.write("FULL REPLICATION REPORT\n")
        report.write("Does Spec-Driven Development Reduce Defects?\n")
        report.write(f"Generated: {__import__('datetime').datetime.now().isoformat()}\n")
        report.write("=" * 70 + "\n\n")

        report.write("DATA NOTES\n")
        report.write("-" * 70 + "\n\n")
        report.write("SZZ blame links vs JIT features:\n\n")
        report.write("  SZZ traces fix commits back to the commits that introduced the\n")
        report.write("  bug via git blame. It only produces rows for PRs that introduced\n")
        report.write("  a bug that was LATER FIXED. The ~65K SZZ rows are blame links\n")
        report.write("  (fix → bug-introducing commit), not PR counts. Many PRs never\n")
        report.write("  introduced a traced bug, so they have no SZZ rows.\n\n")
        report.write("  JIT features (lines added, entropy, developer experience, etc.)\n")
        report.write("  are computed from diff metadata and can be calculated for ANY PR.\n")
        report.write("  The ~109K JIT rows cover nearly all PRs in the dataset.\n\n")
        report.write("  16 of 119 repos have zero SZZ coverage because their squash-merge\n")
        report.write("  workflows cause GitHub's merge SHAs to be garbage-collected,\n")
        report.write("  making them unreachable via git blame.\n\n")

        for fname in result_files:
            fpath = results_dir / fname
            if fpath.exists():
                report.write("\n" + "#" * 70 + "\n")
                report.write(f"# {fname}\n")
                report.write("#" * 70 + "\n\n")
                report.write(fpath.read_text())
                report.write("\n")
            else:
                report.write("\n" + "#" * 70 + "\n")
                report.write(f"# {fname} — NOT FOUND (pipeline step may have failed)\n")
                report.write("#" * 70 + "\n\n")
                print(f"  WARNING: {fname} not found", file=sys.stderr)

    print("\n" + "=" * 70)
    print("REPLICATION COMPLETE")
    print("=" * 70)
    print(f"\nFull report: results/FULL-REPORT.txt ({report_path.stat().st_size:,} bytes)")
    print(f"\nIndividual result files:")
    for f in sorted(results_dir.glob("*.txt")):
        if f.name != "FULL-REPORT.txt":
            size = f.stat().st_size
            print(f"  {f.name:45s} {size:>8,} bytes")

    print(f"\nTo view the full report: cat results/FULL-REPORT.txt")
    print(f"To re-run a single analysis: python3 scripts/pipeline/<script>.py")


if __name__ == "__main__":
    main()
