"""The Module 4 kill switch. Instructor-provided and complete (Part E).

A degradation ladder controlled by one environment variable,
``CARTWHEEL_KILL_SWITCH``. This is the Manage-function control from the
governance record: a documented way to pause the riskiest tools without a
code change or a redeploy. It is deliberately a small, boring, deterministic
seam so that a student can exercise it during a launch drill and attach the
trace as evidence that the kill switch works.

Levels, read from ``CARTWHEEL_KILL_SWITCH``:

  - "off" (the default, and any unset/blank/unknown value): nothing is paused.
    The default is a no-op on purpose, so every existing test still passes.
  - "refunds": the refund tool is paused. Everything else runs.
  - "readonly": every write tool is paused (refunds and cancels), dropping the
    agent to read-only. Read tools still run.

The write tools this ladder governs are named in ``WRITE_TOOLS`` below. The
switch is enforced at the top of each write tool's logic (see
``agent/agent.py`` ``issue_refund_logic`` and ``agent/tools.py``
``cancel_order``), before any work, so a paused tool returns a structured
``paused`` result instead of touching the database.
"""

from __future__ import annotations

import os

# Environment variable that holds the current kill-switch level.
KILL_SWITCH_ENV = "CARTWHEEL_KILL_SWITCH"

# The write (state-changing) tools the ladder can pause. Read tools are never
# paused by this switch; authorization and read scope live in agent/auth.py.
WRITE_TOOLS: frozenset[str] = frozenset({"issue_refund", "cancel_order"})


def _level() -> str:
    """The current kill-switch level, normalized to lowercase.

    An unset, blank, or unrecognized value reads as "off", so the safe
    default is to pause nothing.
    """
    value = (os.environ.get(KILL_SWITCH_ENV) or "off").strip().lower()
    if value not in ("off", "refunds", "readonly"):
        return "off"
    return value


def kill_switch(tool_name: str) -> str | None:
    """Return a reason string when ``tool_name`` is paused, else ``None``.

    Args:
        tool_name: The tool being invoked, e.g. "issue_refund" or
            "cancel_order". Names outside ``WRITE_TOOLS`` are never paused.

    Returns:
        ``None`` when the tool may run. A short human-readable reason string
        when the current ``CARTWHEEL_KILL_SWITCH`` level pauses this tool,
        suitable for the ``reason`` field of a structured ``paused`` result.

    Behavior by level:
        - "off": always returns ``None``.
        - "refunds": returns a reason for "issue_refund" only.
        - "readonly": returns a reason for every tool in ``WRITE_TOOLS``.
    """
    level = _level()
    if level == "off":
        return None
    if tool_name not in WRITE_TOOLS:
        return None
    if level == "refunds":
        if tool_name == "issue_refund":
            return (
                "the refund tool is paused by the kill switch "
                f"({KILL_SWITCH_ENV}=refunds); a human will handle refunds"
            )
        return None
    # level == "readonly": all write tools are paused.
    return (
        f"write actions are paused by the kill switch ({KILL_SWITCH_ENV}=readonly); "
        "the agent is running read-only"
    )
