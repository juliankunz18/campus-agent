"""Manifest of the events module: events, registrations and participant lists."""

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
from campus_agent_events import tools


class EventsSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    organizer_role: str | None = None
    """Role that creates events and sees participant lists; defaults to the approver."""


ORGANIZER = "organizer"


EVENTS_LIST = ListSpec(
    name="Veranstaltungen",
    columns=(
        ListColumn(name="Titel", type=ColumnType.TEXT, required=True),
        ListColumn(name="Beginn", type=ColumnType.DATETIME, required=True, indexed=True),
        ListColumn(name="Ende", type=ColumnType.DATETIME),
        ListColumn(name="Ort", type=ColumnType.TEXT),
        ListColumn(name="Beschreibung", type=ColumnType.NOTE),
        ListColumn(name="Kapazitaet", type=ColumnType.NUMBER),
    ),
)

REGISTRATIONS_LIST = ListSpec(
    name="Anmeldungen",
    columns=(
        ListColumn(
            name="Veranstaltung",
            type=ColumnType.LOOKUP,
            required=True,
            lookup_list="Veranstaltungen",
        ),
        ListColumn(name="MitgliedEntraId", type=ColumnType.TEXT, required=True, indexed=True),
        ListColumn(name="AngemeldetAm", type=ColumnType.DATETIME, required=True),
    ),
)

manifest = ModuleManifest(
    name="events",
    version="0.1.0",
    required_roles=(RoleSlot(name=ORGANIZER, inherits=APPROVER_SLOT, setting="organizer_role"),),
    locale_package="campus_agent_events",
    prompt_fragments=("prompt.events",),
    lists=(EVENTS_LIST, REGISTRATIONS_LIST),
    config_model=EventsSettings,
    tools=(
        ToolSpec(
            name="list_events",
            tool_class=ToolClass.READ,
            min_role=BASE_SLOT,
            input_model=tools.ListEventsInput,
            handler=tools.list_events,
        ),
        ToolSpec(
            name="register_for_event",
            tool_class=ToolClass.COMMIT,
            min_role=BASE_SLOT,
            input_model=tools.EventRef,
            handler=tools.register_for_event,
        ),
        ToolSpec(
            name="cancel_registration",
            tool_class=ToolClass.COMMIT,
            min_role=BASE_SLOT,
            input_model=tools.EventRef,
            handler=tools.cancel_registration,
        ),
        ToolSpec(
            name="create_event",
            tool_class=ToolClass.COMMIT,
            min_role=ORGANIZER,
            input_model=tools.CreateEventInput,
            handler=tools.create_event,
        ),
        ToolSpec(
            name="list_registrations",
            tool_class=ToolClass.READ,
            min_role=ORGANIZER,
            input_model=tools.EventRef,
            handler=tools.list_registrations,
        ),
    ),
)
