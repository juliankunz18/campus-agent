from collections.abc import Callable

import pytest

from campus_agent_core.errors import (
    CampusAgentError,
    ConflictError,
    ErrorCode,
    ForbiddenError,
    InvalidStateError,
    NotFoundError,
    UpstreamError,
    ValidationFailedError,
)


@pytest.mark.parametrize(
    ("error_type", "code"),
    [
        (ForbiddenError, ErrorCode.FORBIDDEN),
        (NotFoundError, ErrorCode.NOT_FOUND),
        (InvalidStateError, ErrorCode.INVALID_STATE),
        (ValidationFailedError, ErrorCode.VALIDATION),
        (ConflictError, ErrorCode.CONFLICT),
        (UpstreamError, ErrorCode.UPSTREAM),
    ],
)
def test_error_subclasses_carry_their_code(
    error_type: Callable[..., CampusAgentError], code: ErrorCode
):
    error = error_type("something happened", target="abc")

    assert error.code is code
    assert error.details == {"target": "abc"}
    assert str(error).startswith(code.value)


def test_error_codes_match_the_bot_contract():
    assert {code.value for code in ErrorCode} == {
        "FORBIDDEN",
        "NOT_FOUND",
        "INVALID_STATE",
        "VALIDATION",
        "CONFLICT",
        "UPSTREAM",
    }
