"""A scriptable language model for tests."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from itertools import count

from pydantic import JsonValue

from campus_agent_core.ports.llm import ChatMessage, LLMResponse, ToolCall, ToolSchema


@dataclass(frozen=True)
class RecordedCall:
    messages: tuple[ChatMessage, ...]
    tools: tuple[ToolSchema, ...]

    @property
    def tool_names(self) -> tuple[str, ...]:
        return tuple(tool.name for tool in self.tools)


@dataclass
class FakeLLM:
    """Returns scripted responses in order and records every request.

    Example::

        llm = FakeLLM().call_tool("get_my_profile").reply("Hier sind deine Daten.")
    """

    responses: list[LLMResponse] = field(default_factory=list[LLMResponse])
    calls: list[RecordedCall] = field(default_factory=list[RecordedCall])
    _ids: count[int] = field(default_factory=lambda: count(1), repr=False)

    def reply(self, text: str) -> FakeLLM:
        self.responses.append(LLMResponse(content=text))
        return self

    def call_tool(self, name: str, **arguments: JsonValue) -> FakeLLM:
        return self.call_tools((name, arguments))

    def call_tools(self, *calls: tuple[str, dict[str, JsonValue]]) -> FakeLLM:
        tool_calls = tuple(
            ToolCall(id=f"call-{next(self._ids)}", name=name, arguments=arguments)
            for name, arguments in calls
        )
        self.responses.append(LLMResponse(tool_calls=tool_calls))
        return self

    async def complete(
        self, messages: Sequence[ChatMessage], tools: Sequence[ToolSchema]
    ) -> LLMResponse:
        self.calls.append(RecordedCall(tuple(messages), tuple(tools)))
        if not self.responses:
            raise AssertionError("FakeLLM has no scripted response left")
        return self.responses.pop(0)
