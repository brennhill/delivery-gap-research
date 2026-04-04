#!/usr/bin/env python3
"""Clear error entries from validation files so they get re-scored.

Usage:
    python fix-validation-errors.py          # clear errors
    python fix-validation-errors.py --dry-run  # show what would be cleared
"""

import argparse
import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"

FILES = [
    DATA_DIR / "high-confidence-validation.json",
    DATA_DIR / "catchrate-validation-results.json",
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    for fp in FILES:
        if not fp.exists():
            continue
        with open(fp) as f:
            data = json.load(f)

        errors = {k: v for k, v in data.items() if "error" in v}
        # Also catch parse errors stored as string values
        parse_errors = {k: v for k, v in data.items()
                        if isinstance(v, dict) and any(
                            str(val).startswith("Parse error") for val in v.values()
                            if isinstance(val, str)
                        )}
        to_remove = set(errors.keys()) | set(parse_errors.keys())

        if not to_remove:
            print(f"{fp.name}: no errors")
            continue

        print(f"{fp.name}: {len(to_remove)} errors to clear")
        for k in sorted(to_remove):
            err = data[k].get("error", "unknown")[:80]
            print(f"  {k}: {err}")

        if not args.dry_run:
            for k in to_remove:
                del data[k]
            tmp = fp.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(data, indent=2))
            tmp.replace(fp)
            print(f"  Cleared. Re-run validation to re-score these.\n")
        else:
            print(f"  (dry run — not cleared)\n")


if __name__ == "__main__":
    main()
