"""The Musterverein example must always validate against the current schema."""

from pathlib import Path

from campus_agent_core.config import load_config

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = REPO_ROOT / "examples" / "musterverein"


def read_env_file(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            key, _, value = line.partition("=")
            env[key.strip()] = value.strip()
    return env


def test_musterverein_config_validates_with_example_env():
    env = read_env_file(EXAMPLE / ".env.example")

    config = load_config(EXAMPLE / "campus-agent.yaml", env=env)

    assert config.group.short_name == "musterverein"
    assert config.role_hierarchy().roles == ("member", "team_lead", "board")
    assert set(config.modules) == {"members", "certificates", "knowledge", "events"}


def test_certificate_template_referenced_by_example_exists():
    env = read_env_file(EXAMPLE / ".env.example")
    config = load_config(EXAMPLE / "campus-agent.yaml", env=env)

    template = config.modules["certificates"]["template"]
    assert isinstance(template, str)
    assert (EXAMPLE / template).is_file()
