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
    ColumnType,
    ListColumn,
    ListKind,
    ListSpec,
    ModuleManifest,
    RoleRef,
    ToolClass,
    ToolContext,
    ToolHandler,
    ToolInput,
    ToolResult,
    ToolSpec,
)

__all__ = [
    "CampusAgentError",
    "ColumnType",
    "ConflictError",
    "ErrorCode",
    "ForbiddenError",
    "InvalidStateError",
    "ListColumn",
    "ListKind",
    "ListSpec",
    "ModuleManifest",
    "NotFoundError",
    "RoleRef",
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
