#!/usr/bin/env python3
"""Train a classifier to filter CatchRate false positives.

Uses three validated data sources:
  1. CONFIRMED reverts (52 pairs, 100% precision) — with "revert" masked
  2. HIGH confidence validated pairs (166 LLM-judged, 114 true / 52 false)
  3. Prior validation sample (99 LLM-judged, 37 true / 62 false)

Features are extracted from PR pair metadata (no LLM needed at inference):
  - same_author, days_delta, file overlap metrics
  - title/body text signals, dependency detection
  - backport/release detection (new filters validated at 87% precision)

Usage:
    python rework-classifier.py              # train + evaluate (default)
    python rework-classifier.py --export     # export model
    python rework-classifier.py --errors     # show misclassified pairs
"""

import argparse
import json
import re
from collections import Counter
from datetime import datetime
from pathlib import Path

import numpy as np
from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.model_selection import LeaveOneOut, StratifiedKFold, cross_val_predict

DATA_DIR = Path(__file__).resolve().parent / "data"

STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "to", "of",
    "in", "for", "on", "with", "at", "by", "from", "as", "and", "but", "or",
    "not", "no", "this", "that", "fix", "from", "update", "add", "remove",
}

# Words masked from revert pairs so model learns underlying patterns
REVERT_MASK_WORDS = {"revert", "reverted", "reverting", "reverts", "reversion"}

FEATURE_NAMES = [
    "same_author",
    "days_delta",
    "file_overlap_pct",
    "overlap_file_count",
    "source_has_fix_title",
    "source_refs_target_num",
    "source_is_dep",
    "source_is_backport",
    "source_is_release",
    "shared_title_words",
    "body_refs_target_keywords",
    "target_file_count",
    "source_file_count",
    "target_lines_changed",
    "source_lines_changed",
    "same_component",
]


# ---------------------------------------------------------------------------
# Feature extraction
# ---------------------------------------------------------------------------

def _title_words(title: str, mask_revert: bool = False) -> set[str]:
    words = set(re.findall(r"[a-z]{3,}", title.lower())) - STOPWORDS
    if mask_revert:
        words -= REVERT_MASK_WORDS
    return words


def _extract_component(title: str) -> str:
    """Extract component from conventional commit: fix(component): ..."""
    m = re.match(r"\w+\(([^)]+)\)", title)
    return m.group(1).lower() if m else ""


def _compute_overlap(source_files: list[str], target_files: list[str]) -> tuple[float, int]:
    """Returns (overlap_pct_of_source, overlap_count)."""
    if not source_files:
        return 0.0, 0
    s = set(source_files)
    t = set(target_files)
    overlap = s & t
    return len(overlap) / len(s), len(overlap)


def extract_features(pair: dict, mask_revert: bool = False) -> dict:
    """Extract classifier features from a PR pair.

    pair must have: target_author, source_author, target_date, source_date,
    target_title, source_title, target_body, source_body,
    target_files, source_files, target_num, source_num,
    target_additions, target_deletions, source_additions, source_deletions
    """
    # Same author
    same_author = pair.get("target_author", "") == pair.get("source_author", "")

    # Time delta
    try:
        t1 = datetime.fromisoformat(pair["target_date"].replace("Z", "+00:00"))
        t2 = datetime.fromisoformat(pair["source_date"].replace("Z", "+00:00"))
        days_delta = abs((t2 - t1).total_seconds()) / 86400
    except Exception:
        days_delta = 7.0

    # File overlap
    target_files = pair.get("target_files", [])
    source_files = pair.get("source_files", [])
    overlap_pct, overlap_count = _compute_overlap(source_files, target_files)

    # Source title signals
    source_title = pair.get("source_title", "")
    source_has_fix = bool(re.search(r"^fix|bugfix|hotfix|patch", source_title, re.I))

    # Source references target PR number
    target_num = str(pair.get("target_num", ""))
    source_body = pair.get("source_body", "") or ""
    source_refs_target = target_num in source_title or f"#{target_num}" in source_body

    # Dependency detection
    source_is_dep = bool(re.search(
        r"bump|chore\(deps\)|dependenc|upgrade.*to \d|update.*to \d|\bfrom \d+\.\d+.*to \d+\.\d+",
        source_title, re.I,
    ))

    # Backport/cherry-pick detection
    source_is_backport = bool(re.search(
        r"backport|cherry[- ]?pick|\((?:core[- ]?2|release/|v\d)",
        f"{source_title} {source_body[:500]}", re.I,
    ))

    # Release PR detection
    source_is_release = bool(re.search(
        r"^(?:chore|release)\s*[:(].*(?:v?\d+\.\d+|release)|"
        r"^(?:Release|Prepare)\s+v?\d+\.\d+|^v\d+\.\d+\.\d+",
        source_title, re.I,
    ))

    # Title word overlap
    target_words = _title_words(pair.get("target_title", ""), mask_revert=mask_revert)
    source_words = _title_words(source_title, mask_revert=mask_revert)
    shared_title_words = len(target_words & source_words)

    # Body references target title keywords
    target_keywords = target_words - {"feat", "chore", "refactor", "test"}
    source_body_lower = source_body.lower()
    body_refs = sum(1 for w in target_keywords if w in source_body_lower)

    # Size features
    target_file_count = len(target_files)
    source_file_count = len(source_files)
    target_lines = pair.get("target_additions", 0) + pair.get("target_deletions", 0)
    source_lines = pair.get("source_additions", 0) + pair.get("source_deletions", 0)

    # Same component (conventional commit scope)
    target_comp = _extract_component(pair.get("target_title", ""))
    source_comp = _extract_component(source_title)
    same_component = bool(target_comp and source_comp and target_comp == source_comp)

    return {
        "same_author": int(same_author),
        "days_delta": min(days_delta, 30),
        "file_overlap_pct": overlap_pct,
        "overlap_file_count": min(overlap_count, 20),
        "source_has_fix_title": int(source_has_fix),
        "source_refs_target_num": int(source_refs_target),
        "source_is_dep": int(source_is_dep),
        "source_is_backport": int(source_is_backport),
        "source_is_release": int(source_is_release),
        "shared_title_words": min(shared_title_words, 10),
        "body_refs_target_keywords": min(body_refs, 5),
        "target_file_count": min(target_file_count, 50),
        "source_file_count": min(source_file_count, 50),
        "target_lines_changed": min(target_lines, 5000),
        "source_lines_changed": min(source_lines, 5000),
        "same_component": int(same_component),
    }


# ---------------------------------------------------------------------------
# Data loading — merge all three sources with full PR metadata
# ---------------------------------------------------------------------------

def _load_pr_index() -> dict[str, dict]:
    """Load all raw PR data, indexed by 'repo#number'."""
    index = {}
    for fp in sorted(DATA_DIR.glob("prs-*.json")):
        slug = fp.stem.replace("prs-", "")
        with open(fp) as f:
            prs = json.load(f)
        for pr in prs:
            repo = pr.get("repo", slug.replace("-", "/", 1))
            num = pr.get("pr_number", pr.get("number"))
            key = f"{repo}#{num}"
            index[key] = pr
    return index


def _enrich_pair(target_pr: dict, source_pr: dict, repo: str,
                 target_num: int, source_num: int) -> dict:
    """Build a full pair dict from raw PR data."""
    return {
        "repo": repo,
        "target_num": target_num,
        "source_num": source_num,
        "target_title": target_pr.get("title", ""),
        "source_title": source_pr.get("title", ""),
        "target_body": (target_pr.get("body", "") or "")[:3000],
        "source_body": (source_pr.get("body", "") or "")[:3000],
        "target_author": target_pr.get("author", ""),
        "source_author": source_pr.get("author", ""),
        "target_date": target_pr.get("merged_at", "") or "",
        "source_date": source_pr.get("merged_at", "") or "",
        "target_files": target_pr.get("files", []),
        "source_files": source_pr.get("files", []),
        "target_additions": target_pr.get("additions", 0),
        "target_deletions": target_pr.get("deletions", 0),
        "source_additions": source_pr.get("additions", 0),
        "source_deletions": source_pr.get("deletions", 0),
    }


def load_training_data():
    """Load and merge all validated training data.

    Returns (X, y, keys, sources) where sources tracks provenance.
    """
    pr_index = _load_pr_index()
    samples = {}  # key -> (pair_dict, label, source_name, mask_revert)

    # --- Source 1: CONFIRMED reverts (label=1, mask revert words) ---
    revert_count = 0
    for fp in sorted(DATA_DIR.glob("catchrate-*.json")):
        slug = fp.stem.replace("catchrate-", "")
        with open(fp) as f:
            cr = json.load(f)
        for pr in cr.get("prs", []):
            if not pr.get("escaped"):
                continue
            reason = pr.get("escape_reason", "")
            if not reason.startswith("reverted by"):
                continue
            target_num = pr["number"]
            m = re.search(r"#(\d+)", reason)
            if not m:
                continue
            source_num = int(m.group(1))

            repo = slug.replace("-", "/", 1)
            target_pr = pr_index.get(f"{repo}#{target_num}")
            source_pr = pr_index.get(f"{repo}#{source_num}")
            if not target_pr or not source_pr:
                continue

            key = f"{repo}#{target_num}->{source_num}"
            pair = _enrich_pair(target_pr, source_pr, repo, target_num, source_num)
            samples[key] = (pair, 1, "confirmed_revert", True)
            revert_count += 1

    print(f"Confirmed reverts: {revert_count}")

    # --- Source 2: HIGH confidence validation ---
    hc_path = DATA_DIR / "high-confidence-validation.json"
    hc_true = hc_false = hc_skip = 0
    if hc_path.exists():
        with open(hc_path) as f:
            hc_data = json.load(f)
        for key, v in hc_data.items():
            if "error" in v or key in samples:
                continue
            repo = v["repo"]
            target_num = v["target"]
            source_num = v["source"]

            target_pr = pr_index.get(f"{repo}#{target_num}")
            source_pr = pr_index.get(f"{repo}#{source_num}")
            if not target_pr or not source_pr:
                hc_skip += 1
                continue

            pair = _enrich_pair(target_pr, source_pr, repo, target_num, source_num)
            label = 1 if v.get("is_fix") else 0
            samples[key] = (pair, label, "high_confidence", False)
            if label:
                hc_true += 1
            else:
                hc_false += 1
    print(f"HIGH confidence: {hc_true} true + {hc_false} false ({hc_skip} skipped, no PR data)")

    # --- Source 3: Prior validation sample ---
    cv_results = DATA_DIR / "catchrate-validation-results.json"
    cv_sample = DATA_DIR / "catchrate-validation-sample.json"
    cv_true = cv_false = 0
    if cv_results.exists() and cv_sample.exists():
        with open(cv_results) as f:
            results = json.load(f)
        with open(cv_sample) as f:
            sample = json.load(f)

        # Index sample pairs by key
        sample_by_key = {}
        for p in sample.get("rework_pairs", []):
            k = f"{p['repo']}#{p['target_num']}->{p['source_num']}"
            sample_by_key[k] = p

        for key, v in results.items():
            if "error" in v or key in samples:
                continue
            p = sample_by_key.get(key)
            if not p:
                continue

            # Enrich from pr_index if possible, fall back to sample data
            repo = p["repo"]
            target_num = p["target_num"]
            source_num = p["source_num"]

            target_pr = pr_index.get(f"{repo}#{target_num}")
            source_pr = pr_index.get(f"{repo}#{source_num}")

            if target_pr and source_pr:
                pair = _enrich_pair(target_pr, source_pr, repo, target_num, source_num)
            else:
                # Fall back to what the sample has
                pair = {
                    "repo": repo,
                    "target_num": target_num,
                    "source_num": source_num,
                    "target_title": p.get("target_title", ""),
                    "source_title": p.get("source_title", ""),
                    "target_body": (p.get("target_body", "") or "")[:3000],
                    "source_body": (p.get("source_body", "") or "")[:3000],
                    "target_author": p.get("target_author", ""),
                    "source_author": p.get("source_author", ""),
                    "target_date": p.get("target_date", ""),
                    "source_date": p.get("source_date", ""),
                    "target_files": p.get("overlapping_files", []),
                    "source_files": p.get("overlapping_files", []),
                    "target_additions": 0,
                    "target_deletions": 0,
                    "source_additions": 0,
                    "source_deletions": 0,
                }

            label = 1 if v.get("is_fix") else 0
            samples[key] = (pair, label, "prior_validation", False)
            if label:
                cv_true += 1
            else:
                cv_false += 1
    print(f"Prior validation: {cv_true} true + {cv_false} false")

    # --- Build arrays ---
    keys = []
    X_rows = []
    y = []
    sources = []

    for key, (pair, label, source, mask_revert) in samples.items():
        feats = extract_features(pair, mask_revert=mask_revert)
        X_rows.append([feats[f] for f in FEATURE_NAMES])
        y.append(label)
        keys.append(key)
        sources.append(source)

    print(f"\nTotal training data: {len(y)} pairs "
          f"({sum(y)} true rework, {len(y) - sum(y)} false positives)")

    return np.array(X_rows), np.array(y), keys, sources


# ---------------------------------------------------------------------------
# Training and evaluation
# ---------------------------------------------------------------------------

def train_and_evaluate(show_errors: bool = False):
    """Train classifier with stratified 5-fold CV."""
    X, y, keys, sources = load_training_data()
    print(f"Features: {len(FEATURE_NAMES)}")
    print()

    # Class balance
    print(f"Class balance: {sum(y)} positive ({100*sum(y)/len(y):.0f}%), "
          f"{len(y)-sum(y)} negative ({100*(len(y)-sum(y))/len(y):.0f}%)")
    source_counts = Counter(sources)
    print(f"By source: {dict(source_counts)}")
    print()

    classifiers = {
        "GradientBoosting": GradientBoostingClassifier(
            n_estimators=200, max_depth=3, min_samples_leaf=5, random_state=42
        ),
        "RandomForest": RandomForestClassifier(
            n_estimators=200, max_depth=4, min_samples_leaf=5, random_state=42
        ),
        "LogisticRegression": LogisticRegression(max_iter=1000, random_state=42),
    }

    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)

    best_name = None
    best_auc = 0

    for name, clf in classifiers.items():
        y_pred = cross_val_predict(clf, X, y, cv=cv)
        y_prob = cross_val_predict(clf, X, y, cv=cv, method="predict_proba")[:, 1]

        auc = roc_auc_score(y, y_prob)

        tp = int(((y_pred == 1) & (y == 1)).sum())
        fp = int(((y_pred == 1) & (y == 0)).sum())
        fn = int(((y_pred == 0) & (y == 1)).sum())
        tn = int(((y_pred == 0) & (y == 0)).sum())

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

        print(f"=== {name} (5-fold CV) ===")
        print(f"  AUC:       {auc:.3f}")
        print(f"  Precision: {precision:.3f}  (CatchRate baseline: 0.37)")
        print(f"  Recall:    {recall:.3f}")
        print(f"  F1:        {f1:.3f}")
        print(f"  TP={tp} FP={fp} FN={fn} TN={tn}")

        if precision > 0.37:
            improvement = (precision - 0.37) / 0.37 * 100
            print(f"  Precision improvement: +{improvement:.0f}% over CatchRate alone")

        if auc > best_auc:
            best_auc = auc
            best_name = name

        # Feature importance
        clf.fit(X, y)
        if hasattr(clf, "feature_importances_"):
            importances = sorted(zip(FEATURE_NAMES, clf.feature_importances_),
                                 key=lambda x: x[1], reverse=True)
            print(f"  Feature importance:")
            for feat, imp in importances:
                if imp > 0.01:
                    print(f"    {feat:<30} {imp:.3f}")
        print()

        # Show misclassified pairs
        if show_errors and name == "GradientBoosting":
            print("  MISCLASSIFIED PAIRS:")
            for i, (pred, true) in enumerate(zip(y_pred, y)):
                if pred != true:
                    label = "FP (predicted rework, actually not)" if pred == 1 else "FN (missed real rework)"
                    print(f"    {label}: {keys[i]} [{sources[i]}] (prob={y_prob[i]:.2f})")
            print()

    print(f"Best model: {best_name} (AUC={best_auc:.3f})")
    return best_name


def export_model():
    """Train final model and export."""
    X, y, keys, sources = load_training_data()

    clf = GradientBoostingClassifier(
        n_estimators=200, max_depth=3, min_samples_leaf=5, random_state=42
    )
    clf.fit(X, y)

    # Export as pickle
    import pickle
    model_path = DATA_DIR / "rework-classifier-model.pkl"
    with open(model_path, "wb") as f:
        pickle.dump({"model": clf, "features": FEATURE_NAMES, "n_train": len(y)}, f)
    print(f"Model exported to {model_path}")

    # Export feature importances as JSON (for inspection)
    importances = dict(zip(FEATURE_NAMES, clf.feature_importances_.tolist()))
    rules_path = DATA_DIR / "rework-classifier-rules.json"
    rules = {
        "n_train": len(y),
        "n_positive": int(y.sum()),
        "n_negative": int(len(y) - y.sum()),
        "features": FEATURE_NAMES,
        "importances": importances,
        "data_sources": dict(Counter(sources)),
    }
    with open(rules_path, "w") as f:
        json.dump(rules, f, indent=2)
    print(f"Feature importances exported to {rules_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--export", action="store_true", help="Export trained model")
    parser.add_argument("--errors", action="store_true", help="Show misclassified pairs")
    args = parser.parse_args()

    best = train_and_evaluate(show_errors=args.errors)

    if args.export:
        print()
        export_model()


if __name__ == "__main__":
    main()
