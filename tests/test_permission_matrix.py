"""Permission matrix: every role x every tool of every installed module.

The expected permission is derived from the manifests: each tool's role slot is mapped
to a configured role (ADR 0019), and a role may use the tool if it inherits that role.
Each pair is checked in the registry, in the list of tools the model sees and in the
tool policy that guards every call. The matrix runs for the Musterverein and for a
group with its own role names and changed role slots.
"""

import contextlib
from datetime import UTC, datetime

import pytest

from campus_agent_core.agent import ToolPolicy
from campus_agent_core.config import CampusAgentConfig, parse_config
from campus_agent_core.domain.user import UserContext
from campus_agent_core.errors import ForbiddenError, ValidationFailedError
from campus_agent_core.modules import (
    ModuleLoadError,
    ToolRegistry,
    discover_manifests,
    load_modules,
)
from campus_agent_core.ports.llm import ToolCall
from tests.helpers import example_config

NOW = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)

# A second, fictional group: German role IDs, four roles, organizers below the board.
CUSTOM_GROUP = """
group: {name: Beispiel-Hochschulgruppe, short_name: beispiel}
roles:
  - {id: mitglied, label: Mitglied, source: all_tenant_users}
  - {id: leitung, label: Projektleitung, entra_group: g-leitung}
  - {id: kasse, label: Kassenwart, entra_group: g-kasse}
  - {id: vorstand, label: Vorstand, entra_group: g-vorstand}
sharepoint: {site_id: site}
llm: {deployment: model}
modules:
  members: {}
  certificates: {}
  knowledge: {}
  events: {organizer_role: leitung}
"""

SCENARIOS: dict[str, CampusAgentConfig] = {
    "musterverein": example_config(),
    "custom": parse_config(CUSTOM_GROUP, env={}),
}


def _expected(config: CampusAgentConfig) -> list[tuple[str, str, bool]]:
    roles = config.role_hierarchy()
    tools = [
        (tool.name, module.slot_roles[tool.min_role])
        for module in load_modules(config, discover_manifests())
        for tool in module.manifest.tools
    ]
    return [
        (role, tool, roles.rank(role) >= roles.rank(min_role))
        for role in roles.roles
        for tool, min_role in tools
    ]


MATRIX = [
    pytest.param(scenario, role, tool, allowed, id=f"{scenario}-{role}-{tool}")
    for scenario, config in SCENARIOS.items()
    for role, tool, allowed in _expected(config)
]


def _registry(scenario: str) -> ToolRegistry:
    config = SCENARIOS[scenario]
    modules = load_modules(config, discover_manifests())
    return ToolRegistry(modules, config.role_hierarchy(), language=config.group.language)


REGISTRIES = {scenario: _registry(scenario) for scenario in SCENARIOS}


def test_matrix_covers_every_role_and_tool():
    for scenario, config in SCENARIOS.items():
        rows = [p for p in MATRIX if p.values[0] == scenario]
        assert len(rows) == len(config.role_hierarchy().roles) * 24


@pytest.mark.parametrize(("scenario", "role", "tool", "allowed"), MATRIX)
def test_permission(scenario: str, role: str, tool: str, allowed: bool):
    registry = REGISTRIES[scenario]
    user = UserContext(user_id=f"user-{role}", role=role)

    assert registry.is_allowed(role, tool) is allowed
    assert (tool in {t.name for t in registry.for_role(role)}) is allowed
    assert (tool in {s.name for s in registry.schemas_for_role(role)}) is allowed

    policy = ToolPolicy(registry)
    request = ToolCall(id="call", name=tool, arguments={})
    if allowed:
        with contextlib.suppress(ValidationFailedError):  # empty arguments may be incomplete
            policy.decide(request, user, now=NOW)
    else:
        with pytest.raises(ForbiddenError):
            policy.decide(request, user, now=NOW)


def test_custom_group_maps_slots_to_its_own_roles():
    registry = REGISTRIES["custom"]
    min_roles = {tool.name: tool.min_role for tool in registry.all()}

    assert min_roles["submit_application"] == "mitglied"
    assert min_roles["approve_application"] == "vorstand"  # approver: highest role
    assert min_roles["search_members"] == "vorstand"  # member_admin inherits approver
    assert min_roles["confirm_activity"] == "leitung"  # second-lowest role
    assert min_roles["create_event"] == "leitung"  # organizer_role setting
    assert min_roles["list_registrations"] == "leitung"


def test_privileged_slot_on_the_lowest_role_is_rejected():
    config = parse_config(
        CUSTOM_GROUP.replace(
            "events: {organizer_role: leitung}", "events: {organizer_role: mitglied}"
        ),
        env={},
    )

    with pytest.raises(ModuleLoadError) as excinfo:
        load_modules(config, discover_manifests())

    (issue,) = excinfo.value.issues
    assert issue.startswith("modules.events.organizer_role: 'mitglied' is the lowest role")
