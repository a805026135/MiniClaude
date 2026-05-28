"""Memory tools - read/write memory from within tool calls."""

from __future__ import annotations

import logging
from typing import Any

from miniclaude.core.config import MiniClaudeConfig
from miniclaude.memory.models import MemoryEntry
from miniclaude.memory.store import MemoryStore
from miniclaude.memory.types import MemoryType
from miniclaude.tools.base import BaseTool, ToolResult

logger = logging.getLogger(__name__)


class MemorySaveTool(BaseTool):
    """Save a piece of knowledge to long-term memory."""

    def __init__(self, config: MiniClaudeConfig, store: MemoryStore) -> None:
        self._config = config
        self._store = store

    @property
    def name(self) -> str:
        return "memory_save"

    @property
    def description(self) -> str:
        return (
            "Save a piece of knowledge or experience to long-term memory. "
            "Use this to remember important information for future sessions. "
            "Memory types: procedural (how-to), episodic (events), profile (user prefs)."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "content": {
                "type": "string",
                "description": "The knowledge to remember (concise, self-contained)",
            },
            "type": {
                "type": "string",
                "enum": ["procedural", "episodic", "profile"],
                "description": "Type of memory: procedural (how-to), episodic (event), profile (preference)",
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Tags for categorization and search",
            },
            "summary": {
                "type": "string",
                "description": "One-line summary (optional, auto-generated if omitted)",
            },
        }

    def _get_required_params(self) -> list[str]:
        return ["content", "type"]

    async def execute(self, **kwargs: Any) -> ToolResult:
        content = kwargs.get("content", "")
        mem_type = MemoryType.from_str(kwargs.get("type", "episodic"))
        tags = kwargs.get("tags", [])
        summary = kwargs.get("summary", "")

        if not content:
            return self._error("Empty content")

        entry = MemoryEntry(
            type=mem_type,
            content=content,
            summary=summary or content[:100],
            tags=tags if isinstance(tags, list) else [],
        )

        self._store.save(entry)

        return self._success(
            f"Memory saved: [{mem_type.value}] {entry.summary}",
            metadata={"memory_id": entry.id},
        )


class MemorySearchTool(BaseTool):
    """Search long-term memories."""

    def __init__(self, config: MiniClaudeConfig, store: MemoryStore) -> None:
        self._config = config
        self._store = store

    @property
    def name(self) -> str:
        return "memory_search"

    @property
    def description(self) -> str:
        return (
            "Search long-term memories by keywords. "
            "Returns relevant memories from past sessions."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "query": {
                "type": "string",
                "description": "Search query (keywords)",
            },
            "type": {
                "type": "string",
                "enum": ["procedural", "episodic", "profile", "all"],
                "description": "Filter by memory type. Default: all",
            },
            "limit": {
                "type": "integer",
                "description": "Max results. Default: 5",
            },
        }

    def _get_required_params(self) -> list[str]:
        return ["query"]

    async def execute(self, **kwargs: Any) -> ToolResult:
        query = kwargs.get("query", "")
        mem_type_str = kwargs.get("type", "all")
        limit = kwargs.get("limit", 5) or 5

        if not query:
            return self._error("Empty query")

        mem_type = None if mem_type_str == "all" else MemoryType.from_str(mem_type_str)
        results = self._store.search(query, memory_type=mem_type, limit=limit)

        if not results:
            return self._success("No memories found matching your query.")

        lines = []
        for r in results:
            entry = r.entry
            lines.append(
                f"[{entry.type.value}] (score: {r.score:.2f}) {entry.content}"
            )
            if entry.tags:
                lines.append(f"  tags: {', '.join(entry.tags)}")

        return self._success("\n".join(lines))
