"""Error-analysis skill helpers (Module 2).

Thin, file-backed helper functions the coding agent calls across the
error-analysis loop, plus direct calculations for validation and corrected
prevalence. All
state persists under ``analysis/state/`` (Artifact J layout) so every run is
inspectable and resumable.

These functions are instructor provided and fully implemented. Students use
the helpers while building the review interface, developing judge prompts,
and interpreting the resulting evidence.

Agent-facing surface (Outline helper table):

    select_traces, next_to_label, split_labels, register_judge, run_judge,
    judge_alignment, iteration_log, freeze_judge, corrected_prevalence,
    failure_report
"""

from __future__ import annotations

from .guards import GuardViolation
from .reporting import corrected_prevalence, failure_report
from .tools import (
    freeze_judge,
    iteration_log,
    judge_alignment,
    next_to_label,
    register_judge,
    run_judge,
    select_traces,
    split_labels,
)

__all__ = [
    "select_traces",
    "next_to_label",
    "split_labels",
    "register_judge",
    "run_judge",
    "judge_alignment",
    "iteration_log",
    "freeze_judge",
    "corrected_prevalence",
    "failure_report",
    "GuardViolation",
]
