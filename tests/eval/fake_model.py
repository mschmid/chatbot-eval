"""A scripted Model for integration tests. Instructor-provided.

The same pattern as the OpenAI Agents SDK's own test helper (its test suite
ships a FakeModel with `set_next_output` and runs it against the real
`Runner`): implement the `Model` interface with a queue of scripted outputs,
so a test exercises the real agent loop and the real tool plumbing with zero
API calls. The first scripted turn typically returns a tool call, the real
tool executes against the seeded world, and the next scripted turn returns
the final message.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Any

from agents.items import ModelResponse, TResponseOutputItem, TResponseStreamEvent
from agents.models.interface import Model, ModelTracing
from agents.usage import Usage
from openai.types.responses import (
    ResponseFunctionToolCall,
    ResponseOutputMessage,
    ResponseOutputText,
)

_counter = 0


def _next_id(prefix: str) -> str:
    global _counter
    _counter += 1
    return f"{prefix}-{_counter}"


def text_message(text: str) -> TResponseOutputItem:
    """A scripted assistant message output item."""
    return ResponseOutputMessage(
        id=_next_id("msg"),
        content=[ResponseOutputText(annotations=[], text=text, type="output_text")],
        role="assistant",
        status="completed",
        type="message",
    )


def tool_call(name: str, args: dict[str, Any]) -> TResponseOutputItem:
    """A scripted function tool call output item."""
    return ResponseFunctionToolCall(
        id=_next_id("fc"),
        call_id=_next_id("call"),
        name=name,
        arguments=json.dumps(args),
        type="function_call",
    )


class FakeModel(Model):
    """A Model whose outputs are a queue of scripted turns.

    Each entry passed to :meth:`set_next_output` (or ``add_output``) is a
    list of output items for one model turn. The real Runner consumes one
    entry per model call: a turn that returns tool calls makes the Runner
    execute the real tools and call the model again, which pops the next
    entry.
    """

    def __init__(self) -> None:
        self.outputs: list[list[TResponseOutputItem]] = []
        self.requests: list[dict[str, Any]] = []

    def set_next_output(self, items: list[TResponseOutputItem]) -> None:
        self.outputs.append(items)

    add_output = set_next_output

    async def get_response(
        self,
        system_instructions: str | None,
        input: Any,
        model_settings: Any,
        tools: list[Any],
        output_schema: Any,
        handoffs: list[Any],
        tracing: ModelTracing,
        *,
        previous_response_id: str | None,
        conversation_id: str | None,
        prompt: Any | None,
    ) -> ModelResponse:
        self.requests.append(
            {
                "system_instructions": system_instructions,
                "input": input,
                "tools": [getattr(t, "name", None) for t in tools],
            }
        )
        if not self.outputs:
            raise AssertionError(
                "FakeModel ran out of scripted outputs; the Runner made more "
                "model calls than the test scripted"
            )
        items = self.outputs.pop(0)
        return ModelResponse(output=items, usage=Usage(), response_id=None)

    def stream_response(
        self,
        system_instructions: str | None,
        input: Any,
        model_settings: Any,
        tools: list[Any],
        output_schema: Any,
        handoffs: list[Any],
        tracing: ModelTracing,
        *,
        previous_response_id: str | None,
        conversation_id: str | None,
        prompt: Any | None,
    ) -> AsyncIterator[TResponseStreamEvent]:
        raise NotImplementedError("FakeModel does not stream; use Runner.run")
