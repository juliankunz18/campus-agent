from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from campus_agent_core.agent import PendingAction
from campus_agent_core.i18n import load_catalog
from campus_agent_core.modules import LoadedModule
from campus_agent_core.ports import ColumnType, ListColumn, ListSpec, ModuleManifest
from campus_agent_core.ports.llm import ChatMessage, ChatRole, ToolCall, ToolSchema
from campus_agent_core.testing import catalog_for, minimal_config
from campus_agent_integrations.azure_openai import (
    AzureOpenAIProvider,
    to_openai_messages,
    to_openai_tools,
)
from campus_agent_integrations.sharepoint import TTLCache, plan_lists
from campus_agent_integrations.teams import confirmation_card

NOW = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)


class TestAzureOpenAIFormat:
    def test_messages(self):
        call = ToolCall(id="c1", name="get_my_profile", arguments={"x": "ä"})
        converted = to_openai_messages(
            [
                ChatMessage(role=ChatRole.SYSTEM, content="S"),
                ChatMessage(role=ChatRole.ASSISTANT, tool_calls=(call,)),
                ChatMessage(role=ChatRole.TOOL, tool_call_id="c1", content="{}"),
            ]
        )

        assert converted == [
            {"role": "system", "content": "S"},
            {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "c1",
                        "type": "function",
                        "function": {"name": "get_my_profile", "arguments": '{"x": "ä"}'},
                    }
                ],
            },
            {"role": "tool", "content": "{}", "tool_call_id": "c1"},
        ]

    def test_tools(self):
        schema = ToolSchema(name="t", description="d", parameters={"type": "object"})

        assert to_openai_tools([schema]) == [
            {
                "type": "function",
                "function": {"name": "t", "description": "d", "parameters": {"type": "object"}},
            }
        ]

    async def test_network_call_is_a_stub(self):
        provider = AzureOpenAIProvider(endpoint="https://example.invalid", deployment="d")

        with pytest.raises(NotImplementedError):
            await provider.complete([], [])


def module_with(name: str, *lists: ListSpec) -> LoadedModule:
    manifest = ModuleManifest(
        name=name, version="1.0.0", required_roles=("member",), locale_package="x", lists=lists
    )
    return LoadedModule(manifest, catalog_for(manifest))


class TestPlanLists:
    def test_lookup_targets_come_first(self):
        members = ListSpec(
            name="Mitglieder",
            columns=(ListColumn(name="Ressort", type=ColumnType.LOOKUP, lookup_list="Ressorts"),),
        )
        teams = ListSpec(name="Ressorts")

        plan = plan_lists([module_with("a", members), module_with("b", teams)])

        assert [(item.module, item.spec.name) for item in plan] == [
            ("b", "Ressorts"),
            ("a", "Mitglieder"),
        ]

    def test_duplicate_lists(self):
        with pytest.raises(ValueError, match="declared by 'a' and 'b'"):
            plan_lists([module_with("a", ListSpec(name="X")), module_with("b", ListSpec(name="X"))])

    def test_undeclared_lookup(self):
        broken = ListSpec(
            name="A", columns=(ListColumn(name="B", type=ColumnType.LOOKUP, lookup_list="Missing"),)
        )

        with pytest.raises(ValueError, match="undeclared list 'Missing'"):
            plan_lists([module_with("a", broken)])

    def test_lookup_cycle(self):
        a = ListSpec(
            name="A", columns=(ListColumn(name="B", type=ColumnType.LOOKUP, lookup_list="B"),)
        )
        b = ListSpec(
            name="B", columns=(ListColumn(name="A", type=ColumnType.LOOKUP, lookup_list="A"),)
        )

        with pytest.raises(ValueError, match="cycle"):
            plan_lists([module_with("a", a, b)])


class TestTTLCache:
    async def test_expires_after_ttl(self):
        now = [NOW]
        cache: TTLCache[str, str] = TTLCache(timedelta(minutes=5), clock=lambda: now[0])
        loads: list[str] = []

        async def load() -> str:
            loads.append("x")
            return "board"

        assert await cache.get_or_load("u", load) == "board"
        now[0] += timedelta(minutes=4)
        assert await cache.get_or_load("u", load) == "board"
        now[0] += timedelta(minutes=1)
        assert await cache.get_or_load("u", load) == "board"
        assert len(loads) == 2


def test_role_for_groups_used_by_the_resolver():
    config = minimal_config()

    assert config.role_for_groups(["group-team-lead"]) == "team_lead"
    assert config.role_for_groups(["group-team-lead", "group-board"]) == "board"


class TestConfirmationCard:
    def action(self) -> PendingAction:
        return PendingAction(
            id=uuid4(),
            idempotency_key="k" * 32,
            tool="submit_application",
            arguments={},
            user_id="u1",
            created_at=NOW,
            expires_at=NOW + timedelta(hours=24),
        )

    def test_card_structure_and_german_texts(self):
        action = self.action()

        card = confirmation_card(
            action,
            label="Antrag einreichen",
            facts=[("Zeitraum", "01.04.2026 bis 30.09.2026")],
            catalog=load_catalog("campus_agent_integrations"),
            language="de",
        )

        assert card["type"] == "AdaptiveCard"
        assert card["version"] == "1.5"
        body = card["body"]
        assert isinstance(body, list)
        assert body[0] == {
            "type": "TextBlock",
            "text": "Bitte bestätigen",
            "weight": "Bolder",
            "size": "Medium",
            "wrap": True,
        }
        assert body[-1]["text"] == "Gültig bis 02.10.2026 12:00."  # type: ignore[index]
        actions = card["actions"]
        assert isinstance(actions, list)
        assert [a["title"] for a in actions] == ["Bestätigen", "Abbrechen"]  # type: ignore[index]
        assert actions[0]["data"] == {  # type: ignore[index]
            "campus_agent": {"verb": "confirm", "pending_action_id": str(action.id)}
        }

    def test_idempotency_key_is_not_exposed(self):
        action = self.action()

        card = confirmation_card(
            action,
            label="x",
            facts=[],
            catalog=load_catalog("campus_agent_integrations"),
            language="en",
        )

        assert action.idempotency_key not in str(card)
