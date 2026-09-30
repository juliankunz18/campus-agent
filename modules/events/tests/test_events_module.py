from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from campus_agent_core.ports import ToolContext, UserContext
from campus_agent_events import tools
from campus_agent_events.manifest import manifest

START = datetime(2026, 11, 5, 18, 0, tzinfo=UTC)


def test_events_need_timezone_aware_times():
    with pytest.raises(ValidationError):
        tools.CreateEventInput(title="Stammtisch", starts_at=datetime(2026, 11, 5, 18, 0))  # noqa: DTZ001


def test_end_after_start():
    with pytest.raises(ValidationError, match="ends_at"):
        tools.CreateEventInput(
            title="Stammtisch", starts_at=START, ends_at=START - timedelta(hours=1)
        )


@pytest.mark.parametrize("spec", manifest.tools, ids=lambda spec: spec.name)
async def test_handlers_are_stubs(spec):
    context = ToolContext(user=UserContext(user_id="user-1", role="board"), now=START)

    with pytest.raises(NotImplementedError, match=spec.name):
        await spec.handler(context, spec.input_model.model_construct())
