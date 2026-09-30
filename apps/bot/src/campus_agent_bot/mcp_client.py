"""Tool execution through the MCP server (the only component that writes to SharePoint)."""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import JsonValue

from campus_agent_core.domain.user import UserContext
from campus_agent_core.ports import ToolResult

USER_HEADER = "X-Campus-Agent-User"
IDEMPOTENCY_HEADER = "Idempotency-Key"


@dataclass(frozen=True)
class McpToolExecutor:
    """Implements ``ToolExecutor``.

    TODO(bot): connect with the mcp SDK client over Streamable HTTP to ``mcp_url``,
    authenticate with a Managed Identity token for ``mcp_audience`` and pass the user ID
    in the ``X-Campus-Agent-User`` header (never as a tool argument) plus the idempotency
    key for commit tools. Map tool errors ("CODE: message") back to CampusAgentError.
    Verify how the v2 client sets per-request headers before implementing.
    """

    mcp_url: str
    mcp_audience: str

    async def execute(
        self,
        user: UserContext,
        tool: str,
        arguments: dict[str, JsonValue],
        *,
        idempotency_key: str | None = None,
    ) -> ToolResult:
        raise NotImplementedError("MCP client is not implemented yet")
