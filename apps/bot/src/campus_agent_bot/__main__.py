"""Entry point: ``campus-agent-bot`` (aiohttp on port 3978)."""

from __future__ import annotations

import logging
import os

from aiohttp import web

from campus_agent_bot.app import create_app
from campus_agent_bot.mcp_client import McpToolExecutor
from campus_agent_bot.runtime import build_runtime
from campus_agent_core.config import RuntimeSettings, load_config
from campus_agent_core.modules import discover_manifests, load_modules
from campus_agent_integrations.azure_openai import AzureOpenAIProvider


def build_app() -> web.Application:
    settings = RuntimeSettings()  # pyright: ignore[reportCallIssue]
    config = load_config(settings.config_path)
    modules = load_modules(config, discover_manifests())
    runtime = build_runtime(
        config,
        modules,
        llm=AzureOpenAIProvider(
            endpoint=os.environ.get("AZURE_OPENAI_ENDPOINT", ""),
            deployment=config.llm.deployment,
        ),
        executor=McpToolExecutor(
            mcp_url=os.environ.get("MCP_URL", "http://localhost:8000/mcp"),
            mcp_audience=os.environ.get("MCP_AUDIENCE", ""),
        ),
    )
    return create_app(runtime)


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    web.run_app(
        build_app(),
        host=os.environ.get("BOT_BIND_HOST", "127.0.0.1"),
        port=int(os.environ.get("BOT_PORT", "3978")),
    )


if __name__ == "__main__":
    main()
