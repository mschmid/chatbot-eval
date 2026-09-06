"""Unit tests for deterministic behavior in the application (Artifact D).

A tool is a Python function, so test it like one. Every assertion here is a
pure-function call against the pinned demo facts: no LLM, no database, no
network, milliseconds per test. The unit tests run on every commit;
it costs nothing, and it catches a refactor that breaks your logic (not the
agent misbehaving; the complete agent tests cover that behavior).

The expectations are the pinned demo orders and the facts sheet:
  - #4127: delivered 12 days before the anchor, $84  -> eligible, auto
  - #3980: delivered 45 days before the anchor, $52  -> outside the window
  - #4455: delivered  5 days before the anchor, $240 -> eligible, queued
  - Juniper Home Goods carries a 14-day override of the 30-day platform
    window (store over platform, facts.yaml `store_overrides.precedence`).
"""

from __future__ import annotations

from datetime import timedelta

from agent.auth import AuthContext, can_cancel_order, can_view_order
from agent.config import load_facts
from seed.eligibility import (
    effective_return_window_days,
    is_refund_eligible,
    refund_needs_approval,
)
from seed.generate import WORLD_ASOF

FACTS = load_facts()
PLATFORM_WINDOW = FACTS["return_window_days"]
THRESHOLD = FACTS["refund_auto_approve_threshold_usd"]


def _delivered(days_ago: int):
    return WORLD_ASOF - timedelta(days=days_ago)


# ---- refund eligibility: the three pinned demo orders ---------------------


def test_unit_order_4127_is_eligible_and_auto_approves() -> None:
    assert is_refund_eligible(
        status="delivered",
        delivered_at=_delivered(12),
        as_of=WORLD_ASOF,
        return_window_days=PLATFORM_WINDOW,
    )
    assert not refund_needs_approval(84.0, THRESHOLD)


def test_unit_order_3980_is_outside_the_window() -> None:
    assert not is_refund_eligible(
        status="delivered",
        delivered_at=_delivered(45),
        as_of=WORLD_ASOF,
        return_window_days=PLATFORM_WINDOW,
    )


def test_unit_order_4455_is_eligible_but_queues_for_approval() -> None:
    assert is_refund_eligible(
        status="delivered",
        delivered_at=_delivered(5),
        as_of=WORLD_ASOF,
        return_window_days=PLATFORM_WINDOW,
    )
    assert refund_needs_approval(240.0, THRESHOLD)
    # Exactly at the threshold auto-executes; strictly above queues.
    assert not refund_needs_approval(float(THRESHOLD), THRESHOLD)


def test_unit_store_override_takes_precedence() -> None:
    # Juniper Home Goods: 14-day override of the 30-day platform default.
    window = effective_return_window_days(PLATFORM_WINDOW, 14)
    assert window == 14
    # Delivered 20 days ago: inside the platform window, outside the
    # override. The override wins, so the order is NOT eligible.
    assert not is_refund_eligible(
        status="delivered",
        delivered_at=_delivered(20),
        as_of=WORLD_ASOF,
        return_window_days=window,
    )
    # No override falls back to the platform default.
    assert effective_return_window_days(PLATFORM_WINDOW, None) == PLATFORM_WINDOW


def test_unit_non_delivered_orders_are_never_eligible() -> None:
    for status in ("placed", "shipped", "cancelled", "refunded"):
        assert not is_refund_eligible(
            status=status,
            delivered_at=_delivered(2) if status != "placed" else None,
            as_of=WORLD_ASOF,
            return_window_days=PLATFORM_WINDOW,
        )


# ---- permission checks: the access matrix ---------------------------------


def test_unit_merchant_cannot_view_another_stores_order() -> None:
    merchant_s1 = AuthContext(user_id=9001, role="merchant", store_id=1)
    # An order belonging to shopper 444 at store 2: out of scope.
    assert not can_view_order(merchant_s1, order_user_id=444, order_store_id=2)
    # The same merchant's own store is in scope.
    assert can_view_order(merchant_s1, order_user_id=444, order_store_id=1)


def test_unit_shopper_sees_only_their_own_orders() -> None:
    shopper = AuthContext(user_id=1, role="shopper")
    assert can_view_order(shopper, order_user_id=1, order_store_id=2)
    assert not can_view_order(shopper, order_user_id=2, order_store_id=2)


def test_unit_support_sees_any_order() -> None:
    support = AuthContext(user_id=9501, role="support")
    assert can_view_order(support, order_user_id=444, order_store_id=2)


def test_unit_cancel_scope_matches_view_scope() -> None:
    shopper = AuthContext(user_id=1, role="shopper")
    assert can_cancel_order(shopper, order_user_id=1, order_store_id=1)
    assert not can_cancel_order(shopper, order_user_id=2, order_store_id=1)
