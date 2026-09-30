"""Who is calling a tool. The user never comes from tool arguments."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

from campus_agent_core.config import CampusAgentConfig, Environment, RuntimeSettings
from campus_agent_core.domain.user import UserContext
from campus_agent_core.errors import ForbiddenError
from campus_agent_core.ports.directory import RoleResolver

USER_HEADER = "x-campus-agent-user"


class IdentityResolver(Protocol):
    async def current_user(self, headers: Mapping[str, str] | None) -> UserContext: ...


class HeaderIdentityResolver:
    """Reads the user ID the bot backend forwards and derives the role server-side.

    SECURITY TODO(mcp): the header is client-supplied. Before this runs outside local
    development, the server must verify the caller's Entra token (signature, audience =
    MCP app ID URI, caller = the bot's managed identity) through the MCPServer
    ``token_verifier``/``auth`` settings and only then trust ``X-Campus-Agent-User``.
    Until that is implemented, ``build_identity`` refuses to start outside ``local``.
    """

    def __init__(self, roles: RoleResolver) -> None:
        self._roles = roles

    async def current_user(self, headers: Mapping[str, str] | None) -> UserContext:
        user_id = _header(headers, USER_HEADER)
        if not user_id:
            raise ForbiddenError("missing user header")
        return UserContext(user_id=user_id, role=await self._roles.resolve_role(user_id))


class DevIdentityResolver:
    """Local development without Teams: a fixed test user from DEV_FAKE_USER."""

    def __init__(self, user_id: str, role: str) -> None:
        self._user = UserContext(user_id=user_id, first_name="Dev", role=role)

    async def current_user(self, headers: Mapping[str, str] | None) -> UserContext:
        return self._user


def build_identity(settings: RuntimeSettings, config: CampusAgentConfig) -> IdentityResolver:
    if settings.env is Environment.LOCAL and settings.dev_fake_user:
        role = settings.dev_fake_role or config.roles[0].id
        config.role_hierarchy().rank(role)  # fail fast on unknown roles
        return DevIdentityResolver(settings.dev_fake_user, role)
    # TODO(mcp): return HeaderIdentityResolver(EntraRoleResolver(...)) once caller token
    # verification is in place (see HeaderIdentityResolver).
    raise RuntimeError(
        "only local development with DEV_FAKE_USER is supported until caller token "
        "verification is implemented"
    )


def _header(headers: Mapping[str, str] | None, name: str) -> str | None:
    if not headers:
        return None
    for key, value in headers.items():
        if key.lower() == name:
            return value.strip() or None
    return None
