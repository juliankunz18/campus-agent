"""End-to-end flow of the tool policy with the real modules and the fakes:
the model proposes a commit tool, the person confirms on the card, a second click
is rejected."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from pydantic import JsonValue

from campus_agent_core.agent import AgentLoop, PendingActionStore, ToolPolicy
from campus_agent_core.config import CampusAgentConfig
from campus_agent_core.domain.user import UserContext
from campus_agent_core.errors import ConflictError
from campus_agent_core.modules import ToolRegistry
from campus_agent_core.ports import ToolResult
from campus_agent_integrations.fakes import FakeLLM, InMemoryStorage

NOW = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
MEMBER = UserContext(user_id="user-mia", first_name="Mia", role="member")


class Executor:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, JsonValue], str | None]] = []

    async def execute(
        self,
        user: UserContext,
        tool: str,
        arguments: dict[str, JsonValue],
        *,
        idempotency_key: str | None = None,
    ) -> ToolResult:
        self.calls.append((tool, arguments, idempotency_key))
        return ToolResult(summary=f"{tool} ok")


async def test_commit_runs_only_after_card_confirmation(
    musterverein_registry: ToolRegistry, musterverein_config: CampusAgentConfig
):
    registry = musterverein_registry
    policy = ToolPolicy(registry)
    executor = Executor()
    store = PendingActionStore(InMemoryStorage())
    application_id = str(uuid4())
    llm = (
        FakeLLM()
        .call_tool("list_my_applications")
        .call_tool("submit_application", application_id=application_id)
        .reply("Ich habe den Antrag vorbereitet. Bitte bestätige ihn auf der Karte.")
    )
    loop = AgentLoop(
        llm=llm,
        registry=registry,
        policy=policy,
        executor=executor,
        limits=musterverein_config.agent,
        clock=lambda: NOW,
    )

    reply = await loop.run(MEMBER, "Reich meinen Antrag ein", system_prompt="S")

    assert [call[0] for call in executor.calls] == ["list_my_applications"]
    (action,) = reply.pending_actions
    assert "approve_application" not in llm.calls[0].tool_names
    await store.save(action)

    # Card click: a new activity, handled without the model.
    loaded = await store.get(MEMBER.user_id, action.id)
    execution = policy.confirm(loaded, MEMBER, now=NOW + timedelta(minutes=2))
    await store.mark_executed(loaded, now=NOW)
    await executor.execute(
        MEMBER, execution.tool, execution.arguments, idempotency_key=execution.idempotency_key
    )

    assert executor.calls[-1] == (
        "submit_application",
        {"application_id": application_id},
        action.idempotency_key,
    )
    with pytest.raises(ConflictError):
        await store.mark_executed(loaded, now=NOW)
