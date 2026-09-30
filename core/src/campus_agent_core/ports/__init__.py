"""Interfaces between the core, the modules and the concrete adapters.

Modules import only from this package. Adapters in ``campus_agent_integrations``
implement these protocols; tests use the fakes from the same package.
"""

from campus_agent_core.domain.user import UserContext
from campus_agent_core.errors import (
    CampusAgentError,
    ConflictError,
    ErrorCode,
    ForbiddenError,
    InvalidStateError,
    NotFoundError,
    UpstreamError,
    ValidationFailedError,
)
from campus_agent_core.ports.module import (
    APPROVER_SLOT,
    BASE_SLOT,
    ColumnType,
    DefaultRole,
    ListColumn,
    ListKind,
    ListSpec,
    ModuleManifest,
    RoleRef,
    RoleSlot,
    ToolClass,
    ToolContext,
    ToolHandler,
    ToolInput,
    ToolResult,
    ToolSpec,
)

__all__ = [
    "APPROVER_SLOT",
    "BASE_SLOT",
    "CampusAgentError",
    "ColumnType",
    "ConflictError",
    "DefaultRole",
    "ErrorCode",
    "ForbiddenError",
    "InvalidStateError",
    "ListColumn",
    "ListKind",
    "ListSpec",
    "ModuleManifest",
    "NotFoundError",
    "RoleRef",
    "RoleSlot",
    "ToolClass",
    "ToolContext",
    "ToolHandler",
    "ToolInput",
    "ToolResult",
    "ToolSpec",
    "UpstreamError",
    "UserContext",
    "ValidationFailedError",
]
