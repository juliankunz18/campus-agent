from datetime import UTC, datetime

import pytest

from campus_agent_core.domain import applications as wf
from campus_agent_core.domain.applications import ApplicationStatus
from campus_agent_core.errors import ConflictError, NotFoundError
from campus_agent_core.ports.llm import ChatMessage, ChatRole, ToolSchema
from campus_agent_integrations.fakes import FakeLLM, InMemoryApplicationRepository, InMemoryStorage

NOW = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)


class TestFakeLLM:
    async def test_scripted_responses_in_order(self):
        llm = FakeLLM().call_tool("get_my_profile").reply("Fertig.")
        tools = [ToolSchema(name="get_my_profile", description="d", parameters={})]
        messages = [ChatMessage(role=ChatRole.USER, content="Hallo")]

        first = await llm.complete(messages, tools)
        second = await llm.complete(messages, tools)

        assert first.tool_calls[0].name == "get_my_profile"
        assert first.tool_calls[0].id == "call-1"
        assert second.content == "Fertig."
        assert llm.calls[0].tool_names == ("get_my_profile",)
        assert llm.calls[0].messages[0].content == "Hallo"

    async def test_parallel_tool_calls(self):
        llm = FakeLLM().call_tools(("a", {}), ("b", {"x": 1}))

        response = await llm.complete([], [])

        assert [(c.id, c.name) for c in response.tool_calls] == [("call-1", "a"), ("call-2", "b")]

    async def test_running_out_of_responses_fails_loudly(self):
        with pytest.raises(AssertionError, match="no scripted response"):
            await FakeLLM().complete([], [])


class TestInMemoryStorage:
    async def test_crud(self):
        store = InMemoryStorage()

        await store.insert("T", "p", "r1", {"a": 1})
        await store.upsert("T", "p", "r2", {"a": 2})
        await store.upsert("T", "other", "r1", {"a": 3})

        assert await store.get("T", "p", "r1") == {"a": 1}
        assert await store.list_partition("T", "p") == [{"a": 1}, {"a": 2}]
        await store.delete("T", "p", "r1")
        await store.delete("T", "p", "missing")
        assert await store.get("T", "p", "r1") is None

    async def test_insert_conflicts(self):
        store = InMemoryStorage()
        await store.insert("T", "p", "r", {})

        with pytest.raises(ConflictError):
            await store.insert("T", "p", "r", {})

    async def test_entities_are_copied(self):
        store = InMemoryStorage()
        entity: dict[str, object] = {"items": [1]}
        await store.insert("T", "p", "r", entity)  # type: ignore[arg-type]

        entity["items"] = [2]
        loaded = await store.get("T", "p", "r")
        assert loaded == {"items": [1]}


class TestInMemoryApplicationRepository:
    async def test_optimistic_status_check(self):
        draft = wf.new_draft(kind="certificate", applicant_id="u1", now=NOW)
        repository = InMemoryApplicationRepository()
        await repository.add(draft)

        submitted = wf.submit(draft, actor_id="u1", now=NOW)
        await repository.save(submitted, expected_status=ApplicationStatus.DRAFT)

        with pytest.raises(ConflictError):
            await repository.save(submitted, expected_status=ApplicationStatus.DRAFT)
        assert await repository.list_by_status(ApplicationStatus.SUBMITTED) == [submitted]
        assert await repository.list_for_applicant("u1") == [submitted]

    async def test_missing_and_duplicate(self):
        draft = wf.new_draft(kind="certificate", applicant_id="u1", now=NOW)
        repository = InMemoryApplicationRepository([draft])

        with pytest.raises(ConflictError):
            await repository.add(draft)
        await repository.delete(draft.id)
        assert await repository.get(draft.id) is None
        with pytest.raises(NotFoundError):
            await repository.save(draft, expected_status=ApplicationStatus.DRAFT)
