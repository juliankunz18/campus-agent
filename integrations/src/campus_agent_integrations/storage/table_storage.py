"""Runtime state (history, pending actions, audit log) in Azure Table Storage.

Locally the same code runs against Azurite (see compose.yaml).
"""

from __future__ import annotations

from azure.data.tables.aio import TableServiceClient

from campus_agent_core.ports.storage import Entity


class TableStorage:
    """Implements ``RuntimeStore``."""

    def __init__(self, service: TableServiceClient) -> None:
        self._service = service

    # TODO(storage): implement with TableServiceClient.get_table_client(table) and the
    #   entity operations of azure-data-tables (create_entity raises ResourceExistsError
    #   -> ConflictError; get_entity raises ResourceNotFoundError -> None). Serialise
    #   nested JSON values to strings because table entities only hold flat properties.
    #   Authenticate with Managed Identity in Azure and the Azurite connection string
    #   locally.

    async def get(self, table: str, partition_key: str, row_key: str) -> Entity | None:
        raise NotImplementedError

    async def insert(self, table: str, partition_key: str, row_key: str, entity: Entity) -> None:
        raise NotImplementedError

    async def upsert(self, table: str, partition_key: str, row_key: str, entity: Entity) -> None:
        raise NotImplementedError

    async def delete(self, table: str, partition_key: str, row_key: str) -> None:
        raise NotImplementedError

    async def list_partition(self, table: str, partition_key: str) -> list[Entity]:
        raise NotImplementedError
