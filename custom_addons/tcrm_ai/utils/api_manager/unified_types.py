# Part of TCRM AI. See LICENSE for details.

"""Shared request/response dataclasses and exceptions for the API manager."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class UnifiedMessage:
    role: str  # "user" | "assistant" | "system"
    content: str


@dataclass
class ToolCall:
    name: str
    arguments: dict


@dataclass
class TokenUsage:
    input_tokens: int
    output_tokens: int
    total_tokens: int


@dataclass
class UnifiedResponse:
    text: str
    tool_calls: list
    usage: TokenUsage
    provider: str
    model: str
    key_label: str
    latency_ms: int

    def __post_init__(self):
        if self.tool_calls is None:
            self.tool_calls = []


@dataclass
class KeySlot:
    """In-memory key representation for the API manager. Never log api_key."""
    id: int
    api_key: str
    provider_code: str
    default_model: str
    key_label: str
    provider_id: int


class AllProvidersExhaustedError(Exception):
    """Raised when no key is available across all providers."""

    def __init__(self, next_available_at=None):
        self.next_available_at = next_available_at
        super().__init__(self.user_message())

    def user_message(self):
        if self.next_available_at:
            now = datetime.utcnow()
            if self.next_available_at.tzinfo:
                from datetime import timezone
                now = datetime.now(timezone.utc).replace(tzinfo=None)
            delta = self.next_available_at - now
            mins = max(0, int(delta.total_seconds() / 60))
            return (
                f"All AI services are temporarily at capacity. "
                f"Please try again in {mins} minutes."
            )
        return (
            "All AI services are temporarily unavailable. "
            "Please try again later."
        )
