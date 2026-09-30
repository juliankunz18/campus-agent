"""Adaptive Cards for confirmations.

Card content is built only from server-side data (the pending action and localized
labels), never from text written by the model.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Final

from pydantic import JsonValue

from campus_agent_core.agent import PendingAction
from campus_agent_core.i18n import Catalog, load_catalog

CARD_SCHEMA: Final = "http://adaptivecards.io/schemas/adaptive-card.json"
CARD_VERSION: Final = "1.5"
SUBMIT_NAMESPACE: Final = "campus_agent"


def texts() -> Catalog:
    return load_catalog("campus_agent_integrations")


def confirmation_card(
    action: PendingAction,
    *,
    label: str,
    facts: Sequence[tuple[str, str]],
    catalog: Catalog,
    language: str,
) -> dict[str, JsonValue]:
    """Card with confirm and cancel buttons. The click comes back as a new activity with
    the pending action ID; the bot then executes it without the model."""
    expires = action.expires_at.strftime("%d.%m.%Y %H:%M" if language == "de" else "%Y-%m-%d %H:%M")
    body: list[JsonValue] = [
        {
            "type": "TextBlock",
            "text": catalog.get("cards.confirm.title", language),
            "weight": "Bolder",
            "size": "Medium",
            "wrap": True,
        },
        {"type": "TextBlock", "text": label, "wrap": True},
    ]
    if facts:
        body.append(
            {"type": "FactSet", "facts": [{"title": key, "value": value} for key, value in facts]}
        )
    body.append(
        {
            "type": "TextBlock",
            "text": catalog.get("cards.confirm.expires", language).format(expires=expires),
            "isSubtle": True,
            "size": "Small",
            "wrap": True,
        }
    )
    # TODO(teams): switch to Action.Execute (Universal Actions) once the Agents SDK
    # handler for invoke activities is wired up in apps/bot.
    return {
        "type": "AdaptiveCard",
        "$schema": CARD_SCHEMA,
        "version": CARD_VERSION,
        "body": body,
        "actions": [
            _submit(catalog.get("cards.confirm.confirm", language), "confirm", action),
            _submit(catalog.get("cards.confirm.cancel", language), "cancel", action),
        ],
    }


def _submit(title: str, verb: str, action: PendingAction) -> dict[str, JsonValue]:
    return {
        "type": "Action.Submit",
        "title": title,
        "data": {SUBMIT_NAMESPACE: {"verb": verb, "pending_action_id": str(action.id)}},
    }
