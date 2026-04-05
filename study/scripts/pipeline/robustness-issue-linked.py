#!/usr/bin/env python3
"""
Robustness check: Do ISSUE-LINKED specs reduce defects?

Addresses the objection: "PR descriptions aren't real specs. Linked GitHub
issues are the closest thing to pre-implementation specifications."

Tests H1-H4 using only PRs with linked GitHub issues (#NNN or github.com
issue URLs) as the treatment group, excluding ticket IDs and template sections.

Uses within-author LPM with full demeaning + clustered SEs.
"""

import pandas as pd
import numpy as np
import statsmodels.api as sm
import json
import re
import sys
from pathlib import Path
from datetime import datetime, timezone

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
OUT_FILE = Path(__file__).resolve().parent.parent.parent / "results" / "robustness-issue-linked.txt"

class Tee:
    def __init__(self, *files):
        self.files = files
    def write(self, obj):
        for f in self.files:
            f.write(obj)
            f.flush()
    def flush(self):
        for f in self.files:
            f.flush()

out_f = open(OUT_FILE, "w")
sys.stdout = Tee(sys.__stdout__, out_f)

print(f"Issue-linked robustness run: {datetime.now(timezone.utc).isoformat()}")
print(f"Script: {__file__}")

# ── Load and prep ─────────────────────────────────────────────────────

df = pd.read_csv(DATA_DIR / "master-prs.csv", low_memory=False)
szz = pd.read_csv(DATA_DIR / "szz-results-merged.csv")

for col in ["reworked", "specd"]:
    if col in df.columns:
        df[col] = df[col].fillna(False).astype(bool)

bug_prs = szz[["repo", "bug_pr_number"]].drop_duplicates()
bug_prs = bug_prs.rename(columns={"bug_pr_number": "pr_number"})
bug_prs["szz_buggy"] = True
df = df.merge(bug_prs, on=["repo", "pr_number"], how="left")
df["szz_buggy"] = df["szz_buggy"].fillna(False).astype(int)

df["ai_tagged"] = df["f_ai_tagged"].fillna(False).astype(bool)
df["is_bot"] = df["f_is_bot_author"].fillna(False).astype(bool)
df = df[~df["is_bot"]].copy()
df["reworked"] = df["reworked"].astype(int)

df["log_add"] = np.log1p(df["additions"].astype(float))
df["log_del"] = np.log1p(df["deletions"].astype(float))
df["log_files"] = np.log1p(df["files_count"].astype(float))

szz_repo_set = set(szz["repo"].unique())
df["in_szz"] = df["repo"].isin(szz_repo_set)

SIZE_CONTROLS = ["log_add", "log_del", "log_files"]

# ── Identify issue-linked PRs ────────────────────────────────────────

issue_linked = set()
for p in sorted(DATA_DIR.glob("spec-signals-*.json")):
    with open(p) as f:
        data = json.load(f)
    repo = data.get("repo", "")
    for pr in data["coverage"]["prs"]:
        if not pr.get("specd"):
            continue
        src = str(pr.get("spec_source", "") or "")
        if re.match(r"#\d+$", src) or ("github.com" in src and "/issues/" in src):
            issue_linked.add((repo, int(pr["number"])))

df["has_github_issue"] = df.apply(
    lambda r: (r["repo"], r["pr_number"]) in issue_linked, axis=1
)

n_total = len(df)
n_issue = df["has_github_issue"].sum()
n_specd = df["specd"].sum()
n_no_spec = (~df["specd"]).sum()

print(f"\nDataset: {n_total:,} PRs (non-bot)")
print(f"  With linked GitHub issue: {n_issue:,} ({n_issue/n_total*100:.1f}%)")
print(f"  Spec'd (any source): {n_specd:,} ({n_specd/n_total*100:.1f}%)")
print(f"  No spec: {n_no_spec:,} ({n_no_spec/n_total*100:.1f}%)")
print(f"  Spec'd but no issue link: {n_specd - n_issue:,}")


# ── Within-author LPM ────────────────────────────────────────────────

def within_author_lpm(data, treatment_col, outcome_col, controls=None,
                      min_prs=2, label=""):
    if controls is None:
        controls = SIZE_CONTROLS

    ac = data["author"].value_counts()
    multi = data[data["author"].isin(ac[ac >= min_prs].index)].copy()
    if len(multi) < 50:
        print(f"  [{label}] Too few PRs: {len(multi)}")
        return None

    all_cols = [treatment_col] + controls + [outcome_col]
    for col in all_cols:
        multi[col] = pd.to_numeric(multi[col], errors="coerce")
    multi = multi.dropna(subset=all_cols)

    if len(multi) < 50:
        print(f"  [{label}] Too few complete cases: {len(multi)}")
        return None

    author_var = multi.groupby("author")[treatment_col].agg(["min", "max"])
    n_with_var = (author_var["min"] != author_var["max"]).sum()
    n_authors = multi["author"].nunique()

    author_means = multi.groupby("author")[all_cols].transform("mean")
    demeaned = multi[all_cols] - author_means

    X = demeaned[[treatment_col] + controls]
    y = demeaned[outcome_col]

    try:
        model = sm.OLS(y, X, hasconst=False).fit(
            cov_type="cluster",
            cov_kwds={"groups": multi["author"]},
        )
    except Exception as e:
        print(f"  [{label}] OLS failed: {e}")
        return None

    coef = model.params[treatment_col]
    pval = model.pvalues[treatment_col]
    ci = model.conf_int().loc[treatment_col]
    sig = "***" if pval < 0.001 else "**" if pval < 0.01 else "*" if pval < 0.05 else ""

    print(f"  [{label}] N={len(multi):,}, authors={n_authors:,} "
          f"({n_with_var:,} with variation)")
    print(f"  coef={coef:+.4f}, p={pval:.4f}, 95% CI [{ci[0]:+.4f}, {ci[1]:+.4f}] {sig}")

    return {"coef": coef, "p": pval, "n": len(multi),
            "n_authors": n_authors, "n_with_var": n_with_var}


# ════════════════════════════════════════════════════════════════════
# TEST 1: ISSUE-LINKED vs NO SPEC (cleanest comparison)
# ════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("TEST 1: GITHUB ISSUE-LINKED vs NO SPEC")
print("=" * 70)
print("Excludes ticket-ID and template-section specs.")
print("This is the cleanest pre-implementation spec vs no spec comparison.")

subset = df[df["has_github_issue"] | ~df["specd"]].copy()
subset["has_issue"] = subset["has_github_issue"].astype(int)
szz_sub = subset[subset["in_szz"]].copy()

print(f"\n  Issue-linked: {subset['has_issue'].sum():,}")
print(f"  No spec: {(~subset['specd']).sum():,}")

for grp, label in [(szz_sub[szz_sub["has_issue"] == 1], "issue"),
                    (szz_sub[szz_sub["has_issue"] == 0], "no spec")]:
    print(f"  Bug rate ({label}): {grp['szz_buggy'].mean():.1%}  "
          f"Rework rate: {subset[subset['has_issue'] == (1 if label == 'issue' else 0)]['reworked'].mean():.1%}")

print(f"\n  H1: Issue-linked → bugs:")
r_h1 = within_author_lpm(szz_sub, "has_issue", "szz_buggy", label="issue-H1")

print(f"\n  H2: Issue-linked → rework:")
r_h2 = within_author_lpm(subset, "has_issue", "reworked", label="issue-H2")

# Quality on issue-linked subset
scored_szz = szz_sub[szz_sub["q_overall"].notna() & (szz_sub["has_issue"] == 1)].copy()
if len(scored_szz) > 50:
    print(f"\n  H3: Quality → bugs (issue-linked only, N={len(scored_szz):,}):")
    r_h3 = within_author_lpm(scored_szz, "q_overall", "szz_buggy", label="issue-H3")
else:
    print(f"\n  H3: SKIPPED ({len(scored_szz)} scored issue-linked PRs)")
    r_h3 = None

scored_all = subset[subset["q_overall"].notna() & (subset["has_issue"] == 1)].copy()
if len(scored_all) > 50:
    print(f"\n  H4: Quality → rework (issue-linked only, N={len(scored_all):,}):")
    r_h4 = within_author_lpm(scored_all, "q_overall", "reworked", label="issue-H4")
else:
    print(f"\n  H4: SKIPPED ({len(scored_all)} scored issue-linked PRs)")
    r_h4 = None


# ════════════════════════════════════════════════════════════════════
# TEST 2: AI + ISSUE-LINKED
# ════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("TEST 2: AI-TAGGED + ISSUE-LINKED (closest to agentic SDD)")
print("=" * 70)

ai_issue = df[df["ai_tagged"] & df["has_github_issue"]]
ai_no_spec = df[df["ai_tagged"] & ~df["specd"]]
ai_subset = df[df["ai_tagged"] & (df["has_github_issue"] | ~df["specd"])].copy()
ai_subset["has_issue"] = ai_subset["has_github_issue"].astype(int)
ai_szz = ai_subset[ai_subset["in_szz"]].copy()

print(f"\n  AI + issue-linked: {len(ai_issue):,}")
print(f"  AI + no spec: {len(ai_no_spec):,}")

if len(ai_szz) > 100 and ai_szz["has_issue"].sum() > 10:
    print(f"\n  AI + issue-linked → bugs:")
    within_author_lpm(ai_szz, "has_issue", "szz_buggy", label="ai-issue-bugs")

    print(f"\n  AI + issue-linked → rework:")
    within_author_lpm(ai_subset, "has_issue", "reworked", label="ai-issue-rework")
else:
    print("  SKIPPED (too few AI + issue-linked PRs)")


# ════════════════════════════════════════════════════════════════════
# TEST 3: ISSUE-LINKED vs TICKET-ID ONLY (spec type comparison)
# ════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("TEST 3: ISSUE-LINKED vs TICKET-ID SPECS")
print("=" * 70)
print("Do PRs with GitHub issues have different outcomes than PRs with")
print("just a PROJ-123 ticket reference? Both are 'spec'd' but the issue")
print("content is visible to us while the ticket content is not.")

ticket_only = set()
for p in sorted(DATA_DIR.glob("spec-signals-*.json")):
    with open(p) as f:
        data = json.load(f)
    repo = data.get("repo", "")
    for pr in data["coverage"]["prs"]:
        if not pr.get("specd"):
            continue
        src = str(pr.get("spec_source", "") or "")
        if "-" in src and src.split("-")[0].isupper() and not src.startswith("#"):
            if (repo, int(pr["number"])) not in issue_linked:
                ticket_only.add((repo, int(pr["number"])))

df["has_ticket_only"] = df.apply(
    lambda r: (r["repo"], r["pr_number"]) in ticket_only, axis=1
)

print(f"\n  Issue-linked: {df['has_github_issue'].sum():,}")
print(f"  Ticket-only: {df['has_ticket_only'].sum():,}")

spec_compare = df[df["has_github_issue"] | df["has_ticket_only"]].copy()
spec_compare["is_issue"] = spec_compare["has_github_issue"].astype(int)
spec_szz = spec_compare[spec_compare["in_szz"]].copy()

if len(spec_szz) > 200:
    print(f"\n  Issue vs ticket → bugs (within-author):")
    within_author_lpm(spec_szz, "is_issue", "szz_buggy", label="issue-vs-ticket-bugs")

    print(f"\n  Issue vs ticket → rework (within-author):")
    within_author_lpm(spec_compare, "is_issue", "reworked", label="issue-vs-ticket-rework")

    # Raw rates
    issue_bug = spec_szz[spec_szz["is_issue"] == 1]["szz_buggy"].mean()
    ticket_bug = spec_szz[spec_szz["is_issue"] == 0]["szz_buggy"].mean()
    issue_rw = spec_compare[spec_compare["is_issue"] == 1]["reworked"].mean()
    ticket_rw = spec_compare[spec_compare["is_issue"] == 0]["reworked"].mean()
    print(f"\n  Raw rates:")
    print(f"    Issue-linked: bugs={issue_bug:.1%}, rework={issue_rw:.1%}")
    print(f"    Ticket-only:  bugs={ticket_bug:.1%}, rework={ticket_rw:.1%}")


# ════════════════════════════════════════════════════════════════════
# SUMMARY
# ════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)

print(f"""
Issue-linked GitHub issues are the closest available proxy for
pre-implementation specifications. If any spec type should show
a protective effect, it is this one.

Results:
  H1 (issue → bugs):    {'coef=' + f"{r_h1['coef']:+.4f}, p={r_h1['p']:.4f}" if r_h1 else 'SKIPPED'}
  H2 (issue → rework):  {'coef=' + f"{r_h2['coef']:+.4f}, p={r_h2['p']:.4f}" if r_h2 else 'SKIPPED'}
  H3 (quality → bugs):  {'coef=' + f"{r_h3['coef']:+.4f}, p={r_h3['p']:.4f}" if r_h3 else 'SKIPPED'}
  H4 (quality → rework): {'coef=' + f"{r_h4['coef']:+.4f}, p={r_h4['p']:.4f}" if r_h4 else 'SKIPPED'}
""")

print(f"Results saved to: {OUT_FILE}")
out_f.close()
sys.stdout = sys.__stdout__
print(f"Issue-linked robustness complete. Results in {OUT_FILE}")
