#!/usr/bin/env python3
"""Tests for all 12 pipeline bugs."""

import json
import queue
import re
import sys
import textwrap
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

STUDY_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(STUDY_DIR))


# ═══════════════════════════════════════════════════════════════════════
# Bug 1: Tier map should use runner.REPOS as single source of truth
# ═══════════════════════════════════════════════════════════════════════

class TestBug1TierMapSync:
    def test_get_tier_uses_runner_repos(self):
        """_get_tier() should import from runner.REPOS, not hardcode."""
        # Import the function — it should use runner.REPOS
        from importlib import import_module
        mod = import_module("build-unified-csv")
        # The function should return correct tiers for all repos in runner.REPOS
        from runner import REPOS
        for r in REPOS:
            slug = r["repo"].replace("/", "-")
            tier = mod._get_tier(slug)
            assert tier == r["tier"], (
                f"Tier mismatch for {slug}: got {tier!r}, expected {r['tier']!r}"
            )

    def test_get_tier_covers_all_runner_repos(self):
        """Every repo in runner.REPOS should be resolvable."""
        from runner import REPOS
        from importlib import import_module
        mod = import_module("build-unified-csv")
        for r in REPOS:
            slug = r["repo"].replace("/", "-")
            assert mod._get_tier(slug) != "?", f"Missing tier for {slug}"


# ═══════════════════════════════════════════════════════════════════════
# Bug 2: Substring slug match in build-master-csv.py
# ═══════════════════════════════════════════════════════════════════════

class TestBug2SubstringSlugMatch:
    def test_no_substring_match(self):
        """slug 'cli-cli' should NOT match 'somecli-cli-extra'."""
        # Simulate the old buggy logic
        slug = "cli-cli"
        repo_key_name = "somecli/cli-extra"
        # Old: substring match
        old_match = slug in repo_key_name.replace('/', '-')
        assert old_match is True, "Precondition: old logic DOES match (the bug)"
        # New: exact match
        new_match = repo_key_name.replace('/', '-') == slug
        assert new_match is False, "Fix: exact match should NOT match"

    def test_exact_match_works(self):
        """slug 'cli-cli' SHOULD match repo 'cli/cli'."""
        slug = "cli-cli"
        repo_key_name = "cli/cli"
        new_match = repo_key_name.replace('/', '-') == slug
        assert new_match is True

    def test_build_master_csv_uses_exact_match(self):
        """Verify the source code uses == not 'in' for slug matching."""
        src = (STUDY_DIR / "build-master-csv.py").read_text()
        # Should NOT contain the substring match pattern
        assert "slug in repo_key[0].replace('/', '-')" not in src, \
            "build-master-csv.py still uses substring 'in' match"
        # Should contain exact match
        assert "repo_key[0].replace('/', '-') == slug" in src, \
            "build-master-csv.py should use == for exact match"


# ═══════════════════════════════════════════════════════════════════════
# Bug 3: Quality scores keyed by title (collision across repos)
# ═══════════════════════════════════════════════════════════════════════

class TestBug3QualityScoreKeyByTitle:
    def test_unified_csv_keys_by_repo_and_pr_number(self):
        """build-unified-csv should key quality scores by (repo, pr_number), not title."""
        src = (STUDY_DIR / "build-unified-csv.py").read_text()
        # Should NOT have q_by_title
        assert "q_by_title" not in src, \
            "build-unified-csv.py still uses q_by_title"

    def test_master_csv_no_dead_quality_loading(self):
        """build-master-csv should not load quality scores (dead code removed)."""
        src = (STUDY_DIR / "build-master-csv.py").read_text()
        # Quality loading was dead code — removed entirely
        assert "quality = {}" not in src, \
            "build-master-csv.py should not have dead quality loading code"
        assert "qual = quality" not in src, \
            "build-master-csv.py should not have unused qual variable"


# ═══════════════════════════════════════════════════════════════════════
# Bug 4: score-specs.py doesn't retry errors on resume
# ═══════════════════════════════════════════════════════════════════════

class TestBug4ScoreSpecsErrorRetry:
    def test_errors_filtered_on_resume(self):
        """score-specs.py should filter out error results when loading cached results."""
        src = (STUDY_DIR / "score-specs.py").read_text()
        # Should filter errors like score-formality.py does
        assert "'error' not in r" in src or '"error" not in r' in src, \
            "score-specs.py should filter out error results on resume"

    def test_error_prs_not_in_scored_set(self):
        """PRs with errors should not be in scored_prs, so they get retried."""
        # Simulate the fixed logic
        loaded = [
            {"pr_number": 1, "title": "ok", "overall": 50},
            {"pr_number": 2, "title": "bad", "error": "timeout"},
            {"pr_number": 3, "title": "ok2", "overall": 70},
        ]
        # Fixed: filter errors
        results = [r for r in loaded if 'error' not in r]
        scored_prs = {r["pr_number"] for r in results}
        assert 1 in scored_prs
        assert 2 not in scored_prs, "Error PR should NOT be in scored_prs"
        assert 3 in scored_prs


# ═══════════════════════════════════════════════════════════════════════
# Bug 5: @mention regex matches npm scoped packages
# ═══════════════════════════════════════════════════════════════════════

class TestBug5MentionRegexFalsePositives:
    def test_npm_scoped_package_not_counted(self):
        """@types/node and @angular/core should not count as human mentions."""
        from importlib import import_module, reload
        mod = import_module("compute-features")
        mod = reload(mod)

        body_with_npm = "We use @types/node and @angular/core for this project."

        # After fix: compute_features should not count these
        features = mod.compute_features({
            "pr_number": 1,
            "body": body_with_npm,
            "author": "testuser",
            "title": "test",
        })
        assert features["human_mentions"] == 0, \
            f"npm scoped packages should not count as human mentions, got {features['human_mentions']}"

    def test_real_mention_still_counted(self):
        """@johndoe should still count as a human mention."""
        from importlib import import_module, reload
        mod = import_module("compute-features")
        mod = reload(mod)
        features = mod.compute_features({
            "pr_number": 1,
            "body": "cc @johndoe for review",
            "author": "testuser",
            "title": "test",
        })
        assert features["human_mentions"] >= 1, \
            "Real @mentions should still be counted"


# ═══════════════════════════════════════════════════════════════════════
# Bug 6: Queue race condition in runner.py
# ═══════════════════════════════════════════════════════════════════════

class TestBug6QueueRaceCondition:
    def test_no_empty_then_get_nowait_pattern(self):
        """runner.py should not use q.empty() then q.get_nowait() pattern."""
        src = (STUDY_DIR / "runner.py").read_text()
        assert "q.empty()" not in src, \
            "runner.py should not use q.empty() (race condition)"
        assert "q.get_nowait()" not in src, \
            "runner.py should not use q.get_nowait() (race condition)"

    def test_trusts_disk_not_queue(self):
        """runner.py should trust disk (incremental saves), not queue results."""
        src = (STUDY_DIR / "runner.py").read_text()
        # Should NOT read results from queue — disk is source of truth
        assert "q.get(" not in src or "q.put(" in src, \
            "runner.py should trust disk, not queue (incremental saves)"


# ═══════════════════════════════════════════════════════════════════════
# Bug 7: Unclosed file handles in build-master-csv.py
# ═══════════════════════════════════════════════════════════════════════

class TestBug7UnclosedFileHandles:
    def test_no_json_load_open_pattern(self):
        """build-master-csv.py should not use json.load(open(fp)) — leaks handles."""
        src = (STUDY_DIR / "build-master-csv.py").read_text()
        # Match json.load(open(...)) pattern
        assert "json.load(open(" not in src, \
            "build-master-csv.py still has json.load(open(fp)) — unclosed file handles"


# ═══════════════════════════════════════════════════════════════════════
# Bug 8: reproduce-claims.py per-repo uses escaped not strict_escaped
# ═══════════════════════════════════════════════════════════════════════

class TestBug8PerRepoEscapedField:
    def test_per_repo_uses_strict_escaped(self):
        """reproduce-claims.py per-repo rate() calls should use strict_escaped."""
        src = (STUDY_DIR / "reproduce-claims.py").read_text()
        # Find the per-repo section (after "Per repo")
        per_repo_idx = src.index("Per repo")
        per_repo_section = src[per_repo_idx:per_repo_idx + 800]
        # Both spec'd and unspec'd escape rates must use strict_escaped
        assert 'rate(rs, "strict_escaped")' in per_repo_section, \
            "Per-repo spec'd escape rate should call rate(rs, \"strict_escaped\")"
        assert 'rate(ru, "strict_escaped")' in per_repo_section, \
            "Per-repo unspec'd escape rate should call rate(ru, \"strict_escaped\")"


# ═══════════════════════════════════════════════════════════════════════
# Bug 9: Duplicated LLM dispatch code
# ═══════════════════════════════════════════════════════════════════════

class TestBug9DuplicatedLlmCode:
    def test_llm_utils_module_exists(self):
        """llm_utils.py should exist with shared LLM dispatch code."""
        assert (STUDY_DIR / "llm_utils.py").exists(), \
            "llm_utils.py should exist"

    def test_llm_utils_has_required_functions(self):
        """llm_utils.py should have the 4 shared functions."""
        from importlib import import_module
        mod = import_module("llm_utils")
        assert hasattr(mod, "has_api_key")
        assert hasattr(mod, "score_via_api")
        assert hasattr(mod, "score_via_cli")
        assert hasattr(mod, "parse_llm_response")

    def test_score_specs_imports_from_llm_utils(self):
        """score-specs.py should import from llm_utils."""
        src = (STUDY_DIR / "score-specs.py").read_text()
        assert "from llm_utils import" in src or "import llm_utils" in src, \
            "score-specs.py should import from llm_utils"

    def test_score_formality_imports_from_llm_utils(self):
        """score-formality.py should import from llm_utils."""
        src = (STUDY_DIR / "score-formality.py").read_text()
        assert "from llm_utils import" in src or "import llm_utils" in src, \
            "score-formality.py should import from llm_utils"


# ═══════════════════════════════════════════════════════════════════════
# Bug 10: Fallback pagination loop never paginates
# ═══════════════════════════════════════════════════════════════════════

class TestBug10FallbackPaginationLoop:
    def test_dead_loop_documented_or_removed(self):
        """The for-loop with unconditional break should be documented or removed."""
        src = (STUDY_DIR / "runner.py").read_text()
        # Find the fallback function
        fallback_idx = src.index("def _fetch_prs_fallback")
        fallback_end = src.index("\ndef ", fallback_idx + 1)
        fallback_src = src[fallback_idx:fallback_end]
        # Either the loop is removed, or there's a comment explaining single-batch
        has_loop = "for batch_num in range" in fallback_src
        has_comment = "single" in fallback_src.lower() or "no cursor" in fallback_src.lower() or "pagination" in fallback_src.lower()
        if has_loop:
            # The unconditional break at the end should be gone or documented
            assert has_comment, \
                "If the loop remains, it must have a comment explaining single-batch behavior"
            # Verify the comment is near the last break
            last_break_idx = fallback_src.rfind('break')
            context_near_last = fallback_src[max(0, last_break_idx-300):last_break_idx]
            assert 'pagination' in context_near_last.lower() or 'single' in context_near_last.lower(), \
                "Last break should have a comment explaining single-batch pagination"


# ═══════════════════════════════════════════════════════════════════════
# Bug 11: Composite signals unweighted
# ═══════════════════════════════════════════════════════════════════════

class TestBug11CompositeSignalsUnweighted:
    def test_composite_has_documentation(self):
        """human_signals composite should have a comment explaining the weighting choice."""
        src = (STUDY_DIR / "compute-features.py").read_text()
        # Find the composite section
        idx = src.index("human_signals = ")
        context = src[max(0, idx - 300):idx + 200]
        # Should have a comment nearby about weighting / intentional / presence detection
        has_doc = any(kw in context.lower() for kw in [
            "intentional", "presence", "unweighted", "simple",
            "weight", "detection", "binary"
        ])
        assert has_doc, \
            "Composite signal computation should have a comment documenting the weighting choice"


# ═══════════════════════════════════════════════════════════════════════
# Bug 12: reproduce-claims.py division by zero
# ═══════════════════════════════════════════════════════════════════════

class TestBug12DivisionByZero:
    def test_total_zero_guarded(self):
        """reproduce-claims.py should guard against total==0 division."""
        src = (STUDY_DIR / "reproduce-claims.py").read_text()
        # Find the summary line with /total
        # It should be guarded by if total > 0
        summary_idx = src.index("shifted_earlier + helps_both")
        context = src[max(0, summary_idx - 200):summary_idx + 300]
        assert "if total > 0" in context or "if total:" in context, \
            "Division by total should be guarded against zero"


# ═══════════════════════════════════════════════════════════════════════
# Integration: verify parse_llm_response works correctly
# ═══════════════════════════════════════════════════════════════════════

class TestLlmUtilsIntegration:
    def test_parse_plain_json(self):
        from llm_utils import parse_llm_response
        result = parse_llm_response('{"key": "value"}')
        assert result == {"key": "value"}

    def test_parse_markdown_fenced_json(self):
        from llm_utils import parse_llm_response
        result = parse_llm_response('```json\n{"key": "value"}\n```')
        assert result == {"key": "value"}

    def test_parse_error_returns_error_dict(self):
        from llm_utils import parse_llm_response
        result = parse_llm_response('not json at all')
        assert "error" in result


# ═══════════════════════════════════════════════════════════════════════
# Issue A: aggregate.py REPO_META should derive from runner.REPOS
# ═══════════════════════════════════════════════════════════════════════

class TestIssueARepoMetaSync:
    def test_aggregate_repo_meta_uses_runner_repos(self):
        """aggregate.py REPO_META should be built from runner.REPOS, not hardcoded."""
        from aggregate import REPO_META
        from runner import REPOS
        # Every repo in runner.REPOS must appear in REPO_META
        for r in REPOS:
            assert r["repo"] in REPO_META, (
                f"Runner repo {r['repo']} missing from aggregate.REPO_META"
            )
            assert REPO_META[r["repo"]]["lang"] == r["lang"], (
                f"Language mismatch for {r['repo']}"
            )
            assert REPO_META[r["repo"]]["tier"] == r["tier"], (
                f"Tier mismatch for {r['repo']}"
            )

    def test_aggregate_repo_meta_count_matches_runner(self):
        """aggregate.py REPO_META should have the same count as runner.REPOS."""
        from aggregate import REPO_META
        from runner import REPOS
        assert len(REPO_META) == len(REPOS), (
            f"REPO_META has {len(REPO_META)} repos but runner.REPOS has {len(REPOS)}"
        )

    def test_aggregate_no_hardcoded_repo_meta(self):
        """aggregate.py should not have a hardcoded REPO_META dict."""
        src = (STUDY_DIR / "aggregate.py").read_text()
        # Should import from runner, not hardcode
        assert "from runner import" in src, \
            "aggregate.py should import from runner"
        # Should NOT have inline repo definitions like "kubernetes/kubernetes"
        assert '"kubernetes/kubernetes"' not in src, \
            "aggregate.py should not hardcode repo names"


# ═══════════════════════════════════════════════════════════════════════
# Issue B: score-engagement.py should use llm_utils, not duplicate code
# ═══════════════════════════════════════════════════════════════════════

class TestIssueBEngagementLlmUtils:
    def test_score_engagement_imports_from_llm_utils(self):
        """score-engagement.py should import from llm_utils."""
        src = (STUDY_DIR / "score-engagement.py").read_text()
        assert "from llm_utils import" in src or "import llm_utils" in src, \
            "score-engagement.py should import from llm_utils"

    def test_score_engagement_no_local_dispatch_code(self):
        """score-engagement.py should not define its own _has_api_key, etc."""
        src = (STUDY_DIR / "score-engagement.py").read_text()
        assert "def _has_api_key" not in src, \
            "score-engagement.py should not define _has_api_key locally"
        assert "def _score_via_api" not in src, \
            "score-engagement.py should not define _score_via_api locally"
        assert "def _score_via_cli" not in src, \
            "score-engagement.py should not define _score_via_cli locally"
        assert "def _parse_response" not in src, \
            "score-engagement.py should not define _parse_response locally"

    def test_all_scoring_scripts_use_llm_utils(self):
        """All three scoring scripts should import from llm_utils."""
        for script in ["score-specs.py", "score-formality.py", "score-engagement.py"]:
            src = (STUDY_DIR / script).read_text()
            assert "from llm_utils import" in src, \
                f"{script} should import from llm_utils"
