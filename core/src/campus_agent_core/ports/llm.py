"""Port for the language model. The Azure OpenAI adapter and the fake implement it."""

from __future__ import annotations

from collections.abc import Sequence
from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field, JsonValue


class ChatRole(StrEnum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class ToolCall(BaseModel):
    """A tool invocation proposed by the model."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    arguments: dict[str, JsonValue] = Field(default_factory=dict[str, JsonValue])


class ChatMessage(BaseModel):
    model_config = ConfigDict(frozen=True)

    role: ChatRole
    content: str | None = None
    tool_calls: tuple[ToolCall, ...] = ()
    tool_call_id: str | None = None


class ToolSchema(BaseModel):
    """What the model sees of a tool: name, description and JSON schema of the input."""

    model_config = ConfigDict(frozen=True)

    name: str
    description: str
    parameters: dict[str, JsonValue]


class LLMResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    content: str | None = None
    tool_calls: tuple[ToolCall, ...] = ()


class LLMProvider(Protocol):
    """Chat completion with tool calling. Timeouts are enforced by the caller."""

    async def complete(
        self, messages: Sequence[ChatMessage], tools: Sequence[ToolSchema]
    ) -> LLMResponse: ...
