"""Role resolution from Entra group membership, cached for a short time."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime, timedelta

from msgraph.graph_service_client import GraphServiceClient

from campus_agent_core.config import CampusAgentConfig


def _utc_now() -> datetime:
    return datetime.now(UTC)


class TTLCache[K, V]:
    """Tiny time-based cache (the role cache keeps entries for 5 minutes by default)."""

    def __init__(self, ttl: timedelta, clock: Callable[[], datetime] = _utc_now) -> None:
        self._ttl = ttl
        self._clock = clock
        self._items: dict[K, tuple[datetime, V]] = {}

    def get(self, key: K) -> V | None:
        item = self._items.get(key)
        if item is None:
            return None
        stored_at, value = item
        if self._clock() - stored_at >= self._ttl:
            del self._items[key]
            return None
        return value

    def put(self, key: K, value: V) -> None:
        self._items[key] = (self._clock(), value)

    async def get_or_load(self, key: K, load: Callable[[], Awaitable[V]]) -> V:
        cached = self.get(key)
        if cached is not None:
            return cached
        value = await load()
        self.put(key, value)
        return value


class EntraRoleResolver:
    """Implements ``RoleResolver``: the server derives the role, never the model."""

    def __init__(
        self,
        graph: GraphServiceClient,
        config: CampusAgentConfig,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        self._graph = graph
        self._config = config
        self._cache: TTLCache[str, str] = TTLCache(config.agent.role_cache_ttl, clock)

    async def resolve_role(self, user_id: str) -> str:
        return await self._cache.get_or_load(user_id, lambda: self._load(user_id))

    async def _load(self, user_id: str) -> str:
        return self._config.role_for_groups(await self._group_ids(user_id))

    async def _group_ids(self, user_id: str) -> list[str]:
        # TODO(sharepoint): check membership of the configured entra_group IDs with the
        #   Graph checkMemberGroups action for the user and map Graph errors to
        #   UpstreamError. Verify the msgraph-sdk request builder and body model first.
        raise NotImplementedError("Entra group lookup is not implemented yet")
