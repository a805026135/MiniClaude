"""Context Manager - orchestrates all context compression subsystems."""

from __future__ import annotations

import logging
from typing import Any

from miniclaude.context.budget import TokenBudget
from miniclaude.context.compressor import ContextCompressor
from miniclaude.context.externalizer import Externalizer
from miniclaude.context.placeholder import PlaceholderManager
from miniclaude.core.config import MiniClaudeConfig
from miniclaude.tools.base import ToolResult

logger = logging.getLogger(__name__)


class ContextManager:
    """Orchestrates context management across all compression layers.

    Coordinates:
    - TokenBudget: tracks usage against limits
    - Externalizer: saves large results to disk
    - PlaceholderManager: manages reference placeholders
    - ContextCompressor: compresses history when needed

    Compression Pipeline:
    Summary Preview → Placeholder Replace → On-demand Retrieval → Overflow Fallback
    """

    def __init__(self, config: MiniClaudeConfig) -> None:
        self.config = config
        self.budget = TokenBudget(max_tokens=config.context_limit)
        self.externalizer = Externalizer(config)
        self.placeholders = PlaceholderManager()
        self.compressor = ContextCompressor()

    def process_tool_result(self, result: ToolResult) -> ToolResult:
        """Process a tool result through the externalization pipeline.

        If the result is too large, it gets saved to disk and replaced
        with a summary + placeholder.
        """
        return self.externalizer.process(result)

    def process_tool_results(self, results: list[ToolResult]) -> list[ToolResult]:
        """Process a batch of tool results."""
        return self.externalizer.process_batch(results)

    def check_and_compress(
        self,
        messages: list[dict[str, Any]],
        system_prompt: str,
        tool_schemas: list[dict],
    ) -> list[dict[str, Any]]:
        """Check context usage and compress if needed.

        This should be called before each LLM request.

        Args:
            messages: Current conversation messages.
            system_prompt: The system prompt text.
            tool_schemas: Tool schema definitions.

        Returns:
            Possibly compressed messages.
        """
        # Update budget tracking
        self.budget.update_system_tokens(system_prompt)
        self.budget.update_tool_schema_tokens(tool_schemas)
        self.budget.update_history_tokens(messages)

        logger.debug("Context: %s", self.budget.status_line())

        if not self.budget.needs_compression():
            return messages

        logger.warning("Context compression needed: %s", self.budget.status_line())

        # Run compression
        target_tokens = int(self.budget.available_for_history * 0.7)
        compressed = self.compressor.compress_messages(
            messages,
            target_tokens=target_tokens,
            current_tokens=self.budget.history_tokens,
        )

        # Update budget after compression
        self.budget.update_history_tokens(compressed)

        logger.info("After compression: %s", self.budget.status_line())
        return compressed

    def get_status(self) -> dict[str, Any]:
        """Get context management status."""
        return {
            "budget": self.budget.status_line(),
            "usage_ratio": self.budget.usage_ratio,
            "externalized_count": self.externalizer.externalized_count,
            "placeholder_count": self.placeholders.count,
            "needs_compression": self.budget.needs_compression(),
        }
