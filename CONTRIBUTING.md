# Contributing to campus-agent

Thank you for helping student groups run their association with less paperwork!
Support happens through public issues and pull requests, without guaranteed response
times.

## Developer Certificate of Origin (DCO)

Every commit must be signed off. By signing off you certify the
[Developer Certificate of Origin 1.1](https://developercertificate.org/): you wrote the
contribution or otherwise have the right to submit it under the project license.

```bash
git commit -s -m "feat(events): add waiting list"
```

This adds a line `Signed-off-by: Your Name <you@example.org>` matching your Git author.
CI rejects pull requests with commits that lack it. To fix a branch:

```bash
git rebase --signoff main
git push --force-with-lease
```

**Copyright stays with you.** There is no contributor license agreement: you keep the
copyright of your contribution and license it under the project license, the
[Apache License 2.0](LICENSE) ("inbound = outbound", section 5 of the license).

## Development setup

```bash
uv sync                      # Python 3.12 and all workspace packages
uvx pre-commit install       # ruff and gitleaks before each commit
```

Checks (the same as in CI):

```bash
uv run ruff check
uv run ruff format --check
uv run pyright
uv run pytest
docker compose config --quiet
```

## Conventions

* **Commits** follow [Conventional Commits](https://www.conventionalcommits.org/)
  (`feat:`, `fix:`, `docs:`, `test:`, `build:`, `ci:`, `chore:`); the changelog is
  derived from them.
* **`main` is protected**; changes land through pull requests with green CI.
* **Fundamental decisions** are recorded as short ADRs in [`docs/adr/`](docs/adr/).
* **Language:** code, comments and docstrings in English. User-visible texts (tool
  descriptions, cards, prompts) live in `locales/de` and `locales/en`, German first.
* **Boundaries:** modules import only `campus_agent_core.ports`, never adapters; bot and
  MCP server never import each other. `tests/test_architecture.py` enforces this.
* **Tools** have an English snake_case name, a class (`read`, `draft`, `commit`), a
  minimum role and a Pydantic input model. No tool takes a user ID or role: the caller
  always comes from the verified request.
* **Types:** full type hints; the core is checked with pyright in strict mode.
* **Data:** only fictional data of the Musterverein. Never commit real names, member
  data, tenant, site, group or app IDs, secrets or `.env` files.

## New modules

Read [docs/module-development.md](docs/module-development.md) and open a
"New module" issue first. A module can live in this repository or be published as a
separate package that registers the `campus_agent.modules` entry point.

## Reporting bugs and vulnerabilities

Use the issue templates for bugs and feature ideas. Report security problems privately
as described in [SECURITY.md](SECURITY.md).

By participating you agree to follow the [Code of Conduct](CODE_OF_CONDUCT.md).
