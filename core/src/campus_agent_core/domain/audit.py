"""Audit records for every writing action."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class AuditOutcome(StrEnum):
    SUCCESS = "success"
    DENIED = "denied"
    FAILED = "failed"


class AuditEntry(BaseModel):
    """One audit log line. Contains IDs only, never personal field values."""

    model_config = ConfigDict(frozen=True)

    timestamp: datetime
    actor_id: str = Field(min_length=1)
    action: str = Field(min_length=1, description="Tool name or domain transition.")
    target_id: str | None = None
    outcome: AuditOutcome
    error_code: str | None = None
    prompt_version: str | None = Field(
        default=None, description="Version of the system prompt that led to the action."
    )
