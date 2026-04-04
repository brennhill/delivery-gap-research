#!/usr/bin/env python3
"""Test CatchRate filters against 126 human labels."""

import sys, json, re, math
from pathlib import Path

sys.path.insert(0, "/Users/brenn/dev/catchrate")
from catchrate.rework import _is_not_escape
from catchrate.models import Classification

DATA_DIR = Path(__file__).resolve().parent / "data"

all_labels = [
    "no","yes","yes","no","yes","yes","yes","yes","yes","yes",
    "no","yes","yes","yes","no","no","yes","yes","no","yes",
    "yes","yes","yes","no","yes","yes","yes","yes","yes","yes",
    "yes","no","no","yes","yes","yes","yes","yes","yes","yes",
    "yes","no","yes","yes","yes","no","no","no","no","no",
    "no","no","yes","no","no","no","yes","no","no","yes",
    "yes","yes","yes","yes","no","no","yes","no","no","no",
    "no","no","yes","yes","no","no","yes","no","no","no",
    "yes","yes","no","yes","yes","no","yes","no","yes","yes",
    "yes","no","no","no","no","no","yes","yes","yes","yes",
    # holdout
    "no","no","no","no","yes","yes","no","no","yes","yes",
    "yes","yes","yes","yes","no","no","no","no","no","no",
    "no","no","no","no","no","no",
]

with open(DATA_DIR / "human-validation-high-all.json") as f:
    pairs = json.load(f)

pr_index = {}
for fp in sorted(DATA_DIR.glob("prs-*.json")):
    slug = fp.stem.replace("prs-", "")
    with open(fp) as f:
        prs = json.load(f)
    for pr in prs:
        repo = pr.get("repo", slug.replace("-", "/", 1))
        num = pr.get("pr_number")
        pr_index[f"{repo}#{num}"] = pr


def wilson_ci(s, n, z=1.96):
    if n == 0:
        return 0, 1
    p = s / n
    d = 1 + z**2 / n
    c = (p + z**2 / (2*n)) / d
    sp = z * ((p*(1-p) + z**2/(4*n)) / n)**0.5 / d
    return max(0, c-sp), min(1, c+sp)


def get_component(title):
    m = re.match(r"\w+\(([^)]+)\)", title)
    return m.group(1).lower() if m else None


# Test current filters
tp = fp = fn = tn = 0
fps_remaining = []
fns = []

for i, label in enumerate(all_labels):
    human = label == "yes"
    p = pairs[i]
    repo = p["repo"]
    target_pr = pr_index.get(f"{repo}#{p['target_num']}")
    source_pr = pr_index.get(f"{repo}#{p['source_num']}")

    filtered = False
    if target_pr and source_pr:
        fix_cls = Classification(
            number=p["source_num"], title=source_pr.get("title", ""),
            classification="escape", ci_status="clean_pass",
            review_modified=False, escaped=False, escape_reason="",
            body=source_pr.get("body", "") or "",
            author=source_pr.get("author", ""),
            files=source_pr.get("files", []),
        )
        orig_cls = Classification(
            number=p["target_num"], title=target_pr.get("title", ""),
            classification="escape", ci_status="clean_pass",
            review_modified=False, escaped=False, escape_reason="",
            body=target_pr.get("body", "") or "",
            author=target_pr.get("author", ""),
            files=target_pr.get("files", []),
        )
        filtered = _is_not_escape(fix_cls, orig_cls)

    pred = not filtered
    if human and pred:
        tp += 1
    elif not human and pred:
        fp += 1
        fps_remaining.append(i)
    elif human and not pred:
        fn += 1
        fns.append(i)
    else:
        tn += 1

prec = tp / (tp + fp) if (tp + fp) else 0
rec = tp / (tp + fn) if (tp + fn) else 0
lo, hi = wilson_ci(tp, tp + fp)

print(f"WITH EXPANDED CI FILTER (N=126):")
print(f"Precision: {tp}/{tp+fp} = {prec:.0%} (CI: {lo:.0%}-{hi:.0%})")
print(f"Recall: {tp}/{tp+fn} = {rec:.0%}")
print(f"TP={tp} FP={fp} FN={fn} TN={tn}")

if fns:
    print(f"\nFalse negatives:")
    for i in fns:
        print(f"  H{i+1}: {pairs[i]['source_title'][:60]}")

# Test component filter on remaining FPs
print(f"\nRemaining {fp} FPs — component filter analysis:")
comp_catches_fp = 0
comp_catches_tp = 0

for i in fps_remaining:
    p = pairs[i]
    source_pr = pr_index.get(f"{p['repo']}#{p['source_num']}")
    target_pr = pr_index.get(f"{p['repo']}#{p['target_num']}")
    if not source_pr or not target_pr:
        continue
    comp_a = get_component(target_pr.get("title", ""))
    comp_b = get_component(source_pr.get("title", ""))
    if comp_a and comp_b and comp_a != comp_b:
        comp_catches_fp += 1
        print(f"  GOOD: H{i+1} ({comp_a}) vs ({comp_b})")

# Check false negatives from component filter on true escapes
for i, label in enumerate(all_labels):
    if label != "yes":
        continue
    p = pairs[i]
    source_pr = pr_index.get(f"{p['repo']}#{p['source_num']}")
    target_pr = pr_index.get(f"{p['repo']}#{p['target_num']}")
    if not source_pr or not target_pr:
        continue
    comp_a = get_component(target_pr.get("title", ""))
    comp_b = get_component(source_pr.get("title", ""))
    if comp_a and comp_b and comp_a != comp_b:
        comp_catches_tp += 1
        print(f"  BAD: H{i+1} ({comp_a}) vs ({comp_b}) — real escape wrongly filtered")

print(f"\nComponent filter: removes {comp_catches_fp} FPs, wrongly removes {comp_catches_tp} TPs")

if comp_catches_fp > 0:
    new_fp = fp - comp_catches_fp
    new_tp = tp - comp_catches_tp
    new_prec = new_tp / (new_tp + new_fp) if (new_tp + new_fp) else 0
    new_rec = new_tp / (new_tp + fn + comp_catches_tp) if (new_tp + fn + comp_catches_tp) else 0
    lo2, hi2 = wilson_ci(new_tp, new_tp + new_fp)
    print(f"With component filter: {new_tp}/{new_tp+new_fp} = {new_prec:.0%} (CI: {lo2:.0%}-{hi2:.0%}) rec={new_rec:.0%}")
