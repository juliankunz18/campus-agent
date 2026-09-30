import pytest

from campus_agent_core.domain.roles import RoleHierarchy, UnknownRoleError
from campus_agent_core.errors import ErrorCode, ForbiddenError

ROLES = RoleHierarchy(["member", "team_lead", "board"])


def test_roles_keep_configured_order():
    assert ROLES.roles == ("member", "team_lead", "board")
    assert ROLES.lowest == "member"
    assert ROLES.highest == "board"


@pytest.mark.parametrize(
    ("granted", "required", "expected"),
    [
        ("member", "member", True),
        ("member", "team_lead", False),
        ("member", "board", False),
        ("team_lead", "member", True),
        ("team_lead", "team_lead", True),
        ("team_lead", "board", False),
        ("board", "member", True),
        ("board", "team_lead", True),
        ("board", "board", True),
    ],
)
def test_higher_roles_inherit_lower_roles(granted: str, required: str, expected: bool):
    assert ROLES.includes(granted, required) is expected


def test_inherited_roles_list_the_role_and_everything_below():
    assert ROLES.inherited_roles("member") == ("member",)
    assert ROLES.inherited_roles("board") == ("member", "team_lead", "board")


def test_unknown_role_is_rejected():
    with pytest.raises(UnknownRoleError, match="admin"):
        ROLES.includes("admin", "member")
    with pytest.raises(UnknownRoleError):
        ROLES.rank("")


def test_highest_of_ignores_unknown_roles():
    assert ROLES.highest_of(["member", "board", "admin"]) == "board"
    assert ROLES.highest_of(["team_lead"]) == "team_lead"
    assert ROLES.highest_of(["admin"]) is None
    assert ROLES.highest_of([]) is None


def test_contains():
    assert "board" in ROLES
    assert "admin" not in ROLES


def test_ensure_permitted_raises_forbidden():
    ROLES.ensure_permitted("board", "team_lead", action="confirm_activity")

    with pytest.raises(ForbiddenError) as excinfo:
        ROLES.ensure_permitted("member", "board", action="approve_application")

    assert excinfo.value.code is ErrorCode.FORBIDDEN
    assert excinfo.value.details == {
        "action": "approve_application",
        "required_role": "board",
    }


@pytest.mark.parametrize(
    "role_ids",
    [
        [],
        ["member", "member"],
        ["Member"],
        ["team-lead"],
        ["1st"],
    ],
)
def test_invalid_hierarchies_are_rejected(role_ids: list[str]):
    with pytest.raises(ValueError, match=r"role"):
        RoleHierarchy(role_ids)


def test_custom_hierarchies_are_supported():
    roles = RoleHierarchy(["guest", "member", "chair"])

    assert roles.includes("chair", "guest")
    assert not roles.includes("guest", "member")
