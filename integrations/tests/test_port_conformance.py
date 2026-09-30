"""Adapters and fakes must satisfy the core ports. Checked by pyright via these assignments."""

from azure.data.tables.aio import TableServiceClient
from msgraph.graph_service_client import GraphServiceClient

from campus_agent_core.ports.applications import ApplicationRepository
from campus_agent_core.ports.channel import Channel
from campus_agent_core.ports.directory import RoleResolver
from campus_agent_core.ports.llm import LLMProvider
from campus_agent_core.ports.storage import RuntimeStore
from campus_agent_core.testing import minimal_config
from campus_agent_integrations.azure_openai import AzureOpenAIProvider
from campus_agent_integrations.fakes import FakeLLM, InMemoryApplicationRepository, InMemoryStorage
from campus_agent_integrations.sharepoint import EntraRoleResolver, SharePointApplicationRepository
from campus_agent_integrations.storage import TableStorage
from campus_agent_integrations.teams import TeamsChannel


def test_fakes_implement_ports():
    llm: LLMProvider = FakeLLM()
    store: RuntimeStore = InMemoryStorage()
    repository: ApplicationRepository = InMemoryApplicationRepository()

    assert all([llm, store, repository])


def test_adapters_implement_ports():
    graph = GraphServiceClient.__new__(GraphServiceClient)  # no network, no credentials
    tables = TableServiceClient.__new__(TableServiceClient)

    llm: LLMProvider = AzureOpenAIProvider(endpoint="https://example.invalid", deployment="d")
    store: RuntimeStore = TableStorage(tables)
    repository: ApplicationRepository = SharePointApplicationRepository(graph, "site")
    roles: RoleResolver = EntraRoleResolver(graph, minimal_config())
    channel: Channel = TeamsChannel()

    assert all([llm, store, repository, roles, channel])
