from pathlib import Path

import pytest
from typer.testing import CliRunner

from campus_agent_cli.main import EXAMPLE_FILES, app, read_env_file
from tests.helpers import EXAMPLE

runner = CliRunner()
EXAMPLE_ENV = EXAMPLE / ".env.example"
EXAMPLE_CONFIG = EXAMPLE / "campus-agent.yaml"


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch: pytest.MonkeyPatch):
    for name in ("CAMPUS_AGENT_ENV", "DEV_FAKE_USER", "DEV_FAKE_ROLE", "GROUP_BOARD"):
        monkeypatch.delenv(name, raising=False)


def test_packaged_example_matches_examples_directory():
    packaged = Path(__file__).resolve().parents[1] / "src" / "campus_agent_cli" / "example"

    for source, target in EXAMPLE_FILES.items():
        assert (packaged / source).read_text(encoding="utf-8") == (EXAMPLE / target).read_text(
            encoding="utf-8"
        ), source


class TestInit:
    def test_copies_the_example(self, tmp_path: Path):
        result = runner.invoke(app, ["init", str(tmp_path)])

        assert result.exit_code == 0, result.output
        assert (tmp_path / "campus-agent.yaml").read_text(
            encoding="utf-8"
        ) == EXAMPLE_CONFIG.read_text(encoding="utf-8")
        assert (tmp_path / ".env.example").is_file()
        assert (tmp_path / "templates" / "bescheinigung.html.j2").is_file()
        assert "Next steps" in result.output

    def test_refuses_to_overwrite(self, tmp_path: Path):
        (tmp_path / "campus-agent.yaml").write_text("mine", encoding="utf-8")

        result = runner.invoke(app, ["init", str(tmp_path)])

        assert result.exit_code == 1
        assert (tmp_path / "campus-agent.yaml").read_text(encoding="utf-8") == "mine"

    def test_force_overwrites(self, tmp_path: Path):
        (tmp_path / "campus-agent.yaml").write_text("mine", encoding="utf-8")

        result = runner.invoke(app, ["init", str(tmp_path), "--force"])

        assert result.exit_code == 0
        assert "Musterverein" in (tmp_path / "campus-agent.yaml").read_text(encoding="utf-8")


class TestDoctor:
    def test_healthy_example(self):
        result = runner.invoke(
            app, ["doctor", "--config", str(EXAMPLE_CONFIG), "--env-file", str(EXAMPLE_ENV)]
        )

        assert result.exit_code == 0, result.output
        assert "[ok]   configuration" in result.output
        assert "[ok]   roles: member < team_lead < board" in result.output
        assert "[ok]   tools and texts: 24 tools" in result.output
        assert "[skip] Graph permissions" in result.output

    def test_reports_missing_variables(self):
        result = runner.invoke(app, ["doctor", "--config", str(EXAMPLE_CONFIG)])

        assert result.exit_code == 1
        assert "[fail] environment" in result.output
        assert "environment variable GROUP_TEAM_LEAD is not set" in result.output

    def test_reports_missing_template(self, tmp_path: Path):
        runner.invoke(app, ["init", str(tmp_path)])
        (tmp_path / "templates" / "bescheinigung.html.j2").unlink()

        result = runner.invoke(
            app,
            [
                "doctor",
                "--config",
                str(tmp_path / "campus-agent.yaml"),
                "--env-file",
                str(EXAMPLE_ENV),
            ],
        )

        assert result.exit_code == 1
        assert "[fail] certificate template not found" in result.output


class TestProvision:
    def test_dry_run_lists_the_plan(self):
        result = runner.invoke(
            app, ["provision", "--config", str(EXAMPLE_CONFIG), "--env-file", str(EXAMPLE_ENV)]
        )

        assert result.exit_code == 0, result.output
        assert "Planned lists and libraries (8)" in result.output
        assert result.output.index("Ressorts") < result.output.index("Mitglieder")
        assert "Dry run only" in result.output

    def test_apply_is_not_implemented(self):
        result = runner.invoke(
            app,
            [
                "provision",
                "--config",
                str(EXAMPLE_CONFIG),
                "--env-file",
                str(EXAMPLE_ENV),
                "--apply",
            ],
        )

        assert result.exit_code == 2
        assert "not implemented yet" in result.output


def test_read_env_file(tmp_path: Path):
    env_file = tmp_path / ".env"
    env_file.write_text('# comment\nA=1\nexport B="two"\n\nbroken line\n', encoding="utf-8")

    assert read_env_file(env_file) == {"A": "1", "B": "two"}
