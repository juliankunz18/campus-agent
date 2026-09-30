"""Port for persisting applications (SharePoint list in production)."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from campus_agent_core.domain.applications import Application, ApplicationStatus


class ApplicationRepository(Protocol):
    async def get(self, application_id: UUID) -> Application | None: ...

    async def add(self, application: Application) -> None: ...

    async def save(self, application: Application, *, expected_status: ApplicationStatus) -> None:
        """Persist a transition.

        Raises ``ConflictError`` if the stored status differs from ``expected_status``
        (the application was changed concurrently or the action already ran).
        """
        ...

    async def delete(self, application_id: UUID) -> None: ...

    async def list_for_applicant(self, applicant_id: str) -> list[Application]: ...

    async def list_by_status(self, status: ApplicationStatus) -> list[Application]: ...
