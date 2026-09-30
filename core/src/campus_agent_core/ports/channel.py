"""Port for the chat channel. Only Microsoft Teams is implemented."""

from __future__ import annotations

from typing import Protocol

from pydantic import JsonValue


class Channel(Protocol):
    async def send_typing(self, conversation_id: str) -> None: ...

    async def send_text(self, conversation_id: str, text: str) -> None: ...

    async def send_card(self, conversation_id: str, card: dict[str, JsonValue]) -> None:
        """Send an Adaptive Card (JSON payload)."""
        ...
