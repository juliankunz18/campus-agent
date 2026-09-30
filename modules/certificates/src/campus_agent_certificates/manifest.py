"""Manifest of the certificates module: activities and engagement certificates."""

from __future__ import annotations

from campus_agent_certificates import tools
from campus_agent_certificates.settings import CertificatesSettings
from campus_agent_core.ports import (
    ColumnType,
    ListColumn,
    ListKind,
    ListSpec,
    ModuleManifest,
    ToolClass,
    ToolSpec,
)

ACTIVITIES_LIST = ListSpec(
    name="Aktivitaeten",
    columns=(
        ListColumn(name="Titel", type=ColumnType.TEXT, required=True),
        ListColumn(name="Beschreibung", type=ColumnType.NOTE),
        ListColumn(name="MitgliedEntraId", type=ColumnType.TEXT, required=True, indexed=True),
        ListColumn(name="Von", type=ColumnType.DATE, required=True),
        ListColumn(name="Bis", type=ColumnType.DATE),
        ListColumn(name="Bestaetigt", type=ColumnType.BOOLEAN, required=True),
        ListColumn(name="BestaetigtVon", type=ColumnType.TEXT),
    ),
)

CERTIFICATES_LIBRARY = ListSpec(
    name="Bescheinigungen",
    kind=ListKind.LIBRARY,
    columns=(
        ListColumn(name="Nummer", type=ColumnType.TEXT, required=True, indexed=True, unique=True),
        ListColumn(name="AntragId", type=ColumnType.TEXT, required=True, indexed=True),
        ListColumn(name="AusgestelltAm", type=ColumnType.DATE, required=True),
    ),
)

manifest = ModuleManifest(
    name="certificates",
    version="0.1.0",
    required_roles=("member", "team_lead"),
    locale_package="campus_agent_certificates",
    prompt_fragments=("prompt.certificates",),
    lists=(ACTIVITIES_LIST, CERTIFICATES_LIBRARY),
    config_model=CertificatesSettings,
    tools=(
        ToolSpec(
            name="list_my_activities",
            tool_class=ToolClass.READ,
            min_role="member",
            input_model=tools.ListMyActivitiesInput,
            handler=tools.list_my_activities,
        ),
        ToolSpec(
            name="create_certificate_draft",
            tool_class=ToolClass.DRAFT,
            min_role="member",
            input_model=tools.CreateCertificateDraftInput,
            handler=tools.create_certificate_draft,
        ),
        ToolSpec(
            name="list_team_activities",
            tool_class=ToolClass.READ,
            min_role="team_lead",
            input_model=tools.ListTeamActivitiesInput,
            handler=tools.list_team_activities,
        ),
        ToolSpec(
            name="confirm_activity",
            tool_class=ToolClass.COMMIT,
            min_role="team_lead",
            input_model=tools.ConfirmActivityInput,
            handler=tools.confirm_activity,
        ),
    ),
)
