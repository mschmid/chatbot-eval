"""Optional reader extension: export a Langfuse trace as an ATIF trajectory.

ATIF is the Agent Trajectory Interchange Format from the Harbor project: a
JSON spec for complete trajectories (messages, tool calls, observations,
subagent nesting, token usage) designed so trajectories can feed SFT and RL
pipelines. The course point: an eval flywheel that stores clean trajectories
is also a training-data flywheel. This exporter is ~50 lines once you get
the mapping right, and it is not required for any later module.

Input shape: one trace as returned by the Langfuse API
(GET /api/public/traces/{id}), reduced to the fields that matter here:

    {
      "id": "...",                       # trace id
      "name": "...",
      "observations": [                   # flat list; parentObservationId nests them
        {
          "id": "...",
          "parentObservationId": null | "...",
          "type": "GENERATION" | "SPAN" | "EVENT",
          "name": "...",
          "startTime": "2026-07-01T10:00:00Z",
          "input": ...,                   # rendered prompt or tool args
          "output": ...,                  # completion or tool result
          "model": "gpt-5.5" | null,
          "usage": {"input": 4000, "output": 500} | null,
          "metadata": {...} | null
        }
      ]
    }

Fetch one with the Langfuse SDK: langfuse.api.trace.get(trace_id).
"""

from __future__ import annotations

from typing import Any


def export_trace(trace: dict[str, Any]) -> dict[str, Any]:
    """Map one Langfuse trace to an ATIF trajectory dict.

    The mapping, field by field:

      Trajectory level:
        - "schema_version": the literal string "ATIF" plus the version you
          target, e.g. "atif-v0.4"; record whichever the Harbor spec you
          read specifies.
        - "session_id": the Langfuse trace id.
        - "agent": {"name": trace["name"], "model": the model of the first
          GENERATION observation, or None if there is none}.
        - "steps": one step per observation, ordered by startTime ascending
          (ties break by observation id).

      Per step:
        - "step_id": the observation id.
        - "parent_step_id": parentObservationId (None at the top level);
          this is how subagent nesting survives the export.
        - "timestamp": startTime, unchanged.
        - "source": "agent" for GENERATION observations, "tool" for SPAN
          observations, "system" for EVENT observations.
        - For GENERATION steps: "message": {"input": input, "output":
          output}, and "usage": {"input_tokens": usage["input"],
          "output_tokens": usage["output"]} when usage is present, else
          None.
        - For SPAN (tool) steps: "tool_call": {"tool_name": name,
          "arguments": input, "tool_call_id": the observation id} and
          "observation": output (the tool result).
        - Carry "metadata" through unchanged on every step when present.

    Returns:
        The trajectory dict described above.

    Raises:
        KeyError if the trace has no "id" or no "observations" list; let it
        propagate, malformed traces should fail loudly.
    """
    ### YOUR CODE HERE (optional ATIF extension)
    raise NotImplementedError("optional extension: implement export_trace")
