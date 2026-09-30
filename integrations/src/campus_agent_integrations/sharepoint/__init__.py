"""SharePoint and Entra ID through Microsoft Graph (msgraph-sdk)."""

from campus_agent_integrations.sharepoint.graph import GRAPH_SCOPES, create_graph_client
from campus_agent_integrations.sharepoint.provisioning import (
    ListProvisioner,
    PlannedList,
    plan_lists,
)
from campus_agent_integrations.sharepoint.repositories import SharePointApplicationRepository
from campus_agent_integrations.sharepoint.roles import EntraRoleResolver, TTLCache

__all__ = [
    "GRAPH_SCOPES",
    "EntraRoleResolver",
    "ListProvisioner",
    "PlannedList",
    "SharePointApplicationRepository",
    "TTLCache",
    "create_graph_client",
    "plan_lists",
]
