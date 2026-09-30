"""Azure OpenAI adapter (openai SDK 3.x, Chat Completions with tool calling).

The request format helpers are implemented; the network call is a TODO until it can be
verified against a real deployment.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass

from pydantic import JsonValue

from campus_agent_core.ports.llm import ChatMessage, ChatRole, LLMResponse, ToolSchema

type OpenAIMessage = dict[str, JsonValue]


def to_openai_messages(messages: Sequence[ChatMessage]) -> list[OpenAIMessage]:
    """Convert port messages to the Chat Completions message format."""
    converted: list[OpenAIMessage] = []
    for message in messages:
        item: OpenAIMessage = {"role": message.role.value, "content": message.content}
        if message.role is ChatRole.ASSISTANT and message.tool_calls:
            item["tool_calls"] = [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {"name": call.name, "arguments": _json(call.arguments)},
                }
                for call in message.tool_calls
            ]
        if message.role is ChatRole.TOOL:
            item["tool_call_id"] = message.tool_call_id
        converted.append(item)
    return converted


def to_openai_tools(tools: Sequence[ToolSchema]) -> list[OpenAIMessage]:
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters,
            },
        }
        for tool in tools
    ]


@dataclass(frozen=True)
class AzureOpenAIProvider:
    """Implements ``LLMProvider``. Authenticates with Managed Identity, never an API key."""

    endpoint: str
    deployment: str
    api_version: str | None = None

    async def complete(
        self, messages: Sequence[ChatMessage], tools: Sequence[ToolSchema]
    ) -> LLMResponse:
        # TODO(azure-openai): create one openai.AsyncAzureOpenAI client per process with
        #   azure_endpoint=self.endpoint and azure_ad_token_provider from
        #   azure.identity.aio.get_bearer_token_provider(ManagedIdentityCredential(),
        #   "https://cognitiveservices.azure.com/.default"), then call
        #   client.chat.completions.create(model=self.deployment,
        #   messages=to_openai_messages(messages), tools=to_openai_tools(tools)) and map
        #   choices[0].message (content, tool_calls[].function.arguments as JSON) to
        #   LLMResponse. Map SDK errors to UpstreamError. Verify the api_version against
        #   the deployment before enabling this.
        raise NotImplementedError("AzureOpenAIProvider.complete is not implemented yet")


def _json(arguments: dict[str, JsonValue]) -> str:
    return json.dumps(arguments, ensure_ascii=False)
