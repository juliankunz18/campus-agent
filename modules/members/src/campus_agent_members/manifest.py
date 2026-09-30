"""Manifest of the members module: own data, change requests, member administration."""

from __future__ import annotations

from campus_agent_core.ports import (
    ColumnType,
    ListColumn,
    ListSpec,
    ModuleManifest,
    ToolClass,
    ToolSpec,
)
from campus_agent_members import tools

MEMBERS_LIST = ListSpec(
    name="Mitglieder",
    columns=(
        ListColumn(name="Name", type=ColumnType.TEXT, required=True),
        ListColumn(name="EMail", type=ColumnType.TEXT, required=True),
        ListColumn(
            name="EntraObjectId", type=ColumnType.TEXT, required=True, indexed=True, unique=True
        ),
        ListColumn(name="Ressort", type=ColumnType.LOOKUP, lookup_list="Ressorts"),
        ListColumn(name="Eintritt", type=ColumnType.DATE),
        ListColumn(name="Aktiv", type=ColumnType.BOOLEAN, required=True),
    ),
)

TEAMS_LIST = ListSpec(
    name="Ressorts",
    columns=(
        ListColumn(name="Name", type=ColumnType.TEXT, required=True, indexed=True, unique=True),
        ListColumn(name="LeitungEntraId", type=ColumnType.TEXT, indexed=True),
    ),
)

manifest = ModuleManifest(
    name="members",
    version="0.1.0",
    required_roles=("member", "board"),
    locale_package="campus_agent_members",
    prompt_fragments=("prompt.members",),
    lists=(TEAMS_LIST, MEMBERS_LIST),
    tools=(
        ToolSpec(
            name="get_my_profile",
            tool_class=ToolClass.READ,
            min_role="member",
            input_model=tools.GetMyProfileInput,
            handler=tools.get_my_profile,
        ),
        ToolSpec(
            name="create_change_draft",
            tool_class=ToolClass.DRAFT,
            min_role="member",
            input_model=tools.CreateChangeDraftInput,
            handler=tools.create_change_draft,
        ),
        ToolSpec(
            name="search_members",
            tool_class=ToolClass.READ,
            min_role="board",
            input_model=tools.SearchMembersInput,
            handler=tools.search_members,
        ),
        ToolSpec(
            name="update_member",
            tool_class=ToolClass.COMMIT,
            min_role="board",
            input_model=tools.UpdateMemberInput,
            handler=tools.update_member,
        ),
    ),
)
