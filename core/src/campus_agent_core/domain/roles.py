"""Roles with inheritance.

Roles are configured from lowest to highest (for example ``member < team_lead < board``).
A higher role inherits every permission of the roles below it. The role of a user is
always derived from the identity provider and never taken from the model.
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence

from campus_agent_core.errors import ForbiddenError

ROLE_ID_PATTERN = re.compile(r"^[a-z][a-z0-9_]*$")


class UnknownRoleError(ValueError):
    """A role ID that is not part of the configured hierarchy."""

    def __init__(self, role: str, known: Sequence[str]) -> None:
        super().__init__(f"unknown role {role!r}; configured roles: {', '.join(known)}")
        self.role = role


class RoleHierarchy:
    """Linear role hierarchy, lowest role first."""

    __slots__ = ("_ranks", "_roles")

    def __init__(self, role_ids: Sequence[str]) -> None:
        if not role_ids:
            raise ValueError("a role hierarchy needs at least one role")
        seen: set[str] = set()
        for role in role_ids:
            if not ROLE_ID_PATTERN.fullmatch(role):
                raise ValueError(f"invalid role id {role!r}: use lower snake_case")
            if role in seen:
                raise ValueError(f"duplicate role id {role!r}")
            seen.add(role)
        self._roles: tuple[str, ...] = tuple(role_ids)
        self._ranks: dict[str, int] = {role: rank for rank, role in enumerate(self._roles)}

    @property
    def roles(self) -> tuple[str, ...]:
        """All role IDs, lowest first."""
        return self._roles

    @property
    def lowest(self) -> str:
        return self._roles[0]

    @property
    def highest(self) -> str:
        return self._roles[-1]

    def __contains__(self, role: object) -> bool:
        return role in self._ranks

    def rank(self, role: str) -> int:
        try:
            return self._ranks[role]
        except KeyError:
            raise UnknownRoleError(role, self._roles) from None

    def includes(self, granted: str, required: str) -> bool:
        """Whether ``granted`` is ``required`` or inherits from it."""
        return self.rank(granted) >= self.rank(required)

    def inherited_roles(self, role: str) -> tuple[str, ...]:
        """The role itself and every role it inherits from, lowest first."""
        return self._roles[: self.rank(role) + 1]

    def highest_of(self, roles: Iterable[str]) -> str | None:
        """Pick the highest known role, ignoring unknown IDs. ``None`` if none is known."""
        known = [role for role in roles if role in self._ranks]
        if not known:
            return None
        return max(known, key=self._ranks.__getitem__)

    def ensure_permitted(self, granted: str, required: str, *, action: str) -> None:
        """Raise ``FORBIDDEN`` unless ``granted`` includes ``required``."""
        if not self.includes(granted, required):
            raise ForbiddenError(
                f"role {granted!r} may not perform {action!r}; requires {required!r}",
                action=action,
                required_role=required,
            )

    def __repr__(self) -> str:
        return f"RoleHierarchy({' < '.join(self._roles)})"
