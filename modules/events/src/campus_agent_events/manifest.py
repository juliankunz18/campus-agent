"""Manifest of the events module: events, registrations and participant lists."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from campus_agent_core.ports import (
    ColumnType,
    ListColumn,
    ListSpec,
    ModuleManifest,
    RoleRef,
    ToolClass,
    ToolSpec,
)
from campus_agent_events import tools


class EventsSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    # TODO(events): tools use the fixed minimum roles of the tool catalog for now;
    # decide whether organizer_role should override the role of create_event and
    # list_registrations (see docs/adr/0011).
    organizer_role: RoleRef = "board"


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
    required_roles=("member", "board"),
    locale_package="campus_agent_events",
    prompt_fragments=("prompt.events",),
    lists=(EVENTS_LIST, REGISTRATIONS_LIST),
    config_model=EventsSettings,
    tools=(
        ToolSpec(
            name="list_events",
            tool_class=ToolClass.READ,
            min_role="member",
            input_model=tools.ListEventsInput,
            handler=tools.list_events,
        ),
        ToolSpec(
            name="register_for_event",
            tool_class=ToolClass.COMMIT,
            min_role="member",
            input_model=tools.EventRef,
            handler=tools.register_for_event,
        ),
        ToolSpec(
            name="cancel_registration",
            tool_class=ToolClass.COMMIT,
            min_role="member",
            input_model=tools.EventRef,
            handler=tools.cancel_registration,
        ),
        ToolSpec(
            name="create_event",
            tool_class=ToolClass.COMMIT,
            min_role="board",
            input_model=tools.CreateEventInput,
            handler=tools.create_event,
        ),
        ToolSpec(
            name="list_registrations",
            tool_class=ToolClass.READ,
            min_role="board",
            input_model=tools.EventRef,
            handler=tools.list_registrations,
        ),
    ),
)
