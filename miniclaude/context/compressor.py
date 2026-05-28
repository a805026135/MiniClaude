"""Context Compressor - compresses conversation history when approaching limits."""

from __future__ import annotations

import logging
from typing import Any

from miniclaude.llm.token_counter import count_tokens, truncate_to_tokens

logger = logging.getLogger(__name__)


class ContextCompressor:
    """Compresses conversation history using multiple strategies.

    Strategy hierarchy:
    1. Tool result truncation (most impactful)
    2. Old message summarization
    3. Message dropping (last resort)
    """

    # Token budget for a single tool result
    MAX_TOOL_RESULT_TOKENS = 2000
    # Summary length target for old messages
    SUMMARY_TOKENS = 200

    def compress_messages(
        self,
        messages: list[dict[str, Any]],
        target_tokens: int,
        current_tokens: int,
    ) -> list[dict[str, Any]]:
        """Compress messages to fit within the target token budget.

        Args:
            messages: Current conversation messages.
            target_tokens: Target token count.
            current_tokens: Current estimated token count.

        Returns:
            Compressed list of messages.
        """
        if current_tokens <= target_tokens:
            return messages

        logger.info(
            "Compressing context: %d tokens → target %d tokens",
            current_tokens, target_tokens,
        )

        compressed = list(messages)
        reduction = current_tokens - target_tokens

        # Strategy 1: Truncate large tool results
        compressed, reduced = self._truncate_tool_results(compressed, reduction)
        reduction -= reduced
        if reduction <= 0:
            return compressed

        # Strategy 2: Summarize old assistant messages
        compressed, reduced = self._summarize_old_messages(compressed, reduction)
        reduction -= reduced
        if reduction <= 0:
            return compressed

        # Strategy 3: Drop oldest messages (keep first user + last N)
        compressed = self._drop_old_messages(compressed, target_tokens)

        logger.info("Compression complete: %d messages remaining", len(compressed))
        return compressed

    def _truncate_tool_results(
        self,
        messages: list[dict],
        target_reduction: int,
    ) -> tuple[list[dict], int]:
        """Truncate large tool results in-place."""
        reduced = 0

        for msg in messages:
            if msg.get("role") != "user":
                continue
            content = msg.get("content")
            if not isinstance(content, list):
                continue

            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") != "tool_result":
                    continue

                result_text = block.get("content", "")
                if isinstance(result_text, str) and count_tokens(result_text) > self.MAX_TOOL_RESULT_TOKENS:
                    original_tokens = count_tokens(result_text)
                    truncated = truncate_to_tokens(result_text, self.MAX_TOOL_RESULT_TOKENS)
                    block["content"] = truncated + "\n[...context compressed...]"
                    reduced += original_tokens - count_tokens(truncated)

                    if reduced >= target_reduction:
                        break

        return messages, reduced

    def _summarize_old_messages(
        self,
        messages: list[dict],
        target_reduction: int,
    ) -> tuple[list[dict], int]:
        """Replace old assistant messages with summaries."""
        reduced = 0
        # Skip the first 2 and last 4 messages
        if len(messages) <= 6:
            return messages, 0

        for i in range(2, len(messages) - 4):
            msg = messages[i]
            if msg.get("role") != "assistant":
                continue

            content = msg.get("content", "")
            if isinstance(content, str) and count_tokens(content) > self.SUMMARY_TOKENS:
                original_tokens = count_tokens(content)
                # Simple summary: first sentence + truncation
                first_line = content.split("\n")[0]
                if len(first_line) > 200:
                    first_line = first_line[:200] + "..."
                msg["content"] = f"[Previous response summarized] {first_line}"
                reduced += original_tokens - count_tokens(msg["content"])

                if reduced >= target_reduction:
                    break

        return messages, reduced

    def _drop_old_messages(
        self,
        messages: list[dict],
        target_tokens: int,
    ) -> list[dict]:
        """Drop oldest messages, keeping the first user message and last N."""
        if len(messages) <= 4:
            return messages

        # Keep first 1 message + last 6 messages
        kept = [messages[0]] + messages[-6:]

        # Insert a note about dropped messages
        dropped_count = len(messages) - len(kept)
        kept.insert(1, {
            "role": "assistant",
            "content": f"[Context compressed: {dropped_count} earlier messages summarized and removed]",
        })

        return kept
