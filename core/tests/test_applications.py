from datetime import UTC, datetime, timedelta
from itertools import product

import pytest
from pydantic import ValidationError

from campus_agent_core.domain import applications as wf
from campus_agent_core.domain.applications import (
    FINAL_STATES,
    TRANSITIONS,
    Application,
    ApplicationStatus,
    Transition,
)
from campus_agent_core.errors import (
    ErrorCode,
    ForbiddenError,
    InvalidStateError,
    NotFoundError,
    ValidationFailedError,
)

NOW = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
APPLICANT = "member-anna"
BOARD_A = "board-berta"
BOARD_B = "board-carl"

S = ApplicationStatus
T = Transition

# The state diagram, written out independently of the implementation.
EXPECTED_TRANSITIONS: dict[tuple[ApplicationStatus, Transition], ApplicationStatus | None] = {
    (S.DRAFT, T.SUBMIT): S.SUBMITTED,
    (S.DRAFT, T.DISCARD): None,
    (S.SUBMITTED, T.REQUEST_CLARIFICATION): S.CLARIFICATION,
    (S.SUBMITTED, T.APPROVE): S.APPROVED,
    (S.SUBMITTED, T.REJECT): S.REJECTED,
    (S.CLARIFICATION, T.ANSWER_CLARIFICATION): S.SUBMITTED,
    (S.CLARIFICATION, T.EXPIRE_CLARIFICATION): S.REJECTED,
}


def make(status: ApplicationStatus = S.DRAFT, **update: object) -> Application:
    application = wf.new_draft(kind="certificate", applicant_id=APPLICANT, now=NOW)
    return application.model_copy(update={"status": status, **update})


def test_transition_table_matches_state_diagram():
    assert dict(TRANSITIONS) == EXPECTED_TRANSITIONS


@pytest.mark.parametrize(("status", "transition"), list(product(S, T)))
def test_every_state_transition_pair(status: ApplicationStatus, transition: Transition):
    key = (status, transition)
    if key in EXPECTED_TRANSITIONS:
        assert wf.target_state(status, transition) == EXPECTED_TRANSITIONS[key]
    else:
        with pytest.raises(InvalidStateError) as excinfo:
            wf.target_state(status, transition)
        assert excinfo.value.code is ErrorCode.INVALID_STATE
        assert excinfo.value.details["current_status"] == status.value


@pytest.mark.parametrize("status", sorted(FINAL_STATES))
@pytest.mark.parametrize("transition", list(T))
def test_final_states_allow_no_transition(status: ApplicationStatus, transition: Transition):
    with pytest.raises(InvalidStateError):
        wf.target_state(status, transition)


def test_happy_path_submit_and_approve():
    draft = wf.new_draft(
        kind="certificate", applicant_id=APPLICANT, now=NOW, payload={"purpose": "Bewerbung"}
    )
    assert draft.status is S.DRAFT

    submitted = wf.submit(draft, actor_id=APPLICANT, now=NOW)
    assert submitted.status is S.SUBMITTED
    assert submitted.submitted_at == NOW

    approved = wf.approve(submitted, approver_id=BOARD_A, now=NOW)
    assert approved.status is S.APPROVED
    assert approved.approver_id == BOARD_A
    assert approved.decided_at == NOW
    assert approved.is_final
    assert draft.status is S.DRAFT, "transitions must not mutate the input"


def test_clarification_round_trip_then_reject():
    submitted = make(S.SUBMITTED)

    asked = wf.request_clarification(
        submitted, actor_id=BOARD_A, question=" Welcher Zeitraum? ", now=NOW
    )
    assert asked.status is S.CLARIFICATION
    assert asked.clarification_question == "Welcher Zeitraum?"
    assert asked.clarification_asked_at == NOW

    answered = wf.answer_clarification(asked, actor_id=APPLICANT, answer="SoSe 26", now=NOW)
    assert answered.status is S.SUBMITTED
    assert answered.clarification_answer == "SoSe 26"

    rejected = wf.reject(answered, approver_id=BOARD_B, reason="Keine Aktivitäten", now=NOW)
    assert rejected.status is S.REJECTED
    assert rejected.rejection_reason == "Keine Aktivitäten"
    assert rejected.is_final


def test_discard_only_drafts():
    wf.discard(make(S.DRAFT), actor_id=APPLICANT)

    with pytest.raises(InvalidStateError):
        wf.discard(make(S.SUBMITTED), actor_id=APPLICANT)


@pytest.mark.parametrize(
    "action",
    [
        lambda app: wf.submit(app, actor_id=BOARD_A, now=NOW),
        lambda app: wf.discard(app, actor_id=BOARD_A),
    ],
)
def test_only_the_applicant_may_submit_or_discard(action):
    with pytest.raises(NotFoundError) as excinfo:
        action(make(S.DRAFT))
    assert excinfo.value.code is ErrorCode.NOT_FOUND


def test_only_the_applicant_may_answer_a_clarification():
    with pytest.raises(NotFoundError):
        wf.answer_clarification(make(S.CLARIFICATION), actor_id=BOARD_A, answer="x", now=NOW)


class TestFourEyes:
    def test_applicant_cannot_approve_own_application(self):
        with pytest.raises(ForbiddenError) as excinfo:
            wf.approve(make(S.SUBMITTED), approver_id=APPLICANT, now=NOW)
        assert excinfo.value.code is ErrorCode.FORBIDDEN

    def test_applicant_cannot_reject_own_application(self):
        with pytest.raises(ForbiddenError):
            wf.reject(make(S.SUBMITTED), approver_id=APPLICANT, reason="x", now=NOW)

    def test_applicant_cannot_request_clarification_on_own_application(self):
        with pytest.raises(ForbiddenError):
            wf.request_clarification(make(S.SUBMITTED), actor_id=APPLICANT, question="x", now=NOW)

    @pytest.mark.parametrize("status", list(S))
    def test_four_eyes_is_checked_in_every_state(self, status: ApplicationStatus):
        with pytest.raises(ForbiddenError):
            wf.approve(make(status), approver_id=APPLICANT, now=NOW)

    def test_board_member_as_applicant_needs_another_board_member(self):
        own = wf.new_draft(kind="certificate", applicant_id=BOARD_A, now=NOW)
        submitted = wf.submit(own, actor_id=BOARD_A, now=NOW)

        with pytest.raises(ForbiddenError):
            wf.approve(submitted, approver_id=BOARD_A, now=NOW)
        assert wf.approve(submitted, approver_id=BOARD_B, now=NOW).status is S.APPROVED


@pytest.mark.parametrize("status", [S.DRAFT, S.CLARIFICATION, S.APPROVED, S.REJECTED])
def test_approve_requires_submitted(status: ApplicationStatus):
    with pytest.raises(InvalidStateError):
        wf.approve(make(status), approver_id=BOARD_A, now=NOW)


@pytest.mark.parametrize(
    "action",
    [
        lambda app: wf.reject(app, approver_id=BOARD_A, reason="  ", now=NOW),
        lambda app: wf.request_clarification(app, actor_id=BOARD_A, question="", now=NOW),
    ],
)
def test_empty_texts_are_rejected(action):
    with pytest.raises(ValidationFailedError):
        action(make(S.SUBMITTED))


class TestClarificationDeadline:
    def asked(self, days_ago: float) -> Application:
        return make(
            S.CLARIFICATION,
            clarification_question="?",
            clarification_asked_at=NOW - timedelta(days=days_ago),
        )

    def test_expires_after_30_days(self):
        application = self.asked(30)

        assert wf.is_clarification_overdue(application, now=NOW)
        expired = wf.expire_clarification(application, now=NOW)
        assert expired.status is S.REJECTED
        assert expired.decided_by_system
        assert expired.approver_id is None

    def test_not_before_deadline(self):
        application = self.asked(29.9)

        assert not wf.is_clarification_overdue(application, now=NOW)
        with pytest.raises(InvalidStateError, match="deadline"):
            wf.expire_clarification(application, now=NOW)

    def test_deadline_is_configurable(self):
        application = self.asked(8)

        expired = wf.expire_clarification(application, now=NOW, deadline=timedelta(days=7))
        assert expired.status is S.REJECTED

    def test_only_in_clarification(self):
        with pytest.raises(InvalidStateError):
            wf.expire_clarification(make(S.SUBMITTED), now=NOW)


def test_bulk_approval_skips_own_and_non_submitted_applications():
    foreign = [make(S.SUBMITTED, applicant_id=f"member-{i}") for i in range(3)]
    own = make(S.SUBMITTED, applicant_id=BOARD_A)
    draft = make(S.DRAFT, applicant_id="member-x")
    clarification = make(S.CLARIFICATION, applicant_id="member-y")

    result = wf.approve_all([*foreign, own, draft, clarification], approver_id=BOARD_A, now=NOW)

    assert [a.id for a in result.approved] == [a.id for a in foreign]
    assert all(a.status is S.APPROVED and a.approver_id == BOARD_A for a in result.approved)
    assert result.skipped_own == (own.id,)
    assert set(result.skipped_not_submitted) == {draft.id, clarification.id}


def test_bulk_approval_with_nothing_to_do():
    result = wf.approve_all([], approver_id=BOARD_A, now=NOW)

    assert result.approved == ()
    assert result.skipped_own == ()


def test_timestamps_must_be_timezone_aware():
    with pytest.raises(ValidationError):
        wf.new_draft(kind="certificate", applicant_id=APPLICANT, now=datetime(2026, 1, 1))  # noqa: DTZ001


def test_kind_must_be_snake_case():
    with pytest.raises(ValidationError):
        wf.new_draft(kind="Data Change", applicant_id=APPLICANT, now=NOW)
