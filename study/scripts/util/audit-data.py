#!/usr/bin/env python3
"""Audit all study data for completeness and consistency.

Checks every repo for:
  1. Raw PR data (prs-*.json) — existence, field completeness
  2. CatchRate output (catchrate-*.json) — existence, PR count match
  3. LLM scores (engagement-*.json, spec-quality-*.json) — coverage
  4. Features (pr-features.csv) — coverage
  5. Master CSV (master-prs.csv) — coverage
  6. Enforcement scores (enforcement-scores.json) — coverage
  7. Infrastructure data (repo-infra.json) — coverage

Usage:
    python audit-data.py           # full audit
    python audit-data.py --fix     # show what needs re-running
"""

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent / "data"

# Expected repos (43)
EXPECTED_REPOS = [
    "apache/arrow", "apache/kafka", "anthropics/anthropic-cookbook",
    "antiwork/gumroad", "astral-sh/ruff", "biomejs/biome",
    "calcom/cal.com", "clerkinc/javascript", "cli/cli",
    "cockroachdb/cockroach", "continuedev/continue", "denoland/deno",
    "django/django", "dotnet/aspire", "elastic/elasticsearch",
    "envoyproxy/envoy", "facebook/react", "grafana/grafana",
    "huggingface/transformers", "kubernetes/kubernetes",
    "langchain-ai/langchain", "liam-hq/liam", "lobehub/lobe-chat",
    "mendableai/firecrawl", "microsoft/vscode", "mlflow/mlflow",
    "n8n-io/n8n", "nats-io/nats-server", "novuhq/novu",
    "oven-sh/bun", "pingcap/tidb", "pnpm/pnpm",
    "PostHog/posthog", "prometheus/prometheus", "promptfoo/promptfoo",
    "python/cpython", "rust-lang/rust", "supabase/supabase",
    "sveltejs/svelte", "temporalio/temporal", "traefik/traefik",
    "vercel/next.js",
]
# Note: 43 repos but some slug mappings differ (e.g. vercel/next.js -> vercel-next.js)


def repo_to_slug(repo: str) -> str:
    return repo.replace("/", "-")


def audit():
    """Run full data audit."""
    issues = []
    warnings = []
    stats = {}

    print("=" * 70)
    print("DATA AUDIT")
    print("=" * 70)

    # --- 1. Raw PR data ---
    print("\n## 1. Raw PR Data (prs-*.json)")
    pr_files = {fp.stem.replace("prs-", ""): fp for fp in DATA_DIR.glob("prs-*.json")}
    print(f"   Found: {len(pr_files)} files")

    pr_counts = {}
    field_issues = defaultdict(list)
    required_fields = ["title", "body", "author", "merged_at", "files", "pr_number",
                       "reviews", "commits", "additions", "deletions"]

    for slug, fp in sorted(pr_files.items()):
        with open(fp) as f:
            prs = json.load(f)
        pr_counts[slug] = len(prs)

        # Check field completeness
        for pr in prs:
            for field in required_fields:
                val = pr.get(field)
                if val is None or val == "":
                    if field not in ("body", "merged_at"):  # body can be empty, merged_at can be null
                        field_issues[slug].append((pr.get("pr_number", "?"), field))

            # Check for missing commits/reviews (known issue for some repos)
            if pr.get("commits") is not None and len(pr.get("commits", [])) == 0 and pr.get("commit_count", 0) > 0:
                field_issues[slug].append((pr.get("pr_number", "?"), "commits_empty"))
            if pr.get("reviews") is not None and len(pr.get("reviews", [])) == 0:
                pass  # reviews can legitimately be empty

    # Check for missing repos
    for repo in EXPECTED_REPOS:
        slug = repo_to_slug(repo)
        if slug not in pr_files:
            # Try alternate slug
            alt_slug = slug.replace(".", "")  # next.js -> nextjs
            if alt_slug not in pr_files:
                issues.append(f"MISSING: prs-{slug}.json")

    # Report field issues
    repos_with_field_issues = {s for s, problems in field_issues.items() if len(problems) > 5}
    if repos_with_field_issues:
        print(f"   Field issues in: {len(repos_with_field_issues)} repos")
        for slug in sorted(repos_with_field_issues):
            problems = field_issues[slug]
            field_counts = Counter(f for _, f in problems)
            print(f"     {slug}: {dict(field_counts)}")
            issues.append(f"FIELD_GAPS: {slug} — {dict(field_counts)}")

    # --- 2. CatchRate output ---
    print("\n## 2. CatchRate Output (catchrate-*.json)")
    cr_files = {fp.stem.replace("catchrate-", ""): fp for fp in DATA_DIR.glob("catchrate-*.json")}
    print(f"   Found: {len(cr_files)} files")

    cr_counts = {}
    cr_escape_counts = {}
    for slug, fp in sorted(cr_files.items()):
        with open(fp) as f:
            cr = json.load(f)
        prs_list = cr.get("prs", [])
        cr_counts[slug] = len(prs_list)
        cr_escape_counts[slug] = sum(1 for p in prs_list if p.get("escaped"))

        # Check if PR counts match raw data
        if slug in pr_counts:
            raw_merged = pr_counts[slug]  # not all raw PRs are merged
            if cr_counts[slug] == 0:
                issues.append(f"EMPTY_CATCHRATE: {slug} (0 PRs classified)")

    # Missing catchrate files
    for slug in pr_files:
        if slug not in cr_files:
            issues.append(f"MISSING: catchrate-{slug}.json")

    # --- 3. LLM Scores ---
    print("\n## 3. LLM Scores")

    # Engagement scores
    eng_files = {fp.stem.replace("engagement-", ""): fp for fp in DATA_DIR.glob("engagement-*.json")}
    print(f"   Engagement files: {len(eng_files)}")

    eng_coverage = {}
    eng_errors = {}
    for slug, fp in sorted(eng_files.items()):
        with open(fp) as f:
            eng = json.load(f)
        # Handle both list and dict formats
        if isinstance(eng, list):
            items = eng
            scored = sum(1 for v in items if "error" not in v and v.get("overall_human_engagement") is not None)
            errored = sum(1 for v in items if "error" in v)
            total = len(items)
        else:
            scored = sum(1 for v in eng.values() if "error" not in v and v.get("engagement_score") is not None)
            errored = sum(1 for v in eng.values() if "error" in v)
            total = len(eng)
        eng_coverage[slug] = scored
        eng_errors[slug] = errored
        if errored > 0:
            warnings.append(f"ENGAGEMENT_ERRORS: {slug} — {errored}/{total} errors")

    # Spec quality scores
    sq_files = {fp.stem.replace("spec-quality-", ""): fp for fp in DATA_DIR.glob("spec-quality-*.json")}
    print(f"   Spec quality files: {len(sq_files)}")

    sq_errors = {}
    for slug, fp in sorted(sq_files.items()):
        with open(fp) as f:
            sq = json.load(f)
        if isinstance(sq, list):
            items = sq
            errored = sum(1 for v in items if "error" in v)
            total = len(items)
        else:
            errored = sum(1 for v in sq.values() if "error" in v)
            total = len(sq)
        sq_errors[slug] = errored
        if errored > 0:
            warnings.append(f"SPEC_QUALITY_ERRORS: {slug} — {errored}/{total} errors")

    # Missing score files
    for slug in pr_files:
        if slug not in eng_files:
            issues.append(f"MISSING: engagement-{slug}.json")
        if slug not in sq_files:
            issues.append(f"MISSING: spec-quality-{slug}.json")

    # --- 4. Features CSV ---
    print("\n## 4. Feature Data (pr-features.csv)")
    features_path = DATA_DIR / "pr-features.csv"
    if features_path.exists():
        with open(features_path) as f:
            reader = csv.DictReader(f)
            feat_rows = list(reader)
        feat_repos = Counter(r.get("repo", "") for r in feat_rows)
        print(f"   Total rows: {len(feat_rows)}")
        print(f"   Repos: {len(feat_repos)}")

        # Check for repos with 0 features
        for slug in pr_files:
            repo_name = slug.replace("-", "/", 1)
            if repo_name not in feat_repos:
                warnings.append(f"NO_FEATURES: {repo_name}")
    else:
        issues.append("MISSING: pr-features.csv")

    # --- 5. Master CSV ---
    print("\n## 5. Master CSV (master-prs.csv)")
    master_path = DATA_DIR / "master-prs.csv"
    if master_path.exists():
        with open(master_path) as f:
            reader = csv.DictReader(f)
            master_rows = list(reader)
        master_repos = Counter(r.get("repo", "") for r in master_rows)
        print(f"   Total rows: {len(master_rows)}")
        print(f"   Repos: {len(master_repos)}")

        # Check columns
        if master_rows:
            cols = list(master_rows[0].keys())
            print(f"   Columns: {len(cols)}")
            expected_cols = ["repo", "pr_number", "title", "author", "merged_at",
                             "rework", "escaped", "escape_confidence",
                             "engagement_score", "spec_quality_score"]
            missing_cols = [c for c in expected_cols if c not in cols]
            if missing_cols:
                warnings.append(f"MASTER_MISSING_COLS: {missing_cols}")
    else:
        issues.append("MISSING: master-prs.csv")

    # --- 6. Enforcement Scores ---
    print("\n## 6. Enforcement Scores")
    enf_path = DATA_DIR / "enforcement-scores.json"
    if enf_path.exists():
        with open(enf_path) as f:
            enf = json.load(f)
        print(f"   Repos scored: {len(enf)}")
    else:
        warnings.append("MISSING: enforcement-scores.json")

    # --- 7. Repo Infrastructure ---
    print("\n## 7. Repo Infrastructure")
    infra_path = DATA_DIR / "repo-infra.json"
    if infra_path.exists():
        with open(infra_path) as f:
            infra = json.load(f)
        print(f"   Repos: {len(infra)}")
    else:
        warnings.append("MISSING: repo-infra.json")

    # --- 8. Validation Data ---
    print("\n## 8. Validation Data")

    hc_path = DATA_DIR / "high-confidence-validation.json"
    if hc_path.exists():
        with open(hc_path) as f:
            hc = json.load(f)
        hc_valid = sum(1 for v in hc.values() if "error" not in v)
        hc_errors = sum(1 for v in hc.values() if "error" in v)
        print(f"   HIGH confidence: {hc_valid} valid, {hc_errors} errors")
        if hc_errors > 0:
            issues.append(f"HC_VALIDATION_ERRORS: {hc_errors} pairs have errors (need re-scoring)")

    cv_path = DATA_DIR / "catchrate-validation-results.json"
    if cv_path.exists():
        with open(cv_path) as f:
            cv = json.load(f)
        cv_valid = sum(1 for v in cv.values() if "error" not in v)
        cv_errors = sum(1 for v in cv.values() if "error" in v)
        print(f"   Prior validation: {cv_valid} valid, {cv_errors} errors")
        if cv_errors > 0:
            issues.append(f"CV_VALIDATION_ERRORS: {cv_errors} pairs have errors (need re-scoring)")

    # --- Summary ---
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    if issues:
        print(f"\n🔴 ISSUES ({len(issues)}) — must fix:")
        for issue in sorted(issues):
            print(f"   {issue}")

    if warnings:
        print(f"\n🟡 WARNINGS ({len(warnings)}) — should investigate:")
        for warn in sorted(warnings):
            print(f"   {warn}")

    if not issues and not warnings:
        print("\n✅ All data checks passed")

    # --- Per-repo completeness matrix ---
    print("\n" + "=" * 70)
    print("PER-REPO COMPLETENESS")
    print("=" * 70)
    print(f"{'Repo':<35} {'PRs':>5} {'CR':>5} {'Eng':>5} {'Spec':>5} {'Esc':>4}")
    print("-" * 70)

    all_slugs = sorted(set(list(pr_files.keys()) + list(cr_files.keys())))
    for slug in all_slugs:
        pr_n = pr_counts.get(slug, 0)
        cr_n = cr_counts.get(slug, 0)
        eng_n = eng_coverage.get(slug, 0)
        eng_e = eng_errors.get(slug, 0)
        sq_e = sq_errors.get(slug, 0)
        esc_n = cr_escape_counts.get(slug, 0)

        eng_str = f"{eng_n}" if eng_e == 0 else f"{eng_n}({eng_e}e)"
        sq_str = "✓" if slug in sq_files and sq_e == 0 else f"({sq_e}e)" if sq_e > 0 else "✗"

        flags = []
        if slug not in pr_files:
            flags.append("no-prs")
        if slug not in cr_files:
            flags.append("no-cr")
        if slug not in eng_files:
            flags.append("no-eng")
        if slug not in sq_files:
            flags.append("no-sq")

        flag_str = " " + ",".join(flags) if flags else ""
        print(f"  {slug:<33} {pr_n:>5} {cr_n:>5} {eng_str:>8} {sq_str:>5} {esc_n:>4}{flag_str}")


def show_fixes():
    """Show commands to fix issues."""
    print("=== COMMANDS TO FIX DATA ISSUES ===\n")

    # Check HC validation errors
    hc_path = DATA_DIR / "high-confidence-validation.json"
    if hc_path.exists():
        with open(hc_path) as f:
            hc = json.load(f)
        errors = {k: v for k, v in hc.items() if "error" in v}
        if errors:
            print(f"# Re-score {len(errors)} HC validation errors:")
            print(f"# Delete error entries and re-run:")
            print(f"python3 validate-high-confidence.py\n")

    # Check prior validation errors
    cv_path = DATA_DIR / "catchrate-validation-results.json"
    if cv_path.exists():
        with open(cv_path) as f:
            cv = json.load(f)
        errors = {k: v for k, v in cv.items() if "error" in v}
        if errors:
            print(f"# Re-score {len(errors)} prior validation errors:")
            print(f"python3 validate-catchrate.py\n")

    # Check engagement errors
    for fp in sorted(DATA_DIR.glob("engagement-*.json")):
        with open(fp) as f:
            eng = json.load(f)
        items = eng if isinstance(eng, list) else list(eng.values())
        errors = sum(1 for v in items if isinstance(v, dict) and "error" in v)
        if errors > 0:
            slug = fp.stem.replace("engagement-", "")
            print(f"# Re-score {errors} engagement errors for {slug}:")
            print(f"python3 score_all.py {slug.replace('-', '/', 1)}\n")

    # Check spec quality errors
    for fp in sorted(DATA_DIR.glob("spec-quality-*.json")):
        with open(fp) as f:
            sq = json.load(f)
        items = sq if isinstance(sq, list) else list(sq.values())
        errors = sum(1 for v in items if isinstance(v, dict) and "error" in v)
        if errors > 0:
            slug = fp.stem.replace("spec-quality-", "")
            print(f"# Re-score {errors} spec-quality errors for {slug}:")
            print(f"python3 score_all.py {slug.replace('-', '/', 1)}\n")

    # Missing files
    pr_slugs = {fp.stem.replace("prs-", "") for fp in DATA_DIR.glob("prs-*.json")}
    eng_slugs = {fp.stem.replace("engagement-", "") for fp in DATA_DIR.glob("engagement-*.json")}
    sq_slugs = {fp.stem.replace("spec-quality-", "") for fp in DATA_DIR.glob("spec-quality-*.json")}
    cr_slugs = {fp.stem.replace("catchrate-", "") for fp in DATA_DIR.glob("catchrate-*.json")}

    missing_eng = pr_slugs - eng_slugs
    missing_sq = pr_slugs - sq_slugs
    missing_cr = pr_slugs - cr_slugs

    if missing_eng:
        print(f"# Missing engagement scores for {len(missing_eng)} repos:")
        for s in sorted(missing_eng):
            print(f"python3 score_all.py {s.replace('-', '/', 1)}")
        print()

    if missing_sq:
        print(f"# Missing spec-quality scores for {len(missing_sq)} repos:")
        for s in sorted(missing_sq):
            print(f"python3 score_all.py {s.replace('-', '/', 1)}")
        print()

    if missing_cr:
        print(f"# Missing catchrate output for {len(missing_cr)} repos:")
        for s in sorted(missing_cr):
            print(f"catchrate {s.replace('-', '/', 1)}")
        print()

    print("# After fixing, rebuild master CSV:")
    print("python3 build-unified-csv.py")
    print("python3 compute-features.py")
    print("python3 build-master-csv.py")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fix", action="store_true", help="Show commands to fix issues")
    args = parser.parse_args()

    audit()

    if args.fix:
        print()
        show_fixes()


if __name__ == "__main__":
    main()
