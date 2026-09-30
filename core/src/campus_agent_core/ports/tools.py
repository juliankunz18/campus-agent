"""Port through which the bot executes tools (the MCP client in production)."""

from __future__ import annotations

from typing import Protocol

from pydantic import JsonValue

from campus_agent_core.domain.user import UserContext
from campus_agent_core.ports.module import ToolResult


class ToolExecutor(Protocol):
    async def execute(
        self,
        user: UserContext,
        tool: str,
        arguments: dict[str, JsonValue],
        *,
        idempotency_key: str | None = None,
    ) -> ToolResult:
        """Run a tool for ``user``. The executor passes the user ID out of band (header),
        never as a tool argument. Raises ``CampusAgentError`` subclasses on failure."""
        ...
