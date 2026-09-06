"""Module 4 guards: your holes (Homework 8, Parts B and D).

Guards are defense in depth for the attacks that code cannot express
(Lecture 4.3). They are probabilistic and bypassable, so they lower risk but
never carry authorization. Authorization lives in ``agent/auth.py`` and stays
there; a guard is the wrong place for it, and the homework grader fails a
submission that guards an authorization hole.

This module has two layers, and you fill holes in both:

1. Two pure detection functions (easy to unit-test, no SDK, no model):

     - ``flags_injection``: rule-based detection of an instruction-override or
       prompt-extraction attempt in the user's message.
     - ``strip_external_links``: removes markdown links and images that point
       at a host outside an allowlist, the direct defense against the
       exfiltration attack A-I2.

2. Three real Agents-SDK objects that wrap those functions and plug into the
   run. These are what ``build_agent(ctx, defenses=True)`` attaches:

     - ``injection_input_guardrail``: an ``@input_guardrail`` that runs
       ``flags_injection`` on the incoming user text and trips the tripwire.
     - ``link_output_guardrail``: an ``@output_guardrail`` that runs
       ``strip_external_links`` on the agent's final reply against
       ``ALLOWED_LINK_HOSTS`` and trips when a non-allowlisted link is present.
     - ``refund_needs_human``: the async ``needs_approval`` predicate the
       refund tool uses to pause an above-threshold refund for a human.

The detection functions stay deterministic so they are gradable. A team may
replace the rule-based input detector with a separately evaluated classifier
or LLM evaluator. The course does not require a particular detector, and a
content-moderation endpoint is not a substitute for prompt-injection detection.

SDK contract (verified against ``openai-agents`` 0.17.7):

  - ``@input_guardrail`` wraps ``async fn(ctx, agent, user_input)`` and returns
    an ``InputGuardrail``; ``@output_guardrail`` wraps
    ``async fn(ctx, agent, agent_output)`` and returns an ``OutputGuardrail``.
    Both callables must return a ``GuardrailFunctionOutput(output_info=...,
    tripwire_triggered=<bool>)``. When the tripwire fires the SDK raises
    ``InputGuardrailTripwireTriggered`` / ``OutputGuardrailTripwireTriggered``.
  - The decorated object keeps the raw callable on ``.guardrail_function``, so
    the offline tests call ``injection_input_guardrail.guardrail_function(...)``
    directly with no live model.
  - ``needs_approval`` accepts ``async fn(run_context, tool_parameters,
    call_id) -> bool``. ``tool_parameters`` is the tool's argument dict (so
    ``params["amount_usd"]`` is the refund amount). Returning True makes the
    run pause with the call in ``result.interruptions`` (Part D).
"""

from __future__ import annotations

from typing import Any

from agents import (
    Agent,
    GuardrailFunctionOutput,
    RunContextWrapper,
    input_guardrail,
    output_guardrail,
)

from agent.auth import AuthContext
from agent.config import load_facts

# The kill switch lives next to the guards conceptually (both are Module 4
# controls), and re-exporting it here keeps a single import site for the
# safety seams. The implementation is in agent/killswitch.py.
from agent.killswitch import kill_switch  # noqa: F401  (re-exported for convenience)

# The hosts a reply may link to or embed images from. Anything else is treated
# as an exfiltration channel (attack A-I2) and stripped by the output guard.
# The customer-data-leaking store page plants an image at attacker.example,
# which is not here, so it gets removed.
ALLOWED_LINK_HOSTS: frozenset[str] = frozenset(
    {"cartwheel.example", "help.cartwheel.example"}
)


def flags_injection(text: str) -> bool:
    """Return True when ``text`` looks like a prompt-injection or extraction attempt.

    This is the rule-based input guard (Lecture 4.3, Artifact C). It is a
    deterministic pattern match, case-insensitive, over a short list of
    instruction-override and prompt-extraction phrases. It is intentionally
    simple so it is gradable. A broader detector could use a classifier or an
    LLM evaluator, but it would still require labeled Cartwheel cases and would
    not reliably stop a determined attacker. This guard reduces the volume of
    attempts that reach the model but never carries authorization.

    Detect (case-insensitive substring or simple pattern) at least these
    families, which cover the A-D2 extraction attack and the common override
    openers:
      - instruction override: "ignore all instructions",
        "ignore previous instructions", "disregard your instructions"
        (match "ignore"/"disregard" combined with "instructions", with
        "all"/"previous"/"prior"/"above"/"the" optionally between them),
      - prompt/context extraction: "system prompt", "reveal your instructions",
        "print your instructions", "your instructions verbatim",
        "session context" (the injected-context block name),
      - role reset: "you are now",
      - mode switch: "debug mode", "developer mode".

    Args:
        text: The user's message (or any untrusted string to screen). ``None``
            or an empty/whitespace string returns False.

    Returns:
        True when any pattern matches, else False. A benign message returns
        False.

    Implementation notes:
        Lowercase once, then test membership of a set of substrings and a
        couple of small regex patterns for the "ignore ... instructions"
        family. Keep it to a handful of rules; do not try to be exhaustive.
    """
    ### YOUR CODE HERE (m4)
    raise NotImplementedError("m4: implement flags_injection (rule-based input guard)")


def strip_external_links(reply: str, allowlist: frozenset[str]) -> str:
    """Remove markdown links and images whose host is not in ``allowlist``.

    This is the output guard that defends attack A-I2 (exfiltration through a
    poisoned store page that plants a markdown image whose URL encodes the
    customer's data). Any client that renders the reply's markdown would fetch
    that image and leak the data to the attacker's server. Stripping
    non-allowlisted links and images at the output boundary removes the
    exfiltration channel. It is a pure function so it is easy to test and
    cannot itself reach the network.

    What to strip:
      - Markdown images: ``![alt](url)``. If the url's host is not in
        ``allowlist``, remove the whole image (both the ``!`` and the
        ``[alt](url)``), leaving the surrounding text intact.
      - Markdown links: ``[text](url)``. If the url's host is not in
        ``allowlist``, replace the whole ``[text](url)`` with just ``text``
        (drop the link target, keep the visible words). This keeps the reply
        readable rather than blanking it.

    What to keep:
      - Images and links whose host is in ``allowlist`` are left unchanged.
      - All non-link text is left unchanged.

    Host matching:
      - Parse the host with ``urllib.parse.urlparse`` and compare
        ``parsed.hostname`` (already lowercased by urlparse) against
        ``allowlist``. A url with no host (for example a relative path or a
        bare fragment) is treated as NOT allowlisted, so it is stripped like
        any other non-allowlisted target. ``allowlist`` holds bare hostnames,
        e.g. ``frozenset({"cartwheel.example", "help.cartwheel.example"})``.

    Args:
        reply: The agent's final reply text, possibly containing markdown.
        allowlist: The set of hostnames whose links and images may stay.

    Returns:
        The reply with non-allowlisted links and images removed as described.
        When there is nothing to strip, the reply is returned unchanged.

    Implementation notes:
        A single regex that matches an optional leading ``!`` then
        ``[...](...)`` lets you handle images and links in one pass; inspect
        the leading ``!`` in the replacement function to decide whether to
        drop the whole match (image) or keep the link text (link).
    """
    ### YOUR CODE HERE (m4)
    raise NotImplementedError("m4: implement strip_external_links (output guard)")


# ---------------------------------------------------------------------------
# Real SDK guard objects (Homework 8, Part B). These wrap the pure
# functions above so build_agent(ctx, defenses=True) can attach them. The
# wiring in agent/agent.py imports these three names; the bodies below are
# your holes. A hole must NOT raise at import or construction time (offline
# tests build the agent with defenses on), so each raises NotImplementedError
# only when the guard actually runs.
# ---------------------------------------------------------------------------


@input_guardrail
async def injection_input_guardrail(
    ctx: RunContextWrapper[AuthContext],
    agent: Agent[AuthContext],
    user_input: str | list[Any],
) -> GuardrailFunctionOutput:
    """Input guardrail: trip when the incoming user text looks like an injection.

    This is the SDK object that wraps ``flags_injection``. When
    ``build_agent(ctx, defenses=True)`` attaches it, the SDK runs it on every
    turn's input before the model sees it, and raises
    ``InputGuardrailTripwireTriggered`` when the tripwire fires, halting the
    run. It is the defense against the A-D2 prompt-extraction family and the
    common override openers.

    Contract:
      - Normalize ``user_input`` to a single string. The SDK passes either a
        plain ``str`` (the common case for a chat turn) or a list of input
        items. For the list case, concatenate the text you can pull from it
        (each item is a dict; join the string values, or fall back to
        ``str(user_input)``). A robust one-liner is acceptable; the point is
        that ``flags_injection`` receives text, not a list.
      - Call ``flags_injection`` on that text.
      - Return ``GuardrailFunctionOutput(output_info={...},
        tripwire_triggered=<result of flags_injection>)``. Put something useful
        in ``output_info`` for the trace, for example
        ``{"flagged": <bool>, "guard": "injection"}``.

    Args:
        ctx: The run context wrapper (carries the ``AuthContext``). Not needed
            for the rule-based check, but it is part of the SDK signature.
        agent: The agent being guarded (part of the SDK signature).
        user_input: The turn's input, a ``str`` or a list of input-item dicts.

    Returns:
        A ``GuardrailFunctionOutput`` whose ``tripwire_triggered`` is True when
        ``flags_injection`` flags the text.

    Testability:
        The offline test calls
        ``injection_input_guardrail.guardrail_function(None, None, "...")`` and
        awaits it, so your body must work with a ``None`` context and agent.
        Do not touch ``ctx``/``agent`` beyond the signature.
    """
    ### YOUR CODE HERE (m4)
    raise NotImplementedError(
        "m4: implement injection_input_guardrail (wrap flags_injection)"
    )


@output_guardrail
async def link_output_guardrail(
    ctx: RunContextWrapper[AuthContext],
    agent: Agent[AuthContext],
    agent_output: Any,
) -> GuardrailFunctionOutput:
    """Output guardrail: trip when the final reply carries a non-allowlisted link.

    This is the SDK object that wraps ``strip_external_links``. When attached
    by ``build_agent(ctx, defenses=True)``, the SDK runs it on the agent's
    final output. It is the defense against the A-I2 exfiltration attack: a
    poisoned store page plants a markdown image whose URL encodes the
    customer's order ids, and any client that renders the reply would fetch
    that image and leak the data.

    Contract:
      - Coerce ``agent_output`` to a string (``str(agent_output)`` is fine; the
        final output is usually already text).
      - Run ``strip_external_links(text, ALLOWED_LINK_HOSTS)``.
      - Trip the tripwire when the cleaned text differs from the original, i.e.
        something was stripped: ``tripwire_triggered = (cleaned != text)``.
      - Return the cleaned text in ``output_info`` so the caller can log or
        substitute it, for example
        ``{"cleaned": cleaned, "stripped": cleaned != text,
        "guard": "link"}``.

    Two acceptable postures, both fine for the homework:
      - Trip and halt (raise ``OutputGuardrailTripwireTriggered``), treating a
        planted exfiltration link as a failed turn, or
      - use ``output_info["cleaned"]`` at the call site to rewrite the reply
        (the run loop can substitute it) while still recording the trip.
    Pick one and say which in your writeup. The offline test only checks the
    tripwire and the cleaned text.

    The fuller version of this guard also reuses your Module 2
    ``tool_result_misreport`` judge. That judge catches a reply that claims a
    refund was approved when the ``issue_refund`` tool actually returned
    ``queued_for_approval``. Load your frozen judge id with
    ``analysis.helpers._judges_by_mode()["tool_result_misreport"]`` and score
    the final reply against the tool result in the trace with
    ``analysis.helpers.run_judge(judge_id, trace_ids=[...], classify=...)``,
    then trip when the judge returns fail. That judge-reuse path is a
    live-run deliverable (Part C), not an offline test, because it needs a
    model call; keep it out of the offline ``tripwire_triggered`` logic above
    and demonstrate it with a before/after trace instead.

    Args:
        ctx: The run context wrapper (part of the SDK signature).
        agent: The agent being guarded (part of the SDK signature).
        agent_output: The agent's final output (usually a string).

    Returns:
        A ``GuardrailFunctionOutput`` whose ``tripwire_triggered`` is True when
        a non-allowlisted link or image was stripped.

    Testability:
        The offline test calls
        ``link_output_guardrail.guardrail_function(None, None, "...")`` and
        awaits it, so the body must work with a ``None`` context and agent.
    """
    ### YOUR CODE HERE (m4)
    raise NotImplementedError(
        "m4: implement link_output_guardrail (wrap strip_external_links)"
    )


async def refund_needs_human(
    ctx: RunContextWrapper[AuthContext],
    params: dict[str, Any],
    call_id: str,
) -> bool:
    """`needs_approval` predicate for the refund tool: pause above the threshold.

    This is the async predicate the ``issue_refund`` tool uses for its
    ``needs_approval`` argument when ``build_agent(ctx, defenses=True)`` rebuilds
    it. When it returns True, the SDK does not run the tool; it pauses the run
    and surfaces the pending call in ``result.interruptions`` for a human to
    approve or reject (the Part D run loop). This is the in-process twin of
    the durable ``queued_for_approval`` seam already in ``issue_refund_logic``:
    the same dollar threshold, enforced in code, decided here and never by the
    model.

    Contract:
      - Read the refund amount from ``params``. The tool's parameter is named
        ``amount_usd``; use ``params.get("amount_usd")`` and treat a missing or
        non-numeric value as 0.0 (fail safe toward NOT pausing an unparseable
        call is acceptable; a malformed refund is caught by the tool's own
        ``invalid_argument`` check).
      - Load the threshold from the facts sheet with ``load_facts()`` and read
        ``facts["refund_auto_approve_threshold_usd"]`` (do not hardcode 100).
      - Return True when ``amount_usd`` is strictly above the threshold, else
        False. At or below the threshold the refund auto-approves and does not
        need a human, matching ``seed.eligibility.refund_needs_approval``.

    Args:
        ctx: The run context wrapper (part of the SDK signature; not needed
            for the amount check).
        params: The tool call's arguments as a dict, including ``amount_usd``.
        call_id: The SDK's id for this tool call (part of the signature).

    Returns:
        True when the refund amount is above the auto-approval threshold.

    Testability:
        The offline test awaits ``refund_needs_human(None, {"amount_usd": ...},
        "call-1")`` directly, so the body must work with a ``None`` context.
    """
    ### YOUR CODE HERE (m4)
    raise NotImplementedError(
        "m4: implement refund_needs_human (needs_approval threshold predicate)"
    )
