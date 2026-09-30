"""Manifest of the knowledge module: answers from statutes, FAQ, onboarding and minutes."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from campus_agent_core.ports import (
    ColumnType,
    ListColumn,
    ListKind,
    ListSpec,
    ModuleManifest,
    ToolClass,
    ToolSpec,
)
from campus_agent_knowledge import tools


class KnowledgeSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    library: str = Field(default="Wissen", pattern=r"^[A-Za-z][A-Za-z0-9]*$")


KNOWLEDGE_LIBRARY = ListSpec(
    name="Wissen",
    kind=ListKind.LIBRARY,
    columns=(
        ListColumn(
            name="Kategorie",
            type=ColumnType.CHOICE,
            required=True,
            choices=("Satzung", "FAQ", "Onboarding", "Protokoll"),
        ),
        ListColumn(name="Stand", type=ColumnType.DATE),
    ),
)

manifest = ModuleManifest(
    name="knowledge",
    version="0.1.0",
    required_roles=("member",),
    locale_package="campus_agent_knowledge",
    prompt_fragments=("prompt.knowledge",),
    lists=(KNOWLEDGE_LIBRARY,),
    config_model=KnowledgeSettings,
    tools=(
        ToolSpec(
            name="search_knowledge",
            tool_class=ToolClass.READ,
            min_role="member",
            input_model=tools.SearchKnowledgeInput,
            handler=tools.search_knowledge,
        ),
    ),
)
