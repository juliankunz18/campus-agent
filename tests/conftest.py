import pytest

from campus_agent_core.config import CampusAgentConfig
from campus_agent_core.modules import ToolRegistry, discover_manifests, load_modules
from tests.helpers import example_config


@pytest.fixture(scope="session")
def musterverein_config() -> CampusAgentConfig:
    return example_config()


@pytest.fixture(scope="session")
def musterverein_registry(musterverein_config: CampusAgentConfig) -> ToolRegistry:
    modules = load_modules(musterverein_config, discover_manifests())
    return ToolRegistry(
        modules, musterverein_config.role_hierarchy(), language=musterverein_config.group.language
    )
