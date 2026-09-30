"""System prompt assembly. Texts live in locale files; tools go through the tool schema.

``PROMPT_VERSION`` is written into every audit entry. Bump it whenever a prompt text or
the assembly order changes.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from typing import Final

from campus_agent_core.config.schema import GroupConfig
from campus_agent_core.domain.user import UserContext
from campus_agent_core.i18n import Catalog
from campus_agent_core.modules.loader import LoadedModule

PROMPT_VERSION: Final = "0.1.0"

_SYSTEM_PARTS: Final = (
    "prompt.system.role",
    "prompt.system.user",
    "prompt.system.rules",
    "prompt.system.security",
)


def format_date(value: date, language: str) -> str:
    return value.strftime("%d.%m.%Y") if language == "de" else value.isoformat()


def build_system_prompt(
    *,
    core_catalog: Catalog,
    modules: Sequence[LoadedModule],
    group: GroupConfig,
    user: UserContext,
    role_label: str,
    today: date,
) -> str:
    """Role and tone, user context (first name, role, date only), rules, security rule,
    then the prompt fragments of the active modules."""
    language = group.language
    values = {
        "group_name": group.name,
        "first_name": user.first_name or "-",
        "role_label": role_label,
        "today": format_date(today, language),
    }
    parts = [core_catalog.get(key, language).format(**values) for key in _SYSTEM_PARTS]
    for module in modules:
        parts.extend(module.catalog.get(key, language) for key in module.manifest.prompt_fragments)
    return "\n\n".join(parts)
