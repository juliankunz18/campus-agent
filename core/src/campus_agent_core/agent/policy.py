"""Tool policy of the agent loop (see ADR 0008).

``read`` and ``draft`` tools run inside the loop. ``commit`` tools never run on the
model's request: they become a :class:`PendingAction` with an idempotency key that is
executed only after the person confirms it on a card, without involving the model.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, JsonValue, ValidationError

from campus_agent_core.domain.user import UserContext
from campus_agent_core.errors import (
    ConflictError,
    InvalidStateError,
    NotFoundError,
    ValidationFailedError,
)
from campus_agent_core.modules.registry import ToolRegistry
from campus_agent_core.ports.llm import ToolCall
from campus_agent_core.ports.module import ToolClass
from campus_agent_core.ports.storage import RuntimeStore

DEFAULT_PENDING_TTL = timedelta(hours=24)


class ExecuteNow(BaseModel):
    """Run the tool immediately with validated arguments."""

    model_config = ConfigDict(frozen=True)

    tool: str
    arguments: dict[str, JsonValue]
    idempotency_key: str | None = None


class PendingAction(BaseModel):
    """A binding action waiting for confirmation on a card."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    idempotency_key: str = Field(min_length=16)
    tool: str
    arguments: dict[str, JsonValue]
    user_id: str
    created_at: AwareDatetime
    expires_at: AwareDatetime

    def is_expired(self, now: datetime) -> bool:
        return now >= self.expires_at


type Decision = ExecuteNow | PendingAction


def _new_key() -> str:
    return uuid4().hex


class ToolPolicy:
    def __init__(
        self,
        registry: ToolRegistry,
        *,
        pending_ttl: timedelta = DEFAULT_PENDING_TTL,
        key_factory: Callable[[], str] = _new_key,
    ) -> None:
        self._registry = registry
        self._pending_ttl = pending_ttl
        self._key_factory = key_factory

    def decide(self, call: ToolCall, user: UserContext, *, now: datetime) -> Decision:
        """Check role and arguments, then run now or defer to a confirmation card.

        Raises ``NOT_FOUND`` for unknown tools, ``FORBIDDEN`` for tools above the role
        and ``VALIDATION`` for invalid arguments (including any identity parameter).
        """
        tool = self._registry.ensure_allowed(user.role, call.name)
        try:
            params = tool.spec.input_model.model_validate(call.arguments)
        except ValidationError as error:
            raise ValidationFailedError(
                f"invalid arguments for {call.name!r}",
                tool=call.name,
                errors=[f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in error.errors()],
            ) from error
        arguments: dict[str, JsonValue] = params.model_dump(mode="json")

        if tool.tool_class in (ToolClass.READ, ToolClass.DRAFT):
            return ExecuteNow(tool=tool.name, arguments=arguments)
        return PendingAction(
            id=uuid4(),
            idempotency_key=self._key_factory(),
            tool=tool.name,
            arguments=arguments,
            user_id=user.user_id,
            created_at=now,
            expires_at=now + self._pending_ttl,
        )

    def confirm(self, action: PendingAction, user: UserContext, *, now: datetime) -> ExecuteNow:
        """Turn a confirmed pending action into an execution (card click, no model).

        The role is checked again because it may have changed since the proposal.
        """
        if action.user_id != user.user_id:
            raise NotFoundError("pending action not found", action_id=str(action.id))
        if action.is_expired(now):
            raise InvalidStateError("pending action has expired", action_id=str(action.id))
        tool = self._registry.ensure_allowed(user.role, action.tool)
        return ExecuteNow(
            tool=tool.name, arguments=action.arguments, idempotency_key=action.idempotency_key
        )


class PendingActionStore:
    """Persists pending actions and guarantees each runs at most once."""

    ACTIONS_TABLE = "PendingActions"
    EXECUTED_TABLE = "ExecutedActions"

    def __init__(self, store: RuntimeStore) -> None:
        self._store = store

    async def save(self, action: PendingAction) -> None:
        await self._store.insert(
            self.ACTIONS_TABLE, action.user_id, str(action.id), action.model_dump(mode="json")
        )

    async def get(self, user_id: str, action_id: UUID) -> PendingAction:
        """Only the proposing user can load an action; others get ``NOT_FOUND``."""
        entity = await self._store.get(self.ACTIONS_TABLE, user_id, str(action_id))
        if entity is None:
            raise NotFoundError("pending action not found", action_id=str(action_id))
        return PendingAction.model_validate(entity)

    async def mark_executed(self, action: PendingAction, *, now: datetime) -> None:
        """Claim the idempotency key. Raises ``CONFLICT`` if the action already ran."""
        try:
            await self._store.insert(
                self.EXECUTED_TABLE,
                action.user_id,
                action.idempotency_key,
                {"action_id": str(action.id), "executed_at": now.isoformat()},
            )
        except ConflictError:
            raise ConflictError("action was already executed", action_id=str(action.id)) from None
