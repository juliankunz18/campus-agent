from collections.abc import Mapping
from datetime import UTC, datetime

import pytest
from mcp import Client
from starlette.testclient import TestClient

from campus_agent_core.config import RuntimeSettings
from campus_agent_core.domain.user import UserContext
from campus_agent_core.errors import ForbiddenError
from campus_agent_core.modules import ToolRegistry
from campus_agent_mcp.__main__ import transport_security
from campus_agent_mcp.identity import (
    DevIdentityResolver,
    HeaderIdentityResolver,
    build_identity,
)
from campus_agent_mcp.server import build_server
from tests.helpers import example_config, example_modules

NOW = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)


def server_for(role: str):
    config = example_config()
    modules = example_modules()
    registry = ToolRegistry(modules, config.role_hierarchy(), language="de")
    return build_server(
        modules=modules,
        registry=registry,
        identity=DevIdentityResolver(f"user-{role}", role),
        language="de",
        clock=lambda: NOW,
    )


async def test_all_tools_are_registered_with_annotations():
    tools = {tool.name: tool for tool in await server_for("board").list_tools()}

    assert len(tools) == 24
    profile = tools["get_my_profile"].annotations
    approve = tools["approve_application"].annotations
    assert profile is not None
    assert approve is not None
    assert profile.read_only_hint is True
    assert approve.read_only_hint is False
    assert approve.destructive_hint is True


async def test_input_schema_comes_from_the_model_with_constraints():
    tools = {tool.name: tool for tool in await server_for("member").list_tools()}

    schema = tools["search_knowledge"].input_schema
    assert set(schema["properties"]) == {"query", "max_results"}
    assert schema["required"] == ["query"]
    assert schema["properties"]["query"]["minLength"] == 2
    assert (tools["search_knowledge"].description or "").startswith("Durchsucht Satzung")


async def test_tools_check_the_role_themselves():
    async with Client(server_for("member")) as client:
        result = await client.call_tool("approve_all_open", {})

    assert result.is_error
    assert "FORBIDDEN" in str(result.content)


async def test_stub_handlers_report_not_implemented():
    async with Client(server_for("member")) as client:
        result = await client.call_tool("search_knowledge", {"query": "Satzung"})

    assert result.is_error
    assert "NOT_IMPLEMENTED: search_knowledge" in str(result.content)


async def test_invalid_arguments_are_rejected():
    async with Client(server_for("member")) as client:
        result = await client.call_tool("search_knowledge", {"query": "x"})

    assert result.is_error


def test_healthz():
    app = server_for("member").streamable_http_app()

    with TestClient(app) as client:
        response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "tools": 24}


class StaticRoles:
    async def resolve_role(self, user_id: str) -> str:
        return "team_lead"


class TestIdentity:
    async def test_header_identity_derives_the_role(self):
        resolver = HeaderIdentityResolver(StaticRoles())
        headers: Mapping[str, str] = {"X-Campus-Agent-User": "user-7"}

        assert await resolver.current_user(headers) == UserContext(
            user_id="user-7", role="team_lead"
        )

    async def test_missing_header(self):
        with pytest.raises(ForbiddenError):
            await HeaderIdentityResolver(StaticRoles()).current_user({})

    def test_dev_identity_only_locally(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("CAMPUS_AGENT_ENV", "local")
        monkeypatch.setenv("DEV_FAKE_USER", "dev-user")
        monkeypatch.setenv("DEV_FAKE_ROLE", "board")

        identity = build_identity(RuntimeSettings(), example_config())  # pyright: ignore[reportCallIssue]

        assert isinstance(identity, DevIdentityResolver)

    def test_refuses_to_start_without_token_verification(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("CAMPUS_AGENT_ENV", "dev")
        monkeypatch.delenv("DEV_FAKE_USER", raising=False)
        monkeypatch.delenv("DEV_FAKE_ROLE", raising=False)

        with pytest.raises(RuntimeError, match="token verification"):
            build_identity(RuntimeSettings(), example_config())  # pyright: ignore[reportCallIssue]


def test_transport_security_allow_list():
    assert transport_security(None) is None
    settings = transport_security("mcp:8000, localhost:*")
    assert settings is not None
    assert settings.allowed_hosts == ["mcp:8000", "localhost:*"]
