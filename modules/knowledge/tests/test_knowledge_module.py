from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from campus_agent_core.ports import ToolContext, UserContext
from campus_agent_knowledge import tools
from campus_agent_knowledge.manifest import KnowledgeSettings, manifest


def test_query_bounds():
    with pytest.raises(ValidationError):
        tools.SearchKnowledgeInput(query="x")
    with pytest.raises(ValidationError):
        tools.SearchKnowledgeInput(query="Satzung", max_results=50)


def test_library_name_is_a_sharepoint_name():
    with pytest.raises(ValidationError):
        KnowledgeSettings(library="Wissen und Doku")


async def test_handler_is_a_stub():
    context = ToolContext(
        user=UserContext(user_id="user-1", role="member"), now=datetime(2026, 10, 1, tzinfo=UTC)
    )
    (spec,) = manifest.tools

    with pytest.raises(NotImplementedError):
        await spec.handler(context, tools.SearchKnowledgeInput(query="Satzung"))
