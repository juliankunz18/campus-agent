"""Map the role slots of a module to the roles configured by a group (ADR 0019)."""

from __future__ import annotations

from collections.abc import Mapping

from pydantic import JsonValue

from campus_agent_core.domain.roles import RoleHierarchy
from campus_agent_core.ports.module import DefaultRole, ModuleManifest, RoleSlot


def resolve_slots(
    manifest: ModuleManifest,
    settings: Mapping[str, JsonValue],
    roles: RoleHierarchy,
    inherited: Mapping[str, str],
) -> tuple[dict[str, str], list[str]]:
    """Return ``{slot: role_id}`` for the module's own slots plus ``inherited`` slots
    (the core slots), and a list of problems.

    Order of precedence: explicit setting, then ``default`` or ``inherits``. A
    privileged slot must never resolve to the lowest role.
    """
    own = {slot.name: slot for slot in manifest.required_roles}
    resolved: dict[str, str] = dict(inherited)
    issues: list[str] = []
    visiting: set[str] = set()

    def resolve(name: str) -> str | None:
        if name in resolved:
            return resolved[name]
        if name not in own:
            issues.append(f"role slot {name!r} is not available")
            return None
        slot = own[name]
        if name in visiting:
            issues.append(f"role slot {name!r}: cycle in 'inherits'")
            return None
        visiting.add(name)
        role = _explicit(slot, settings, roles, issues)
        if role is None and slot.default is not None:
            role = _positional(slot.default, roles)
        elif role is None and slot.inherits is not None:
            role = resolve(slot.inherits)
        visiting.discard(name)
        if role is None:
            return None
        if slot.privileged and role == roles.lowest:
            where = slot.setting or f"role slot {slot.name!r}"
            issues.append(
                f"{where}: {role!r} is the lowest role, but {slot.name!r} is a privileged "
                "role slot (it sees other people's data or acts for them); choose a higher role"
            )
        resolved[name] = role
        return role

    for name in own:
        resolve(name)
    return resolved, issues


def _explicit(
    slot: RoleSlot, settings: Mapping[str, JsonValue], roles: RoleHierarchy, issues: list[str]
) -> str | None:
    if slot.setting is None:
        return None
    value = settings.get(slot.setting)
    if value is None:
        return None
    if not isinstance(value, str) or value not in roles:
        known = ", ".join(roles.roles)
        issues.append(f"{slot.setting}: unknown role {value!r}; configured roles: {known}")
        return None
    return value


def _positional(default: DefaultRole, roles: RoleHierarchy) -> str:
    match default:
        case DefaultRole.LOWEST:
            return roles.lowest
        case DefaultRole.HIGHEST:
            return roles.highest
        case DefaultRole.ABOVE_LOWEST:
            return roles.roles[min(1, len(roles.roles) - 1)]
