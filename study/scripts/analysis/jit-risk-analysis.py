#!/usr/bin/env python3
"""
JIT Risk Analysis: Do specs produce structurally better code?

Sidesteps defect detection entirely. Asks whether spec'd PRs have
lower-risk change profiles (smaller, more focused, less churn)
than unspec'd PRs.
"""

import pandas as pd
import numpy as np
from scipy import stats
import warnings
# Only suppress specific known-harmless warnings, not everything.
warnings.filterwarnings('ignore', message='.*divide by zero.*')
warnings.filterwarnings('ignore', message='.*invalid value.*')

DATA = '/Users/brenn/dev/ai-augmented-dev/research/study/data/master-prs.csv'

# ── Load and prep ──────────────────────────────────────────────────────
df = pd.read_csv(DATA)
print(f"Loaded {len(df):,} PRs from {df['repo'].nunique()} repos\n")

# Print columns for reference
print("=== ALL COLUMNS ===")
for i, c in enumerate(df.columns, 1):
    print(f"  {i:2d}. {c}")
print()

# ── Compute JIT risk features ─────────────────────────────────────────
df['additions'] = pd.to_numeric(df['additions'], errors='coerce').fillna(0)
df['deletions'] = pd.to_numeric(df['deletions'], errors='coerce').fillna(0)
df['files_count'] = pd.to_numeric(df['files_count'], errors='coerce').fillna(0)

df['jit_size'] = df['additions'] + df['deletions']
df['jit_spread'] = df['files_count']
# +1 smoothing avoids division by zero for PRs with 0 additions + 0 deletions.
# This is a Laplace-style smoothing, not the raw Kamei churn ratio.
df['jit_churn'] = df['deletions'] / (df['additions'] + df['deletions'] + 1)
df['jit_focus'] = df['files_count'] / (df['jit_size'] + 1)  # files per line changed

# Size buckets
def size_bucket(n):
    if n < 50: return 'small'
    if n < 200: return 'medium'
    if n < 500: return 'large'
    return 'huge'

df['jit_bucket'] = df['jit_size'].apply(size_bucket)

# ── Parse spec status ─────────────────────────────────────────────────
# specd column exists; q_overall has scores
df['specd'] = df['specd'].astype(str).str.strip().str.lower() == 'true'
df['q_overall'] = pd.to_numeric(df['q_overall'], errors='coerce')

# Has meaningful spec quality score
df['has_spec_score'] = df['q_overall'].notna() & (df['q_overall'] > 0)

# ── AI classification ─────────────────────────────────────────────────
# ai_probability column exists; also check f_ai_tagged, classification
df['ai_probability'] = pd.to_numeric(df['ai_probability'], errors='coerce')
df['f_ai_tagged'] = df['f_ai_tagged'].astype(str).str.strip().str.lower() == 'true'

# Two-bucket: Augmented if tagged OR high ai_probability
df['is_augmented'] = df['f_ai_tagged'] | (df['ai_probability'] > 0.5)
df['is_human'] = ~df['is_augmented']

# ── Filter out bots ──────────────────────────────────────────────────
df['f_is_bot_author'] = df['f_is_bot_author'].astype(str).str.strip().str.lower() == 'true'
df_nobots = df[~df['f_is_bot_author']].copy()
print(f"After removing bots: {len(df_nobots):,} PRs\n")

JIT_FEATURES = ['jit_size', 'jit_spread', 'jit_churn', 'jit_focus']
JIT_LABELS = {
    'jit_size': 'Lines changed',
    'jit_spread': 'Files changed',
    'jit_churn': 'Churn ratio',
    'jit_focus': 'Files/line (focus)'
}


# ══════════════════════════════════════════════════════════════════════
# Analysis 1: Spec'd vs unspec'd risk profiles
# ══════════════════════════════════════════════════════════════════════
print("=" * 70)
print("ANALYSIS 1: SPEC'D vs UNSPEC'D RISK PROFILES")
print("=" * 70)

specd = df_nobots[df_nobots['has_spec_score']]
unspecd = df_nobots[~df_nobots['has_spec_score']]

print(f"\n  Spec'd PRs: {len(specd):,}  |  Unspec'd PRs: {len(unspecd):,}\n")

print(f"  {'Feature':<20} {'Spec median':>12} {'Unspec median':>14} {'Spec mean':>12} {'Unspec mean':>14} {'M-W p':>10} {'Direction':>10}")
print(f"  {'-'*20} {'-'*12} {'-'*14} {'-'*12} {'-'*14} {'-'*10} {'-'*10}")

for feat in JIT_FEATURES:
    s_vals = specd[feat].dropna()
    u_vals = unspecd[feat].dropna()
    s_med = s_vals.median()
    u_med = u_vals.median()
    s_mean = s_vals.mean()
    u_mean = u_vals.mean()
    if len(s_vals) > 0 and len(u_vals) > 0:
        stat, p = stats.mannwhitneyu(s_vals, u_vals, alternative='two-sided')
        direction = "spec<unspec" if s_med < u_med else "spec>unspec" if s_med > u_med else "equal"
    else:
        p = float('nan')
        direction = "n/a"
    print(f"  {JIT_LABELS[feat]:<20} {s_med:>12.1f} {u_med:>14.1f} {s_mean:>12.1f} {u_mean:>14.1f} {p:>10.4f} {direction:>10}")

# Size bucket distribution
print(f"\n  Size bucket distribution:")
print(f"  {'Bucket':<10} {'Spec %':>10} {'Unspec %':>10}")
print(f"  {'-'*10} {'-'*10} {'-'*10}")
for bucket in ['small', 'medium', 'large', 'huge']:
    s_pct = (specd['jit_bucket'] == bucket).mean() * 100
    u_pct = (unspecd['jit_bucket'] == bucket).mean() * 100
    print(f"  {bucket:<10} {s_pct:>9.1f}% {u_pct:>9.1f}%")


# ══════════════════════════════════════════════════════════════════════
# Analysis 2: AI vs Human risk profiles (with/without specs)
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("ANALYSIS 2: AI vs HUMAN × SPEC INTERACTION")
print("=" * 70)

groups = {
    'AI + spec':       df_nobots[df_nobots['is_augmented'] & df_nobots['has_spec_score']],
    'AI + no spec':    df_nobots[df_nobots['is_augmented'] & ~df_nobots['has_spec_score']],
    'Human + spec':    df_nobots[df_nobots['is_human'] & df_nobots['has_spec_score']],
    'Human + no spec': df_nobots[df_nobots['is_human'] & ~df_nobots['has_spec_score']],
}

print(f"\n  Group sizes:")
for name, grp in groups.items():
    print(f"    {name:<20}: {len(grp):,} PRs")

print(f"\n  {'Group':<20} {'Lines med':>10} {'Files med':>10} {'Churn med':>10} {'% huge':>10}")
print(f"  {'-'*20} {'-'*10} {'-'*10} {'-'*10} {'-'*10}")
for name, grp in groups.items():
    lines_med = grp['jit_size'].median()
    files_med = grp['jit_spread'].median()
    churn_med = grp['jit_churn'].median()
    pct_huge = (grp['jit_bucket'] == 'huge').mean() * 100
    print(f"  {name:<20} {lines_med:>10.0f} {files_med:>10.0f} {churn_med:>10.3f} {pct_huge:>9.1f}%")

# Mann-Whitney: AI+spec vs AI+nospec, Human+spec vs Human+nospec
print(f"\n  Mann-Whitney U tests (spec vs no-spec within group):")
for author_type, label in [('augmented', 'AI'), ('human', 'Human')]:
    if author_type == 'augmented':
        with_spec = groups['AI + spec']
        without_spec = groups['AI + no spec']
    else:
        with_spec = groups['Human + spec']
        without_spec = groups['Human + no spec']

    print(f"\n    {label} PRs:")
    for feat in JIT_FEATURES:
        s = with_spec[feat].dropna()
        u = without_spec[feat].dropna()
        if len(s) > 5 and len(u) > 5:
            stat, p = stats.mannwhitneyu(s, u, alternative='two-sided')
            direction = "spec<" if s.median() < u.median() else "spec>" if s.median() > u.median() else "="
            print(f"      {JIT_LABELS[feat]:<20} p={p:.4f}  {direction}  (med: {s.median():.1f} vs {u.median():.1f})")
        else:
            print(f"      {JIT_LABELS[feat]:<20} insufficient data")


# ══════════════════════════════════════════════════════════════════════
# Analysis 3: Spec quality and risk profile
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("ANALYSIS 3: SPEC QUALITY × RISK PROFILE (Spearman correlations)")
print("=" * 70)

specd_with_q = df_nobots[df_nobots['q_overall'].notna() & (df_nobots['q_overall'] > 0)].copy()
print(f"\n  PRs with spec quality scores: {len(specd_with_q):,}")
print(f"  q_overall range: {specd_with_q['q_overall'].min():.0f} - {specd_with_q['q_overall'].max():.0f}")
print(f"  q_overall median: {specd_with_q['q_overall'].median():.0f}\n")

print(f"  {'Feature':<20} {'Spearman r':>10} {'p-value':>10} {'Direction':>20}")
print(f"  {'-'*20} {'-'*10} {'-'*10} {'-'*20}")
for feat in JIT_FEATURES:
    valid = specd_with_q[[feat, 'q_overall']].dropna()
    if len(valid) > 10:
        rho, p = stats.spearmanr(valid['q_overall'], valid[feat])
        if p < 0.05:
            direction = "higher quality → smaller" if rho < 0 else "higher quality → larger"
        else:
            direction = "not significant"
        print(f"  {JIT_LABELS[feat]:<20} {rho:>10.3f} {p:>10.4f} {direction:>20}")
    else:
        print(f"  {JIT_LABELS[feat]:<20} insufficient data")

# Also check sub-dimensions
print(f"\n  Sub-dimension correlations with jit_size:")
subdims = ['q_outcome_clarity', 'q_error_states', 'q_scope_boundaries',
           'q_acceptance_criteria', 'q_data_contracts', 'q_dependency_context',
           'q_behavioral_specificity']
for dim in subdims:
    # Convert on specd_with_q directly — converting on df_nobots doesn't
    # propagate because specd_with_q is a .copy() made before this loop.
    specd_with_q[dim] = pd.to_numeric(specd_with_q[dim], errors='coerce')
    valid = specd_with_q[['jit_size', dim]].dropna()
    if len(valid) > 10:
        rho, p = stats.spearmanr(valid[dim], valid['jit_size'])
        sig = "*" if p < 0.05 else " "
        print(f"    {dim:<30} r={rho:>6.3f}  p={p:.4f} {sig}")


# ══════════════════════════════════════════════════════════════════════
# Analysis 4: Per-repo comparison (controlling for repo)
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("ANALYSIS 4: PER-REPO SPEC'd vs UNSPEC'd (controlling for repo)")
print("=" * 70)

print(f"\n  {'Repo':<35} {'n_spec':>6} {'n_unsp':>6} {'med_spec':>9} {'med_unsp':>9} {'M-W p':>8} {'Dir':>8}")
print(f"  {'-'*35} {'-'*6} {'-'*6} {'-'*9} {'-'*9} {'-'*8} {'-'*8}")

repo_results = []
for repo in sorted(df_nobots['repo'].unique()):
    rdf = df_nobots[df_nobots['repo'] == repo]
    s = rdf[rdf['has_spec_score']]['jit_size']
    u = rdf[~rdf['has_spec_score']]['jit_size']
    if len(s) >= 10 and len(u) >= 10:
        stat, p = stats.mannwhitneyu(s, u, alternative='two-sided')
        direction = "spec<" if s.median() < u.median() else "spec>"
        print(f"  {repo:<35} {len(s):>6} {len(u):>6} {s.median():>9.0f} {u.median():>9.0f} {p:>8.4f} {direction:>8}")
        repo_results.append({
            'repo': repo, 'n_spec': len(s), 'n_unspec': len(u),
            'med_spec': s.median(), 'med_unspec': u.median(),
            'p': p, 'spec_smaller': s.median() < u.median()
        })

if repo_results:
    n_smaller = sum(1 for r in repo_results if r['med_spec'] < r['med_unspec'])
    n_sig_smaller = sum(1 for r in repo_results if r['med_spec'] < r['med_unspec'] and r['p'] < 0.05)
    n_tied = sum(1 for r in repo_results if r['med_spec'] == r['med_unspec'])
    n_larger = sum(1 for r in repo_results if r['med_spec'] > r['med_unspec'])
    n_sig_larger = sum(1 for r in repo_results if r['med_spec'] > r['med_unspec'] and r['p'] < 0.05)
    print(f"\n  Summary: {n_smaller}/{len(repo_results)} repos have smaller spec'd PRs ({n_sig_smaller} significant)")
    print(f"           {n_larger}/{len(repo_results)} repos have larger spec'd PRs ({n_sig_larger} significant)")
    if n_tied > 0:
        print(f"           {n_tied}/{len(repo_results)} repos have equal medians (excluded from sign test)")

    # Sign test across repos — exclude ties (standard practice)
    non_tied = [r for r in repo_results if r['med_spec'] != r['med_unspec']]
    if len(non_tied) > 0:
        n_pos = sum(1 for r in non_tied if r['med_spec'] < r['med_unspec'])
        binom_p = stats.binomtest(n_pos, len(non_tied), 0.5).pvalue
        print(f"  Sign test (spec smaller across repos, {len(non_tied)} non-tied): p={binom_p:.4f}")


# ══════════════════════════════════════════════════════════════════════
# Analysis 5: Effect size (Cohen's d) for key comparisons
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("ANALYSIS 5: EFFECT SIZES")
print("=" * 70)

def cohens_d(a, b):
    na, nb = len(a), len(b)
    pooled_std = np.sqrt(((na-1)*a.std()**2 + (nb-1)*b.std()**2) / (na+nb-2))
    if pooled_std == 0:
        return 0
    return (a.mean() - b.mean()) / pooled_std

print(f"\n  Cohen's d (spec'd - unspec'd, negative = spec'd smaller):")
for feat in JIT_FEATURES:
    s = specd[feat].dropna()
    u = unspecd[feat].dropna()
    d = cohens_d(s, u)
    magnitude = "negligible" if abs(d) < 0.2 else "small" if abs(d) < 0.5 else "medium" if abs(d) < 0.8 else "large"
    print(f"    {JIT_LABELS[feat]:<20} d={d:>7.3f}  ({magnitude})")


# ══════════════════════════════════════════════════════════════════════
# CLEAN SUMMARY
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 70)
print("=== DO SPECS PRODUCE STRUCTURALLY BETTER CODE? (JIT Risk Analysis) ===")
print("=" * 70)

print(f"""
Sample: {len(df_nobots):,} non-bot PRs from {df_nobots['repo'].nunique()} repos
  Spec'd (q_overall > 0): {len(specd):,}
  Unspec'd: {len(unspecd):,}

Spec'd vs unspec'd:
  Median lines changed:  {specd['jit_size'].median():.0f} vs {unspecd['jit_size'].median():.0f}
  Median files changed:  {specd['jit_spread'].median():.0f} vs {unspecd['jit_spread'].median():.0f}
  Median churn ratio:    {specd['jit_churn'].median():.3f} vs {unspecd['jit_churn'].median():.3f}
  % huge PRs (>500 lines): {(specd['jit_bucket']=='huge').mean()*100:.1f}% vs {(unspecd['jit_bucket']=='huge').mean()*100:.1f}%""")

# AI interaction
for label, grp_s, grp_u in [
    ('AI + spec vs AI + no spec', groups['AI + spec'], groups['AI + no spec']),
    ('Human + spec vs Human + no spec', groups['Human + spec'], groups['Human + no spec']),
]:
    if len(grp_s) > 5 and len(grp_u) > 5:
        stat, p = stats.mannwhitneyu(grp_s['jit_size'].dropna(), grp_u['jit_size'].dropna())
        print(f"\n{label}:")
        print(f"  Median lines: {grp_s['jit_size'].median():.0f} vs {grp_u['jit_size'].median():.0f}  (M-W p={p:.4f})")
        print(f"  Median files: {grp_s['jit_spread'].median():.0f} vs {grp_u['jit_spread'].median():.0f}")
        print(f"  % huge: {(grp_s['jit_bucket']=='huge').mean()*100:.1f}% vs {(grp_u['jit_bucket']=='huge').mean()*100:.1f}%")

if repo_results:
    print(f"\nPer-repo control:")
    print(f"  {n_smaller}/{len(repo_results)} repos: spec'd PRs are smaller")
    print(f"  {n_sig_smaller} of those are significant (p<0.05)")
    if len(non_tied) > 0:
        print(f"  Sign test p={binom_p:.4f}")
    else:
        print(f"  Sign test: all repos tied, cannot compute")

# Correlations summary
print(f"\nSpec quality correlations (Spearman, among spec'd PRs):")
for feat in JIT_FEATURES:
    valid = specd_with_q[[feat, 'q_overall']].dropna()
    if len(valid) > 10:
        rho, p = stats.spearmanr(valid['q_overall'], valid[feat])
        sig = "***" if p < 0.001 else "**" if p < 0.01 else "*" if p < 0.05 else "ns"
        print(f"  q_overall vs {JIT_LABELS[feat]:<20}: r={rho:.3f} {sig}")
