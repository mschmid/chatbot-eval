"""Invariants for the judge life cycle.

These guards teach the method by refusing to break it (the lecture states
them as rules, Outline "Guardrails"):

  - ``judge_alignment`` on the ``test`` split raises unless the judge is
    frozen. You do not get to peek at the test set while you are still
    tuning the prompt.
  - ``freeze_judge`` is one-way per version. Fixing a frozen judge means
    registering a *new* version, which re-locks ``test``.
  - ``split_labels`` refuses thin classes instead of silently producing
    unstable estimates.
  - ``corrected_prevalence`` runs only on a frozen judge.
  - Label writes append rather than overwrite, so the flip history in the
    iteration log is complete. (Enforced structurally in ``tools.py`` via
    :func:`analysis.helpers._state.append_jsonl`; this module supplies the
    guard the SKILL doc points at.)

The functions here are the single source of truth for these checks; the
other helpers call them so the error messages stay identical everywhere.
"""

from __future__ import annotations

from typing import Any


class GuardViolation(RuntimeError):
    """Raised when a judge-life-cycle invariant would be broken.

    A distinct type so tests can assert on the failure mode precisely and
    students can catch it without swallowing unrelated ``RuntimeError``s.
    """


def is_frozen(judge: dict[str, Any]) -> bool:
    """True when the judge record is frozen (its prompt is locked)."""
    return judge.get("status") == "frozen"


def require_frozen_for_test(judge: dict[str, Any], split: str) -> None:
    """Guard for ``judge_alignment``: the ``test`` split is unavailable
    until the judge is frozen.

    Any split other than ``test`` passes through untouched. ``test`` passes
    only when the judge's status is ``frozen``.
    """
    if split == "test" and not is_frozen(judge):
        raise GuardViolation(
            f"judge '{judge.get('judge_id', '?')}' is not frozen; the test "
            "split is locked until you call freeze_judge. Refine and freeze "
            "first, then measure on test exactly once."
        )


def require_frozen_for_prevalence(judge: dict[str, Any]) -> None:
    """Guard for ``corrected_prevalence``: a raw judge count is only worth
    correcting once the judge has test-set TPR/TNR, which requires a
    freeze."""
    if not is_frozen(judge):
        raise GuardViolation(
            f"judge '{judge.get('judge_id', '?')}' is not frozen; "
            "corrected_prevalence needs the frozen judge's test TPR/TNR. "
            "Freeze the judge and run judge_alignment on test first."
        )


def require_not_frozen_for_iteration(judge: dict[str, Any]) -> None:
    """Guard for dev refinement: a frozen version accepts no more dev
    iterations. Register a new version to keep tuning."""
    if is_frozen(judge):
        raise GuardViolation(
            f"judge '{judge.get('judge_id', '?')}' is frozen; register a new "
            "version to keep iterating (freezing is one-way per version, and "
            "a new version re-locks the test split)."
        )


def check_freeze_allowed(judge: dict[str, Any]) -> None:
    """Guard for ``freeze_judge``: freezing twice is a no-op-that-should-be
    -an-error, because it signals the caller thinks they can re-freeze after
    edits. They cannot; a new version is the only way forward."""
    if is_frozen(judge):
        raise GuardViolation(
            f"judge '{judge.get('judge_id', '?')}' is already frozen; "
            "freezing is one-way per version. Register a new version to make "
            "further changes."
        )


def check_split_class_counts(
    fail_total: int,
    pass_total: int,
    min_per_class: int,
    fractions: tuple[float, float, float],
) -> None:
    """Guard for ``split_labels``: refuse to split when either class is too
    thin to land ``min_per_class`` examples in the smallest of development or test.

    We size the check against the smaller of the dev and test fractions,
    because that split is the binding constraint. When the pool cannot
    support the target, we raise rather than proceed, since two examples from
    either class cannot support a useful estimate for the corresponding rate.
    """
    _, dev_frac, test_frac = fractions
    smallest_eval_frac = min(dev_frac, test_frac)
    # Smallest number of a class we would expect in the tighter eval split.
    reachable_fail = int(fail_total * smallest_eval_frac)
    reachable_pass = int(pass_total * smallest_eval_frac)
    if reachable_fail < min_per_class or reachable_pass < min_per_class:
        raise GuardViolation(
            "human judgments are too thin to split: with fractions "
            f"{fractions} the smaller eval split would hold about "
            f"{reachable_fail} fail / {reachable_pass} pass, below the "
            f"minimum of {min_per_class} per class. Label more traces "
            "(next_to_label enriches for both classes) or lower "
            "min_per_class deliberately."
        )
