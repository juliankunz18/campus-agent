"""Permission matrix: every role x every tool of every installed module.

The expected permission is derived from the manifests (a role may use a tool if it
inherits the tool's minimum role). Each pair is checked in the registry, in the list of
tools the model sees and in the tool policy that guards every call.
"""

import contextlib
from datetime import UTC, datetime

import pytest

from campus_agent_core.agent import ToolPolicy
from campus_agent_core.domain.user import UserContext
from campus_agent_core.errors import ForbiddenError, ValidationFailedError
from campus_agent_core.modules import ToolRegistry
from campus_agent_core.ports.llm import ToolCall
from tests.helpers import example_config, example_modules

NOW = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)

_CONFIG = example_config()
_ROLES = _CONFIG.role_hierarchy()
_TOOLS = [
    (tool.name, tool.min_role) for module in example_modules() for tool in module.manifest.tools
]
MATRIX = [
    pytest.param(role, tool, _ROLES.rank(role) >= _ROLES.rank(min_role), id=f"{role}-{tool}")
    for role in _ROLES.roles
    for tool, min_role in _TOOLS
]


def test_matrix_covers_every_role_and_tool():
    assert len(MATRIX) == len(_ROLES.roles) * len(_TOOLS)
    assert len(_TOOLS) == 24


@pytest.mark.parametrize(("role", "tool", "allowed"), MATRIX)
def test_permission(musterverein_registry: ToolRegistry, role: str, tool: str, allowed: bool):
    registry = musterverein_registry
    user = UserContext(user_id=f"user-{role}", role=role)

    assert registry.is_allowed(role, tool) is allowed
    assert (tool in {t.name for t in registry.for_role(role)}) is allowed
    assert (tool in {s.name for s in registry.schemas_for_role(role)}) is allowed

    policy = ToolPolicy(registry)
    request = ToolCall(id="call", name=tool, arguments={})
    if allowed:
        with contextlib.suppress(
            ValidationFailedError
        ):  # allowed; empty arguments may be incomplete
            policy.decide(request, user, now=NOW)
    else:
        with pytest.raises(ForbiddenError):
            policy.decide(request, user, now=NOW)
