"""The access matrix (SPEC.md section 3), tested as pure functions."""

from __future__ import annotations

import pytest

from agent.auth import AuthContext, can_cancel_order, can_refund_order, can_view_order

SHOPPER_1 = AuthContext(user_id=1, role="shopper")
SHOPPER_2 = AuthContext(user_id=2, role="shopper")
MERCHANT_STORE_1 = AuthContext(user_id=9001, role="merchant", store_id=1)
MERCHANT_STORE_2 = AuthContext(user_id=9002, role="merchant", store_id=2)
SUPPORT = AuthContext(user_id=9501, role="support")

# An order owned by shopper 1 at store 1.
ORDER_USER, ORDER_STORE = 1, 1


def test_shopper_sees_only_own_orders() -> None:
    assert can_view_order(SHOPPER_1, ORDER_USER, ORDER_STORE) is True
    assert can_view_order(SHOPPER_2, ORDER_USER, ORDER_STORE) is False


def test_merchant_sees_only_own_stores_orders() -> None:
    assert can_view_order(MERCHANT_STORE_1, ORDER_USER, ORDER_STORE) is True
    assert can_view_order(MERCHANT_STORE_2, ORDER_USER, ORDER_STORE) is False


def test_support_sees_any_order() -> None:
    assert can_view_order(SUPPORT, ORDER_USER, ORDER_STORE) is True


def test_refund_and_cancel_scopes_match_view_scope() -> None:
    for check in (can_refund_order, can_cancel_order):
        assert check(SHOPPER_1, ORDER_USER, ORDER_STORE) is True
        assert check(SHOPPER_2, ORDER_USER, ORDER_STORE) is False
        assert check(MERCHANT_STORE_2, ORDER_USER, ORDER_STORE) is False
        assert check(SUPPORT, ORDER_USER, ORDER_STORE) is True


def test_merchant_context_requires_store_id() -> None:
    with pytest.raises(ValueError):
        AuthContext(user_id=9001, role="merchant")


def test_unknown_role_is_rejected() -> None:
    with pytest.raises(ValueError):
        AuthContext(user_id=1, role="admin")
