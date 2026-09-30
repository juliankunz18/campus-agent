"""Configuration of a group (campus-agent.yaml) and of the runtime environment."""

from campus_agent_core.config.errors import ConfigError
from campus_agent_core.config.loader import load_config, parse_config
from campus_agent_core.config.schema import AgentLimits, CampusAgentConfig
from campus_agent_core.config.settings import Environment, RuntimeSettings

__all__ = [
    "AgentLimits",
    "CampusAgentConfig",
    "ConfigError",
    "Environment",
    "RuntimeSettings",
    "load_config",
    "parse_config",
]
