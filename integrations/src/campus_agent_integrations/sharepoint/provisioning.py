"""Create the SharePoint lists and libraries declared by the active modules."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from msgraph.graph_service_client import GraphServiceClient

from campus_agent_core.modules import LoadedModule
from campus_agent_core.ports.module import ListSpec


@dataclass(frozen=True)
class PlannedList:
    module: str
    spec: ListSpec


def plan_lists(modules: Sequence[LoadedModule]) -> list[PlannedList]:
    """All lists of the active modules, ordered so that lookup targets come first.

    Raises ``ValueError`` for duplicate list names, lookups to undeclared lists and
    lookup cycles.
    """
    planned: dict[str, PlannedList] = {}
    for module in modules:
        for spec in module.manifest.lists:
            if spec.name in planned:
                owner = planned[spec.name].module
                raise ValueError(f"list {spec.name!r} is declared by {owner!r} and {module.name!r}")
            planned[spec.name] = PlannedList(module.name, spec)

    ordered: dict[str, PlannedList] = {}
    visiting: set[str] = set()

    def visit(name: str, needed_by: str) -> None:
        if name not in planned:
            raise ValueError(f"list {needed_by!r} looks up the undeclared list {name!r}")
        if name in ordered:
            return
        if name in visiting:
            raise ValueError(f"lookup cycle involving list {name!r}")
        visiting.add(name)
        for column in planned[name].spec.columns:
            if column.lookup_list is not None:
                visit(column.lookup_list, name)
        visiting.discard(name)
        ordered[name] = planned[name]

    for name in planned:
        visit(name, name)
    return list(ordered.values())


class ListProvisioner:
    """Creates missing lists and columns; never deletes anything."""

    def __init__(self, graph: GraphServiceClient, site_id: str) -> None:
        self._graph = graph
        self._site_id = site_id

    async def apply(self, plan: Sequence[PlannedList]) -> None:
        # TODO(sharepoint): for each planned list, read the existing lists of the site via
        #   the msgraph-sdk sites request builder, create missing lists or libraries and
        #   missing columns (indexed and unique flags, choice values, lookups), and set
        #   unique permissions (board only; the knowledge library readable by members).
        #   Verify request builders and models against the msgraph-sdk docs first.
        raise NotImplementedError("SharePoint provisioning is not implemented yet")
