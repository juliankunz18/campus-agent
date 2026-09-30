"""Port for resolving roles from the identity provider (Entra ID groups)."""

from __future__ import annotations

from typing import Protocol


class RoleResolver(Protocol):
    async def resolve_role(self, user_id: str) -> str:
        """Return the highest configured role ID of the user.

        Implementations cache results (see ``AgentLimits.role_cache_ttl``). The role is
        never stored with the member record; it is derived on every request.
        """
        ...
