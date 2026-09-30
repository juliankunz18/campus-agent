from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from campus_agent_core.ports import ToolContext, UserContext
from campus_agent_members import tools
from campus_agent_members.manifest import manifest

CONTEXT = ToolContext(
    user=UserContext(user_id="user-1", role="member"), now=datetime(2026, 10, 1, tzinfo=UTC)
)


def test_manifest_declares_lists_for_provisioning():
    assert [spec.name for spec in manifest.lists] == ["Ressorts", "Mitglieder"]


def test_sensitive_fields_cannot_be_changed_through_the_bot():
    with pytest.raises(ValidationError):
        tools.CreateChangeDraftInput.model_validate({"field": "iban", "new_value": "DE00"})


@pytest.mark.parametrize("spec", manifest.tools, ids=lambda spec: spec.name)
async def test_handlers_are_stubs(spec):
    params = spec.input_model.model_construct()

    with pytest.raises(NotImplementedError, match=spec.name):
        await spec.handler(CONTEXT, params)
