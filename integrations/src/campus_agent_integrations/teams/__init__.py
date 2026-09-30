"""Microsoft Teams through the Microsoft 365 Agents SDK."""

from campus_agent_integrations.teams.cards import confirmation_card
from campus_agent_integrations.teams.channel import TeamsChannel

__all__ = ["TeamsChannel", "confirmation_card"]
