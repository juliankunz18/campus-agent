"""Tools of the events module. Handlers are stubs until the SharePoint adapter exists."""

from __future__ import annotations

from datetime import date
from typing import Self

from pydantic import AwareDatetime, Field, model_validator

from campus_agent_core.ports import ToolContext, ToolInput, ToolResult


class ListEventsInput(ToolInput):
    start: date | None = None
    limit: int = Field(default=10, ge=1, le=50)


class EventRef(ToolInput):
    event_id: int = Field(ge=1, description="SharePoint item ID of the event.")


class CreateEventInput(ToolInput):
    title: str = Field(min_length=1, max_length=120)
    starts_at: AwareDatetime
    ends_at: AwareDatetime | None = None
    location: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=2000)
    capacity: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def _ordered(self) -> Self:
        if self.ends_at is not None and self.ends_at < self.starts_at:
            raise ValueError("ends_at must not be before starts_at")
        return self


# TODO(events): implement against an EventRepository port (planned for roadmap phase 2).


async def list_events(context: ToolContext, params: ListEventsInput) -> ToolResult:
    raise NotImplementedError("list_events")


async def register_for_event(context: ToolContext, params: EventRef) -> ToolResult:
    raise NotImplementedError("register_for_event")


async def cancel_registration(context: ToolContext, params: EventRef) -> ToolResult:
    raise NotImplementedError("cancel_registration")


async def create_event(context: ToolContext, params: CreateEventInput) -> ToolResult:
    raise NotImplementedError("create_event")


async def list_registrations(context: ToolContext, params: EventRef) -> ToolResult:
    raise NotImplementedError("list_registrations")
