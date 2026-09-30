# 4. Python 3.12 and a uv workspace monorepo

Date: 2026-09-30 · Status: Accepted

## Context

The SDKs for Teams (Microsoft 365 Agents SDK), MCP and Azure OpenAI exist for Python,
and Python is the language student volunteers are most likely to maintain. Two services
(bot, MCP server), a CLI, a shared core and several modules must stay in sync.

## Decision

* Python 3.12 with full type hints; pyright in strict mode for the core.
* One repository with a uv workspace: `core`, `integrations`, `modules/*`, `apps/*`.
  One lockfile (`uv.lock`) for all packages; dependencies are pinned and updated by
  Dependabot.
* ruff for linting and formatting, pytest for tests.

## Consequences

* A single `uv sync` sets up everything; CI runs the same commands as developers.
* Container images install the locked workspace packages non-editable.
