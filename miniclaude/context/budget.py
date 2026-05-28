"""Token budget management for context window control."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from miniclaude.llm.token_counter import count_message_tokens, count_tokens

logger = logging.getLogger(__name__)


@dataclass
class TokenBudget:
    """Tracks token usage against the context window limit.

    Manages the allocation between:
    - System prompt (fixed)
    - Tool schemas (fixed per request)
    - Conversation history (grows over time)
    - Reserved output space
    """

    max_tokens: int = 200_000
    reserved_output: int = 16_000
    system_tokens: int = 0
    tool_schema_tokens: int = 0
    history_tokens: int = 0
    warning_threshold: float = 0.85  # Warn when 85% full

    @property
    def fixed_overhead(self) -> int:
        """Tokens consumed by system prompt + tool schemas."""
        return self.system_tokens + self.tool_schema_tokens

    @property
    def available_for_history(self) -> int:
        """Tokens available for conversation history."""
        return self.max_tokens - self.reserved_output - self.fixed_overhead

    @property
    def current_usage(self) -> int:
        """Total tokens currently in use."""
        return self.fixed_overhead + self.history_tokens

    @property
    def usage_ratio(self) -> float:
        """Current usage as a ratio of max tokens (0.0 to 1.0)."""
        if self.max_tokens == 0:
            return 0.0
        return self.current_usage / self.max_tokens

    @property
    def remaining(self) -> int:
        """Tokens remaining before hitting the limit."""
        return max(0, self.max_tokens - self.reserved_output - self.current_usage)

    def needs_compression(self) -> bool:
        """Check if context compression is needed."""
        return self.usage_ratio > self.warning_threshold

    def is_critical(self) -> bool:
        """Check if context is critically full (>95%)."""
        return self.usage_ratio > 0.95

    def update_system_tokens(self, text: str) -> None:
        """Update system prompt token count."""
        self.system_tokens = count_tokens(text)

    def update_tool_schema_tokens(self, schemas: list[dict]) -> None:
        """Update tool schema token count."""
        import json
        total = 0
        for schema in schemas:
            total += count_tokens(json.dumps(schema))
        self.tool_schema_tokens = total

    def update_history_tokens(self, messages: list[dict]) -> None:
        """Update conversation history token count."""
        self.history_tokens = count_message_tokens(messages)

    def status_line(self) -> str:
        """Human-readable status line."""
        return (
            f"Tokens: {self.current_usage:,}/{self.max_tokens:,} "
            f"({self.usage_ratio:.0%}) | "
            f"System: {self.system_tokens:,} | "
            f"Tools: {self.tool_schema_tokens:,} | "
            f"History: {self.history_tokens:,} | "
            f"Remaining: {self.remaining:,}"
        )
