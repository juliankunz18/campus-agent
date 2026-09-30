import pytest
from pydantic import BaseModel, ConfigDict, ValidationError

from campus_agent_core.domain.roles import RoleHierarchy
from campus_agent_core.modules import ModuleLoadError, ToolRegistry, load_modules
from campus_agent_core.modules.builtin import manifest as core_manifest
from campus_agent_core.modules.slots import resolve_slots
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
from campus_agent_core.testing import minimal_config

ROLES = RoleHierarchy(["member", "team_lead", "board"])
CORE = {"base": "member", "approver": "board"}


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid")

    organizer_role: str | None = None


class NoInput(ToolInput):
    pass


async def handler(context: ToolContext, params: object) -> ToolResult:
    raise NotImplementedError


def manifest(*slots: RoleSlot, name: str = "demo") -> ModuleManifest:
    return ModuleManifest(
        name=name,
        version="1.0.0",
        required_roles=slots,
        locale_package="demo_texts",
        config_model=Settings,
    )


class TestRoleSlotModel:
    def test_exactly_one_default(self):
        with pytest.raises(ValidationError, match="exactly one of 'default' or 'inherits'"):
            RoleSlot(name="x")
        with pytest.raises(ValidationError, match="exactly one"):
            RoleSlot(name="x", default=DefaultRole.LOWEST, inherits="approver")

    def test_snake_case(self):
        with pytest.raises(ValidationError):
            RoleSlot(name="Organizer", inherits="approver")

    def test_duplicate_slots(self):
        slot = RoleSlot(name="organizer", inherits="approver")

        with pytest.raises(ValidationError, match="duplicate role slots: organizer"):
            manifest(slot, slot)

    def test_core_slots_cannot_be_redeclared(self):
        with pytest.raises(ValidationError, match="core slots cannot be redeclared: approver"):
            manifest(RoleSlot(name="approver", default=DefaultRole.LOWEST))

    def test_unknown_parent(self):
        with pytest.raises(ValidationError, match="inherit unknown slots: chair"):
            manifest(RoleSlot(name="organizer", inherits="chair"))

    def test_setting_must_exist_in_config_model(self):
        with pytest.raises(ValidationError, match="missing from config_model: host_role"):
            manifest(RoleSlot(name="organizer", inherits="approver", setting="host_role"))

    def test_tools_may_use_core_slots_without_declaring_them(self):
        tool = ToolSpec(
            name="do_it",
            tool_class=ToolClass.READ,
            min_role="approver",
            input_model=NoInput,
            handler=handler,
        )

        assert ModuleManifest(
            name="demo", version="1.0.0", locale_package="x", tools=(tool,)
        ).tools == (tool,)


class TestResolveSlots:
    def test_positional_defaults(self):
        slots, issues = resolve_slots(
            manifest(
                RoleSlot(name="low", default=DefaultRole.LOWEST, privileged=False),
                RoleSlot(name="mid", default=DefaultRole.ABOVE_LOWEST),
                RoleSlot(name="top", default=DefaultRole.HIGHEST),
            ),
            {},
            ROLES,
            CORE,
        )

        assert issues == []
        assert slots == {**CORE, "low": "member", "mid": "team_lead", "top": "board"}

    def test_inherits_follows_the_parent(self):
        slots, _ = resolve_slots(
            manifest(
                RoleSlot(name="organizer", inherits="host"),
                RoleSlot(name="host", inherits="approver"),
            ),
            {},
            ROLES,
            CORE,
        )

        assert slots["organizer"] == slots["host"] == "board"

    def test_explicit_setting_wins(self):
        slots, issues = resolve_slots(
            manifest(RoleSlot(name="organizer", inherits="approver", setting="organizer_role")),
            {"organizer_role": "team_lead"},
            ROLES,
            CORE,
        )

        assert issues == []
        assert slots["organizer"] == "team_lead"

    def test_unknown_role_in_setting(self):
        _, issues = resolve_slots(
            manifest(RoleSlot(name="organizer", inherits="approver", setting="organizer_role")),
            {"organizer_role": "chair"},
            ROLES,
            CORE,
        )

        assert issues == [
            "organizer_role: unknown role 'chair'; configured roles: member, team_lead, board"
        ]

    def test_privileged_slot_never_resolves_to_the_lowest_role(self):
        _, issues = resolve_slots(
            manifest(RoleSlot(name="organizer", inherits="approver", setting="organizer_role")),
            {"organizer_role": "member"},
            ROLES,
            CORE,
        )

        (issue,) = issues
        assert issue.startswith("organizer_role: 'member' is the lowest role")

    def test_unprivileged_slot_may_use_the_lowest_role(self):
        slots, issues = resolve_slots(
            manifest(RoleSlot(name="reader", default=DefaultRole.LOWEST, privileged=False)),
            {},
            ROLES,
            CORE,
        )

        assert issues == []
        assert slots["reader"] == "member"

    def test_cycles_are_reported(self):
        _, issues = resolve_slots(
            manifest(RoleSlot(name="a", inherits="b"), RoleSlot(name="b", inherits="a")),
            {},
            ROLES,
            CORE,
        )

        assert "role slot 'a': cycle in 'inherits'" in issues


class TestCoreApproverRole:
    def registry(self, extra_yaml: str = "") -> ToolRegistry:
        config = minimal_config(extra_yaml)
        modules = load_modules(config, {"core": core_manifest})
        return ToolRegistry(modules, config.role_hierarchy(), language="de")

    def test_defaults_to_the_highest_role(self):
        registry = self.registry()

        assert registry.get("approve_application").min_role == "board"
        assert registry.get("approve_application").role_slot == "approver"
        assert registry.get("submit_application").min_role == "member"

    def test_can_be_configured(self):
        registry = self.registry("applications:\n  approver_role: team_lead\n")

        assert registry.get("approve_all_open").min_role == "team_lead"
        assert registry.is_allowed("team_lead", "approve_application")

    def test_lowest_role_is_rejected(self):
        with pytest.raises(ModuleLoadError) as excinfo:
            self.registry("applications:\n  approver_role: member\n")

        (issue,) = excinfo.value.issues
        assert issue.startswith("applications.approver_role: 'member' is the lowest role")

    def test_unknown_role_is_rejected(self):
        with pytest.raises(ModuleLoadError) as excinfo:
            self.registry("applications:\n  approver_role: chair\n")

        assert excinfo.value.issues == (
            "applications.approver_role: unknown role 'chair'; "
            "configured roles: member, team_lead, board",
        )
