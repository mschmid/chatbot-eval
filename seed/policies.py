"""Dev-scale policy doc templates.

These ~15 docs are placeholders for the full drafted help-center corpus
(~600 to 800 docs at full scale, drafted by a model and validated against the
facts sheet; see the Module 1 outline, Lecture 3.1). At dev scale a template
function renders them straight from facts.yaml so the corpus and the database
cannot disagree. Every number in every body is declared in the doc's front
matter, and seed/validate.py checks those declarations against facts.yaml.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class PolicyDoc:
    policy_id: str
    title: str
    audience: str  # "shopper" | "merchant" | "all"
    body: str
    # Facts-sheet keys this doc uses, with the value the doc claims.
    facts_used: dict[str, Any] = field(default_factory=dict)
    # Numbers in the body that come from seed data (e.g. a store override),
    # not from facts.yaml.
    extra_numbers: list[int] = field(default_factory=list)

    def to_markdown(self) -> str:
        lines = ["---"]
        lines.append(f"policy_id: {self.policy_id}")
        lines.append(f"title: {self.title}")
        lines.append(f"audience: {self.audience}")
        lines.append("status: dev-placeholder")
        if self.facts_used:
            lines.append("facts_used:")
            for key, value in self.facts_used.items():
                lines.append(f"  {key}: {value}")
        if self.extra_numbers:
            lines.append(f"extra_numbers: [{', '.join(str(n) for n in self.extra_numbers)}]")
        lines.append("---")
        lines.append("")
        lines.append(f"# {self.title}")
        lines.append("")
        lines.append(self.body.strip())
        lines.append("")
        return "\n".join(lines)


def render_platform_policies(facts: dict[str, Any]) -> list[PolicyDoc]:
    """Render the platform-wide policy docs from the facts sheet."""
    name = facts["platform_name"]
    window = facts["return_window_days"]
    threshold = facts["refund_auto_approve_threshold_usd"]
    refund_min = facts["refund_processing_days_min"]
    refund_max = facts["refund_processing_days_max"]
    restock = facts["restocking_fee_max_percent"]
    dispute = facts["dispute_window_days"]
    payout_processing = facts["payout_processing_business_days"]
    sla = facts["support_escalation_sla_hours"]
    handling = facts["shipping_handling_days_max"]
    transit = facts["shipping_transit_days_max"]

    docs = [
        PolicyDoc(
            policy_id="cw-returns",
            title=f"{name} return policy",
            audience="all",
            facts_used={"return_window_days": window},
            body=(
                f"Items bought on {name} can be returned within {window} days "
                f"of delivery. The window counts from the delivery date, not the "
                f"purchase date. Items must be in the condition described by the "
                f"store's listing. Individual stores may override this window; "
                f"see the store overrides policy and the store's own policy page."
            ),
        ),
        PolicyDoc(
            policy_id="cw-refunds",
            title=f"{name} refund policy",
            audience="all",
            facts_used={
                "refund_processing_days_min": refund_min,
                "refund_processing_days_max": refund_max,
                "refund_auto_approve_threshold_usd": threshold,
            },
            body=(
                f"Approved refunds go back to the original payment method and "
                f"arrive in {refund_min} to {refund_max} business days. Refunds "
                f"of {threshold} dollars or less execute automatically once the "
                f"order passes the eligibility check. Refunds above {threshold} "
                f"dollars are queued for review by a human support agent before "
                f"any money moves."
            ),
        ),
        PolicyDoc(
            policy_id="cw-store-overrides",
            title="How store policies interact with platform policy",
            audience="all",
            facts_used={"return_window_days": window},
            body=(
                f"Stores on {name} may set their own return windows and fees. "
                f"An override is valid only if it is stated on the store's own "
                f"policy page. When a store policy and the platform default "
                f"disagree, the store policy wins, whether it is stricter or "
                f"looser than the platform default of {window} days."
            ),
        ),
        PolicyDoc(
            policy_id="cw-cancellations",
            title=f"{name} order cancellation policy",
            audience="all",
            facts_used={},
            body=(
                f"An order can be cancelled at no cost any time before the store "
                f"ships it. Once an order has shipped it can no longer be "
                f"cancelled; the buyer should instead wait for delivery and "
                f"request a return under the {name} return policy."
            ),
        ),
        PolicyDoc(
            policy_id="cw-disputes",
            title=f"{name} dispute policy",
            audience="all",
            facts_used={"dispute_window_days": dispute},
            body=(
                f"Buyers can dispute a charge for up to {dispute} days after "
                f"delivery. Disputes are always handled by a human support "
                f"agent, never resolved automatically. Opening a dispute pauses "
                f"any pending refund on the same order."
            ),
        ),
        PolicyDoc(
            policy_id="cw-restocking-fees",
            title=f"{name} restocking fee policy",
            audience="all",
            facts_used={"restocking_fee_max_percent": restock},
            body=(
                f"A store may charge a restocking fee of up to {restock} percent "
                f"on returned items that have been opened. The fee applies only "
                f"if the store has opted in, and the fee must be stated on the "
                f"store's policy page. Unopened items are never charged a "
                f"restocking fee."
            ),
        ),
        PolicyDoc(
            policy_id="cw-payouts",
            title=f"{name} merchant payout schedule",
            audience="merchant",
            facts_used={"payout_processing_business_days": payout_processing},
            body=(
                f"Merchant payouts run weekly, on Fridays. Each payout takes "
                f"{payout_processing} business days to process after the run. "
                f"Refunds issued during the week are deducted from the next "
                f"payout."
            ),
        ),
        PolicyDoc(
            policy_id="cw-escalations",
            title="When a case goes to a human",
            audience="all",
            facts_used={
                "support_escalation_sla_hours": sla,
                "refund_auto_approve_threshold_usd": threshold,
            },
            body=(
                f"Some cases always go to a human support agent: refunds above "
                f"{threshold} dollars, account changes, disputes, and anything "
                f"the assistant cannot resolve from policy and the order record. "
                f"A human responds to an escalation within {sla} hours."
            ),
        ),
        PolicyDoc(
            policy_id="cw-roles",
            title=f"Roles and permissions on {name}",
            audience="all",
            facts_used={},
            body=(
                f"{name} has three roles. Shoppers can see and manage their own "
                f"orders. Merchants can see and manage orders of their own "
                f"store, and cannot see other stores' orders or shoppers' other "
                f"purchases. Support staff can look up any order. The platform "
                f"enforces these permissions in its systems; support assistants "
                f"cannot grant exceptions."
            ),
        ),
        PolicyDoc(
            policy_id="cw-shipping",
            title=f"{name} shipping policy",
            audience="all",
            facts_used={
                "shipping_handling_days_max": handling,
                "shipping_transit_days_max": transit,
            },
            body=(
                f"Stores ship orders within {handling} days of purchase. "
                f"Standard delivery takes up to {transit} days in transit after "
                f"shipment. Tracking is available on the order page once the "
                f"store marks the order shipped."
            ),
        ),
        PolicyDoc(
            policy_id="cw-account-security",
            title="Account and payment security",
            audience="all",
            facts_used={},
            body=(
                f"{name} support assistants never change payment cards, "
                f"passwords, or account details in chat, and never ask for full "
                f"card numbers. Account and payment changes happen only through "
                f"account settings. Requests for legal advice are outside "
                f"support's scope and are declined."
            ),
        ),
        PolicyDoc(
            policy_id="cw-getting-help",
            title=f"Getting help on {name}",
            audience="all",
            facts_used={"support_escalation_sla_hours": sla},
            body=(
                f"The {name} support assistant answers questions about orders, "
                f"returns, refunds, products, and platform policy, and it cites "
                f"the policy page behind every policy answer. If the assistant "
                f"cannot resolve a case it opens a ticket for a human agent, who "
                f"responds within {sla} hours."
            ),
        ),
    ]
    return docs


def render_store_policy(
    facts: dict[str, Any],
    store_name: str,
    store_slug: str,
    return_window_override_days: int | None,
    restocking_fee_opt_in: bool,
) -> PolicyDoc | None:
    """Render a store's own policy page, or None if the store has no overrides.

    Only stores that deviate from platform defaults get a page, which mirrors
    the facts-sheet rule that an override must be visible in the store's
    policy doc.
    """
    if return_window_override_days is None and not restocking_fee_opt_in:
        return None

    name = facts["platform_name"]
    window = facts["return_window_days"]
    restock = facts["restocking_fee_max_percent"]
    parts: list[str] = []
    facts_used: dict[str, Any] = {"return_window_days": window}
    extra_numbers: list[int] = []

    if return_window_override_days is not None:
        parts.append(
            f"{store_name} accepts returns within "
            f"{return_window_override_days} days of delivery, instead of the "
            f"{name} platform default of {window} days. This store window "
            f"takes precedence for all {store_name} orders."
        )
        extra_numbers.append(return_window_override_days)
    else:
        parts.append(
            f"{store_name} follows the {name} platform return window of "
            f"{window} days from delivery."
        )
    if restocking_fee_opt_in:
        parts.append(
            f"{store_name} charges a restocking fee of up to {restock} percent "
            f"on opened items, as permitted by the {name} restocking fee "
            f"policy."
        )
        facts_used["restocking_fee_max_percent"] = restock

    return PolicyDoc(
        policy_id=f"store-{store_slug}-policy",
        title=f"{store_name} store policy",
        audience="all",
        facts_used=facts_used,
        extra_numbers=extra_numbers,
        body=" ".join(parts),
    )
