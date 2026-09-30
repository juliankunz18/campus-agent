from datetime import timedelta
from pathlib import Path

import pytest

from campus_agent_core.config import (
    AgentLimits,
    ConfigError,
    Environment,
    RuntimeSettings,
    load_config,
    parse_config,
)
from campus_agent_core.config.env import substitute_env

VALID = """
group:
  name: Beispielgruppe
  short_name: beispiel
roles:
  - id: member
    label: Mitglied
    source: all_tenant_users
  - id: board
    label: Vorstand
    entra_group: ${GROUP_BOARD}
sharepoint:
  site_id: ${SITE:-default-site}
llm:
  deployment: model-x
"""

ENV = {"GROUP_BOARD": "group-1"}


def issues_of(text: str, env: dict[str, str] | None = None) -> tuple[str, ...]:
    with pytest.raises(ConfigError) as excinfo:
        parse_config(text, env=ENV if env is None else env)
    return excinfo.value.issues


class TestEnvSubstitution:
    def test_variables_and_defaults(self):
        config = parse_config(VALID, env=ENV)

        assert config.roles[1].entra_group == "group-1"
        assert config.sharepoint.site_id == "default-site"

    def test_default_applies_to_empty_values(self):
        value, issues = substitute_env("${EMPTY:-fallback}", {"EMPTY": ""})

        assert (value, issues) == ("fallback", [])

    def test_escaped_variables_stay_literal(self):
        value, issues = substitute_env("cost: $${NOT_A_VAR}", {})

        assert (value, issues) == ("cost: ${NOT_A_VAR}", [])

    def test_multiple_variables_in_one_string(self):
        value, _ = substitute_env("${A}-${B}", {"A": "x", "B": "y"})

        assert value == "x-y"

    def test_nested_structures_and_non_strings(self):
        value, issues = substitute_env({"a": [{"b": "${X}"}, 3, None, True]}, {"X": "1"})

        assert value == {"a": [{"b": "1"}, 3, None, True]}
        assert issues == []

    def test_all_missing_variables_are_reported_with_their_path(self):
        issues = issues_of(VALID.replace("model-x", "${DEPLOYMENT}"), env={})

        assert issues == (
            "roles[1].entra_group: environment variable GROUP_BOARD is not set",
            "llm.deployment: environment variable DEPLOYMENT is not set",
        )

    def test_keys_are_not_substituted(self):
        value, issues = substitute_env({"${KEY}": "v"}, {"KEY": "k"})

        assert value == {"${KEY}": "v"}
        assert issues == []


class TestSchema:
    def test_defaults(self):
        config = parse_config(VALID, env=ENV)

        assert config.group.language == "de"
        assert config.agent == AgentLimits()
        assert config.agent.max_tool_rounds == 6
        assert config.agent.llm_timeout == timedelta(seconds=30)
        assert config.agent.history_max_messages == 10
        assert config.agent.history_max_age == timedelta(hours=24)
        assert config.agent.role_cache_ttl == timedelta(minutes=5)
        assert config.agent.rate_limit_per_hour == 30
        assert config.agent.pending_action_ttl == timedelta(hours=24)
        assert config.agent.tool_result_max_tokens == 4000
        assert config.applications.clarification_deadline == timedelta(days=30)
        assert config.modules == {}

    def test_role_hierarchy_follows_configured_order(self):
        config = parse_config(VALID, env=ENV)

        assert config.role_hierarchy().roles == ("member", "board")

    def test_unknown_keys_are_rejected(self):
        issues = issues_of(VALID + "unknown_section: 1\n")

        assert issues == ("unknown_section: Extra inputs are not permitted",)

    def test_role_needs_exactly_one_membership_source(self):
        text = VALID.replace("entra_group: ${GROUP_BOARD}", "")

        assert issues_of(text) == (
            "roles[1]: Value error, set exactly one of 'source' or 'entra_group'",
        )

    def test_lowest_role_must_include_all_tenant_users(self):
        text = VALID.replace("source: all_tenant_users", "entra_group: g0")

        (issue,) = issues_of(text)
        assert issue.startswith("roles: Value error, the lowest role 'member'")

    def test_duplicate_role_ids(self):
        text = VALID.replace("id: board", "id: member")

        (issue,) = issues_of(text)
        assert "duplicate role ids: member" in issue

    def test_invalid_values_list_every_problem(self):
        text = VALID.replace("short_name: beispiel", "short_name: Beispiel Gruppe") + (
            "agent:\n  max_tool_rounds: 0\n  llm_timeout: -5\n"
        )

        issues = issues_of(text)
        assert [issue.split(":")[0] for issue in issues] == [
            "group.short_name",
            "agent.max_tool_rounds",
            "agent.llm_timeout",
        ]

    def test_durations_accept_iso_and_seconds(self):
        text = VALID + "agent:\n  llm_timeout: PT45S\n  role_cache_ttl: 60\n"

        config = parse_config(text, env=ENV)
        assert config.agent.llm_timeout == timedelta(seconds=45)
        assert config.agent.role_cache_ttl == timedelta(minutes=1)

    def test_module_names_must_be_slugs(self):
        (issue,) = issues_of(VALID + "modules:\n  Bad-Name: {}\n")

        assert issue.startswith("modules.Bad-Name.[key]")


class TestLoading:
    def test_yaml_syntax_errors_name_the_line(self):
        (issue,) = issues_of("group:\n  name: [unclosed\n")

        assert issue.startswith("YAML syntax error at line")

    def test_top_level_must_be_a_mapping(self):
        assert issues_of("- a\n- b\n") == ("<root>: expected a mapping at the top level",)

    def test_missing_file(self, tmp_path: Path):
        with pytest.raises(ConfigError) as excinfo:
            load_config(tmp_path / "missing.yaml", env=ENV)

        assert "cannot read file" in excinfo.value.issues[0]

    def test_load_from_file(self, tmp_path: Path):
        path = tmp_path / "campus-agent.yaml"
        path.write_text(VALID, encoding="utf-8")

        assert load_config(path, env=ENV).group.name == "Beispielgruppe"

    def test_error_message_is_readable(self):
        with pytest.raises(ConfigError) as excinfo:
            parse_config(VALID, source="campus-agent.yaml", env={})

        assert str(excinfo.value) == (
            "invalid configuration in campus-agent.yaml:\n"
            "  - roles[1].entra_group: environment variable GROUP_BOARD is not set"
        )


class TestRuntimeSettings:
    def test_environment_is_required(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.delenv("CAMPUS_AGENT_ENV", raising=False)

        with pytest.raises(ValueError, match="CAMPUS_AGENT_ENV"):
            RuntimeSettings()  # pyright: ignore[reportCallIssue]

    def test_fake_user_allowed_locally(self, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("CAMPUS_AGENT_ENV", "local")
        monkeypatch.setenv("DEV_FAKE_USER", "user-1")

        settings = RuntimeSettings()  # pyright: ignore[reportCallIssue]
        assert settings.env is Environment.LOCAL
        assert settings.dev_fake_user == "user-1"

    @pytest.mark.parametrize("env", ["dev", "prod"])
    def test_fake_user_refused_outside_local(self, monkeypatch: pytest.MonkeyPatch, env: str):
        monkeypatch.setenv("CAMPUS_AGENT_ENV", env)
        monkeypatch.setenv("DEV_FAKE_USER", "user-1")

        with pytest.raises(ValueError, match="DEV_FAKE_USER is only allowed"):
            RuntimeSettings()  # pyright: ignore[reportCallIssue]
