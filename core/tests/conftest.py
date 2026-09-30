import pytest

from campus_agent_core.config import CampusAgentConfig
from campus_agent_core.domain.user import UserContext
from campus_agent_core.errors import ConflictError
from campus_agent_core.i18n import Catalog, load_catalog
from campus_agent_core.modules import ToolRegistry, load_modules
from campus_agent_core.modules.builtin import manifest as core_manifest
from campus_agent_core.ports import (
    DefaultRole,
    ModuleManifest,
    RoleSlot,
    ToolClass,
    ToolContext,
    ToolInput,
    ToolResult,
    ToolSpec,
)
from campus_agent_core.ports.storage import Entity
from campus_agent_core.testing import catalog_for, minimal_config


@pytest.fixture
def config() -> CampusAgentConfig:
    return minimal_config()


class NoteInput(ToolInput):
    text: str


async def _unused(context: ToolContext, params: object) -> ToolResult:
    raise NotImplementedError


DEMO = ModuleManifest(
    name="demo",
    version="1.0.0",
    required_roles=(RoleSlot(name="publisher", default=DefaultRole.ABOVE_LOWEST),),
    locale_package="demo_texts",
    prompt_fragments=("prompt.demo",),
    tools=(
        ToolSpec(
            name="create_note_draft",
            tool_class=ToolClass.DRAFT,
            min_role="base",
            input_model=NoteInput,
            handler=_unused,
        ),
        ToolSpec(
            name="publish_note",
            tool_class=ToolClass.COMMIT,
            min_role="publisher",
            input_model=NoteInput,
            handler=_unused,
        ),
    ),
)


@pytest.fixture
def registry() -> ToolRegistry:
    """Core tools plus a demo module with a draft tool and a team_lead commit tool."""
    config = minimal_config("modules:\n  demo: {}\n")
    demo_catalog = catalog_for(DEMO)
    core_catalog = load_catalog("campus_agent_core")

    def catalogs(package: str) -> Catalog:
        return core_catalog if package == "campus_agent_core" else demo_catalog

    modules = load_modules(config, {"core": core_manifest, "demo": DEMO}, catalog_loader=catalogs)
    return ToolRegistry(modules, config.role_hierarchy(), language="de")


@pytest.fixture
def member() -> UserContext:
    return UserContext(user_id="user-member", first_name="Mia", role="member")


@pytest.fixture
def team_lead() -> UserContext:
    return UserContext(user_id="user-lead", first_name="Leo", role="team_lead")


@pytest.fixture
def board() -> UserContext:
    return UserContext(user_id="user-board", first_name="Bo", role="board")


class DictStore:
    """Minimal RuntimeStore for core tests (the full fake lives in integrations)."""

    def __init__(self) -> None:
        self.tables: dict[tuple[str, str, str], Entity] = {}

    async def get(self, table: str, partition_key: str, row_key: str) -> Entity | None:
        return self.tables.get((table, partition_key, row_key))

    async def insert(self, table: str, partition_key: str, row_key: str, entity: Entity) -> None:
        key = (table, partition_key, row_key)
        if key in self.tables:
            raise ConflictError("exists")
        self.tables[key] = entity

    async def upsert(self, table: str, partition_key: str, row_key: str, entity: Entity) -> None:
        self.tables[(table, partition_key, row_key)] = entity

    async def delete(self, table: str, partition_key: str, row_key: str) -> None:
        self.tables.pop((table, partition_key, row_key), None)

    async def list_partition(self, table: str, partition_key: str) -> list[Entity]:
        return [e for (t, p, _), e in self.tables.items() if (t, p) == (table, partition_key)]


@pytest.fixture
def store() -> DictStore:
    return DictStore()
