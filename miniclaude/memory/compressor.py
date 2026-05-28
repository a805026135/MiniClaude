"""Memory Compressor - condenses and merges memories to save space."""

from __future__ import annotations

import logging
from typing import Any

from miniclaude.memory.models import MemoryEntry
from miniclaude.memory.store import MemoryStore
from miniclaude.memory.types import MemoryType

logger = logging.getLogger(__name__)

# Thresholds for memory management
MAX_MEMORIES_PER_TYPE = 100
LOW_RELEVANCE_THRESHOLD = 0.3
OLD_MEMORY_DAYS = 30


class MemoryCompressor:
    """Compresses and manages memory lifecycle.

    Operations:
    - Remove low-relevance entries
    - Merge similar entries
    - Archive old episodic memories
    """

    def __init__(self, store: MemoryStore) -> None:
        self.store = store

    def cleanup(self) -> dict[str, int]:
        """Run all compression operations and return stats."""
        stats = {
            "decayed": 0,
            "removed": 0,
            "total_before": self.store.count(),
        }

        # 1. Decay relevance scores
        stats["decayed"] = self.store.decay_relevance(0.95)

        # 2. Remove very low relevance entries
        all_memories = self.store.get_recent(limit=1000)
        for entry in all_memories:
            if entry.relevance_score < LOW_RELEVANCE_THRESHOLD and entry.access_count < 2:
                self.store.delete(entry.id)
                stats["removed"] += 1

        stats["total_after"] = self.store.count()
        logger.info(
            "Memory cleanup: %d decayed, %d removed, %d → %d total",
            stats["decayed"], stats["removed"],
            stats["total_before"], stats["total_after"],
        )
        return stats

    def get_stats(self) -> dict[str, Any]:
        """Get memory statistics."""
        return {
            "total": self.store.count(),
            "procedural": self.store.count(MemoryType.PROCEDURAL),
            "episodic": self.store.count(MemoryType.EPISODIC),
            "profile": self.store.count(MemoryType.PROFILE),
        }
