from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest

from campus_agent_core.agent import AgentReply, PendingAction
from campus_agent_core.modules import ToolRegistry
from evals.runner import (
    DatasetError,
    EvalCase,
    check_against_registry,
    load_cases,
    main,
    score,
    summarize,
    wilson_interval,
)
from tests.helpers import REPO_ROOT

DATASETS = REPO_ROOT / "evals" / "datasets"


def test_datasets_have_five_cases_each():
    golden = load_cases(DATASETS / "golden_set.synthetic.jsonl")
    attacks = load_cases(DATASETS / "attacks.jsonl")

    assert len(golden) == 5
    assert len(attacks) == 5
    assert {case.category for case in golden} == {"golden"}
    assert {case.category for case in attacks} == {"attack"}


def test_datasets_reference_existing_tools_and_roles(musterverein_registry: ToolRegistry):
    cases = [case for path in DATASETS.glob("*.jsonl") for case in load_cases(path)]

    assert check_against_registry(cases, musterverein_registry) == []


def test_invalid_lines_are_reported_with_line_numbers(tmp_path: Path):
    path = tmp_path / "broken.jsonl"
    path.write_text(
        '{"id": "ok-1", "category": "golden", "role": "member", "question": "?"}\nnot json\n',
        encoding="utf-8",
    )

    with pytest.raises(DatasetError, match=r"broken\.jsonl:2"):
        load_cases(path)


def test_scoring():
    case = EvalCase(
        id="c",
        category="attack",
        role="member",
        question="?",
        expected_tools=("search_knowledge",),
        forbidden_tools=("approve_all_open",),
    )

    good = score(case, AgentReply(text="ok", tool_calls=("search_knowledge",)))
    bad = score(case, AgentReply(text="ok", tool_calls=("approve_all_open",)))

    assert good.passed
    assert not bad.passed
    assert bad.reasons == (
        "expected tools not used: search_knowledge",
        "forbidden tools used: approve_all_open",
    )


def test_proposed_commit_tools_count_as_used():
    now = datetime(2026, 10, 1, tzinfo=UTC)
    action = PendingAction(
        id=uuid4(),
        idempotency_key="k" * 32,
        tool="approve_application",
        arguments={},
        user_id="u",
        created_at=now,
        expires_at=now + timedelta(hours=24),
    )
    case = EvalCase(
        id="c",
        category="attack",
        role="board",
        question="?",
        forbidden_tools=("approve_application",),
    )

    assert not score(case, AgentReply(text=None, pending_actions=(action,))).passed


def test_wilson_interval():
    low, high = wilson_interval(45, 50)

    assert 0.78 < low < 0.80
    assert 0.95 < high < 0.97
    assert wilson_interval(0, 0) == (0.0, 1.0)
    assert "1/2 passed" in summarize([score_ok(), score_fail()])


def score_ok():
    case = EvalCase(id="a", category="golden", role="member", question="?")
    return score(case, AgentReply(text="ok"))


def score_fail():
    case = EvalCase(
        id="b", category="golden", role="member", question="?", expected_tools=("list_events",)
    )
    return score(case, AgentReply(text="ok"))


def test_cli_validate_and_run(capsys: pytest.CaptureFixture[str]):
    files = [str(path) for path in sorted(DATASETS.glob("*.jsonl"))]

    assert main(["validate", *files]) == 0
    assert "10 cases OK" in capsys.readouterr().out
    assert main(["run", *files]) == 2
