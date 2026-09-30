"""In-memory implementations of the ports for tests and local development."""

from campus_agent_integrations.fakes.applications import InMemoryApplicationRepository
from campus_agent_integrations.fakes.llm import FakeLLM
from campus_agent_integrations.fakes.storage import InMemoryStorage

__all__ = ["FakeLLM", "InMemoryApplicationRepository", "InMemoryStorage"]
