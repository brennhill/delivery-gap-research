#!/usr/bin/env python3
"""
JIT feature profiles: AI vs Human, Buggy vs Clean.

Compares JIT risk feature distributions between AI-tagged and human PRs,
and between bug-introducing and clean PRs, for the recent 3-month window.
"""

import pandas as pd
import numpy as np
from scipy import stats
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

df = pd.read_csv(DATA_DIR / "master-prs.csv", low_memory=False)
szz = pd.read_csv(DATA_DIR / "szz-results-merged.csv")
jit = pd.read_csv(DATA_DIR / "jit-features-merged.csv")

df["merged_at"] = pd.to_datetime(df["merged_at"], utc=True, errors="coerce")
for col in ["reworked", "specd"]:
    df[col] = df[col].fillna(False).astype(bool)
df["ai_tagged"] = df["f_ai_tagged"].fillna(False).astype(bool)

# SZZ merge
bug_prs = szz[["repo", "bug_pr_number"]].drop_duplicates()
bug_prs = bug_prs.rename(columns={"bug_pr_number": "pr_number"})
bug_prs["szz_buggy"] = True
df = df.merge(bug_prs, on=["repo", "pr_number"], how="left")
df["szz_buggy"] = df["szz_buggy"].fillna(False).astype(bool)

# JIT merge
jit_cols = [c for c in ["repo", "pr_number", "ns", "nd", "nf", "entropy",
            "la", "ld", "lt", "fix", "ndev", "age", "nuc", "exp", "rexp", "sexp"]
            if c in jit.columns]
df = df.merge(jit[jit_cols], on=["repo", "pr_number"], how="left")

# Bot exclusion
df["is_bot"] = df["f_is_bot_author"].fillna(False).astype(bool)
df = df[~df["is_bot"]].copy()

# Restrict to SZZ repos with JIT data
szz_repo_set = set(szz["repo"].unique())
df = df[df["repo"].isin(szz_repo_set)].copy()

jit_feats = ["ns", "nd", "nf", "entropy", "la", "ld", "lt", "fix",
             "ndev", "age", "nuc", "exp", "rexp", "sexp"]

# Restrict to PRs with complete JIT data to avoid differential missingness
# (AI vs human groups may have different JIT coverage rates)
jit_available = [f for f in jit_feats if f in df.columns]
n_before = len(df)
df = df.dropna(subset=jit_available).copy()
print(f"Restricted to complete JIT data: {n_before:,} → {len(df):,} PRs ({len(df)/n_before*100:.1f}%)")

# Recent 3 months
cutoff = pd.Timestamp("2026-01-01", tz="UTC")
recent = df[df["merged_at"] >= cutoff].copy()

# Feature labels for readability
feat_labels = {
    "ns": "subsystems",
    "nd": "directories",
    "nf": "files",
    "entropy": "change entropy",
    "la": "lines added",
    "ld": "lines deleted",
    "lt": "lines in file",
    "fix": "is bug fix",
    "ndev": "prior developers",
    "age": "file age (days)",
    "nuc": "prior changes",
    "exp": "author experience",
    "rexp": "recent experience",
    "sexp": "subsystem exp",
}


def compare_groups(group_a, group_b, label_a, label_b, feats):
    print(f"\n  {'Feature':>15s} ({'':>13s})  {label_a:>10s}  {label_b:>10s}  {'Ratio':>7s}  {'p':>10s}")
    print(f"  {'─'*15} {'─'*15}  {'─'*10}  {'─'*10}  {'─'*7}  {'─'*10}")

    for feat in feats:
        a_vals = group_a[feat].dropna()
        b_vals = group_b[feat].dropna()
        if len(a_vals) < 30 or len(b_vals) < 30:
            continue
        a_med = a_vals.median()
        b_med = b_vals.median()
        ratio = a_med / b_med if b_med != 0 else float("inf")
        try:
            _, p = stats.mannwhitneyu(a_vals, b_vals, alternative="two-sided")
            sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else ""
        except Exception:
            p = 1.0
            sig = ""
        label = feat_labels.get(feat, feat)
        print(f"  {feat:>15s} ({label:>13s})  {a_med:10.1f}  {b_med:10.1f}  {ratio:7.2f}  {p:10.4f} {sig}")


# ════════════════════════════════════════════════════════════════════
# 1. AI vs HUMAN (recent 3 months)
# ════════════════════════════════════════════════════════════════════
print("=" * 70)
print("1. JIT FEATURE PROFILES: AI vs HUMAN (Jan-Mar 2026)")
print("=" * 70)

ai = recent[recent["ai_tagged"]].copy()
human = recent[~recent["ai_tagged"]].copy()

print(f"\n  AI-tagged PRs: {len(ai):,} (bug rate: {ai['szz_buggy'].mean():.1%})")
print(f"  Human PRs:     {len(human):,} (bug rate: {human['szz_buggy'].mean():.1%})")

compare_groups(ai, human, "AI med", "Human med", jit_feats)


# ════════════════════════════════════════════════════════════════════
# 2. BUGGY vs CLEAN (recent 3 months, all PRs)
# ════════════════════════════════════════════════════════════════════
print(f"\n\n{'=' * 70}")
print("2. JIT FEATURE PROFILES: BUGGY vs CLEAN (Jan-Mar 2026)")
print("=" * 70)

buggy = recent[recent["szz_buggy"] == True].copy()
clean = recent[recent["szz_buggy"] == False].copy()

print(f"\n  Buggy PRs: {len(buggy):,}")
print(f"  Clean PRs: {len(clean):,}")

compare_groups(buggy, clean, "Buggy med", "Clean med", jit_feats)


# ════════════════════════════════════════════════════════════════════
# 3. AI BUGGY vs AI CLEAN (recent 3 months)
# ════════════════════════════════════════════════════════════════════
print(f"\n\n{'=' * 70}")
print("3. AI PRs ONLY: BUGGY vs CLEAN (Jan-Mar 2026)")
print("=" * 70)

ai_buggy = ai[ai["szz_buggy"] == True].copy()
ai_clean = ai[ai["szz_buggy"] == False].copy()

print(f"\n  AI buggy: {len(ai_buggy):,}")
print(f"  AI clean: {len(ai_clean):,}")

compare_groups(ai_buggy, ai_clean, "Buggy med", "Clean med", jit_feats)


# ════════════════════════════════════════════════════════════════════
# 4. HUMAN BUGGY vs HUMAN CLEAN (recent 3 months)
# ════════════════════════════════════════════════════════════════════
print(f"\n\n{'=' * 70}")
print("4. HUMAN PRs ONLY: BUGGY vs CLEAN (Jan-Mar 2026)")
print("=" * 70)

human_buggy = human[human["szz_buggy"] == True].copy()
human_clean = human[human["szz_buggy"] == False].copy()

print(f"\n  Human buggy: {len(human_buggy):,}")
print(f"  Human clean: {len(human_clean):,}")

compare_groups(human_buggy, human_clean, "Buggy med", "Clean med", jit_feats)


# ════════════════════════════════════════════════════════════════════
# 5. SPEC'D vs UNSPEC'D feature profiles (recent 3 months)
# ════════════════════════════════════════════════════════════════════
print(f"\n\n{'=' * 70}")
print("5. SPEC'D vs UNSPEC'D: JIT FEATURE PROFILES (Jan-Mar 2026)")
print("=" * 70)

specd = recent[recent["specd"]].copy()
unspesd = recent[~recent["specd"]].copy()

print(f"\n  Spec'd PRs:   {len(specd):,} (bug rate: {specd['szz_buggy'].mean():.1%})")
print(f"  Unspec'd PRs: {len(unspesd):,} (bug rate: {unspesd['szz_buggy'].mean():.1%})")

compare_groups(specd, unspesd, "Spec med", "Unspec med", jit_feats)

print(f"\n\nInterpretation:")
print(f"  If spec'd PRs have higher JIT risk features (more subsystems,")
print(f"  more entropy, more lines, more prior changes), this directly")
print(f"  demonstrates confounding by indication: specs accompany harder tasks.")
