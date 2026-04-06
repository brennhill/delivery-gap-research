"""
Logistic regression: Do specs reduce defect risk after controlling for change size?

Six regressions (3 models × 2 DVs) + continuous q_overall analysis for spec'd PRs only.
"""

import pandas as pd
import numpy as np
import statsmodels.api as sm
from statsmodels.discrete.discrete_model import Logit
import warnings
warnings.filterwarnings("ignore")

SPECD_MAP = {
    True: 1.0,
    False: 0.0,
    "True": 1.0,
    "False": 0.0,
    "true": 1.0,
    "false": 0.0,
    1: 1.0,
    0: 0.0,
    "1": 1.0,
    "0": 0.0,
}

# ── Load data ──────────────────────────────────────────────────────
df = pd.read_csv("data/master-prs.csv")
print(f"Loaded {len(df):,} PRs")

# ── Create variables ───────────────────────────────────────────────
df["has_spec"] = df["specd"].map(SPECD_MAP)
df["log_additions"] = np.log1p(df["additions"])
df["log_deletions"] = np.log1p(df["deletions"])
df["log_files"] = np.log1p(df["files_count"])

# Ensure DVs are numeric
df["strict_escaped"] = df["strict_escaped"].map({True: 1, False: 0, 1: 1, 0: 0}).astype(float)
df["reworked"] = df["reworked"].map({True: 1, False: 0, 1: 1, 0: 0}).astype(float)

# ── Raw rates table ────────────────────────────────────────────────
print("\n" + "=" * 70)
print("RAW RATES: has_spec vs no_spec")
print("=" * 70)

for dv in ["strict_escaped", "reworked"]:
    print(f"\n  {dv}:")
    for spec_val, label in [(1, "has_spec"), (0, "no_spec ")]:
        subset = df[df["has_spec"] == spec_val]
        valid = subset[dv].dropna()
        rate = valid.mean()
        print(f"    {label}: {rate:.4f}  ({int(valid.sum()):,} / {len(valid):,})")

# ── Median change size comparison ──────────────────────────────────
print("\n" + "=" * 70)
print("MEDIAN CHANGE SIZE: has_spec vs no_spec")
print("=" * 70)

for spec_val, label in [(1, "has_spec"), (0, "no_spec ")]:
    subset = df[df["has_spec"] == spec_val]
    print(f"\n  {label} (n={len(subset):,}):")
    print(f"    additions:  {subset['additions'].median():.0f}")
    print(f"    deletions:  {subset['deletions'].median():.0f}")
    print(f"    files:      {subset['files_count'].median():.0f}")

# ── Helper to run logistic regression ──────────────────────────────
def run_logit(dv_name, iv_names, data, focus_var=None):
    """Run logistic regression, return results dict for focus_var (or first IV)."""
    cols = [dv_name] + iv_names
    sub = data[cols].dropna()
    if sub[dv_name].nunique() < 2:
        return None
    y = sub[dv_name]
    X = sm.add_constant(sub[iv_names])
    try:
        model = Logit(y, X).fit(disp=0, maxiter=100)
    except Exception as e:
        print(f"    [FAILED: {e}]")
        return None

    fv = focus_var or iv_names[0]
    coef = model.params[fv]
    pval = model.pvalues[fv]
    odds = np.exp(coef)
    return {"coef": coef, "p": pval, "odds": odds, "n": len(sub), "model": model}

def fmt_result(r, label=""):
    if r is None:
        return "  [model failed]"
    sig = "***" if r["p"] < 0.001 else "**" if r["p"] < 0.01 else "*" if r["p"] < 0.05 else ""
    direction = "REDUCES" if r["odds"] < 1 else "INCREASES"
    pct = abs(1 - r["odds"]) * 100
    return (f"  coef={r['coef']:+.4f}, OR={r['odds']:.4f}, p={r['p']:.4f}{sig}  "
            f"→ {direction} odds by {pct:.1f}%  (n={r['n']:,})")

# ── Run 6 regressions ─────────────────────────────────────────────
size_ivs = ["log_additions", "log_deletions", "log_files"]
review_ivs = ["review_cycles", "time_to_merge_hours"]

print("\n" + "=" * 70)
print("LOGISTIC REGRESSIONS: has_spec → DV")
print("=" * 70)

for dv in ["strict_escaped", "reworked"]:
    print(f"\n{'─' * 60}")
    print(f"DV: {dv}")
    print(f"{'─' * 60}")

    # Model 1: raw
    print(f"\n  Model 1 — Raw (no controls):")
    r1 = run_logit(dv, ["has_spec"], df)
    print(fmt_result(r1))

    # Model 2: + size
    print(f"\n  Model 2 — Controlling for change size:")
    r2 = run_logit(dv, ["has_spec"] + size_ivs, df, focus_var="has_spec")
    print(fmt_result(r2))

    # Model 3: + size + review
    print(f"\n  Model 3 — Controlling for change size + review effort:")
    r3 = run_logit(dv, ["has_spec"] + size_ivs + review_ivs, df, focus_var="has_spec")
    print(fmt_result(r3))

# ── Among spec'd PRs: does q_overall help? ────────────────────────
print("\n" + "=" * 70)
print("AMONG SPEC'D PRs: q_overall (continuous) → DV")
print("=" * 70)

specd_scored = df[(df["has_spec"] == 1) & df["q_overall"].notna()].copy()
print(f"\n  Spec'd + scored PRs: {len(specd_scored):,}")
print(f"  q_overall range: {specd_scored['q_overall'].min():.2f} – {specd_scored['q_overall'].max():.2f}")
print(f"  q_overall median: {specd_scored['q_overall'].median():.2f}")

for dv in ["strict_escaped", "reworked"]:
    print(f"\n{'─' * 60}")
    print(f"DV: {dv} (spec'd PRs only)")
    print(f"{'─' * 60}")

    # Raw
    print(f"\n  Raw (q_overall only):")
    r1 = run_logit(dv, ["q_overall"], specd_scored)
    print(fmt_result(r1))

    # + size
    print(f"\n  Controlling for change size:")
    r2 = run_logit(dv, ["q_overall"] + size_ivs, specd_scored, focus_var="q_overall")
    print(fmt_result(r2))

    # + size + review
    print(f"\n  Controlling for change size + review effort:")
    r3 = run_logit(dv, ["q_overall"] + size_ivs + review_ivs, specd_scored, focus_var="q_overall")
    print(fmt_result(r3))

# ── Clean summary ──────────────────────────────────────────────────
print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)

for dv in ["strict_escaped", "reworked"]:
    r1 = run_logit(dv, ["has_spec"], df)
    r2 = run_logit(dv, ["has_spec"] + size_ivs, df, focus_var="has_spec")
    r3 = run_logit(dv, ["has_spec"] + size_ivs + review_ivs, df, focus_var="has_spec")

    raw_spec = df[df["has_spec"] == 1][dv].dropna().mean()
    raw_nospec = df[df["has_spec"] == 0][dv].dropna().mean()
    raw_dir = "lower" if raw_spec < raw_nospec else "higher"
    raw_diff = abs(raw_spec - raw_nospec) / raw_nospec * 100 if raw_nospec > 0 else 0

    print(f"\nQUESTION: Do specs reduce {dv} risk?")
    print(f"  Raw: spec'd rate is {raw_dir} ({raw_diff:.1f}% {'reduction' if raw_dir == 'lower' else 'increase'})")
    if r2:
        dir2 = "yes, reduces" if r2["odds"] < 1 else "no, increases"
        print(f"  After controlling for change size: {dir2} (OR={r2['odds']:.3f}, p={r2['p']:.4f})")
    if r3:
        dir3 = "yes, reduces" if r3["odds"] < 1 else "no, increases"
        print(f"  After controlling for size + review: {dir3} (OR={r3['odds']:.3f}, p={r3['p']:.4f})")

# Continuous q_overall summary
for dv in ["strict_escaped", "reworked"]:
    r_raw = run_logit(dv, ["q_overall"], specd_scored)
    r_size = run_logit(dv, ["q_overall"] + size_ivs, specd_scored, focus_var="q_overall")

    print(f"\nQUESTION: Among spec'd PRs, do better specs reduce {dv}?")
    if r_raw:
        dir_raw = "better specs → fewer" if r_raw["odds"] < 1 else "better specs → MORE (paradox)"
        print(f"  Raw: {dir_raw} (OR={r_raw['odds']:.3f}, p={r_raw['p']:.4f})")
    if r_size:
        dir_size = "better specs → fewer" if r_size["odds"] < 1 else "still more (paradox persists)"
        print(f"  After controlling for change size: {dir_size} (OR={r_size['odds']:.3f}, p={r_size['p']:.4f})")
