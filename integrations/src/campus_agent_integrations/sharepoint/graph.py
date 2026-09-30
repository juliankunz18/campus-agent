"""Graph client factory. Authentication uses Managed Identity in Azure."""

from __future__ import annotations

from typing import Final

from azure.core.credentials_async import AsyncTokenCredential
from msgraph.graph_service_client import GraphServiceClient

GRAPH_SCOPES: Final = ["https://graph.microsoft.com/.default"]


def create_graph_client(credential: AsyncTokenCredential) -> GraphServiceClient:
    """Create a Graph client. The app registration only has ``Sites.Selected`` with write
    access to the group's own site (ADR 0007)."""
    return GraphServiceClient(credentials=credential, scopes=GRAPH_SCOPES)
