"""The built-in ``core`` module: the application workflow shared by all modules.

Registered through the same entry point group as every other module so that the tool
registry, the permission matrix and the MCP server treat it uniformly.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from campus_agent_core.domain.applications import ApplicationStatus
from campus_agent_core.ports.module import (
    APPROVER_SLOT,
    BASE_SLOT,
    ColumnType,
    DefaultRole,
    ListColumn,
    ListSpec,
    ModuleManifest,
    RoleSlot,
    ToolClass,
    ToolContext,
    ToolInput,
    ToolResult,
    ToolSpec,
)

type ApplicationKind = str


class CoreSettings(BaseModel):
    """Settings of the core, taken from the top-level ``applications`` section."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    approver_role: str | None = None


# One list for every kind of application, distinguished by "Typ". Only the repository
# adapter in integrations/sharepoint knows these names.
APPLICATIONS_LIST = ListSpec(
    name="Antraege",
    columns=(
        ListColumn(name="AntragId", type=ColumnType.TEXT, required=True, indexed=True, unique=True),
        ListColumn(name="Typ", type=ColumnType.TEXT, required=True, indexed=True),
        ListColumn(
            name="Status",
            type=ColumnType.CHOICE,
            required=True,
            indexed=True,
            choices=tuple(status.value for status in ApplicationStatus),
        ),
        ListColumn(name="AntragstellerEntraId", type=ColumnType.TEXT, required=True, indexed=True),
        ListColumn(name="FreigeberEntraId", type=ColumnType.TEXT),
        ListColumn(name="ErstelltAm", type=ColumnType.DATETIME, required=True),
        ListColumn(name="EingereichtAm", type=ColumnType.DATETIME),
        ListColumn(name="EntschiedenAm", type=ColumnType.DATETIME),
        ListColumn(name="Rueckfrage", type=ColumnType.NOTE),
        ListColumn(name="RueckfrageAm", type=ColumnType.DATETIME),
        ListColumn(name="RueckfrageAntwort", type=ColumnType.NOTE),
        ListColumn(name="Begruendung", type=ColumnType.NOTE),
        # Certificate applications
        ListColumn(name="Von", type=ColumnType.DATE),
        ListColumn(name="Bis", type=ColumnType.DATE),
        ListColumn(name="Zweck", type=ColumnType.TEXT),
        ListColumn(name="AktivitaetIds", type=ColumnType.NOTE),
        # Data change applications
        ListColumn(name="Feld", type=ColumnType.TEXT),
        ListColumn(name="NeuerWert", type=ColumnType.TEXT),
    ),
)


class ListMyApplicationsInput(ToolInput):
    status: ApplicationStatus | None = None


class ApplicationRef(ToolInput):
    application_id: UUID


class AnswerClarificationInput(ToolInput):
    application_id: UUID
    answer: str = Field(min_length=1, max_length=2000)


class ListOpenApplicationsInput(ToolInput):
    kind: ApplicationKind | None = Field(default=None, pattern=r"^[a-z][a-z0-9_]*$")


class RejectApplicationInput(ToolInput):
    application_id: UUID
    reason: str = Field(min_length=1, max_length=2000)


class RequestClarificationInput(ToolInput):
    application_id: UUID
    question: str = Field(min_length=1, max_length=2000)


class ApproveAllOpenInput(ToolInput):
    kind: ApplicationKind | None = Field(default=None, pattern=r"^[a-z][a-z0-9_]*$")


# TODO(core): implement the handlers against ports.applications.ApplicationRepository,
# using domain.applications for every transition and writing an audit entry per commit.


async def list_my_applications(context: ToolContext, params: ListMyApplicationsInput) -> ToolResult:
    raise NotImplementedError("list_my_applications")


async def submit_application(context: ToolContext, params: ApplicationRef) -> ToolResult:
    raise NotImplementedError("submit_application")


async def discard_draft(context: ToolContext, params: ApplicationRef) -> ToolResult:
    raise NotImplementedError("discard_draft")


async def answer_clarification(
    context: ToolContext, params: AnswerClarificationInput
) -> ToolResult:
    raise NotImplementedError("answer_clarification")


async def list_open_applications(
    context: ToolContext, params: ListOpenApplicationsInput
) -> ToolResult:
    raise NotImplementedError("list_open_applications")


async def get_application(context: ToolContext, params: ApplicationRef) -> ToolResult:
    raise NotImplementedError("get_application")


async def approve_application(context: ToolContext, params: ApplicationRef) -> ToolResult:
    raise NotImplementedError("approve_application")


async def reject_application(context: ToolContext, params: RejectApplicationInput) -> ToolResult:
    raise NotImplementedError("reject_application")


async def request_clarification(
    context: ToolContext, params: RequestClarificationInput
) -> ToolResult:
    raise NotImplementedError("request_clarification")


async def approve_all_open(context: ToolContext, params: ApproveAllOpenInput) -> ToolResult:
    raise NotImplementedError("approve_all_open")


manifest = ModuleManifest(
    name="core",
    version="0.1.0",
    required_roles=(
        RoleSlot(name=BASE_SLOT, default=DefaultRole.LOWEST, privileged=False),
        RoleSlot(name=APPROVER_SLOT, default=DefaultRole.HIGHEST, setting="approver_role"),
    ),
    config_model=CoreSettings,
    locale_package="campus_agent_core",
    prompt_fragments=("prompt.applications",),
    lists=(APPLICATIONS_LIST,),
    tools=(
        ToolSpec(
            name="list_my_applications",
            tool_class=ToolClass.READ,
            min_role=BASE_SLOT,
            input_model=ListMyApplicationsInput,
            handler=list_my_applications,
        ),
        ToolSpec(
            name="submit_application",
            tool_class=ToolClass.COMMIT,
            min_role=BASE_SLOT,
            input_model=ApplicationRef,
            handler=submit_application,
        ),
        ToolSpec(
            name="discard_draft",
            tool_class=ToolClass.COMMIT,
            min_role=BASE_SLOT,
            input_model=ApplicationRef,
            handler=discard_draft,
        ),
        ToolSpec(
            name="answer_clarification",
            tool_class=ToolClass.COMMIT,
            min_role=BASE_SLOT,
            input_model=AnswerClarificationInput,
            handler=answer_clarification,
        ),
        ToolSpec(
            name="list_open_applications",
            tool_class=ToolClass.READ,
            min_role=APPROVER_SLOT,
            input_model=ListOpenApplicationsInput,
            handler=list_open_applications,
        ),
        ToolSpec(
            name="get_application",
            tool_class=ToolClass.READ,
            min_role=APPROVER_SLOT,
            input_model=ApplicationRef,
            handler=get_application,
        ),
        ToolSpec(
            name="approve_application",
            tool_class=ToolClass.COMMIT,
            min_role=APPROVER_SLOT,
            input_model=ApplicationRef,
            handler=approve_application,
        ),
        ToolSpec(
            name="reject_application",
            tool_class=ToolClass.COMMIT,
            min_role=APPROVER_SLOT,
            input_model=RejectApplicationInput,
            handler=reject_application,
        ),
        ToolSpec(
            name="request_clarification",
            tool_class=ToolClass.COMMIT,
            min_role=APPROVER_SLOT,
            input_model=RequestClarificationInput,
            handler=request_clarification,
        ),
        ToolSpec(
            name="approve_all_open",
            tool_class=ToolClass.COMMIT,
            min_role=APPROVER_SLOT,
            input_model=ApproveAllOpenInput,
            handler=approve_all_open,
        ),
    ),
)
