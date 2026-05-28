"""Placeholder management for externalized content references."""

from __future__ import annotations

import re
from typing import Any


# Placeholder format: [REF:{hash}]
PLACEHOLDER_PATTERN = re.compile(r'\[REF:([a-f0-9]+)\]')


class PlaceholderManager:
    """Manages placeholders that replace externalized content in conversation history.

    When messages become too long, large tool results are replaced with
    placeholders like [REF:abc123def456]. This manager tracks these
    replacements and can restore content on demand.
    """

    def __init__(self) -> None:
        self._registry: dict[str, PlaceholderEntry] = {}

    def register(
        self,
        ref_id: str,
        original_content: str,
        summary: str,
        tool_name: str,
        file_path: str | None = None,
    ) -> str:
        """Register an externalized content and return its placeholder.

        Args:
            ref_id: Unique reference ID (hash).
            original_content: The full original content.
            summary: Brief summary of the content.
            tool_name: Name of the tool that produced the content.
            file_path: Path to the externalized file on disk.

        Returns:
            The placeholder string to use in place of the content.
        """
        self._registry[ref_id] = PlaceholderEntry(
            ref_id=ref_id,
            original_content=original_content,
            summary=summary,
            tool_name=tool_name,
            file_path=file_path,
        )
        return f"[REF:{ref_id}]"

    def resolve(self, ref_id: str) -> str | None:
        """Resolve a placeholder to its full content.

        Args:
            ref_id: The reference ID from the placeholder.

        Returns:
            Full content if found, None otherwise.
        """
        entry = self._registry.get(ref_id)
        if entry:
            entry.access_count += 1
            return entry.original_content
        return None

    def get_summary(self, ref_id: str) -> str | None:
        """Get the summary for a placeholder without full content."""
        entry = self._registry.get(ref_id)
        return entry.summary if entry else None

    def find_placeholders(self, text: str) -> list[str]:
        """Find all placeholder references in a text."""
        return PLACEHOLDER_PATTERN.findall(text)

    def replace_in_text(self, text: str, expand: bool = False) -> str:
        """Replace placeholders in text with either full content or summary.

        Args:
            text: Text containing placeholders.
            expand: If True, replace with full content. If False, use summary.

        Returns:
            Text with placeholders replaced.
        """
        def _replacer(match: re.Match) -> str:
            ref_id = match.group(1)
            if expand:
                content = self.resolve(ref_id)
                if content:
                    return content
            summary = self.get_summary(ref_id)
            if summary:
                return f"[Ref:{ref_id}: {summary}]"
            return match.group(0)

        return PLACEHOLDER_PATTERN.sub(_replacer, text)

    @property
    def count(self) -> int:
        return len(self._registry)


class PlaceholderEntry:
    """A single placeholder entry."""

    __slots__ = ("ref_id", "original_content", "summary", "tool_name", "file_path", "access_count")

    def __init__(
        self,
        ref_id: str,
        original_content: str,
        summary: str,
        tool_name: str,
        file_path: str | None = None,
    ) -> None:
        self.ref_id = ref_id
        self.original_content = original_content
        self.summary = summary
        self.tool_name = tool_name
        self.file_path = file_path
        self.access_count = 0
