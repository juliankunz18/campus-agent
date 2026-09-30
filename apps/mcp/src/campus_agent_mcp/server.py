"""MCP server exposing the tools of all active modules (official mcp SDK, v2).

The server is the only component with write access to SharePoint and enforces every
rule itself - role, four-eyes principle, state machine - regardless of what the model
proposes. Transport: Streamable HTTP, internal ingress only.
"""

from __future__ import annotations

import inspect
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Annotated, Any

from mcp.server import MCPServer
from mcp.server.mcpserver import Context
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import ValidationError
from starlette.requests import Request
from starlette.responses import JSONResponse

from campus_agent_core.errors import CampusAgentError
from campus_agent_core.modules import LoadedModule, RegisteredTool, ToolRegistry
from campus_agent_core.ports import ToolClass, ToolContext
from campus_agent_mcp.identity import IdentityResolver

SERVER_NAME = "campus-agent"


def _utc_now() -> datetime:
    return datetime.now(UTC)


def build_server(
    *,
    modules: list[LoadedModule],
    registry: ToolRegistry,
    identity: IdentityResolver,
    language: str,
    version: str = "0.1.0",
    clock: Callable[[], datetime] = _utc_now,
) -> MCPServer:
    """Register every tool of the active modules and a ``/healthz`` route."""
    # TODO(mcp): filter list_tools by the caller's role with a server middleware; each
    # tool already checks the role itself.
    server = MCPServer(SERVER_NAME, version=version)
    settings = {module.name: dict(module.raw_settings) for module in modules}

    for tool in registry.all():
        server.add_tool(
            _make_handler(tool, registry, identity, language, settings[tool.module], clock),
            name=tool.name,
            description=tool.description,
            annotations=_annotations(tool.tool_class),
        )

    @server.custom_route("/healthz", methods=["GET"], include_in_schema=False)
    async def healthz(request: Request) -> JSONResponse:  # pyright: ignore[reportUnusedFunction]
        return JSONResponse({"status": "ok", "tools": len(registry.all())})

    return server


def _annotations(tool_class: ToolClass) -> ToolAnnotations:
    return ToolAnnotations(
        read_only_hint=tool_class is ToolClass.READ,
        destructive_hint=tool_class is ToolClass.COMMIT,
        idempotent_hint=tool_class is ToolClass.READ,
        open_world_hint=False,
    )


def _make_handler(
    tool: RegisteredTool,
    registry: ToolRegistry,
    identity: IdentityResolver,
    language: str,
    module_settings: dict[str, Any],
    clock: Callable[[], datetime],
) -> Callable[..., Any]:
    model = tool.spec.input_model

    async def handler(ctx: Context, **arguments: Any) -> dict[str, Any]:
        try:
            user = await identity.current_user(ctx.headers)
            registry.ensure_allowed(user.role, tool.name)  # never trust the tool list alone
            try:
                params = model.model_validate(arguments)
            except ValidationError as error:
                raise ToolError(f"VALIDATION: {error.error_count()} invalid argument(s)") from error
            context = ToolContext(
                user=user, now=clock(), language=language, module_config=module_settings
            )
            result = await tool.spec.handler(context, params)
        except CampusAgentError as error:
            raise ToolError(f"{error.code.value}: {error.message}") from error
        except NotImplementedError as error:
            raise ToolError(f"NOT_IMPLEMENTED: {tool.name}") from error
        return result.model_dump(mode="json")

    # FastMCP-style servers derive the input schema from the signature, so expose the
    # fields of the input model as keyword-only parameters (with their constraints).
    parameters = [
        inspect.Parameter("ctx", inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=Context)
    ]
    for name, field in model.model_fields.items():
        parameters.append(
            inspect.Parameter(
                name,
                inspect.Parameter.KEYWORD_ONLY,
                annotation=Annotated[field.annotation, field],
                default=inspect.Parameter.empty if field.is_required() else field.default,
            )
        )
    handler.__signature__ = inspect.Signature(parameters)  # pyright: ignore[reportFunctionMemberAccess]
    handler.__annotations__ = {p.name: p.annotation for p in parameters}
    handler.__name__ = tool.name
    return handler
