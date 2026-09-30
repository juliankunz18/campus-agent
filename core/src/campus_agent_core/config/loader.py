"""Load and validate ``campus-agent.yaml``."""

from __future__ import annotations

import os
from collections.abc import Mapping
from pathlib import Path
from typing import cast

import yaml
from pydantic import ValidationError

from campus_agent_core.config.env import substitute_env
from campus_agent_core.config.errors import ConfigError, format_location
from campus_agent_core.config.schema import CampusAgentConfig


def load_config(path: Path | str, env: Mapping[str, str] | None = None) -> CampusAgentConfig:
    """Read, substitute and validate a configuration file.

    Raises :class:`ConfigError` listing every problem at once.
    """
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        raise ConfigError(str(path), [f"cannot read file: {error.strerror or error}"]) from error
    return parse_config(text, source=str(path), env=env)


def parse_config(
    text: str, *, source: str = "<string>", env: Mapping[str, str] | None = None
) -> CampusAgentConfig:
    env = os.environ if env is None else env
    try:
        raw: object = yaml.safe_load(text)
    except yaml.YAMLError as error:
        raise ConfigError(source, [_describe_yaml_error(error)]) from error
    if not isinstance(raw, dict):
        raise ConfigError(source, ["<root>: expected a mapping at the top level"])

    substituted, issues = substitute_env(cast(dict[str, object], raw), env)
    if issues:
        raise ConfigError(source, issues)

    try:
        return CampusAgentConfig.model_validate(substituted)
    except ValidationError as error:
        raise ConfigError(source, _describe_validation_error(error)) from error


def _describe_yaml_error(error: yaml.YAMLError) -> str:
    if isinstance(error, yaml.MarkedYAMLError) and error.problem_mark is not None:
        mark = error.problem_mark
        return (
            f"YAML syntax error at line {mark.line + 1}, column {mark.column + 1}: {error.problem}"
        )
    return f"YAML syntax error: {error}"


def _describe_validation_error(error: ValidationError) -> list[str]:
    return [f"{format_location(item['loc'])}: {item['msg']}" for item in error.errors()]
