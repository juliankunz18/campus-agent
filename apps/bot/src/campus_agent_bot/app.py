"""aiohttp application of the bot backend."""

from __future__ import annotations

from aiohttp import web

from campus_agent_bot.runtime import BotRuntime

RUNTIME_KEY = web.AppKey("runtime", BotRuntime)


async def messages(request: web.Request) -> web.Response:
    """Teams activities from the Azure Bot Service.

    TODO(bot): hand the request to the Microsoft 365 Agents SDK
    (microsoft_agents.hosting.aiohttp.start_agent_process with a CloudAdapter and an
    AgentApplication, behind jwt_authorization_middleware). Per activity: send a typing
    indicator, resolve the user from the validated token and the role via RoleResolver,
    enforce the rate limit, then either run the agent loop (message) or confirm a pending
    action without the model (card click) and reply with a card.
    """
    return web.json_response(
        {"error": "NOT_IMPLEMENTED", "message": "Teams integration is not implemented yet"},
        status=501,
    )


async def healthz(request: web.Request) -> web.Response:
    runtime = request.app[RUNTIME_KEY]
    return web.json_response(
        {
            "status": "ok",
            "group": runtime.config.group.short_name,
            "tools": len(runtime.registry.all()),
            "prompt_version": runtime.prompt_version,
        }
    )


def create_app(runtime: BotRuntime) -> web.Application:
    app = web.Application()
    app[RUNTIME_KEY] = runtime
    app.router.add_post("/api/messages", messages)
    app.router.add_get("/healthz", healthz)
    return app
