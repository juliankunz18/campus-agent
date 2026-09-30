from datetime import UTC, date, datetime, timedelta
from uuid import uuid4

import pytest
from aiohttp.test_utils import TestClient, TestServer

from campus_agent_bot.app import create_app
from campus_agent_bot.mcp_client import McpToolExecutor
from campus_agent_bot.runtime import BotRuntime, build_runtime
from campus_agent_core.agent import PendingAction
from campus_agent_core.config import CampusAgentConfig
from campus_agent_core.domain.user import UserContext
from campus_agent_core.modules import discover_manifests, load_modules
from campus_agent_core.ports.llm import ToolCall
from campus_agent_core.testing import minimal_config
from campus_agent_integrations.fakes import FakeLLM
from tests.helpers import example_config

MEMBER = UserContext(user_id="user-1", first_name="Mia", role="member")
NOW = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)


def runtime_with(llm: FakeLLM, config: CampusAgentConfig | None = None) -> BotRuntime:
    config = config or example_config()
    modules = load_modules(config, discover_manifests())
    executor = McpToolExecutor(mcp_url="http://mcp.invalid/mcp", mcp_audience="api://example")
    return build_runtime(config, modules, llm=llm, executor=executor)


async def test_healthz_and_message_stub():
    app = create_app(runtime_with(FakeLLM()))

    async with TestClient(TestServer(app)) as client:
        health = await client.get("/healthz")
        messages = await client.post("/api/messages", json={"type": "message"})

        assert health.status == 200
        assert await health.json() == {
            "status": "ok",
            "group": "musterverein",
            "tools": 24,
            "prompt_version": "0.1.0",
        }
        assert messages.status == 501


def test_pending_action_validity_comes_from_the_configuration():
    runtime = runtime_with(FakeLLM(), minimal_config("agent:\n  pending_action_ttl: PT2H\n"))
    request = ToolCall(
        id="c", name="submit_application", arguments={"application_id": str(uuid4())}
    )

    action = runtime.policy.decide(request, MEMBER, now=NOW)

    assert isinstance(action, PendingAction)
    assert action.expires_at - action.created_at == timedelta(hours=2)


async def test_loop_uses_the_configured_round_limit():
    llm = FakeLLM().call_tool("discard_draft", application_id=str(uuid4()))
    llm.call_tool("discard_draft", application_id=str(uuid4()))
    runtime = runtime_with(llm, minimal_config("agent:\n  max_tool_rounds: 1\n"))

    reply = await runtime.loop.run(MEMBER, "?", system_prompt="S")

    assert reply.error_code == "TOO_MANY_ROUNDS"
    assert len(llm.calls) == 1


async def test_read_tools_go_to_the_mcp_client():
    runtime = runtime_with(FakeLLM().call_tool("list_my_applications"))

    with pytest.raises(NotImplementedError, match="MCP client"):
        await runtime.loop.run(MEMBER, "?", system_prompt="S")


def test_system_prompt_uses_group_and_role_label():
    prompt = runtime_with(FakeLLM()).system_prompt(MEMBER, date(2026, 10, 1))

    assert prompt.startswith("Du bist der Assistent von Musterverein e.V.")
    assert "(Rolle: Mitglied)" in prompt
