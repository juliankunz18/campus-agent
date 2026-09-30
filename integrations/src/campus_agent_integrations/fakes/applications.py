"""In-memory application repository for tests and the local example."""

from __future__ import annotations

from uuid import UUID

from campus_agent_core.domain.applications import Application, ApplicationStatus
from campus_agent_core.errors import ConflictError, NotFoundError


class InMemoryApplicationRepository:
    """Implements ``ApplicationRepository`` including the optimistic status check."""

    def __init__(self, applications: list[Application] | None = None) -> None:
        self._items: dict[UUID, Application] = {a.id: a for a in applications or []}

    async def get(self, application_id: UUID) -> Application | None:
        return self._items.get(application_id)

    async def add(self, application: Application) -> None:
        if application.id in self._items:
            raise ConflictError("application already exists", application_id=str(application.id))
        self._items[application.id] = application

    async def save(self, application: Application, *, expected_status: ApplicationStatus) -> None:
        stored = self._items.get(application.id)
        if stored is None:
            raise NotFoundError("application not found", application_id=str(application.id))
        if stored.status is not expected_status:
            raise ConflictError(
                "application was changed concurrently",
                application_id=str(application.id),
                current_status=stored.status.value,
            )
        self._items[application.id] = application

    async def delete(self, application_id: UUID) -> None:
        self._items.pop(application_id, None)

    async def list_for_applicant(self, applicant_id: str) -> list[Application]:
        return [a for a in self._items.values() if a.applicant_id == applicant_id]

    async def list_by_status(self, status: ApplicationStatus) -> list[Application]:
        return [a for a in self._items.values() if a.status is status]
