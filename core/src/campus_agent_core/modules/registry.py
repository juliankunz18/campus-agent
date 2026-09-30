"""Tool registry filtered by role."""

from __future__ import annotations

import copy
from collections.abc import Sequence
from dataclasses import dataclass
from typing import cast

from pydantic import JsonValue

from campus_agent_core.domain.roles import RoleHierarchy
from campus_agent_core.errors import ForbiddenError, NotFoundError
from campus_agent_core.i18n import Catalog
from campus_agent_core.modules.loader import LoadedModule
from campus_agent_core.ports.llm import ToolSchema
from campus_agent_core.ports.module import ToolClass, ToolSpec


@dataclass(frozen=True)
class RegisteredTool:
    """A tool with its owning module and texts resolved for the group language."""

    spec: ToolSpec
    module: str
    description: str
    parameters: dict[str, JsonValue]

    @property
    def name(self) -> str:
        return self.spec.name

    @property
    def tool_class(self) -> ToolClass:
        return self.spec.tool_class

    @property
    def min_role(self) -> str:
        return self.spec.min_role

    def schema(self) -> ToolSchema:
        return ToolSchema(name=self.name, description=self.description, parameters=self.parameters)


class ToolRegistry:
    """All tools of the active modules; answers "may role X use tool Y"."""

    def __init__(
        self, modules: Sequence[LoadedModule], roles: RoleHierarchy, *, language: str
    ) -> None:
        self._roles = roles
        self._tools: dict[str, RegisteredTool] = {}
        for module in modules:
            for spec in module.manifest.tools:
                if spec.name in self._tools:
                    raise ValueError(f"duplicate tool name {spec.name!r}")
                roles.rank(spec.min_role)  # unknown roles fail early
                self._tools[spec.name] = RegisteredTool(
                    spec=spec,
                    module=module.name,
                    description=module.catalog.get(spec.description_key, language),
                    parameters=_localized_schema(spec, module.catalog, language),
                )

    @property
    def roles(self) -> RoleHierarchy:
        return self._roles

    def all(self) -> tuple[RegisteredTool, ...]:
        return tuple(self._tools.values())

    def names(self) -> tuple[str, ...]:
        return tuple(self._tools)

    def get(self, name: str) -> RegisteredTool:
        try:
            return self._tools[name]
        except KeyError:
            raise NotFoundError(f"unknown tool {name!r}", tool=name) from None

    def is_allowed(self, role: str, name: str) -> bool:
        return self._roles.includes(role, self.get(name).min_role)

    def ensure_allowed(self, role: str, name: str) -> RegisteredTool:
        """Return the tool or raise ``NOT_FOUND`` (unknown) / ``FORBIDDEN`` (role too low)."""
        tool = self.get(name)
        if not self._roles.includes(role, tool.min_role):
            raise ForbiddenError(
                f"role {role!r} may not use tool {name!r}", tool=name, required_role=tool.min_role
            )
        return tool

    def for_role(self, role: str) -> tuple[RegisteredTool, ...]:
        """Tools the role may use - the only ones the model ever sees."""
        return tuple(
            tool for tool in self._tools.values() if self._roles.includes(role, tool.min_role)
        )

    def schemas_for_role(self, role: str) -> list[ToolSchema]:
        return [tool.schema() for tool in self.for_role(role)]


def _localized_schema(spec: ToolSpec, catalog: Catalog, language: str) -> dict[str, JsonValue]:
    schema = copy.deepcopy(spec.input_model.model_json_schema())
    schema.pop("title", None)
    raw_properties = schema.get("properties")
    if isinstance(raw_properties, dict):
        properties = cast(dict[str, dict[str, object]], raw_properties)
        for field, definition in properties.items():
            definition.pop("title", None)
            definition["description"] = catalog.get(spec.parameter_key(field), language)
    return cast(dict[str, JsonValue], schema)
