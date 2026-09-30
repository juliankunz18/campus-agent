"""Entry point: ``campus-agent-mcp`` (Streamable HTTP on port 8000, path ``/mcp``)."""

from __future__ import annotations

import logging
import os

import uvicorn
from mcp.server.transport_security import TransportSecuritySettings
from starlette.applications import Starlette

from campus_agent_core.config import RuntimeSettings, load_config
from campus_agent_core.modules import ToolRegistry, discover_manifests, load_modules
from campus_agent_mcp.identity import build_identity
from campus_agent_mcp.server import build_server

logger = logging.getLogger("campus_agent_mcp")


def transport_security(allowed_hosts: str | None) -> TransportSecuritySettings | None:
    """Host header allow-list against DNS rebinding, e.g. ``mcp:8000,localhost:*``.

    Without a list the SDK protects localhost binds only.
    """
    if not allowed_hosts:
        return None
    hosts = [host.strip() for host in allowed_hosts.split(",") if host.strip()]
    return TransportSecuritySettings(enable_dns_rebinding_protection=True, allowed_hosts=hosts)


def create_app() -> Starlette:
    settings = RuntimeSettings()  # pyright: ignore[reportCallIssue]
    config = load_config(settings.config_path)
    modules = load_modules(config, discover_manifests())
    registry = ToolRegistry(modules, config.role_hierarchy(), language=config.group.language)
    server = build_server(
        modules=modules,
        registry=registry,
        identity=build_identity(settings, config),
        language=config.group.language,
    )
    logger.info("loaded %d tools from %d modules", len(registry.all()), len(modules))
    return server.streamable_http_app(
        host=os.environ.get("MCP_BIND_HOST", "127.0.0.1"),
        transport_security=transport_security(os.environ.get("MCP_ALLOWED_HOSTS")),
    )


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    uvicorn.run(
        create_app(),
        host=os.environ.get("MCP_BIND_HOST", "127.0.0.1"),
        port=int(os.environ.get("MCP_PORT", "8000")),
    )


if __name__ == "__main__":
    main()
