"""The human approval flow for above threshold refunds (Homework 8, Part D).

Module 1 left a seam: ``issue_refund_logic`` writes a refund row with status
``queued_for_approval`` when the amount is above the auto-approval threshold,
and then stops. Nothing ever approves it. This module fills that seam
(Lecture 4.4). It adds a review surface, an approve/deny action, and an audit
trail, so a queued refund can only become effective through a logged human
decision.

Design (fixed by the spec, do not change):

  - The ``refunds`` table's CHECK constraint only allows the two statuses
    ``('auto_approved', 'queued_for_approval')``, and Module 4 does not alter
    it. So a human decision is NOT recorded by mutating the refund row's
    status. Instead:
      * every decision writes one row to a separate ``approvals`` audit table
        (who, when, approve or deny, and why), and
      * an approval updates the underlying ORDER's status to ``refunded`` via
        ``agent.db.set_order_status``. The refund row keeps its
        ``queued_for_approval`` status; the order status and the approvals row
        together are the record that the money moved.
  - Authorization is in code, not a prompt and not a guard: only a caller with
    role ``support`` may approve or reject. Anyone else gets
    ``permission_denied``. This is the same rule as the rest of the access
    matrix; the approval flow adds a handler, it does not weaken any check.

``ensure_approvals_table`` is provided. The four action functions
(``list_pending_refunds``, ``approve_refund``, ``reject_refund``, and
``render_decision_record``) are your holes. Contract tests are in
``tests/test_adversarial.py`` (``-k m4``).

``render_decision_record`` is Artifact D: the compact record a reviewer
actually reads before approving or denying. A reviewer looks at THIS, built
from structured data (the order and amount, the computed eligibility, the
user's stated reason, and the cited policy id if the reason names one), not at
the whole chat transcript. The review tool (``agent/review.py``) renders it
before asking a support operator to decide.

Result convention (see ``agent/auth.py``): success dictionaries contain
``"ok": True`` plus result fields; failures are ``{"ok": False, "error": <code>,
"reason": <str>}``.
"""

from __future__ import annotations

import re
import sqlite3
from typing import Any

from agent import db
from agent.auth import AuthContext, permission_denied


def ensure_approvals_table(conn: sqlite3.Connection) -> None:
    """Create the ``approvals`` audit table if it does not exist. PROVIDED.

    This is a separate table from ``refunds`` on purpose (see the module
    docstring): it records the human decision without touching the refund
    row's constrained status column. Idempotent, so it is safe to call before
    every approval action.

    Columns:
      - id: surrogate key.
      - refund_id: the queued refund this decision is about.
      - approver_id: the user id of the human who decided.
      - decision: 'approve' or 'deny' (CHECK-constrained).
      - reason: the human's free-text reason (required, non-empty by
        convention; the action functions enforce non-empty).
      - created_at: ISO timestamp of the decision.
    """
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS approvals (
            id INTEGER PRIMARY KEY,
            refund_id INTEGER NOT NULL REFERENCES refunds(id),
            approver_id INTEGER NOT NULL,
            decision TEXT NOT NULL CHECK (decision IN ('approve', 'deny')),
            reason TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
    )
    conn.commit()


def list_pending_refunds(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Return the refunds still awaiting a human decision (the review surface).

    A refund is pending when its status is ``queued_for_approval`` AND it has
    no row in the ``approvals`` table yet. A refund that already has an
    approvals row (approve or deny) has been decided and is not pending, even
    though its refund-row status is still ``queued_for_approval`` (recall that
    the status column is never mutated by the approval flow).

    This is the data behind the reviewer's queue. The reviewer reviews the
    decision, not the whole conversation, so return the compact fields that
    make a refund reviewable at a glance.

    Args:
        conn: An open connection to the world database. The caller is
            responsible for having created the ``approvals`` table first
            (call ``ensure_approvals_table``); if it does not exist, treat
            that as "no decisions recorded yet" is NOT allowed here, since the
            join needs the table. Assume ``ensure_approvals_table`` was
            called.

    Returns:
        A list of dicts, one per pending refund, newest first (order by the
        refund's ``created_at`` descending, then ``id`` descending). Each dict
        has exactly:
          {
            "refund_id": int,        # refunds.id
            "order_id": int,         # refunds.order_id
            "amount_usd": float,     # refunds.amount_cents / 100
            "reason": str,           # refunds.reason (the requested reason)
            "created_at": str,       # refunds.created_at
          }
        An empty list when nothing is pending.

    Implementation notes:
        One SQL query with a LEFT JOIN from ``refunds`` to ``approvals`` on
        ``refund_id``, filtered to status ``queued_for_approval`` and to rows
        where the joined ``approvals.id IS NULL``, works. Convert cents to USD
        by dividing by 100.
    """
    ### YOUR CODE HERE (m4)
    raise NotImplementedError("m4: implement list_pending_refunds")


def approve_refund(
    conn: sqlite3.Connection, refund_id: int, approver: AuthContext, reason: str
) -> dict[str, Any]:
    """Approve a queued refund: authorize, audit, and settle the order.

    Order of operations, exactly:

    1. Authorization, in code. Only ``approver.role == 'support'`` may
       approve. Otherwise return ``permission_denied(...)`` with a reason
       naming the role, and change nothing. This check comes first so an
       unauthorized caller cannot even learn whether the refund exists.
    2. Validate the reason: a non-empty string after stripping. Otherwise
       return ``{"ok": False, "error": "invalid_argument", "reason": ...}``.
    3. Look up the refund by id. If there is no refund with that id, or its
       status is not ``queued_for_approval``, return
       ``{"ok": False, "error": "not_found", "reason": ...}`` naming the id.
    4. Refuse a double decision: if an ``approvals`` row already exists for
       this ``refund_id`` (approve or deny), return
       ``{"ok": False, "error": "already_decided", "reason": ...}`` and change
       nothing.
    5. Otherwise: insert one ``approvals`` row with decision ``'approve'``,
       the ``approver.user_id``, the reason, and the world's current date as
       ``created_at`` (use ``agent.db.world_asof(conn).isoformat()``). Then
       update the refunded ORDER's status to ``'refunded'`` via
       ``agent.db.set_order_status`` (look up the refund's ``order_id``
       first). Do NOT change the refund row's status.

    Args:
        conn: Open world-database connection. Assume ``ensure_approvals_table``
            was already called.
        refund_id: The queued refund to approve.
        approver: The human's auth context. Must have role ``support``.
        reason: The human's reason for approving (required, non-empty).

    Returns:
        On success:
          {
            "ok": True,
            "status": "approved",
            "refund_id": refund_id,
            "order_id": int,          # the order now marked refunded
            "approver_id": approver.user_id,
          }
        Otherwise one of the structured errors described above.

    Implementation notes:
        Read the refund row with a small SELECT (id, order_id, status). Use
        ``agent.db.set_order_status(conn, order_id, "refunded")``, which
        commits. Insert the approvals row with a parameterized INSERT and
        commit.
    """
    ### YOUR CODE HERE (m4)
    raise NotImplementedError("m4: implement approve_refund")


def reject_refund(
    conn: sqlite3.Connection, refund_id: int, approver: AuthContext, reason: str
) -> dict[str, Any]:
    """Deny a queued refund: authorize and audit, leaving the order unchanged.

    Same shape as ``approve_refund`` but for a denial. Order of operations:

    1. Authorization: only ``approver.role == 'support'`` may reject;
       otherwise ``permission_denied(...)``.
    2. Validate the reason is non-empty (else ``invalid_argument``).
    3. Look up the refund; unknown id or a non-``queued_for_approval`` status
       is ``not_found``.
    4. Refuse a double decision: an existing ``approvals`` row for this
       ``refund_id`` returns ``already_decided`` and changes nothing.
    5. Otherwise insert one ``approvals`` row with decision ``'deny'``, the
       approver id, the reason, and ``world_asof`` as ``created_at``. Do NOT
       change the order status and do NOT change the refund row: a denied
       refund leaves the order exactly as it was.

    Args:
        conn: Open world-database connection (table already ensured).
        refund_id: The queued refund to deny.
        approver: The human's auth context; role ``support`` required.
        reason: The human's reason for denying (required, non-empty).

    Returns:
        On success:
          {
            "ok": True,
            "status": "denied",
            "refund_id": refund_id,
            "approver_id": approver.user_id,
          }
        Otherwise the structured errors above.
    """
    ### YOUR CODE HERE (m4)
    raise NotImplementedError("m4: implement reject_refund")


# A cited policy id in a free-text reason looks like the corpus ids: a short
# lowercased token such as "cw-returns" or "store-adversarial-21-policy". This
# is a convenience for render_decision_record; it does not validate the id.
_POLICY_ID_RE = re.compile(r"\b([a-z]{2,}[a-z0-9-]*-[a-z0-9-]+)\b")


def render_decision_record(conn: sqlite3.Connection, refund_id: int) -> str:
    """Build the compact reviewer record for one queued refund (Artifact D).

    This is what a human reads before approving or denying. It is assembled
    from STRUCTURED data, not from the transcript: the reviewer should be able
    to decide from the order, the amount, the computed eligibility, the stated
    reason, and any cited policy id, without trusting a model's narration. The
    review tool (``agent/review.py``) prints this for each pending refund
    before asking a support operator to approve or deny it.

    Pull the facts yourself from the database, do not accept them from chat:

      - The refund row (``refunds``): its ``order_id``, ``amount_cents`` (show
        as USD), ``reason`` (the user's stated reason), and ``created_at``.
      - The underlying order (via ``agent.db.get_order``): its ``total_usd``,
        ``status``, ``delivered_at``, and ``refund_eligible`` (the computed
        eligibility, the same field the tool checked).
      - A cited policy id, IF the stated reason names one. A reason may embed a
        corpus-style id such as ``cw-returns``; surface it as a separate field
        so the reviewer can check the cited policy rather than trust the prose.
        Use ``_POLICY_ID_RE`` (provided) to pull the first match; when the
        reason cites none, say so ("none cited"). Do not fetch or trust the
        policy text here; the reviewer follows the id.

    Format: a short, human-readable multi-line block. The exact wording is
    yours, but it MUST contain, as readable text, at least:
      - the refund id and order id,
      - the refund amount in USD (e.g. "$240.00"),
      - the order total and the computed eligibility (eligible or not),
      - the user's stated reason,
      - the cited policy id (or that none was cited).
    Keep it compact (a handful of lines). This is a record, not a transcript.

    Args:
        conn: Open world-database connection.
        refund_id: The queued refund to render.

    Returns:
        A multi-line string reviewer record. When there is no refund with that
        id, return a short one-line string saying so (this is a display helper,
        not an action, so it does not return the structured error dict).

    Implementation notes:
        One SELECT for the refund row, then ``agent.db.get_order`` for the
        order. Divide ``amount_cents`` by 100 for USD. Build the string with an
        f-string or a small list of lines joined by newlines. Do not mutate
        anything; this is read-only.
    """
    ### YOUR CODE HERE (m4)
    raise NotImplementedError("m4: implement render_decision_record (Artifact D)")
