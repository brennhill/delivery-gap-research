#!/usr/bin/env python3
"""Train and validate AI text classifier with proper holdout design.

Three classifier variants:
  A. Full 57 features (contaminated — features designed on this corpus)
  B. StyloAI-only 20 features (uncontaminated — features from independent study)
  C. Perplexity only (single feature baseline)

Holdout controls (never in training):
  - Control A (positive): Known AI agent authors (cursor, devin, renovate)
  - Control B (negative): 2023-H1 PRs (pre-AI era)
  - Control C (negative): Veteran human authors (20+ PRs, 0% AI tags)

Usage:
    python train-classifier.py                # full pipeline
    python train-classifier.py --recompute    # recompute features first
"""

import csv
import json
import re
import argparse
import importlib.util
from pathlib import Path
from collections import Counter, defaultdict
from statistics import mean

import numpy as np
from scipy.stats import spearmanr
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import cross_val_score, StratifiedKFold
from sklearn.metrics import roc_auc_score, classification_report

DATA_DIR = Path(__file__).resolve().parent / "data"
HIST_DIR = Path(__file__).resolve().parent / "data-2023-H1"

# Known AI agent authors — holdout as positive control
# NOTE: renovate, dependabot, github-actions write dependency bumps / releases,
# NOT AI-assisted feature development. They're automation, not "AI coding."
# We exclude them from Control A and from training as they're noise.
AI_AGENTS_CODING = {
    "cursor", "devin-ai-integration", "copilot-swe-agent",
}
AI_AGENTS_AUTOMATION = {
    "renovate", "dependabot", "github-actions",
}

# Noise authors to exclude entirely (not AI-assisted development)
NOISE_AUTHORS = AI_AGENTS_AUTOMATION | {"clerk-cookie"}

# StyloAI-aligned features (designed on independent corpus, arXiv:2405.10129)
# These are uncontaminated — someone else picked them on different data
STYLOAI_FEATURES = [
    # Lexical diversity
    "f_word_count", "f_body_len", "f_avg_word_len", "f_type_token_ratio",
    "f_unique_word_count", "f_hapax_rate",
    # Syntactic
    "f_sentence_count", "f_sent_len_mean", "f_punctuation_count",
    "f_stop_word_count", "f_exclamation_count", "f_questions",
    # Readability
    "f_flesch_reading_ease", "f_gunning_fog",
    # Named entities / address
    "f_direct_address_count", "f_fp_experience",
    # Uniqueness
    "f_bigram_uniqueness", "f_trigram_uniqueness",
    # Sentiment
    "f_vader_compound",
    # Variance (ours but analogous to StyloAI's structural measures)
    "f_sent_len_std",
]

# Full feature set (includes our domain-specific features — contaminated)
FULL_FEATURES = STYLOAI_FEATURES + [
    "f_casual", "f_typos", "f_fp_action", "f_human_mentions",
    "f_templates", "f_slop", "f_empty_sections", "f_negations",
    "f_causal_chains", "f_specific_edges", "f_generic_edges",
    "f_tradeoffs", "f_domain_grounding", "f_history",
    "f_people_context", "f_external_context", "f_incidents",
    "f_perplexity",
]


def sf(v):
    try:
        return float(v)
    except (ValueError, TypeError):
        return 0.0


def is_noise(r):
    """Filter out PRs that aren't real development work."""
    import re
    title = (r.get("title", "") or "").lower()
    author = (r.get("author", "") or "").lower()
    body_len = sf(r.get("f_body_len", 0))

    # Automated authors
    if author in {a.lower() for a in NOISE_AUTHORS}:
        return True
    # Dependency bumps / version bumps
    if re.search(r"bump[s ]|chore\(deps\)|update.*dependenc|upgrade.*dependenc", title):
        return True
    # Release chores
    if re.search(r"chore.*release|^release |^v\d+\.\d+\.\d+", title):
        return True
    # Reverts (not original work)
    if title.startswith("revert"):
        return True
    # Trivially small with no body
    try:
        adds = int(r.get("additions", "0") or 0)
        dels = int(r.get("deletions", "0") or 0)
        if adds + dels <= 5 and body_len < 50:
            return True
    except (ValueError, TypeError):
        pass
    # Empty body (no description to classify)
    if body_len < 30:
        return True

    return False


def load_master_csv():
    with open(DATA_DIR / "master-prs.csv") as f:
        return list(csv.DictReader(f))


def load_historical_prs():
    """Load 2023-H1 PRs and compute features on them."""
    spec = importlib.util.spec_from_file_location(
        "cf", str(Path(__file__).resolve().parent / "compute-features.py")
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    prs = []
    for fp in sorted(HIST_DIR.glob("prs-*.json")):
        with open(fp) as f:
            raw = json.load(f)
        for p in raw:
            if not p.get("body"):
                continue
            feats = mod.compute_features(p)
            # Prefix with f_ to match master CSV convention
            row = {f"f_{k}": v for k, v in feats.items()}
            row["author"] = p.get("author", "")
            row["repo"] = p.get("repo", "")
            row["pr_number"] = p.get("pr_number", 0)
            prs.append(row)
    return prs


def build_feature_matrix(rows, feature_cols):
    X = np.array([[sf(r.get(c, 0)) for c in feature_cols] for r in rows])
    # Replace NaN/inf
    X = np.nan_to_num(X, nan=0.0, posinf=0.0, neginf=0.0)
    return X


def train_and_evaluate(X_train, y_train, X_test, y_test, label, feature_names):
    """Train logistic regression + random forest, report AUC."""
    scaler = StandardScaler()
    X_tr = scaler.fit_transform(X_train)
    X_te = scaler.transform(X_test)

    results = {}

    # Logistic Regression
    lr = LogisticRegression(max_iter=1000, random_state=42)
    cv_scores = cross_val_score(lr, X_tr, y_train, cv=5, scoring="roc_auc")
    lr.fit(X_tr, y_train)
    lr_probs = lr.predict_proba(X_te)[:, 1]
    lr_auc = roc_auc_score(y_test, lr_probs) if len(set(y_test)) > 1 else 0

    results["lr"] = {
        "cv_auc": cv_scores.mean(),
        "cv_std": cv_scores.std(),
        "test_auc": lr_auc,
        "model": lr,
        "scaler": scaler,
        "probs": lr_probs,
    }

    # Random Forest (StyloAI uses this)
    rf = RandomForestClassifier(n_estimators=100, random_state=42)
    cv_scores_rf = cross_val_score(rf, X_train, y_train, cv=5, scoring="roc_auc")
    rf.fit(X_train, y_train)
    rf_probs = rf.predict_proba(X_te)[:, 1]
    rf_auc = roc_auc_score(y_test, rf_probs) if len(set(y_test)) > 1 else 0

    results["rf"] = {
        "cv_auc": cv_scores_rf.mean(),
        "cv_std": cv_scores_rf.std(),
        "test_auc": rf_auc,
        "model": rf,
        "probs": rf_probs,
    }

    print(f"\n  {label}:")
    print(f"    Logistic Regression: CV AUC={cv_scores.mean():.3f}±{cv_scores.std():.3f}, "
          f"Test AUC={lr_auc:.3f}")
    print(f"    Random Forest:      CV AUC={cv_scores_rf.mean():.3f}±{cv_scores_rf.std():.3f}, "
          f"Test AUC={rf_auc:.3f}")

    # Top features (LR)
    importances = sorted(zip(feature_names, lr.coef_[0]),
                         key=lambda x: abs(x[1]), reverse=True)
    print(f"    Top 5 LR features:")
    for feat, coef in importances[:5]:
        print(f"      {feat:<30} coef={coef:+.3f}")

    return results


def evaluate_control(model, scaler, control_X, label, expected_class):
    """Evaluate model on a holdout control set."""
    if scaler is not None:
        X = scaler.transform(control_X)
    else:
        X = control_X
    probs = model.predict_proba(X)[:, 1]

    if expected_class == "AI":
        correct = sum(1 for p in probs if p > 0.5)
        metric = "True positive rate"
    else:
        correct = sum(1 for p in probs if p < 0.5)
        metric = "True negative rate"

    rate = 100 * correct / len(probs) if probs.size else 0
    print(f"    {label}: {correct}/{len(probs)} ({rate:.0f}%) {metric}, "
          f"mean prob={probs.mean():.3f}")
    return rate


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--recompute", action="store_true",
                        help="Recompute features before training")
    args = parser.parse_args()

    if args.recompute:
        import subprocess
        print("Recomputing features...")
        subprocess.run(["python3", "compute-features.py"], check=True)
        print()

    # Load data
    print("Loading master CSV...")
    rows = load_master_csv()
    print(f"  Total rows: {len(rows)}")

    # Check if new features exist
    sample_row = rows[0]
    has_new = "f_hapax_rate" in sample_row
    if not has_new:
        print("\nWARNING: New StyloAI features not found in master CSV.")
        print("Run: python3 compute-features.py && python3 build-master-csv.py")
        print("Or: python3 train-classifier.py --recompute")
        print("\nProceeding with available features only...")
        STYLOAI_FEATURES_AVAIL = [f for f in STYLOAI_FEATURES if f in sample_row]
        FULL_FEATURES_AVAIL = [f for f in FULL_FEATURES if f in sample_row]
    else:
        STYLOAI_FEATURES_AVAIL = STYLOAI_FEATURES
        FULL_FEATURES_AVAIL = FULL_FEATURES

    print(f"  StyloAI features available: {len(STYLOAI_FEATURES_AVAIL)}/{len(STYLOAI_FEATURES)}")
    print(f"  Full features available: {len(FULL_FEATURES_AVAIL)}/{len(FULL_FEATURES)}")

    # === SPLIT DATA ===

    # Filter noise from all data
    human_raw = [r for r in rows if r.get("f_is_bot_author") != "True"]
    human = [r for r in human_raw if not is_noise(r)]
    noise_count = len(human_raw) - len(human)
    print(f"  Noise filtered: {noise_count} PRs removed ({100*noise_count/len(human_raw):.1f}%)")
    print(f"  Clean PRs: {len(human)}")

    # Control A: known AI coding agents (NOT automation bots)
    control_a = [r for r in human if r.get("author", "").lower() in
                 {a.lower() for a in AI_AGENTS_CODING}]

    # Control C: veteran humans (20+ clean PRs, 0% AI tags)
    author_stats = defaultdict(lambda: {"total": 0, "ai": 0})
    for r in human:
        a = r.get("author", "")
        author_stats[a]["total"] += 1
        if r.get("f_ai_tagged") == "True":
            author_stats[a]["ai"] += 1

    veteran_authors = {a for a, s in author_stats.items()
                       if s["total"] >= 20 and s["ai"] == 0}
    control_c = [r for r in human if r.get("author", "") in veteran_authors]

    # Training population: exclude controls
    holdout_authors = AI_AGENTS_CODING | AI_AGENTS_AUTOMATION | veteran_authors
    train_pool = [r for r in human
                  if r.get("author", "").lower() not in {a.lower() for a in holdout_authors}
                  and r.get("f_ai_tagged") in ("True", "False")]

    print(f"\n  Control A (AI agents): {len(control_a)} PRs")
    print(f"  Control C (veteran humans): {len(control_c)} PRs")
    print(f"  Training pool (holdouts excluded): {len(train_pool)} PRs")
    print(f"    AI-tagged: {sum(1 for r in train_pool if r['f_ai_tagged']=='True')}")
    print(f"    Not tagged: {sum(1 for r in train_pool if r['f_ai_tagged']!='True')}")

    # 80/20 train/test split
    np.random.seed(42)
    indices = np.random.permutation(len(train_pool))
    split = int(0.8 * len(indices))
    train_idx = indices[:split]
    test_idx = indices[split:]

    train_rows = [train_pool[i] for i in train_idx]
    test_rows = [train_pool[i] for i in test_idx]

    y_train = np.array([1 if r["f_ai_tagged"] == "True" else 0 for r in train_rows])
    y_test = np.array([1 if r["f_ai_tagged"] == "True" else 0 for r in test_rows])

    print(f"\n  Train: {len(train_rows)} ({y_train.sum()} AI, {len(y_train)-y_train.sum()} human)")
    print(f"  Test:  {len(test_rows)} ({y_test.sum()} AI, {len(y_test)-y_test.sum()} human)")

    # === TRAIN THREE VARIANTS ===

    print("\n" + "=" * 70)
    print("CLASSIFIER COMPARISON")
    print("=" * 70)

    all_results = {}

    # Variant A: Full features (contaminated)
    X_train_full = build_feature_matrix(train_rows, FULL_FEATURES_AVAIL)
    X_test_full = build_feature_matrix(test_rows, FULL_FEATURES_AVAIL)
    all_results["full"] = train_and_evaluate(
        X_train_full, y_train, X_test_full, y_test,
        f"A. Full features ({len(FULL_FEATURES_AVAIL)} — contaminated)",
        FULL_FEATURES_AVAIL,
    )

    # Variant B: StyloAI features only (uncontaminated)
    X_train_stylo = build_feature_matrix(train_rows, STYLOAI_FEATURES_AVAIL)
    X_test_stylo = build_feature_matrix(test_rows, STYLOAI_FEATURES_AVAIL)
    all_results["styloai"] = train_and_evaluate(
        X_train_stylo, y_train, X_test_stylo, y_test,
        f"B. StyloAI features only ({len(STYLOAI_FEATURES_AVAIL)} — uncontaminated)",
        STYLOAI_FEATURES_AVAIL,
    )

    # Variant C: Perplexity only (single feature baseline)
    if "f_perplexity" in sample_row:
        perp_rows_train = [r for r in train_rows if sf(r.get("f_perplexity", 0)) > 0]
        perp_rows_test = [r for r in test_rows if sf(r.get("f_perplexity", 0)) > 0]
        if perp_rows_train and perp_rows_test:
            X_train_perp = build_feature_matrix(perp_rows_train, ["f_perplexity"])
            X_test_perp = build_feature_matrix(perp_rows_test, ["f_perplexity"])
            y_train_perp = np.array([1 if r["f_ai_tagged"] == "True" else 0
                                     for r in perp_rows_train])
            y_test_perp = np.array([1 if r["f_ai_tagged"] == "True" else 0
                                    for r in perp_rows_test])
            all_results["perplexity"] = train_and_evaluate(
                X_train_perp, y_train_perp, X_test_perp, y_test_perp,
                "C. Perplexity only (1 feature — baseline)",
                ["f_perplexity"],
            )

    # === HOLDOUT CONTROL EVALUATION ===

    print("\n" + "=" * 70)
    print("HOLDOUT CONTROL VALIDATION")
    print("=" * 70)

    for variant_name, feature_set, variant_label in [
        ("full", FULL_FEATURES_AVAIL, "Full features"),
        ("styloai", STYLOAI_FEATURES_AVAIL, "StyloAI only"),
    ]:
        if variant_name not in all_results:
            continue
        res = all_results[variant_name]

        print(f"\n  --- {variant_label} ---")

        for model_name in ["lr", "rf"]:
            model = res[model_name]["model"]
            scaler = res[model_name].get("scaler")
            print(f"\n  {model_name.upper()}:")

            # Control A: AI agents
            X_ctrl_a = build_feature_matrix(control_a, feature_set)
            if X_ctrl_a.shape[0] > 0:
                evaluate_control(model, scaler if model_name == "lr" else None,
                                 X_ctrl_a, "Control A (AI agents)", "AI")

            # Control C: veteran humans
            X_ctrl_c = build_feature_matrix(control_c, feature_set)
            if X_ctrl_c.shape[0] > 0:
                evaluate_control(model, scaler if model_name == "lr" else None,
                                 X_ctrl_c, "Control C (veteran humans)", "human")

    # === CONTROL B: Historical 2023-H1 data ===
    print(f"\n  --- Control B: 2023-H1 PRs (requires feature computation) ---")
    try:
        hist_prs = load_historical_prs()
        print(f"  Loaded {len(hist_prs)} historical PRs with features")

        for variant_name, feature_set, variant_label in [
            ("full", FULL_FEATURES_AVAIL, "Full"),
            ("styloai", STYLOAI_FEATURES_AVAIL, "StyloAI"),
        ]:
            if variant_name not in all_results:
                continue
            res = all_results[variant_name]
            X_hist = build_feature_matrix(hist_prs, feature_set)
            if X_hist.shape[0] == 0:
                continue

            for model_name in ["lr", "rf"]:
                model = res[model_name]["model"]
                scaler = res[model_name].get("scaler")
                print(f"\n  {variant_label} {model_name.upper()}:")
                evaluate_control(model, scaler if model_name == "lr" else None,
                                 X_hist, "Control B (2023-H1 pre-AI)", "human")
    except Exception as e:
        print(f"  Skipped: {e}")

    # === SUMMARY ===
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print()
    for name, label in [("full", "A. Full (contaminated)"),
                         ("styloai", "B. StyloAI (uncontaminated)"),
                         ("perplexity", "C. Perplexity baseline")]:
        if name not in all_results:
            continue
        res = all_results[name]
        lr = res["lr"]
        rf = res.get("rf", {})
        print(f"  {label}:")
        print(f"    LR:  CV AUC={lr['cv_auc']:.3f}  Test AUC={lr['test_auc']:.3f}")
        if rf:
            print(f"    RF:  CV AUC={rf['cv_auc']:.3f}  Test AUC={rf['test_auc']:.3f}")

    print()
    print("If B ≈ A: contamination is not driving the result.")
    print("If B << A: our domain features add real signal beyond StyloAI.")
    print("If controls pass: classifier generalizes beyond training labels.")


if __name__ == "__main__":
    main()
