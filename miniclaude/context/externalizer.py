"""Externalizer - saves large tool results to disk and replaces with placeholders."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path
from typing import Any

from miniclaude.core.config import MiniClaudeConfig
from miniclaude.tools.base import ToolResult

logger = logging.getLogger(__name__)


class Externalizer:
    """Externalizes large tool results to disk files.

    When a tool result exceeds the threshold:
    1. Save full content to data/externalized/{hash}.md
    2. Generate a summary/preview
    3. Replace the result content with a placeholder + summary

    This keeps the conversation context small while preserving
    the ability to retrieve full results on demand.
    """

    def __init__(self, config: MiniClaudeConfig) -> None:
        self.config = config
        self._externalized: dict[str, str] = {}  # hash -> file path
        self.threshold = config.externalize_threshold

    def process(self, result: ToolResult) -> ToolResult:
        """Process a tool result, externalizing if it's too large.

        Args:
            result: The tool result to potentially externalize.

        Returns:
            The (possibly modified) tool result with externalized content.
        """
        if len(result.content) <= self.threshold:
            return result

        # Generate content hash for deduplication
        content_hash = hashlib.md5(result.content.encode()).hexdigest()[:12]
        filename = f"{result.tool_name}_{content_hash}.md"
        save_path = self.config.externalized_dir / filename

        # Save full content to disk
        save_path.write_text(result.content, encoding="utf-8")
        self._externalized[content_hash] = str(save_path)

        # Generate summary
        summary = self._generate_summary(result.content)

        # Build placeholder content
        placeholder = (
            f"[Result externalized to: {save_path.name}]\n"
            f"[Content: {len(result.content)} chars, {result.content.count(chr(10))} lines]\n\n"
            f"Summary/Preview:\n{summary}\n\n"
            f"[Use read_file to retrieve full content if needed]"
        )

        logger.info(
            "Externalized %s result: %d chars → %s + %d char summary",
            result.tool_name,
            len(result.content),
            save_path.name,
            len(summary),
        )

        result.content = placeholder
        result.truncated = True
        result.external_path = str(save_path)
        return result

    def process_batch(self, results: list[ToolResult]) -> list[ToolResult]:
        """Process a batch of tool results."""
        return [self.process(r) for r in results]

    def retrieve(self, ref_id: str) -> str | None:
        """Retrieve an externalized result by its hash/ID."""
        path = self._externalized.get(ref_id)
        if path and Path(path).exists():
            return Path(path).read_text(encoding="utf-8")
        return None

    @staticmethod
    def _generate_summary(content: str, max_lines: int = 10, max_chars: int = 500) -> str:
        """Generate a summary of the content.

        Takes the first N lines as a preview.
        """
        lines = content.splitlines()
        preview_lines = lines[:max_lines]
        summary = "\n".join(preview_lines)

        if len(summary) > max_chars:
            summary = summary[:max_chars] + "..."
        if len(lines) > max_lines:
            summary += f"\n... ({len(lines) - max_lines} more lines)"

        return summary

    @property
    def externalized_count(self) -> int:
        return len(self._externalized)
