"""Run the frozen Module 2 judges over the sampled traces.

Instructor-provided. This is the expensive track of the two-track plan: the
code checks run on 100 percent of the stream because they are free, and the
judges run only on the plan `monitoring/sample.py` produced, asynchronously
off the serving path (here: a batch job, which at course scale is the same
thing).

Each trace dict needs "id", "final_reply", and "retrieved_docs" (the
policy text the agent saw; the judge grades support, so it sees what the
agent saw). The judge is the frozen Module 2 judge, prompt and model pinned;
the call goes through the same LiteLLM routing as the course models.
"""

from __future__ import annotations

from typing import Any

from replay.rollout import judge_reply, load_frozen_judge


def judge_sample(
    mode: str, traces: list[dict[str, Any]]
) -> dict[str, int]:
    """Run the frozen judge for ``mode`` over the sampled traces.

    Returns trace_id -> 0/1 verdict in the failure-positive convention the
    whole course uses (1 = the failure is present, i.e. the judge said
    "fail"). Requires the judge model's API key.
    """
    judge = load_frozen_judge(mode)
    verdicts: dict[str, int] = {}
    for trace in traces:
        answer = judge_reply(
            judge,
            trace.get("final_reply", ""),
            trace.get("retrieved_docs", "(no policy documents were retrieved)"),
        )
        verdicts[trace["id"]] = 1 if answer == "fail" else 0
    return verdicts
