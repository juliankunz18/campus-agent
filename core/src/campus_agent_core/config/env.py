"""``${VAR}`` substitution in configuration values.

Supported forms (only inside string values, never in keys):

* ``${VAR}`` - value of ``VAR``; missing variables are reported as errors
* ``${VAR:-default}`` - ``default`` if ``VAR`` is unset or empty
* ``$${VAR}`` - the literal text ``${VAR}``
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import cast

from campus_agent_core.config.errors import format_location

_PATTERN = re.compile(r"\$(\$)?\{([A-Za-z_][A-Za-z0-9_]*)(?::-([^}]*))?\}")


def substitute_env(value: object, env: Mapping[str, str]) -> tuple[object, list[str]]:
    """Return ``value`` with variables replaced, plus a list of problems."""
    issues: list[str] = []
    result = _walk(value, env, [], issues)
    return result, issues


def _walk(
    value: object, env: Mapping[str, str], path: list[str | int], issues: list[str]
) -> object:
    if isinstance(value, str):
        return _substitute(value, env, path, issues)
    if isinstance(value, dict):
        mapping = cast(dict[object, object], value)
        return {key: _walk(item, env, [*path, str(key)], issues) for key, item in mapping.items()}
    if isinstance(value, list):
        items = cast(list[object], value)
        return [_walk(item, env, [*path, index], issues) for index, item in enumerate(items)]
    return value


def _substitute(text: str, env: Mapping[str, str], path: list[str | int], issues: list[str]) -> str:
    def replace(match: re.Match[str]) -> str:
        escaped, name, default = match.group(1), match.group(2), match.group(3)
        if escaped:
            return match.group(0)[1:]
        current = env.get(name)
        if default is not None and not current:
            return default
        if current is None:
            issues.append(f"{format_location(path)}: environment variable {name} is not set")
            return ""
        return current

    return _PATTERN.sub(replace, text)
