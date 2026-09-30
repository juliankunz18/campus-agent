"""Port for technical runtime state (history, pending actions, audit log).

Business data lives in SharePoint behind repository ports; this store maps to Azure
Table Storage in production and to an in-memory fake in tests.
"""

from __future__ import annotations

from typing import Protocol

from pydantic import JsonValue

type Entity = dict[str, JsonValue]


class RuntimeStore(Protocol):
    async def get(self, table: str, partition_key: str, row_key: str) -> Entity | None:
        """Return the entity or ``None`` if it does not exist."""
        ...

    async def insert(self, table: str, partition_key: str, row_key: str, entity: Entity) -> None:
        """Insert a new entity. Raises ``ConflictError`` if the key already exists."""
        ...

    async def upsert(
        self, table: str, partition_key: str, row_key: str, entity: Entity
    ) -> None: ...

    async def delete(self, table: str, partition_key: str, row_key: str) -> None:
        """Delete the entity. Deleting a missing entity is not an error."""
        ...

    async def list_partition(self, table: str, partition_key: str) -> list[Entity]: ...
