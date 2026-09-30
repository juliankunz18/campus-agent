"""Shared helpers for the cross-package tests."""

from pathlib import Path

from campus_agent_core.config import CampusAgentConfig, load_config
from campus_agent_core.modules import LoadedModule, discover_manifests, load_modules

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = REPO_ROOT / "examples" / "musterverein"


def read_env_file(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            key, _, value = line.partition("=")
            env[key.strip()] = value.strip()
    return env


def example_env() -> dict[str, str]:
    return read_env_file(EXAMPLE / ".env.example")


def example_config() -> CampusAgentConfig:
    return load_config(EXAMPLE / "campus-agent.yaml", env=example_env())


def example_modules() -> list[LoadedModule]:
    return load_modules(example_config(), discover_manifests())
