"""Tools of the members module. Handlers are stubs until the SharePoint adapter exists."""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field

from campus_agent_core.ports import ToolContext, ToolInput, ToolResult


class MemberField(StrEnum):
    """Master data fields that can be changed. Sensitive fields (bank details, birth date,
    address) are deliberately absent: they never reach the model."""

    NAME = "name"
    EMAIL = "email"
    TEAM = "team"


class GetMyProfileInput(ToolInput):
    pass


class CreateChangeDraftInput(ToolInput):
    field: MemberField
    new_value: str = Field(min_length=1, max_length=200)


class SearchMembersInput(ToolInput):
    query: str = Field(min_length=2, max_length=100)
    active_only: bool = True


class UpdateMemberInput(ToolInput):
    member_id: int = Field(ge=1, description="SharePoint item ID of the member to change.")
    field: MemberField
    new_value: str = Field(min_length=1, max_length=200)


# TODO(members): implement against a MemberRepository port once the SharePoint adapter
# exists. Return only the fields the use case needs (data minimisation).


async def get_my_profile(context: ToolContext, params: GetMyProfileInput) -> ToolResult:
    raise NotImplementedError("get_my_profile")


async def create_change_draft(context: ToolContext, params: CreateChangeDraftInput) -> ToolResult:
    # Creates a DRAFT application of kind "data_change"; the member submits it by card.
    raise NotImplementedError("create_change_draft")


async def search_members(context: ToolContext, params: SearchMembersInput) -> ToolResult:
    raise NotImplementedError("search_members")


async def update_member(context: ToolContext, params: UpdateMemberInput) -> ToolResult:
    raise NotImplementedError("update_member")
