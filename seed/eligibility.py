"""Refund eligibility as a pure function.

This module is the ground-truth oracle for refunds. The seed script calls it
to stamp `refund_eligible` on every order, the agent's `issue_refund` tool
trusts the stamped flag, and Module 3's tests call the same function as their
oracle. It lives in its own module, with no database or framework imports, so
tests can import it directly.
"""

from __future__ import annotations

from datetime import date


def effective_return_window_days(
    platform_window_days: int, store_override_days: int | None
) -> int:
    """Return the window that applies to an order.

    Per facts.yaml `store_overrides.precedence`, a store override takes
    precedence over the platform default. `store_override_days` is None when
    the store has no override.
    """
    if store_override_days is not None:
        return store_override_days
    return platform_window_days


def is_refund_eligible(
    *,
    status: str,
    delivered_at: date | None,
    as_of: date,
    return_window_days: int,
) -> bool:
    """Decide whether an order is refund-eligible on `as_of`.

    An order is eligible if and only if all of these hold:
      - `status` is exactly "delivered". Placed, shipped, cancelled, and
        already-refunded orders are never eligible.
      - `delivered_at` is not None.
      - The delivery is not in the future: `delivered_at <= as_of`.
      - The window has not passed: `(as_of - delivered_at).days` is at most
        `return_window_days`. Day `return_window_days` itself is still
        eligible (the window is inclusive).

    The window counts from the delivery date, not the purchase date
    (facts.yaml `return_window_days`).
    """
    if status != "delivered":
        return False
    if delivered_at is None:
        return False
    age_days = (as_of - delivered_at).days
    return 0 <= age_days <= return_window_days


def refund_needs_approval(amount_usd: float, threshold_usd: float) -> bool:
    """True when a refund must be queued for human approval.

    Refunds strictly above the threshold queue; a refund of exactly the
    threshold auto-executes (facts.yaml `refund_auto_approve_threshold_usd`).
    """
    return amount_usd > threshold_usd
