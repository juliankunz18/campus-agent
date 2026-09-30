"""Error codes shared by every campus-agent component.

The codes mirror the contract between the MCP server and the bot: the bot maps each
code to a fixed reaction (explain, say "not found", name the current state, ...).
"""

from __future__ import annotations

from enum import StrEnum


class ErrorCode(StrEnum):
    """Machine-readable error codes returned by tools and domain services."""

    FORBIDDEN = "FORBIDDEN"
    """Role is insufficient or the four-eyes principle would be violated."""

    NOT_FOUND = "NOT_FOUND"
    """Does not exist or belongs to someone else (never reveal which)."""

    INVALID_STATE = "INVALID_STATE"
    """Transition is not allowed in the current state."""

    VALIDATION = "VALIDATION"
    """Parameters are invalid; the model may correct them and retry."""

    CONFLICT = "CONFLICT"
    """Action was already executed or changed concurrently."""

    UPSTREAM = "UPSTREAM"
    """Graph, SharePoint or another upstream service is unavailable."""


class CampusAgentError(Exception):
    """Base error carrying an :class:`ErrorCode`.

    ``message`` is a technical English message for logs. User-facing texts are
    resolved from locale files by the caller using ``code``.
    """

    def __init__(self, code: ErrorCode, message: str, **details: object) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message
        self.details: dict[str, object] = details


class ForbiddenError(CampusAgentError):
    def __init__(self, message: str, **details: object) -> None:
        super().__init__(ErrorCode.FORBIDDEN, message, **details)


class NotFoundError(CampusAgentError):
    def __init__(self, message: str, **details: object) -> None:
        super().__init__(ErrorCode.NOT_FOUND, message, **details)


class InvalidStateError(CampusAgentError):
    def __init__(self, message: str, **details: object) -> None:
        super().__init__(ErrorCode.INVALID_STATE, message, **details)


class ValidationFailedError(CampusAgentError):
    def __init__(self, message: str, **details: object) -> None:
        super().__init__(ErrorCode.VALIDATION, message, **details)


class ConflictError(CampusAgentError):
    def __init__(self, message: str, **details: object) -> None:
        super().__init__(ErrorCode.CONFLICT, message, **details)


class UpstreamError(CampusAgentError):
    def __init__(self, message: str, **details: object) -> None:
        super().__init__(ErrorCode.UPSTREAM, message, **details)
