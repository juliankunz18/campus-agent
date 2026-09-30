"""The module interface: what a module declares and how its tools are called.

A module is a Python package registered under the entry point group
``campus_agent.modules``. The entry point points to a :class:`ModuleManifest` (or a
zero-argument callable returning one). Modules import only from
``campus_agent_core.ports``; they never import adapters.
"""

from __future__ import annotations

import re
from collections.abc import Awaitable, Callable, Mapping
from enum import StrEnum
from typing import Annotated, Any, Self, cast

from pydantic import (
    AfterValidator,
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    JsonValue,
    ValidationInfo,
    field_validator,
    model_validator,
)

from campus_agent_core.domain.user import UserContext

SNAKE_CASE = re.compile(r"^[a-z][a-z0-9_]*$")
SHAREPOINT_NAME = re.compile(r"^[A-Za-z][A-Za-z0-9]*$")
SEMVER = re.compile(r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$")

# Parameter names that would let the model choose whose identity or role a tool uses.
# The caller always comes from the verified request (ToolContext.user).
FORBIDDEN_PARAMETER_NAMES = frozenset(
    {
        "user",
        "user_id",
        "userid",
        "caller",
        "caller_id",
        "actor",
        "actor_id",
        "acting_user",
        "as_user",
        "on_behalf_of",
        "requester_id",
        "applicant_id",
        "approver_id",
        "entra_id",
        "entra_object_id",
        "role",
        "user_role",
    }
)


class ToolClass(StrEnum):
    """How the agent loop may run a tool (see ADR 0008)."""

    READ = "read"
    """Runs immediately inside the loop."""

    DRAFT = "draft"
    """Runs immediately but only creates a draft."""

    COMMIT = "commit"
    """Never runs from the model: becomes a pending action confirmed by a card click."""


class ToolInput(BaseModel):
    """Base class for tool input models. Unknown arguments are rejected."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class ToolContext(BaseModel):
    """Everything a handler may know about the call besides its validated input."""

    model_config = ConfigDict(frozen=True)

    user: UserContext
    now: AwareDatetime
    language: str = "de"
    module_config: dict[str, JsonValue] = Field(default_factory=dict[str, JsonValue])


class ToolResult(BaseModel):
    """Compact result: only the fields the use case needs, plus a short summary."""

    model_config = ConfigDict(frozen=True)

    summary: str = Field(description="Short sentence the model can use in its answer.")
    data: dict[str, JsonValue] = Field(default_factory=dict[str, JsonValue])


type ToolHandler = Callable[[ToolContext, Any], Awaitable[ToolResult]]
"""Async handler receiving the context and an instance of the tool's input model."""


class ToolSpec(BaseModel):
    """Declaration of one tool. Texts live in the module's locale files under
    ``tools.<name>.description`` and ``tools.<name>.params.<field>``."""

    model_config = ConfigDict(frozen=True, arbitrary_types_allowed=True)

    name: str = Field(description="English snake_case name.")
    tool_class: ToolClass
    min_role: str = Field(description="Lowest role allowed to use the tool.")
    input_model: type[ToolInput]
    handler: ToolHandler

    @field_validator("name", "min_role")
    @classmethod
    def _snake_case(cls, value: str) -> str:
        if not SNAKE_CASE.fullmatch(value):
            raise ValueError(f"{value!r} must be lower snake_case")
        return value

    @model_validator(mode="after")
    def _no_identity_parameters(self) -> Self:
        if self.input_model.model_config.get("extra") != "forbid":
            raise ValueError(f"input model of {self.name!r} must forbid extra fields")
        forbidden = sorted(FORBIDDEN_PARAMETER_NAMES & set(self.input_model.model_fields))
        if forbidden:
            raise ValueError(
                f"tool {self.name!r} must not take identity parameters: {', '.join(forbidden)}; "
                "the caller comes from the verified request"
            )
        return self

    @property
    def description_key(self) -> str:
        return f"tools.{self.name}.description"

    def parameter_key(self, field: str) -> str:
        return f"tools.{self.name}.params.{field}"


class ColumnType(StrEnum):
    TEXT = "text"
    NOTE = "note"
    NUMBER = "number"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    CHOICE = "choice"
    LOOKUP = "lookup"


class ListColumn(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str = Field(description="SharePoint internal name, e.g. 'EntraObjectId'.")
    type: ColumnType
    required: bool = False
    indexed: bool = False
    unique: bool = False
    choices: tuple[str, ...] = ()
    lookup_list: str | None = None

    @field_validator("name")
    @classmethod
    def _sharepoint_name(cls, value: str) -> str:
        if not SHAREPOINT_NAME.fullmatch(value):
            raise ValueError(f"column name {value!r} must be alphanumeric, starting with a letter")
        return value

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        if self.unique and not self.indexed:
            raise ValueError(f"unique column {self.name!r} must also be indexed")
        if (self.type is ColumnType.CHOICE) != bool(self.choices):
            raise ValueError(f"column {self.name!r}: 'choices' is required exactly for choice")
        if (self.type is ColumnType.LOOKUP) != (self.lookup_list is not None):
            raise ValueError(f"column {self.name!r}: 'lookup_list' is required exactly for lookup")
        return self


class ListKind(StrEnum):
    LIST = "list"
    LIBRARY = "library"


class ListSpec(BaseModel):
    """A SharePoint list or document library the module needs (``campus-agent provision``)."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    name: str
    kind: ListKind = ListKind.LIST
    columns: tuple[ListColumn, ...] = ()

    @field_validator("name")
    @classmethod
    def _sharepoint_name(cls, value: str) -> str:
        if not SHAREPOINT_NAME.fullmatch(value):
            raise ValueError(f"list name {value!r} must be alphanumeric, starting with a letter")
        return value

    @model_validator(mode="after")
    def _unique_columns(self) -> Self:
        names = [column.name for column in self.columns]
        duplicates = sorted({name for name in names if names.count(name) > 1})
        if duplicates:
            raise ValueError(f"list {self.name!r} has duplicate columns: {', '.join(duplicates)}")
        return self


class ModuleManifest(BaseModel):
    """Everything the framework needs to know about a module."""

    model_config = ConfigDict(frozen=True, extra="forbid", arbitrary_types_allowed=True)

    name: str
    version: str
    required_roles: tuple[str, ...] = Field(min_length=1)
    lists: tuple[ListSpec, ...] = ()
    tools: tuple[ToolSpec, ...] = ()
    prompt_fragments: tuple[str, ...] = Field(
        default=(), description="Locale keys added to the system prompt."
    )
    locale_package: str = Field(
        description="Importable package containing locales/<lang>/messages.yaml."
    )
    config_model: type[BaseModel] | None = Field(
        default=None, description="Validates this module's section under 'modules:'."
    )

    @field_validator("name")
    @classmethod
    def _snake_case(cls, value: str) -> str:
        if not SNAKE_CASE.fullmatch(value):
            raise ValueError(f"module name {value!r} must be lower snake_case")
        return value

    @field_validator("version")
    @classmethod
    def _semver(cls, value: str) -> str:
        if not SEMVER.fullmatch(value):
            raise ValueError(f"version {value!r} must follow semantic versioning")
        return value

    @model_validator(mode="after")
    def _consistent(self) -> Self:
        tool_names = [tool.name for tool in self.tools]
        duplicates = sorted({name for name in tool_names if tool_names.count(name) > 1})
        if duplicates:
            raise ValueError(f"duplicate tool names: {', '.join(duplicates)}")
        undeclared = sorted(
            {tool.min_role for tool in self.tools} - set(self.required_roles),
        )
        if undeclared:
            raise ValueError(
                f"tools use roles missing from required_roles: {', '.join(undeclared)}"
            )
        list_names = [spec.name for spec in self.lists]
        duplicate_lists = sorted({name for name in list_names if list_names.count(name) > 1})
        if duplicate_lists:
            raise ValueError(f"duplicate list names: {', '.join(duplicate_lists)}")
        return self


ROLES_CONTEXT_KEY = "roles"


def _known_role(value: str, info: ValidationInfo) -> str:
    # The module loader passes the configured role IDs as validation context.
    context = cast(Mapping[str, object] | None, info.context)
    roles = context.get(ROLES_CONTEXT_KEY) if context is not None else None
    if isinstance(roles, tuple):
        known = cast(tuple[str, ...], roles)
        if value not in known:
            raise ValueError(f"unknown role {value!r}; configured roles: {', '.join(known)}")
    return value


RoleRef = Annotated[str, AfterValidator(_known_role)]
"""A role ID in a module config model, checked against the configured roles."""
