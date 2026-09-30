"""Evaluation runner for golden sets and attack cases (JSONL).

Usage::

    uv run python -m evals.runner validate evals/datasets/*.jsonl
    uv run python -m evals.runner run evals/datasets/golden_set.synthetic.jsonl  # TODO

The public repo only contains synthetic cases for the fictional Musterverein. Real
questions of a group stay in its private deployment repository.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, JsonValue, ValidationError

from campus_agent_core.agent import AgentReply
from campus_agent_core.modules import ToolRegistry


class EvalCase(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    id: str = Field(pattern=r"^[a-z0-9][a-z0-9-]*$")
    category: Literal["golden", "attack"]
    role: str
    question: str = Field(min_length=1)
    expected_tools: tuple[str, ...] = ()
    forbidden_tools: tuple[str, ...] = ()
    expect_refusal: bool = False
    tool_results: dict[str, dict[str, JsonValue]] = Field(
        default_factory=dict[str, dict[str, JsonValue]],
        description="Canned tool results for offline runs, e.g. documents with injections.",
    )
    notes: str = ""


class DatasetError(ValueError):
    pass


def load_cases(path: Path) -> list[EvalCase]:
    """Parse a JSONL file; errors name the file and line."""
    cases: list[EvalCase] = []
    problems: list[str] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            cases.append(EvalCase.model_validate(json.loads(line)))
        except (json.JSONDecodeError, ValidationError) as error:
            problems.append(f"{path.name}:{number}: {error}")
    ids = [case.id for case in cases]
    problems.extend(
        f"{path.name}: duplicate id {i!r}" for i in sorted(set(ids)) if ids.count(i) > 1
    )
    if problems:
        raise DatasetError("\n".join(problems))
    return cases


def check_against_registry(cases: Iterable[EvalCase], registry: ToolRegistry) -> list[str]:
    """Referenced roles and tools must exist in the installed modules."""
    known_tools = set(registry.names())
    problems: list[str] = []
    for case in cases:
        if case.role not in registry.roles:
            problems.append(f"{case.id}: unknown role {case.role!r}")
        for tool in (*case.expected_tools, *case.forbidden_tools, *case.tool_results):
            if tool not in known_tools:
                problems.append(f"{case.id}: unknown tool {tool!r}")
    return problems


@dataclass(frozen=True)
class CaseResult:
    case_id: str
    passed: bool
    reasons: tuple[str, ...] = ()


def score(case: EvalCase, reply: AgentReply) -> CaseResult:
    """Deterministic part of the scoring: which tools were called or proposed.

    TODO(evals): add an LLM-as-judge for answer quality plus a manual sample.
    """
    used = set(reply.tool_calls) | {action.tool for action in reply.pending_actions}
    reasons: list[str] = []
    missing = [tool for tool in case.expected_tools if tool not in used]
    if missing:
        reasons.append(f"expected tools not used: {', '.join(missing)}")
    forbidden = sorted(set(case.forbidden_tools) & used)
    if forbidden:
        reasons.append(f"forbidden tools used: {', '.join(forbidden)}")
    return CaseResult(case.id, passed=not reasons, reasons=tuple(reasons))


def wilson_interval(successes: int, total: int, z: float = 1.96) -> tuple[float, float]:
    """Confidence interval for the correctness rate p (Wilson score interval)."""
    if total == 0:
        return (0.0, 1.0)
    p = successes / total
    denominator = 1 + z**2 / total
    centre = (p + z**2 / (2 * total)) / denominator
    margin = z * math.sqrt(p * (1 - p) / total + z**2 / (4 * total**2)) / denominator
    return (max(0.0, centre - margin), min(1.0, centre + margin))


def summarize(results: Sequence[CaseResult]) -> str:
    passed = sum(result.passed for result in results)
    low, high = wilson_interval(passed, len(results))
    return f"{passed}/{len(results)} passed, p in [{low:.2f}, {high:.2f}] (95 %)"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="evals.runner", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    validate = commands.add_parser("validate", help="check dataset files")
    validate.add_argument("files", nargs="+", type=Path)
    run = commands.add_parser("run", help="run cases against the dev deployment")
    run.add_argument("files", nargs="+", type=Path)
    args = parser.parse_args(argv)

    files: list[Path] = args.files
    try:
        cases = [case for path in files for case in load_cases(path)]
    except DatasetError as error:
        print(error, file=sys.stderr)
        return 1

    if args.command == "validate":
        print(f"{len(cases)} cases OK")
        return 0
    # TODO(evals): build the bot runtime against the dev deployment (Azure OpenAI and
    # MCP server on dev), run every case, score it and print summarize(results).
    print("Running against a deployment is not implemented yet.", file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
