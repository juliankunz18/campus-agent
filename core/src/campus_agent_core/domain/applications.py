"""Application workflow shared by all modules (certificates, data changes, ...).

State machine (see ADR 0010)::

    DRAFT --submit--> SUBMITTED --approve [four eyes]--> APPROVED (final)
    DRAFT --discard--> (deleted)      \\--reject [four eyes]--> REJECTED (final)
    SUBMITTED --request_clarification--> CLARIFICATION --answer--> SUBMITTED
    CLARIFICATION --after 30 days--> REJECTED

APPROVED and REJECTED are final: a decided application is never reopened, corrections
go through a new application. Role checks happen before these functions are called
(tool registry); this module enforces state, ownership and the four-eyes principle.
All functions are pure and return a new :class:`Application`.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from datetime import datetime, timedelta
from enum import StrEnum
from types import MappingProxyType
from typing import Final
from uuid import UUID, uuid4

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, JsonValue, field_validator

from campus_agent_core.errors import (
    ForbiddenError,
    InvalidStateError,
    NotFoundError,
    ValidationFailedError,
)

KIND_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")
DEFAULT_CLARIFICATION_DEADLINE: Final = timedelta(days=30)


class ApplicationStatus(StrEnum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    CLARIFICATION = "CLARIFICATION"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class Transition(StrEnum):
    SUBMIT = "submit"
    DISCARD = "discard"
    REQUEST_CLARIFICATION = "request_clarification"
    ANSWER_CLARIFICATION = "answer_clarification"
    APPROVE = "approve"
    REJECT = "reject"
    EXPIRE_CLARIFICATION = "expire_clarification"


FINAL_STATES: Final = frozenset({ApplicationStatus.APPROVED, ApplicationStatus.REJECTED})

TRANSITIONS: Final[Mapping[tuple[ApplicationStatus, Transition], ApplicationStatus | None]] = (
    MappingProxyType(
        {
            (ApplicationStatus.DRAFT, Transition.SUBMIT): ApplicationStatus.SUBMITTED,
            # Discarding leaves the state machine: the draft is deleted.
            (ApplicationStatus.DRAFT, Transition.DISCARD): None,
            (
                ApplicationStatus.SUBMITTED,
                Transition.REQUEST_CLARIFICATION,
            ): ApplicationStatus.CLARIFICATION,
            (ApplicationStatus.SUBMITTED, Transition.APPROVE): ApplicationStatus.APPROVED,
            (ApplicationStatus.SUBMITTED, Transition.REJECT): ApplicationStatus.REJECTED,
            (
                ApplicationStatus.CLARIFICATION,
                Transition.ANSWER_CLARIFICATION,
            ): ApplicationStatus.SUBMITTED,
            (
                ApplicationStatus.CLARIFICATION,
                Transition.EXPIRE_CLARIFICATION,
            ): ApplicationStatus.REJECTED,
        }
    )
)


def target_state(status: ApplicationStatus, transition: Transition) -> ApplicationStatus | None:
    """Return the state after ``transition`` or raise ``INVALID_STATE``.

    ``None`` means the application leaves the state machine (discarded draft).
    """
    key = (status, transition)
    if key not in TRANSITIONS:
        raise InvalidStateError(
            f"transition {transition.value!r} is not allowed in state {status.value}",
            current_status=status.value,
            transition=transition.value,
        )
    return TRANSITIONS[key]


class Application(BaseModel):
    """An application of any kind. Module-specific fields live in ``payload``."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    kind: str = Field(description="Application type, e.g. 'certificate' or 'data_change'.")
    applicant_id: str = Field(min_length=1)
    status: ApplicationStatus = ApplicationStatus.DRAFT
    created_at: AwareDatetime
    submitted_at: AwareDatetime | None = None
    decided_at: AwareDatetime | None = None
    approver_id: str | None = None
    decided_by_system: bool = False
    clarification_question: str | None = None
    clarification_asked_at: AwareDatetime | None = None
    clarification_answer: str | None = None
    rejection_reason: str | None = None
    payload: dict[str, JsonValue] = Field(default_factory=dict[str, JsonValue])

    @field_validator("kind")
    @classmethod
    def _check_kind(cls, value: str) -> str:
        if not KIND_PATTERN.fullmatch(value):
            raise ValueError("kind must be lower snake_case")
        return value

    @property
    def is_final(self) -> bool:
        return self.status in FINAL_STATES


def new_draft(
    *,
    kind: str,
    applicant_id: str,
    now: datetime,
    payload: Mapping[str, JsonValue] | None = None,
    application_id: UUID | None = None,
) -> Application:
    return Application(
        id=application_id or uuid4(),
        kind=kind,
        applicant_id=applicant_id,
        created_at=now,
        payload=dict(payload or {}),
    )


def submit(application: Application, *, actor_id: str, now: datetime) -> Application:
    _ensure_owner(application, actor_id)
    status = _require_target(application, Transition.SUBMIT)
    return application.model_copy(update={"status": status, "submitted_at": now})


def discard(application: Application, *, actor_id: str) -> None:
    """Validate that the draft may be discarded. The caller deletes the record."""
    _ensure_owner(application, actor_id)
    target_state(application.status, Transition.DISCARD)


def request_clarification(
    application: Application, *, actor_id: str, question: str, now: datetime
) -> Application:
    """Ask the applicant a question. Role checks (board) happen in the tool layer.

    The four-eyes rule applies here as well: applicants cannot send their own
    application into clarification.
    """
    _ensure_four_eyes(application, actor_id)
    question = _require_text(question, "question")
    status = _require_target(application, Transition.REQUEST_CLARIFICATION)
    return application.model_copy(
        update={
            "status": status,
            "clarification_question": question,
            "clarification_asked_at": now,
            "clarification_answer": None,
        }
    )


def answer_clarification(
    application: Application, *, actor_id: str, answer: str, now: datetime
) -> Application:
    _ensure_owner(application, actor_id)
    answer = _require_text(answer, "answer")
    status = _require_target(application, Transition.ANSWER_CLARIFICATION)
    return application.model_copy(
        update={"status": status, "clarification_answer": answer, "submitted_at": now}
    )


def approve(application: Application, *, approver_id: str, now: datetime) -> Application:
    _ensure_four_eyes(application, approver_id)
    status = _require_target(application, Transition.APPROVE)
    return application.model_copy(
        update={"status": status, "approver_id": approver_id, "decided_at": now}
    )


def reject(
    application: Application, *, approver_id: str, reason: str, now: datetime
) -> Application:
    _ensure_four_eyes(application, approver_id)
    reason = _require_text(reason, "reason")
    status = _require_target(application, Transition.REJECT)
    return application.model_copy(
        update={
            "status": status,
            "approver_id": approver_id,
            "rejection_reason": reason,
            "decided_at": now,
        }
    )


def is_clarification_overdue(
    application: Application,
    *,
    now: datetime,
    deadline: timedelta = DEFAULT_CLARIFICATION_DEADLINE,
) -> bool:
    return (
        application.status is ApplicationStatus.CLARIFICATION
        and application.clarification_asked_at is not None
        and now - application.clarification_asked_at >= deadline
    )


def expire_clarification(
    application: Application,
    *,
    now: datetime,
    deadline: timedelta = DEFAULT_CLARIFICATION_DEADLINE,
) -> Application:
    """Reject an application whose clarification stayed unanswered past the deadline."""
    status = _require_target(application, Transition.EXPIRE_CLARIFICATION)
    if not is_clarification_overdue(application, now=now, deadline=deadline):
        raise InvalidStateError(
            "clarification deadline has not passed yet",
            current_status=application.status.value,
            transition=Transition.EXPIRE_CLARIFICATION.value,
        )
    return application.model_copy(
        update={"status": status, "decided_at": now, "decided_by_system": True}
    )


class BulkApprovalResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    approved: tuple[Application, ...] = ()
    skipped_own: tuple[UUID, ...] = Field(
        default=(), description="The approver's own applications (four-eyes principle)."
    )
    skipped_not_submitted: tuple[UUID, ...] = ()


def approve_all(
    applications: Iterable[Application], *, approver_id: str, now: datetime
) -> BulkApprovalResult:
    """Approve every submitted application except the approver's own."""
    approved: list[Application] = []
    skipped_own: list[UUID] = []
    skipped_not_submitted: list[UUID] = []
    for application in applications:
        if application.applicant_id == approver_id:
            skipped_own.append(application.id)
        elif application.status is not ApplicationStatus.SUBMITTED:
            skipped_not_submitted.append(application.id)
        else:
            approved.append(approve(application, approver_id=approver_id, now=now))
    return BulkApprovalResult(
        approved=tuple(approved),
        skipped_own=tuple(skipped_own),
        skipped_not_submitted=tuple(skipped_not_submitted),
    )


def _require_target(application: Application, transition: Transition) -> ApplicationStatus:
    status = target_state(application.status, transition)
    if status is None:  # pragma: no cover - only DISCARD maps to None
        raise InvalidStateError(f"{transition.value} does not lead to a state")
    return status


def _ensure_owner(application: Application, actor_id: str) -> None:
    # NOT_FOUND instead of FORBIDDEN so that callers cannot probe foreign applications.
    if application.applicant_id != actor_id:
        raise NotFoundError("application not found", application_id=str(application.id))


def _ensure_four_eyes(application: Application, approver_id: str) -> None:
    # Checked before the state so that the rule holds regardless of the current status.
    if application.applicant_id == approver_id:
        raise ForbiddenError(
            "applicants may not decide their own application (four-eyes principle)",
            application_id=str(application.id),
        )


def _require_text(value: str, field: str) -> str:
    stripped = value.strip()
    if not stripped:
        raise ValidationFailedError(f"{field} must not be empty", field=field)
    return stripped
