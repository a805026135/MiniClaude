"""Memory Retriever - fetches relevant memories for context injection."""

from __future__ import annotations

import logging
from typing import Any

from miniclaude.memory.models import MemoryEntry, MemorySearchResult
from miniclaude.memory.store import MemoryStore
from miniclaude.memory.types import MemoryType

logger = logging.getLogger(__name__)

MAX_MEMORIES_IN_CONTEXT = 10
MAX_MEMORY_TOKENS = 2000  # Approximate budget for memory context


class MemoryRetriever:
    """Retrieves relevant memories for injection into the system prompt.

    Strategies:
    - Keyword search: Find memories matching the current query
    - Profile injection: Always include user profile memories
    - Recency boost: Include recently accessed memories
    """

    def __init__(self, store: MemoryStore) -> None:
        self.store = store

    def retrieve(
        self,
        query: str,
        limit: int = MAX_MEMORIES_IN_CONTEXT,
    ) -> list[MemoryEntry]:
        """Retrieve relevant memories for the current query.

        Args:
            query: The user's current input/query.
            limit: Maximum number of memories to return.

        Returns:
            List of relevant memory entries, most relevant first.
        """
        results: dict[str, MemoryEntry] = {}

        # 1. Search by query keywords
        query_results = self.store.search(query, limit=limit)
        for r in query_results:
            results[r.entry.id] = r.entry

        # 2. Always include user profile memories
        profile_memories = self.store.get_by_type(MemoryType.PROFILE, limit=3)
        for m in profile_memories:
            results[m.id] = m

        # 3. Include recently accessed procedural memories
        recent_procedural = self.store.get_by_type(MemoryType.PROCEDURAL, limit=3)
        for m in recent_procedural:
            if m.access_count > 0:
                results[m.id] = m

        # Sort by relevance and limit
        sorted_entries = sorted(
            results.values(),
            key=lambda e: e.relevance_score,
            reverse=True,
        )

        entries = sorted_entries[:limit]

        # Touch accessed entries
        for entry in entries:
            entry.touch()

        logger.debug("Retrieved %d memories for query: %s", len(entries), query[:50])
        return entries

    def format_for_context(self, memories: list[MemoryEntry]) -> str:
        """Format memories for injection into the system prompt.

        Returns a structured string that can be inserted into the
        system prompt's memory_context section.
        """
        if not memories:
            return ""

        sections: list[str] = ["## Relevant Memories\n"]

        # Group by type
        by_type: dict[MemoryType, list[MemoryEntry]] = {}
        for m in memories:
            by_type.setdefault(m.type, []).append(m)

        type_labels = {
            MemoryType.PROCEDURAL: "### Procedural Knowledge",
            MemoryType.EPISODIC: "### Past Interactions",
            MemoryType.PROFILE: "### User Profile",
        }

        for mem_type, label in type_labels.items():
            entries = by_type.get(mem_type, [])
            if entries:
                sections.append(label)
                for entry in entries:
                    sections.append(f"- {entry.content}")
                sections.append("")

        return "\n".join(sections)
