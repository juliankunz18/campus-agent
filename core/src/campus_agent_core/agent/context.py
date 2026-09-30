"""Context limits of the loop: history window, rate limit, tool result size."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime, timedelta

from pydantic import AwareDatetime, BaseModel, ConfigDict

from campus_agent_core.config.schema import AgentLimits
from campus_agent_core.ports.llm import ChatMessage

TRUNCATION_MARKER = "\n[truncated]"
CHARS_PER_TOKEN = 4  # rough estimate; avoids a tokenizer dependency in the core


class HistoryEntry(BaseModel):
    model_config = ConfigDict(frozen=True)

    message: ChatMessage
    at: AwareDatetime


def recent_history(
    entries: Sequence[HistoryEntry], *, now: datetime, limits: AgentLimits
) -> list[ChatMessage]:
    """The last ``history_max_messages`` messages that are at most ``history_max_age`` old."""
    if limits.history_max_messages == 0:
        return []
    cutoff = now - limits.history_max_age
    fresh = [entry for entry in sorted(entries, key=lambda e: e.at) if entry.at >= cutoff]
    return [entry.message for entry in fresh[-limits.history_max_messages :]]


def is_rate_limited(
    message_times: Sequence[datetime], *, now: datetime, limits: AgentLimits
) -> bool:
    """Whether a new message would exceed ``rate_limit_per_hour`` (sliding window)."""
    window_start = now - timedelta(hours=1)
    recent = sum(1 for at in message_times if window_start < at <= now)
    return recent >= limits.rate_limit_per_hour


def truncate_for_context(text: str, *, max_tokens: int) -> str:
    max_chars = max_tokens * CHARS_PER_TOKEN
    if len(text) <= max_chars:
        return text
    return text[: max_chars - len(TRUNCATION_MARKER)] + TRUNCATION_MARKER
