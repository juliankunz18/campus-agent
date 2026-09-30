"""Manifest of the members module: own data, change requests, member administration."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from campus_agent_core.ports import (
    APPROVER_SLOT,
    BASE_SLOT,
    ColumnType,
    ListColumn,
    ListSpec,
    ModuleManifest,
    RoleSlot,
    ToolClass,
    ToolSpec,
)
from campus_agent_members import tools

MEMBER_ADMIN = "member_admin"


class MembersSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    admin_role: str | None = None
    """Role that searches and changes member data; defaults to the approver role."""


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
    required_roles=(RoleSlot(name=MEMBER_ADMIN, inherits=APPROVER_SLOT, setting="admin_role"),),
    config_model=MembersSettings,
    locale_package="campus_agent_members",
    prompt_fragments=("prompt.members",),
    lists=(TEAMS_LIST, MEMBERS_LIST),
    tools=(
        ToolSpec(
            name="get_my_profile",
            tool_class=ToolClass.READ,
            min_role=BASE_SLOT,
            input_model=tools.GetMyProfileInput,
            handler=tools.get_my_profile,
        ),
        ToolSpec(
            name="create_change_draft",
            tool_class=ToolClass.DRAFT,
            min_role=BASE_SLOT,
            input_model=tools.CreateChangeDraftInput,
            handler=tools.create_change_draft,
        ),
        ToolSpec(
            name="search_members",
            tool_class=ToolClass.READ,
            min_role=MEMBER_ADMIN,
            input_model=tools.SearchMembersInput,
            handler=tools.search_members,
        ),
        ToolSpec(
            name="update_member",
            tool_class=ToolClass.COMMIT,
            min_role=MEMBER_ADMIN,
            input_model=tools.UpdateMemberInput,
            handler=tools.update_member,
        ),
    ),
)
