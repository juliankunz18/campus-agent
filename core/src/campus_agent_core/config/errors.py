"""Configuration errors with one readable line per problem."""

from __future__ import annotations

from collections.abc import Sequence


class ConfigError(Exception):
    """The configuration is invalid. ``issues`` lists every problem as ``path: message``."""

    def __init__(self, source: str, issues: Sequence[str]) -> None:
        self.source = source
        self.issues: tuple[str, ...] = tuple(issues)
        lines = "\n".join(f"  - {issue}" for issue in self.issues)
        super().__init__(f"invalid configuration in {source}:\n{lines}")


def format_location(location: Sequence[str | int]) -> str:
    """Render a location like ``("roles", 1, "entra_group")`` as ``roles[1].entra_group``."""
    path = ""
    for part in location:
        if isinstance(part, int):
            path += f"[{part}]"
        else:
            path += f".{part}" if path else part
    return path or "<root>"
