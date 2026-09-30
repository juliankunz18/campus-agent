# CLAUDE.md

Conventions for working on this repository. Read `docs/architecture.md` and the ADRs in
`docs/adr/` before changing anything fundamental.

## What this is

campus-agent is an open-source framework (Apache-2.0) for a Microsoft Teams assistant
of non-profit student groups: Teams (Microsoft 365 Agents SDK), SharePoint via Microsoft
Graph, Azure OpenAI, an own agent loop and an MCP server as the only writer. Status:
early development - the domain core is implemented; Teams, Graph, Azure OpenAI, Table
Storage and the MCP client are stubs marked `TODO(<area>)`.

## Commands

```bash
uv sync                         # install everything (Python 3.12, locked)
uv run ruff check               # lint
uv run ruff format --check      # formatting
uv run pyright                  # types (strict for core/src)
uv run pytest                   # all tests
docker compose config --quiet   # compose file
uv run campus-agent doctor -c examples/musterverein/campus-agent.yaml --env-file examples/musterverein/.env.example
```

On Windows machines where application control blocks `.venv\Scripts\pytest.exe`, use
`uv run python -m pytest`.

All of these must be green before every commit.

## Layout

* `core/` - `campus_agent_core`: `ports/` (interfaces, module API), `domain/` (roles,
  applications, four eyes, audit), `config/` (campus-agent.yaml, runtime settings),
  `modules/` (loader, registry, built-in `core` module), `agent/` (policy, loop,
  prompt), `locales/`.
* `integrations/` - adapters (teams, sharepoint, azure_openai, storage) and `fakes/`.
* `modules/{members,certificates,knowledge,events}` - manifests, tools, locales.
* `apps/{bot,mcp,cli}` - bot backend (aiohttp), MCP server (mcp SDK v2 `MCPServer`),
  Typer CLI.
* `tests/` - cross-package tests: permission matrix, tool catalog, architecture
  boundaries, example config, end-to-end flow, evals. Shared helpers in
  `tests/helpers.py` (tests run with `--import-mode=importlib`; import helpers as
  `from tests.helpers import ...`, not from conftest).
* `examples/musterverein/` - the fictional example group. `apps/cli/.../example/` is a
  packaged copy; a test keeps both identical.

## Hard rules

* **No real data**: no real names, member data, tenant, site, group or app IDs, no
  secrets, no `.env` (only `.env.example` with fictional values). Nothing about the
  pilot group except its mention as pilot partner. Group-specific material belongs in
  the group's private deployment repository.
* **Boundaries**: modules import only `campus_agent_core.ports`; the core imports no
  adapters, apps, modules or SDKs; bot and MCP server never import each other
  (`tests/test_architecture.py`).
* **Identity**: no tool has a user ID or role parameter. The caller always comes from the
  verified request (`ToolContext.user`). Tool input models extend `ToolInput`
  (`extra="forbid"`).
* **Binding actions** are `commit` tools and only run after card confirmation, never
  from the model.
* **Language**: code, comments, docstrings in English. User-visible texts (tool and
  parameter descriptions, prompts, cards, errors) in `locales/de` and `locales/en`,
  German first. Every tool description says when the tool fits and when not.
* **SDKs** (Microsoft 365 Agents SDK, mcp, msgraph-sdk, openai): versions are pinned; do
  not guess APIs. Introspect the installed version or read its docs; if unsure, leave a
  `TODO(<area>)` instead of invented code. Note: `mcp` is v2 (`MCPServer`, formerly
  FastMCP); the Teams package is `microsoft-agents-hosting-msteams`.
* **Types**: full type hints, pyright strict for `core/src`; timezone-aware datetimes
  only (ruff `DTZ`).

## Adding things

* **Tool**: add input model + handler, a `ToolSpec` in the module manifest, texts
  `tools.<name>.description` and `tools.<name>.params.<field>` in both locales, and the
  entry in `tests/test_tool_catalog.py`. The permission matrix picks it up
  automatically.
* **Module**: see `docs/module-development.md`; register the entry point
  `campus_agent.modules`, add it to the workspace (`modules/*`) and, for the default
  images, to the dependencies of `apps/bot` and `apps/mcp`.
* **Decision**: new ADR in `docs/adr/` and a line in `docs/adr/README.md`.
* **User-facing change**: entry under "Unreleased" in `CHANGELOG.md`.

## Commits

* Conventional Commits (`feat(core): ...`, `fix(mcp): ...`, `docs: ...`, `test: ...`,
  `build: ...`, `ci: ...`), one logical step per commit.
* Always sign off: `git commit -s` (DCO, checked in CI).
* Pre-commit hooks: `uvx pre-commit install` (ruff, gitleaks, hygiene).
