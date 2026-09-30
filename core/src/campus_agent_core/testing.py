"""Helpers for testing modules without a tenant. Not used at runtime."""

from __future__ import annotations

from campus_agent_core.config import CampusAgentConfig, parse_config
from campus_agent_core.i18n import Catalog
from campus_agent_core.ports.module import ModuleManifest

MINIMAL_CONFIG_YAML = """
group: {name: Testgruppe, short_name: test}
roles:
  - {id: member, label: Mitglied, source: all_tenant_users}
  - {id: team_lead, label: Ressortleitung, entra_group: group-team-lead}
  - {id: board, label: Vorstand, entra_group: group-board}
sharepoint: {site_id: test-site}
llm: {deployment: test-deployment}
"""


def minimal_config(extra_yaml: str = "") -> CampusAgentConfig:
    """A valid configuration with the default roles, plus optional extra YAML."""
    return parse_config(MINIMAL_CONFIG_YAML + extra_yaml, source="<test>", env={})


def catalog_for(*manifests: ModuleManifest, skip: frozenset[str] = frozenset()) -> Catalog:
    """A catalog with placeholder texts for everything the manifests need, except ``skip``."""
    texts: dict[str, str] = {}
    for manifest in manifests:
        for tool in manifest.tools:
            texts[tool.description_key] = f"Beschreibung {tool.name}"
            for field in tool.input_model.model_fields:
                texts[tool.parameter_key(field)] = f"Parameter {field}"
        for key in manifest.prompt_fragments:
            texts[key] = f"Baustein {key}"
    kept = {key: value for key, value in texts.items() if key not in skip}
    english = {key: f"en: {value}" for key, value in kept.items()}
    return Catalog("test", {"de": kept, "en": english})
