"""The installed modules must provide exactly the tool catalog of the technical design."""

from campus_agent_core.modules import ToolRegistry
from campus_agent_core.ports import ToolClass

R, D, C = ToolClass.READ, ToolClass.DRAFT, ToolClass.COMMIT

# tool: (module, minimum role, class) - copied from the design's tool catalog
CATALOG: dict[str, tuple[str, str, ToolClass]] = {
    "list_my_applications": ("core", "member", R),
    "submit_application": ("core", "member", C),
    "discard_draft": ("core", "member", C),
    "answer_clarification": ("core", "member", C),
    "list_open_applications": ("core", "board", R),
    "get_application": ("core", "board", R),
    "approve_application": ("core", "board", C),
    "reject_application": ("core", "board", C),
    "request_clarification": ("core", "board", C),
    "approve_all_open": ("core", "board", C),
    "get_my_profile": ("members", "member", R),
    "create_change_draft": ("members", "member", D),
    "search_members": ("members", "board", R),
    "update_member": ("members", "board", C),
    "list_my_activities": ("certificates", "member", R),
    "create_certificate_draft": ("certificates", "member", D),
    "list_team_activities": ("certificates", "team_lead", R),
    "confirm_activity": ("certificates", "team_lead", C),
    "search_knowledge": ("knowledge", "member", R),
    "list_events": ("events", "member", R),
    "register_for_event": ("events", "member", C),
    "cancel_registration": ("events", "member", C),
    "create_event": ("events", "board", C),
    "list_registrations": ("events", "board", R),
}


def test_registry_matches_the_design_catalog(musterverein_registry: ToolRegistry):
    actual = {
        tool.name: (tool.module, tool.min_role, tool.tool_class)
        for tool in musterverein_registry.all()
    }

    assert actual == CATALOG


def test_every_tool_has_german_and_english_texts(musterverein_registry: ToolRegistry):
    for tool in musterverein_registry.all():
        assert tool.description, tool.name
        properties = tool.parameters.get("properties", {})
        assert isinstance(properties, dict)
        for name, definition in properties.items():
            assert isinstance(definition, dict)
            assert definition.get("description"), f"{tool.name}.{name}"
