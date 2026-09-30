"""In-memory runtime store with the semantics of Azure Table Storage."""

from __future__ import annotations

import copy

from campus_agent_core.errors import ConflictError
from campus_agent_core.ports.storage import Entity


class InMemoryStorage:
    """Implements ``RuntimeStore``. Entities are deep-copied on the way in and out."""

    def __init__(self) -> None:
        self._tables: dict[str, dict[tuple[str, str], Entity]] = {}

    def _table(self, table: str) -> dict[tuple[str, str], Entity]:
        return self._tables.setdefault(table, {})

    async def get(self, table: str, partition_key: str, row_key: str) -> Entity | None:
        entity = self._table(table).get((partition_key, row_key))
        return copy.deepcopy(entity)

    async def insert(self, table: str, partition_key: str, row_key: str, entity: Entity) -> None:
        rows = self._table(table)
        if (partition_key, row_key) in rows:
            raise ConflictError(
                "entity already exists", table=table, partition_key=partition_key, row_key=row_key
            )
        rows[(partition_key, row_key)] = copy.deepcopy(entity)

    async def upsert(self, table: str, partition_key: str, row_key: str, entity: Entity) -> None:
        self._table(table)[(partition_key, row_key)] = copy.deepcopy(entity)

    async def delete(self, table: str, partition_key: str, row_key: str) -> None:
        self._table(table).pop((partition_key, row_key), None)

    async def list_partition(self, table: str, partition_key: str) -> list[Entity]:
        rows = self._table(table)
        return [
            copy.deepcopy(entity)
            for (partition, _), entity in sorted(rows.items())
            if partition == partition_key
        ]
