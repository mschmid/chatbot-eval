"""Golden cases for the refund-eligibility oracle, including the three
pinned demo orders (Module 1 outline, Artifact L)."""

from __future__ import annotations

from datetime import date

from agent import db
from seed.eligibility import (
    effective_return_window_days,
    is_refund_eligible,
    refund_needs_approval,
)

ASOF = date(2026, 7, 1)


def eligible(days_ago: int, window: int = 30, status: str = "delivered") -> bool:
    return is_refund_eligible(
        status=status,
        delivered_at=ASOF.fromordinal(ASOF.toordinal() - days_ago),
        as_of=ASOF,
        return_window_days=window,
    )


def test_inside_window_is_eligible() -> None:
    assert eligible(12) is True  # order #4127's shape


def test_outside_window_is_not_eligible() -> None:
    assert eligible(45) is False  # order #3980's shape


def test_window_boundary_is_inclusive() -> None:
    assert eligible(30) is True
    assert eligible(31) is False


def test_only_delivered_orders_are_eligible() -> None:
    for status in ("placed", "shipped", "cancelled", "refunded"):
        assert eligible(5, status=status) is False


def test_missing_delivery_date_is_not_eligible() -> None:
    assert (
        is_refund_eligible(
            status="delivered", delivered_at=None, as_of=ASOF, return_window_days=30
        )
        is False
    )


def test_future_delivery_is_not_eligible() -> None:
    assert eligible(-1) is False


def test_store_override_takes_precedence() -> None:
    assert effective_return_window_days(30, 14) == 14
    assert effective_return_window_days(30, None) == 30
    assert eligible(20, window=14) is False  # inside platform window, outside override
    assert eligible(20, window=30) is True


def test_threshold_is_exclusive() -> None:
    assert refund_needs_approval(100.0, 100) is False
    assert refund_needs_approval(100.01, 100) is True
    assert refund_needs_approval(240.0, 100) is True  # order #4455's shape


def test_pinned_demo_orders(world: dict) -> None:
    """The seed must produce exactly the Artifact L orders."""
    conn = db.connect()
    try:
        o4127 = db.get_order(conn, 4127)
        o3980 = db.get_order(conn, 3980)
        o4455 = db.get_order(conn, 4455)
    finally:
        conn.close()

    for order in (o4127, o3980, o4455):
        assert order is not None
        assert order.user_id == 1
        assert order.store_id == 1
        assert order.status == "delivered"

    # #4127: delivered 12 days ago, $84; the happy path.
    assert o4127.total_usd == 84.0
    assert o4127.delivered_at == date(2026, 6, 19)
    assert o4127.refund_eligible is True

    # #3980: delivered 45 days ago; outside the window.
    assert o3980.delivered_at == date(2026, 5, 17)
    assert o3980.refund_eligible is False

    # #4455: $240; eligible, but above the approval threshold.
    assert o4455.total_usd == 240.0
    assert o4455.delivered_at == date(2026, 6, 26)
    assert o4455.refund_eligible is True
