#!/usr/bin/env python3
"""Build master CSV: one row per PR with ALL tags from all data sources.

Joins:
- unified-prs.csv (outcomes: rework, escape, size, spec, catchrate, workflow)
- pr-features.csv (regex features: humanness, org context, reasoning, template/slop, text stats)
- spec-quality-*.json (LLM quality scores: 7 dimensions)
- engagement-*.json (LLM formality scores: 8 dimensions + classification + evidence)
- spec-signals-*.json (effectiveness signals for strict_escaped computation)

Output: data/master-prs.csv
"""

import csv
import json
import re
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


def safe_int(val):
    if isinstance(val, (int, float)):
        return int(val)
    return ''


def safe_float(val):
    if isinstance(val, (int, float)):
        return round(float(val), 2)
    return ''


def main():
    # 1. Load unified CSV as base
    with open(DATA_DIR / 'unified-prs.csv') as f:
        base = {(r['repo'], int(r['pr_number'])): r for r in csv.DictReader(f)}

    # 2. Load pr-features.csv
    features = {}
    feat_path = DATA_DIR / 'pr-features.csv'
    if feat_path.exists():
        with open(feat_path) as f:
            for r in csv.DictReader(f):
                features[(r['repo'], int(r['pr_number']))] = r

    # 3. Load formality scores (from engagement-*.json source files)
    formality = {}
    for fp in DATA_DIR.glob('engagement-*.json'):
        with open(fp) as f:
            for r in json.load(f):
                if 'error' in r:
                    continue
                formality[(r['repo'], r['pr_number'])] = r

    # 5. Load spec-signals for strict_escaped computation
    # strict_escaped = escaped AND has a follow-up PR with fix/revert/regression in title
    spec_fix_targets = set()  # (repo, target_pr) that have a fix-titled follow-up
    all_pr_titles = {}
    for fp in DATA_DIR.glob('prs-*.json'):
        with open(fp) as f:
            for p in json.load(f):
                all_pr_titles[(p.get('repo', ''), p['pr_number'])] = p['title']
    for fp in DATA_DIR.glob('spec-signals-*.json'):
        try:
            with open(fp) as f:
                uf = json.load(f)
        except Exception:
            continue
        slug = fp.stem.replace('spec-signals-', '')
        for s in uf.get('effectiveness', {}).get('signals', []):
            source = int(s['source'])
            target = int(s['target'])
            # Find source PR title — need repo name
            source_title = ''
            for repo_key, title in all_pr_titles.items():
                if repo_key[1] == source and repo_key[0].replace('/', '-') == slug:
                    source_title = title
                    break
            t = source_title.lower()
            if re.search(r'\b(revert|fix|bugfix|hotfix|regression|broke|broken|patch)\b', t) or re.search(r'^fix[\s:(]', t):
                # Find repo name for this slug
                for repo_key in all_pr_titles:
                    if repo_key[0].replace('/', '-') == slug and repo_key[1] == target:
                        spec_fix_targets.add(repo_key)
                        break

    # Build master rows
    all_rows = []
    for key, base_row in base.items():
        feat = features.get(key, {})
        eng = formality.get(key, {})

        row = dict(base_row)  # start with all unified columns

        # Compute strict_escaped: escaped AND has a fix-titled follow-up
        row['strict_escaped'] = (
            str(row.get('escaped', '')).lower() == 'true'
            and key in spec_fix_targets
        )

        # Add regex features (prefix: f_)
        for col in ['is_bot_author', 'ai_tagged', 'typos', 'casual', 'questions',
                     'fp_experience', 'fp_action', 'human_mentions',
                     'history', 'people_context', 'external_context', 'incidents',
                     'has_org_context', 'negations', 'causal_chains', 'specific_edges',
                     'generic_edges', 'edge_ratio', 'tradeoffs', 'domain_grounding',
                     'templates', 'slop', 'empty_sections', 'issue_refs', 'any_issue_refs',
                     'body_len', 'word_count', 'sent_len_mean', 'sent_len_std',
                     'type_token_ratio', 'avg_word_len',
                     'human_signals', 'org_context_signals', 'reasoning_signals', 'anti_signals',
                     'perplexity']:
            row[f'f_{col}'] = feat.get(col, '')

        # Add LLM formality scores (prefix: formality_)
        for col in ['lived_experience', 'organizational_memory', 'uncertainty',
                     'negative_scope', 'causal_reasoning', 'genuine_edge_cases',
                     'template_filler']:
            row[f'formality_{col}'] = safe_int(eng.get(col))

        row['formality_overall'] = safe_int(eng.get('overall_human_engagement'))
        row['formality_classification'] = eng.get('classification', '')

        # Add evidence quotes (prefix: fev_)
        evidence = eng.get('evidence', {})
        if isinstance(evidence, dict):
            for col in ['lived_experience', 'organizational_memory', 'uncertainty', 'causal_reasoning']:
                val = evidence.get(col, '')
                if val and val != 'none found' and val != 'None found':
                    row[f'fev_{col}'] = val[:200]
                else:
                    row[f'fev_{col}'] = ''
        else:
            for col in ['lived_experience', 'organizational_memory', 'uncertainty', 'causal_reasoning']:
                row[f'fev_{col}'] = ''

        all_rows.append(row)

    # Write
    if not all_rows:
        print("No rows to write")
        return

    # Train stylometric classifier and add ai_probability
    try:
        import numpy as np
        from sklearn.preprocessing import StandardScaler
        from sklearn.linear_model import LogisticRegression

        style_features = [
            'f_body_len', 'f_word_count', 'f_sent_len_mean', 'f_sent_len_std',
            'f_type_token_ratio', 'f_avg_word_len',
            'f_typos', 'f_casual', 'f_questions', 'f_fp_experience', 'f_fp_action',
            'f_human_mentions', 'f_history', 'f_people_context', 'f_external_context',
            'f_incidents', 'f_negations', 'f_causal_chains', 'f_specific_edges',
            'f_generic_edges', 'f_tradeoffs', 'f_domain_grounding',
            'f_templates', 'f_slop', 'f_empty_sections', 'f_issue_refs',
        ]

        human = [r for r in all_rows if r.get('f_is_bot_author') != 'True']
        def _sf(v):
            try: return float(v)
            except (ValueError, TypeError): return 0
        with_body = [r for r in human if _sf(r.get('f_body_len')) > 50]

        if len(with_body) > 100:
            X = np.array([[_sf(r.get(f)) for f in style_features] for r in with_body])
            y = np.array([1 if r.get('f_ai_tagged') == 'True' else 0 for r in with_body])

            scaler = StandardScaler()
            lr = LogisticRegression(max_iter=1000, class_weight='balanced')
            lr.fit(scaler.fit_transform(X), y)
            probs = lr.predict_proba(scaler.transform(X))[:, 1]

            for i, r in enumerate(with_body):
                r['ai_probability'] = round(float(probs[i]), 4)
            for r in human:
                if _sf(r.get('f_body_len')) <= 50:
                    r['ai_probability'] = ''
            for r in all_rows:
                if r.get('f_is_bot_author') == 'True':
                    r.setdefault('ai_probability', '')

            ai_scored = sum(1 for r in all_rows if r.get('ai_probability') not in ('', None))
            print(f"  Stylometric classifier: {ai_scored} PRs scored (AUC computed at runtime)")
    except ImportError:
        print("  Skipping ai_probability (numpy/sklearn not installed)")

    out_path = DATA_DIR / 'master-prs.csv'
    fieldnames = list(all_rows[0].keys())
    if 'ai_probability' not in fieldnames:
        fieldnames.append('ai_probability')

    tmp_path = out_path.with_suffix('.csv.tmp')
    with open(tmp_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_rows)
    tmp_path.replace(out_path)

    # Summary
    has_features = sum(1 for r in all_rows if r.get('f_typos', '') != '')
    has_formality = sum(1 for r in all_rows if r.get('formality_overall', '') != '')
    has_quality = sum(1 for r in all_rows if r.get('q_overall', '') != '')

    print(f"Wrote {len(all_rows)} rows, {len(fieldnames)} columns to {out_path}")
    print(f"  With regex features: {has_features}")
    print(f"  With LLM formality:  {has_formality}")
    print(f"  With LLM quality:    {has_quality}")


if __name__ == '__main__':
    main()
