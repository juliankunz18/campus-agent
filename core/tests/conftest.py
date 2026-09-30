import pytest

from campus_agent_core.config import CampusAgentConfig
from campus_agent_core.testing import minimal_config


@pytest.fixture
def config() -> CampusAgentConfig:
    return minimal_config()
