from datetime import UTC, datetime, timedelta
from itertools import count
from uuid import uuid4

import pytest

from campus_agent_core.agent import ExecuteNow, PendingAction, PendingActionStore, ToolPolicy
from campus_agent_core.domain.user import UserContext
from campus_agent_core.errors import (
    ConflictError,
    ErrorCode,
    ForbiddenError,
    InvalidStateError,
    NotFoundError,
    ValidationFailedError,
)
from campus_agent_core.modules import ToolRegistry
from campus_agent_core.ports.llm import ToolCall
from campus_agent_core.ports.storage import RuntimeStore

NOW = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)
APPLICATION = str(uuid4())


def call(name: str, **arguments: object) -> ToolCall:
    return ToolCall(id="call-1", name=name, arguments=arguments)  # type: ignore[arg-type]


@pytest.fixture
def policy(registry: ToolRegistry) -> ToolPolicy:
    keys = count(1)
    return ToolPolicy(registry, key_factory=lambda: f"idempotency-key-{next(keys):04d}")


class TestDecide:
    def test_read_tools_run_immediately(self, policy: ToolPolicy, member: UserContext):
        decision = policy.decide(call("list_my_applications"), member, now=NOW)

        assert decision == ExecuteNow(tool="list_my_applications", arguments={"status": None})

    def test_draft_tools_run_immediately(self, policy: ToolPolicy, member: UserContext):
        decision = policy.decide(call("create_note_draft", text="Hallo"), member, now=NOW)

        assert isinstance(decision, ExecuteNow)
        assert decision.arguments == {"text": "Hallo"}

    def test_commit_tools_become_pending_actions(self, policy: ToolPolicy, member: UserContext):
        decision = policy.decide(
            call("submit_application", application_id=APPLICATION), member, now=NOW
        )

        assert isinstance(decision, PendingAction)
        assert decision.tool == "submit_application"
        assert decision.arguments == {"application_id": APPLICATION}
        assert decision.user_id == member.user_id
        assert decision.idempotency_key == "idempotency-key-0001"
        assert decision.created_at == NOW
        assert decision.expires_at == NOW + timedelta(hours=24)

    def test_each_pending_action_gets_its_own_key(
        self, registry: ToolRegistry, member: UserContext
    ):
        policy = ToolPolicy(registry)
        request = call("submit_application", application_id=APPLICATION)

        first = policy.decide(request, member, now=NOW)
        second = policy.decide(request, member, now=NOW)

        assert isinstance(first, PendingAction)
        assert isinstance(second, PendingAction)
        assert first.idempotency_key != second.idempotency_key
        assert len(first.idempotency_key) >= 32

    def test_pending_ttl_is_configurable(self, registry: ToolRegistry, board: UserContext):
        policy = ToolPolicy(registry, pending_ttl=timedelta(hours=2))

        decision = policy.decide(call("approve_all_open"), board, now=NOW)

        assert isinstance(decision, PendingAction)
        assert decision.expires_at == NOW + timedelta(hours=2)

    def test_tools_above_the_role_are_forbidden(self, policy: ToolPolicy, member: UserContext):
        with pytest.raises(ForbiddenError):
            policy.decide(call("approve_application", application_id=APPLICATION), member, now=NOW)

    def test_unknown_tools_are_not_found(self, policy: ToolPolicy, board: UserContext):
        with pytest.raises(NotFoundError):
            policy.decide(call("drop_database"), board, now=NOW)

    def test_invalid_arguments(self, policy: ToolPolicy, member: UserContext):
        with pytest.raises(ValidationFailedError) as excinfo:
            policy.decide(call("submit_application", application_id="not-a-uuid"), member, now=NOW)

        assert excinfo.value.code is ErrorCode.VALIDATION
        assert excinfo.value.details["tool"] == "submit_application"

    @pytest.mark.parametrize("smuggled", ["user_id", "role", "applicant_id"])
    def test_identity_arguments_from_the_model_are_rejected(
        self, policy: ToolPolicy, member: UserContext, smuggled: str
    ):
        arguments = {"status": None, smuggled: "user-board"}

        with pytest.raises(ValidationFailedError):
            policy.decide(call("list_my_applications", **arguments), member, now=NOW)


class TestConfirm:
    def pending(self, policy: ToolPolicy, user: UserContext) -> PendingAction:
        decision = policy.decide(call("publish_note", text="Hallo"), user, now=NOW)
        assert isinstance(decision, PendingAction)
        return decision

    def test_confirmation_executes_with_the_idempotency_key(
        self, policy: ToolPolicy, team_lead: UserContext
    ):
        action = self.pending(policy, team_lead)

        execution = policy.confirm(action, team_lead, now=NOW + timedelta(hours=1))

        assert execution == ExecuteNow(
            tool="publish_note", arguments={"text": "Hallo"}, idempotency_key=action.idempotency_key
        )

    def test_other_users_cannot_confirm(
        self, policy: ToolPolicy, team_lead: UserContext, board: UserContext
    ):
        action = self.pending(policy, team_lead)

        with pytest.raises(NotFoundError):
            policy.confirm(action, board, now=NOW)

    def test_expired_after_24_hours(self, policy: ToolPolicy, team_lead: UserContext):
        action = self.pending(policy, team_lead)

        assert not action.is_expired(NOW + timedelta(hours=23, minutes=59))
        with pytest.raises(InvalidStateError, match="expired"):
            policy.confirm(action, team_lead, now=NOW + timedelta(hours=24))

    def test_role_is_checked_again(self, policy: ToolPolicy, team_lead: UserContext):
        action = self.pending(policy, team_lead)
        demoted = team_lead.model_copy(update={"role": "member"})

        with pytest.raises(ForbiddenError):
            policy.confirm(action, demoted, now=NOW)


class TestPendingActionStore:
    async def test_round_trip(
        self, policy: ToolPolicy, team_lead: UserContext, store: RuntimeStore
    ):
        pending_store = PendingActionStore(store)
        action = policy.decide(call("publish_note", text="Hallo"), team_lead, now=NOW)
        assert isinstance(action, PendingAction)

        await pending_store.save(action)

        assert await pending_store.get(team_lead.user_id, action.id) == action

    async def test_other_users_cannot_load(
        self, policy: ToolPolicy, team_lead: UserContext, store: RuntimeStore
    ):
        pending_store = PendingActionStore(store)
        action = policy.decide(call("publish_note", text="Hallo"), team_lead, now=NOW)
        assert isinstance(action, PendingAction)
        await pending_store.save(action)

        with pytest.raises(NotFoundError):
            await pending_store.get("user-other", action.id)

    async def test_actions_run_at_most_once(
        self, policy: ToolPolicy, team_lead: UserContext, store: RuntimeStore
    ):
        pending_store = PendingActionStore(store)
        action = policy.decide(call("publish_note", text="Hallo"), team_lead, now=NOW)
        assert isinstance(action, PendingAction)

        await pending_store.mark_executed(action, now=NOW)
        with pytest.raises(ConflictError, match="already executed"):
            await pending_store.mark_executed(action, now=NOW)
