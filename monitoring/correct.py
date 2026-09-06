"""Bias-corrected prevalence, applied on a monitoring schedule.

A judge's raw flag rate on the sample is biased by the judge's own error
rates: a judge with TPR 0.83 and TNR 0.95 both misses real failures and
flags clean traces. Module 2.5 introduced the Rogan-Gladen correction;
monitoring applies the same calculation on a cadence over the
live sample, using the frozen judge's TEST-split labels and predictions
(its measured TPR and TNR) exactly as Module 2 measured them.
"""

from __future__ import annotations

from typing import Any, Sequence


def corrected_mode_prevalence(
    sample_preds: Sequence[int],
    test_labels: Sequence[int],
    test_preds: Sequence[int],
    confidence: float = 0.95,
    bootstrap_iterations: int = 20000,
    seed: int | None = 7,
) -> dict[str, Any]:
    """Bias-corrected live prevalence for one mode from sampled verdicts.

    The contract, precisely:

      1. ``raw`` is the uncorrected flag rate: ``mean(sample_preds)``.
      2. Compute the frozen judge's TPR and TNR from ``test_labels`` and
         ``test_preds`` (failure-positive convention: 1 = failure present).
         TPR is the flagged fraction of true failures; TNR is the unflagged
         fraction of true passes.
      3. Compute the Rogan-Gladen point estimate, then resample the held-out
         records and sampled predictions to obtain a percentile-bootstrap
         interval. Use a seeded NumPy generator so the committed result is
         reproducible.
      4. ``validity_warning`` is a non-empty string when ``tpr + tnr <=
         1.05``: the correction divides by (TPR + TNR - 1), so a judge near
         that boundary produces an unstable estimate nobody should act on.
         Otherwise it is "". A judge with TPR + TNR <= 1 is no better than
         chance; the warning covers the sliver just
         above that, where the math works but the number is not actionable.)

    Args:
        sample_preds: the judge's 0/1 verdicts over the UNIFORM BASE sample
            only (never the risk strata; they are biased toward failure by
            design).
        test_labels: human labels for the judge's test split (from the
            frozen Module 2 judge).
        test_preds: the frozen judge's predictions on that test split.
        confidence: interval confidence level.
        bootstrap_iterations: number of percentile-bootstrap replicates.
        seed: numpy seed for a reproducible interval; None leaves the RNG
            untouched.

    Returns:
        {"raw", "corrected", "ci_low", "ci_high", "confidence",
         "test_tpr", "test_tnr", "n_sample", "validity_warning"}
        with "corrected" clamped to [0, 1] and rates rounded to 4 places.

    Raises:
        ValueError: if sample_preds or test_labels is empty.
    """
    ### YOUR CODE HERE (hw7)
    raise NotImplementedError("hw7: implement corrected_mode_prevalence")
