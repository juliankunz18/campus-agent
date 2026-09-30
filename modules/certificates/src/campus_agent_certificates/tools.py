"""Tools of the certificates module. Handlers are stubs until the SharePoint adapter exists."""

from __future__ import annotations

from datetime import date
from typing import Self

from pydantic import Field, model_validator

from campus_agent_core.ports import ToolContext, ToolInput, ToolResult


class _Period(ToolInput):
    start: date | None = None
    end: date | None = None

    @model_validator(mode="after")
    def _ordered(self) -> Self:
        if self.start and self.end and self.start > self.end:
            raise ValueError("start must not be after end")
        return self


class ListMyActivitiesInput(_Period):
    pass


class CreateCertificateDraftInput(ToolInput):
    start: date
    end: date
    purpose: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def _ordered(self) -> Self:
        if self.start > self.end:
            raise ValueError("start must not be after end")
        return self


class ListTeamActivitiesInput(_Period):
    only_unconfirmed: bool = False


class ConfirmActivityInput(ToolInput):
    activity_id: int = Field(ge=1, description="SharePoint item ID of the activity.")


# TODO(certificates): implement against an ActivityRepository port. The PDF is rendered
# from the Jinja2 template with WeasyPrint when the board approves the application
# (ADR 0014); WeasyPrint is added as a dependency together with that implementation.


async def list_my_activities(context: ToolContext, params: ListMyActivitiesInput) -> ToolResult:
    raise NotImplementedError("list_my_activities")


async def create_certificate_draft(
    context: ToolContext, params: CreateCertificateDraftInput
) -> ToolResult:
    # Creates a DRAFT application of kind "certificate" from the member's own confirmed
    # activities in the period; the member submits it by card.
    raise NotImplementedError("create_certificate_draft")


async def list_team_activities(context: ToolContext, params: ListTeamActivitiesInput) -> ToolResult:
    raise NotImplementedError("list_team_activities")


async def confirm_activity(context: ToolContext, params: ConfirmActivityInput) -> ToolResult:
    # Only activities of the team led by the caller may be confirmed.
    raise NotImplementedError("confirm_activity")
