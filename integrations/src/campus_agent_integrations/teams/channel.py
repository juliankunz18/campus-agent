"""Teams channel adapter on the Microsoft 365 Agents SDK."""

from __future__ import annotations

from pydantic import JsonValue


class TeamsChannel:
    """Implements the ``Channel`` port for one turn.

    TODO(teams): wrap the SDK TurnContext of the current turn (microsoft-agents-hosting-core
    with microsoft-agents-hosting-msteams): send a typing indicator immediately, send text
    and Adaptive Card attachments. Verify the TurnContext, MessageFactory and CardFactory
    signatures of the pinned SDK version before implementing.
    """

    async def send_typing(self, conversation_id: str) -> None:
        raise NotImplementedError

    async def send_text(self, conversation_id: str, text: str) -> None:
        raise NotImplementedError

    async def send_card(self, conversation_id: str, card: dict[str, JsonValue]) -> None:
        raise NotImplementedError
