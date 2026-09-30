"""The agent loop (see ADR 0005 and the activity diagram in docs/architecture.md).

Card clicks do not enter this loop: the bot loads the pending action and calls
``ToolPolicy.confirm`` directly, without the model.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime

from pydantic import JsonValue

from campus_agent_core.agent.context import truncate_for_context
from campus_agent_core.agent.policy import PendingAction, ToolPolicy
from campus_agent_core.config.schema import AgentLimits
from campus_agent_core.domain.user import UserContext
from campus_agent_core.errors import CampusAgentError, UpstreamError
from campus_agent_core.modules.registry import ToolRegistry
from campus_agent_core.ports.llm import ChatMessage, ChatRole, LLMProvider, ToolCall
from campus_agent_core.ports.tools import ToolExecutor

TOO_MANY_ROUNDS = "TOO_MANY_ROUNDS"


def _utc_now() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True)
class AgentReply:
    text: str | None
    pending_actions: tuple[PendingAction, ...] = ()
    rounds: int = 0
    error_code: str | None = None
    tool_calls: tuple[str, ...] = field(default=(), repr=False)


class AgentLoop:
    def __init__(
        self,
        *,
        llm: LLMProvider,
        registry: ToolRegistry,
        policy: ToolPolicy,
        executor: ToolExecutor,
        limits: AgentLimits,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        self._llm = llm
        self._registry = registry
        self._policy = policy
        self._executor = executor
        self._limits = limits
        self._clock = clock

    async def run(
        self,
        user: UserContext,
        message: str,
        *,
        system_prompt: str,
        history: Sequence[ChatMessage] = (),
    ) -> AgentReply:
        """Answer one user message. Only tools of the user's role are offered."""
        messages: list[ChatMessage] = [
            ChatMessage(role=ChatRole.SYSTEM, content=system_prompt),
            *history,
            ChatMessage(role=ChatRole.USER, content=message),
        ]
        tools = self._registry.schemas_for_role(user.role)
        pending: list[PendingAction] = []
        called: list[str] = []

        for round_number in range(1, self._limits.max_tool_rounds + 1):
            try:
                async with asyncio.timeout(self._limits.llm_timeout.total_seconds()):
                    response = await self._llm.complete(messages, tools)
            except TimeoutError as error:
                raise UpstreamError("language model timed out") from error

            if not response.tool_calls:
                return AgentReply(
                    text=response.content,
                    pending_actions=tuple(pending),
                    rounds=round_number,
                    tool_calls=tuple(called),
                )

            messages.append(
                ChatMessage(
                    role=ChatRole.ASSISTANT,
                    content=response.content,
                    tool_calls=response.tool_calls,
                )
            )
            for call in response.tool_calls:
                called.append(call.name)
                content = await self._handle(call, user, pending)
                messages.append(
                    ChatMessage(role=ChatRole.TOOL, tool_call_id=call.id, content=content)
                )

        # TODO(agent): ask the model once more without tools for a final answer instead
        # of giving up, once pilot data shows how often the limit is reached.
        return AgentReply(
            text=None,
            pending_actions=tuple(pending),
            rounds=self._limits.max_tool_rounds,
            error_code=TOO_MANY_ROUNDS,
            tool_calls=tuple(called),
        )

    async def _handle(self, call: ToolCall, user: UserContext, pending: list[PendingAction]) -> str:
        """Run or defer one tool call and return the message content for the model."""
        try:
            decision = self._policy.decide(call, user, now=self._clock())
            if isinstance(decision, PendingAction):
                pending.append(decision)
                return _dump(
                    {
                        "status": "pending_confirmation",
                        "summary": "Waiting for the person to confirm this action on the card.",
                    }
                )
            result = await self._executor.execute(user, decision.tool, decision.arguments)
        except CampusAgentError as error:
            # Errors go back to the model so it can explain or correct (e.g. VALIDATION).
            return _dump({"error": error.code.value, "message": error.message})
        return truncate_for_context(
            _dump(result.model_dump(mode="json")),
            max_tokens=self._limits.tool_result_max_tokens,
        )


def _dump(value: dict[str, JsonValue]) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
