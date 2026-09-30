import textwrap
from importlib.metadata import EntryPoint, entry_points
from pathlib import Path

import pytest
from pydantic import ConfigDict, ValidationError

from campus_agent_core.config import CampusAgentConfig
from campus_agent_core.errors import ForbiddenError, NotFoundError
from campus_agent_core.i18n import Catalog, load_catalog
from campus_agent_core.modules import (
    ENTRY_POINT_GROUP,
    ModuleLoadError,
    ToolRegistry,
    discover_manifests,
    load_modules,
)
from campus_agent_core.modules.builtin import manifest as core_manifest
from campus_agent_core.ports import (
    ColumnType,
    ListColumn,
    ListSpec,
    ModuleManifest,
    RoleRef,
    ToolClass,
    ToolContext,
    ToolInput,
    ToolResult,
    ToolSpec,
)
from campus_agent_core.testing import catalog_for, minimal_config


class SearchInput(ToolInput):
    query: str


class EmptyInput(ToolInput):
    pass


class DemoSettings(ToolInput):
    organizer_role: RoleRef = "board"
    library: str = "Wissen"


async def demo_handler(context: ToolContext, params: object) -> ToolResult:
    return ToolResult(summary=f"ok for {context.user.user_id}")


def make_tool(
    name: str = "search_things",
    *,
    tool_class: ToolClass = ToolClass.READ,
    min_role: str = "member",
    input_model: type[ToolInput] = SearchInput,
) -> ToolSpec:
    return ToolSpec(
        name=name,
        tool_class=tool_class,
        min_role=min_role,
        input_model=input_model,
        handler=demo_handler,
    )


def make_manifest(
    name: str = "demo", tools: tuple[ToolSpec, ...] | None = None, **fields: object
) -> ModuleManifest:
    data: dict[str, object] = {
        "name": name,
        "version": "1.0.0",
        "required_roles": ("member", "team_lead", "board"),
        "locale_package": f"{name}_texts",
        "tools": (make_tool(),) if tools is None else tools,
    }
    data.update(fields)
    return ModuleManifest.model_validate(data)


def loader_for(*manifests: ModuleManifest, skip: frozenset[str] = frozenset()):
    catalog = catalog_for(*manifests, skip=skip)
    core_catalog = load_catalog("campus_agent_core")

    def load(package: str) -> Catalog:
        return core_catalog if package == "campus_agent_core" else catalog

    return load


# --- ToolSpec and manifest validation ---------------------------------------------------


class TestToolSpec:
    @pytest.mark.parametrize("field", ["user_id", "role", "applicant_id", "on_behalf_of"])
    def test_identity_parameters_are_rejected(self, field: str):
        model = type(f"Bad_{field}", (ToolInput,), {"__annotations__": {field: str}})

        with pytest.raises(ValidationError, match="must not take identity parameters"):
            make_tool(input_model=model)

    def test_input_models_must_forbid_extra_fields(self):
        class Lenient(ToolInput):
            model_config = ConfigDict(extra="ignore")

        with pytest.raises(ValidationError, match="must forbid extra fields"):
            make_tool(input_model=Lenient)

    @pytest.mark.parametrize("name", ["GetProfile", "get-profile", "1tool", ""])
    def test_tool_names_are_english_snake_case(self, name: str):
        with pytest.raises(ValidationError):
            make_tool(name)

    def test_text_keys(self):
        tool = make_tool("get_my_profile")

        assert tool.description_key == "tools.get_my_profile.description"
        assert tool.parameter_key("query") == "tools.get_my_profile.params.query"


class TestManifest:
    def test_tool_roles_must_be_declared(self):
        with pytest.raises(ValidationError, match="missing from required_roles: board"):
            make_manifest(tools=(make_tool(min_role="board"),), required_roles=("member",))

    def test_duplicate_tools(self):
        with pytest.raises(ValidationError, match="duplicate tool names: search_things"):
            make_manifest(tools=(make_tool(), make_tool()))

    def test_version_is_semver(self):
        with pytest.raises(ValidationError, match="semantic versioning"):
            make_manifest(version="1.0")

    def test_lists_and_columns(self):
        members = ListSpec(
            name="Mitglieder",
            columns=(
                ListColumn(name="Name", type=ColumnType.TEXT, required=True),
                ListColumn(name="EntraObjectId", type=ColumnType.TEXT, indexed=True, unique=True),
                ListColumn(name="Ressort", type=ColumnType.LOOKUP, lookup_list="Ressorts"),
            ),
        )

        assert make_manifest(lists=(members,)).lists[0].name == "Mitglieder"

    @pytest.mark.parametrize(
        ("column", "message"),
        [
            ({"name": "X", "type": "text", "unique": True}, "must also be indexed"),
            ({"name": "X", "type": "choice"}, "'choices' is required"),
            ({"name": "X", "type": "lookup"}, "'lookup_list' is required"),
            ({"name": "Neuer Wert", "type": "text"}, "alphanumeric"),
        ],
    )
    def test_invalid_columns(self, column: dict[str, object], message: str):
        with pytest.raises(ValidationError, match=message):
            ListColumn.model_validate(column)

    def test_duplicate_columns(self):
        column = ListColumn(name="Name", type=ColumnType.TEXT)

        with pytest.raises(ValidationError, match="duplicate columns: Name"):
            ListSpec(name="Liste", columns=(column, column))


# --- discovery --------------------------------------------------------------------------


def entry(name: str, value: str) -> EntryPoint:
    return EntryPoint(name=name, value=value, group=ENTRY_POINT_GROUP)


class TestDiscovery:
    def test_installed_core_module_is_discovered(self):
        registered = entry_points(group=ENTRY_POINT_GROUP, name="core")

        manifests = discover_manifests(registered)

        assert manifests["core"] is core_manifest

    def test_factories_are_called(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        (tmp_path / "factory_module.py").write_text(
            textwrap.dedent(
                """
                from campus_agent_core.modules.builtin import manifest

                def build():
                    return manifest
                """
            ),
            encoding="utf-8",
        )
        monkeypatch.syspath_prepend(str(tmp_path))

        manifests = discover_manifests([entry("core", "factory_module:build")])

        assert manifests["core"] is core_manifest

    def test_problems_are_collected(self):
        with pytest.raises(ModuleLoadError) as excinfo:
            discover_manifests(
                [
                    entry("broken", "does_not_exist:manifest"),
                    entry("wrong_type", "os:sep"),
                    entry("renamed", "campus_agent_core.modules.builtin:manifest"),
                    entry("core", "campus_agent_core.modules.builtin:manifest"),
                    entry("core", "campus_agent_core.modules.builtin:manifest"),
                ]
            )

        issues = excinfo.value.issues
        assert issues[0].startswith("entry point 'broken': No module named")
        assert issues[1:] == (
            "entry point 'wrong_type': does not provide a ModuleManifest",
            "entry point 'renamed': manifest is named 'core'",
            "module 'core' is registered more than once",
        )


# --- loading against a configuration ----------------------------------------------------


class TestLoadModules:
    def test_core_is_always_loaded(self, config: CampusAgentConfig):
        loaded = load_modules(config, {"core": core_manifest})

        assert [module.name for module in loaded] == ["core"]
        assert loaded[0].catalog.has("tools.approve_application.description", "de")

    def test_enabled_modules_are_loaded_in_config_order(self):
        demo, other = make_manifest("demo"), make_manifest("other", tools=())
        config = minimal_config("modules:\n  other: {}\n  demo: {}\n")

        loaded = load_modules(
            config,
            {"core": core_manifest, "demo": demo, "other": other},
            catalog_loader=loader_for(demo, other),
        )

        assert [module.name for module in loaded] == ["core", "other", "demo"]

    def test_unknown_module(self):
        config = minimal_config("modules:\n  missing: {}\n")

        with pytest.raises(ModuleLoadError) as excinfo:
            load_modules(config, {"core": core_manifest})

        assert excinfo.value.issues == (
            "modules.missing: module is not installed (available: core)",
        )

    def test_required_roles_must_be_configured(self):
        demo = make_manifest(required_roles=("member", "treasurer"), tools=())
        config = minimal_config("modules:\n  demo: {}\n")

        with pytest.raises(ModuleLoadError, match="needs roles that are not configured: treasurer"):
            load_modules(
                config, {"core": core_manifest, "demo": demo}, catalog_loader=loader_for(demo)
            )

    def test_every_text_must_exist_in_every_language(self):
        demo = make_manifest(prompt_fragments=("prompt.demo",))
        config = minimal_config("modules:\n  demo: {}\n")
        skip = frozenset({"tools.search_things.params.query", "prompt.demo"})

        with pytest.raises(ModuleLoadError) as excinfo:
            load_modules(
                config,
                {"core": core_manifest, "demo": demo},
                catalog_loader=loader_for(demo, skip=skip),
            )

        assert excinfo.value.issues == (
            "modules.demo: missing text 'tools.search_things.params.query' for language 'de'",
            "modules.demo: missing text 'prompt.demo' for language 'de'",
            "modules.demo: missing text 'tools.search_things.params.query' for language 'en'",
            "modules.demo: missing text 'prompt.demo' for language 'en'",
        )

    def test_tool_names_are_unique_across_modules(self):
        clash = make_manifest(tools=(make_tool("approve_application", min_role="board"),))
        config = minimal_config("modules:\n  demo: {}\n")

        with pytest.raises(
            ModuleLoadError, match="'approve_application' is already defined by 'core'"
        ):
            load_modules(
                config, {"core": core_manifest, "demo": clash}, catalog_loader=loader_for(clash)
            )

    def test_settings_are_validated_with_configured_roles(self):
        demo = make_manifest(config_model=DemoSettings)
        config = minimal_config("modules:\n  demo: {organizer_role: team_lead}\n")

        (_, loaded) = load_modules(
            config, {"core": core_manifest, "demo": demo}, catalog_loader=loader_for(demo)
        )

        assert loaded.settings == DemoSettings(organizer_role="team_lead")

    def test_invalid_settings_are_reported_with_their_path(self):
        demo = make_manifest(config_model=DemoSettings)
        config = minimal_config("modules:\n  demo: {organizer_role: treasurer, colour: red}\n")

        with pytest.raises(ModuleLoadError) as excinfo:
            load_modules(
                config, {"core": core_manifest, "demo": demo}, catalog_loader=loader_for(demo)
            )

        assert excinfo.value.issues == (
            "modules.demo.organizer_role: Value error, unknown role 'treasurer'; "
            "configured roles: member, team_lead, board",
            "modules.demo.colour: Extra inputs are not permitted",
        )

    def test_modules_without_settings_reject_settings(self):
        demo = make_manifest()
        config = minimal_config("modules:\n  demo: {colour: red}\n")

        with pytest.raises(
            ModuleLoadError, match=r"modules\.demo\.colour: module takes no settings"
        ):
            load_modules(
                config, {"core": core_manifest, "demo": demo}, catalog_loader=loader_for(demo)
            )


# --- registry ---------------------------------------------------------------------------


@pytest.fixture
def registry() -> ToolRegistry:
    demo = make_manifest(
        tools=(
            make_tool("search_things"),
            make_tool("confirm_thing", tool_class=ToolClass.COMMIT, min_role="team_lead"),
            make_tool(
                "delete_all", tool_class=ToolClass.COMMIT, min_role="board", input_model=EmptyInput
            ),
        )
    )
    config = minimal_config("modules:\n  demo: {}\n")
    modules = load_modules(
        config, {"core": core_manifest, "demo": demo}, catalog_loader=loader_for(demo)
    )
    return ToolRegistry(modules, config.role_hierarchy(), language="de")


class TestRegistry:
    def test_tools_are_filtered_by_role(self, registry: ToolRegistry):
        member = {tool.name for tool in registry.for_role("member")}
        team_lead = {tool.name for tool in registry.for_role("team_lead")}
        board = {tool.name for tool in registry.for_role("board")}

        assert "search_things" in member
        assert "confirm_thing" not in member
        assert team_lead - member == {"confirm_thing"}
        assert board == set(registry.names())
        assert member < team_lead < board

    def test_is_allowed(self, registry: ToolRegistry):
        assert registry.is_allowed("board", "confirm_thing")
        assert registry.is_allowed("team_lead", "confirm_thing")
        assert not registry.is_allowed("member", "confirm_thing")

    def test_ensure_allowed(self, registry: ToolRegistry):
        assert registry.ensure_allowed("board", "delete_all").module == "demo"

        with pytest.raises(ForbiddenError):
            registry.ensure_allowed("team_lead", "delete_all")
        with pytest.raises(NotFoundError):
            registry.ensure_allowed("board", "unknown_tool")

    def test_schema_uses_localized_texts(self, registry: ToolRegistry):
        schema = registry.get("search_things").schema()

        assert schema.description == "Beschreibung search_things"
        assert schema.parameters == {
            "additionalProperties": False,
            "properties": {"query": {"description": "Parameter query", "type": "string"}},
            "required": ["query"],
            "type": "object",
        }

    def test_schemas_for_role_hide_other_tools(self, registry: ToolRegistry):
        names = {schema.name for schema in registry.schemas_for_role("member")}

        assert "delete_all" not in names
        assert "approve_application" not in names
        assert "list_my_applications" in names

    def test_english_texts(self, registry: ToolRegistry):
        config = minimal_config("group: {name: Testgruppe, short_name: test, language: en}\n")
        modules = load_modules(config, {"core": core_manifest})
        english = ToolRegistry(modules, config.role_hierarchy(), language="en")

        assert english.get("approve_application").description.startswith("Approves")
