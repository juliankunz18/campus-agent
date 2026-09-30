"""Import boundaries between the packages (see CLAUDE.md and ADR 0011).

* Modules import only ``campus_agent_core.ports`` - never other core internals,
  adapters, apps, other modules or SDKs.
* The core imports no adapters, apps, modules or SDKs.
* Integrations import no apps or modules.
* Bot and MCP server never import each other.
"""

import ast
from collections.abc import Iterator
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
SDKS = {"openai", "msgraph", "microsoft_agents", "azure", "mcp", "aiohttp", "kiota_abstractions"}
APPS = {"campus_agent_bot", "campus_agent_mcp", "campus_agent_cli"}
MODULES = {
    "campus_agent_members",
    "campus_agent_certificates",
    "campus_agent_knowledge",
    "campus_agent_events",
}


def imports_of(path: Path) -> Iterator[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            yield from (alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            yield node.module


def sources(pattern: str) -> list[Path]:
    return sorted(REPO_ROOT.glob(pattern))


def root(name: str) -> str:
    return name.split(".")[0]


@pytest.mark.parametrize("path", sources("modules/*/src/**/*.py"), ids=str)
def test_modules_only_use_core_ports(path: Path):
    own = path.relative_to(REPO_ROOT).parts[3]
    for name in imports_of(path):
        top = root(name)
        if top == "campus_agent_core":
            assert name == "campus_agent_core.ports" or name.startswith(
                "campus_agent_core.ports."
            ), f"{path.name} imports {name}"
        assert top not in SDKS | APPS | {"campus_agent_integrations"}, f"{path.name}: {name}"
        assert top not in MODULES - {own}, f"{path.name} imports another module: {name}"


@pytest.mark.parametrize("path", sources("core/src/**/*.py"), ids=str)
def test_core_has_no_outward_dependencies(path: Path):
    for name in imports_of(path):
        assert root(name) not in SDKS | APPS | MODULES | {"campus_agent_integrations"}, name


@pytest.mark.parametrize("path", sources("integrations/src/**/*.py"), ids=str)
def test_integrations_do_not_import_apps_or_modules(path: Path):
    for name in imports_of(path):
        assert root(name) not in APPS | MODULES, name


@pytest.mark.parametrize(
    ("app", "forbidden"),
    [("bot", "campus_agent_mcp"), ("mcp", "campus_agent_bot")],
)
def test_bot_and_mcp_server_are_independent(app: str, forbidden: str):
    for path in sources(f"apps/{app}/src/**/*.py"):
        assert forbidden not in {root(name) for name in imports_of(path)}, path.name
