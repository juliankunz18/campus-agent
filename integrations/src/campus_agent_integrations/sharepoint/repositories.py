"""Repositories on SharePoint lists: the only code that knows list and column names."""

from __future__ import annotations

from uuid import UUID

from msgraph.graph_service_client import GraphServiceClient

from campus_agent_core.domain.applications import Application, ApplicationStatus

APPLICATIONS_LIST = "Antraege"


class SharePointApplicationRepository:
    """Implements ``ApplicationRepository`` on the ``Antraege`` list."""

    def __init__(self, graph: GraphServiceClient, site_id: str) -> None:
        self._graph = graph
        self._site_id = site_id

    # TODO(sharepoint): map Application to list item fields (AntragId, Typ, Status, ...),
    #   query by the indexed columns and use the item ETag for the optimistic
    #   expected_status check (ConflictError on mismatch). Map Graph errors to
    #   UpstreamError.

    async def get(self, application_id: UUID) -> Application | None:
        raise NotImplementedError

    async def add(self, application: Application) -> None:
        raise NotImplementedError

    async def save(self, application: Application, *, expected_status: ApplicationStatus) -> None:
        raise NotImplementedError

    async def delete(self, application_id: UUID) -> None:
        raise NotImplementedError

    async def list_for_applicant(self, applicant_id: str) -> list[Application]:
        raise NotImplementedError

    async def list_by_status(self, status: ApplicationStatus) -> list[Application]:
        raise NotImplementedError
