#!/usr/bin/env python3
"""Regenerate all spec-signals-*.json files from prs-*.json sources.

Usage:
    python -m tools.regenerate_all              # regenerate all
    python -m tools.regenerate_all --force      # overwrite existing
    python -m tools.regenerate_all --dry-run    # just print what would happen
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools.run_spec_signals import run as run_spec

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def main():
    force = "--force" in sys.argv
    dry_run = "--dry-run" in sys.argv

    prs_files = sorted(DATA_DIR.glob("prs-*.json"))
    print(f"Found {len(prs_files)} prs-*.json files")

    for i, prs_path in enumerate(prs_files, 1):
        slug = prs_path.name.replace("prs-", "").replace(".json", "")
        out_path = DATA_DIR / f"spec-signals-{slug}.json"

        status = "exists" if out_path.exists() else "new"
        if out_path.exists() and not force:
            print(f"[{i}/{len(prs_files)}] {slug}: SKIP (exists, use --force)")
            continue

        if dry_run:
            print(f"[{i}/{len(prs_files)}] {slug}: WOULD regenerate ({status})")
            continue

        print(f"[{i}/{len(prs_files)}] {slug}: regenerating...", end="", flush=True)
        try:
            run_spec(str(prs_path), str(out_path))
            print(" OK")
        except Exception as e:
            print(f" FAILED: {e}")

    print("Done.")


if __name__ == "__main__":
    main()
