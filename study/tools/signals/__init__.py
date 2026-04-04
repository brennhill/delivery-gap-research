"""
delivery-gap-signals — Shared signal detection for delivery pipeline tools.

Pure stateless functions for classifying commit messages and file paths.
No I/O, no subprocess calls, no dependencies beyond the Python stdlib.

Used by: changeledger, CatchRate, Upfront
"""

from .signals import (
    compute_file_overlap,
    extract_fixes_sha,
    extract_pr_number_from_subject,
    extract_revert_pr_numbers,
    extract_ticket_ids,
    is_dependency_change,
    is_fix_message,
    is_revert_message,
    is_source_file,
)

__all__ = [
    "compute_file_overlap",
    "extract_fixes_sha",
    "extract_pr_number_from_subject",
    "extract_revert_pr_numbers",
    "extract_ticket_ids",
    "is_dependency_change",
    "is_fix_message",
    "is_revert_message",
    "is_source_file",
]

from .models import CIStatus, MergedChange, Review

__version__ = "0.2.0"
