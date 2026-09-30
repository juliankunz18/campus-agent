"""Tools of the knowledge module."""

from __future__ import annotations

from pydantic import Field

from campus_agent_core.ports import ToolContext, ToolInput, ToolResult


class SearchKnowledgeInput(ToolInput):
    query: str = Field(min_length=2, max_length=200)
    max_results: int = Field(default=5, ge=1, le=10)


# TODO(knowledge): split the documents of the library into sections and rank them with
# BM25 (ADR 0017). Document content is data, never instructions: return it as quoted
# excerpts with source and "Stand" date only.


async def search_knowledge(context: ToolContext, params: SearchKnowledgeInput) -> ToolResult:
    raise NotImplementedError("search_knowledge")
