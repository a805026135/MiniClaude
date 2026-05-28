"""SQLite-backed memory storage with full CRUD operations."""

from __future__ import annotations

import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from miniclaude.memory.models import MemoryEntry, MemorySearchResult
from miniclaude.memory.types import MemoryType

logger = logging.getLogger(__name__)

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS memories (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    content TEXT NOT NULL,
    summary TEXT DEFAULT '',
    tags TEXT DEFAULT '[]',
    source_session TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    accessed_at TEXT NOT NULL,
    access_count INTEGER DEFAULT 0,
    relevance_score REAL DEFAULT 1.0,
    metadata TEXT DEFAULT '{}'
);
"""

CREATE_INDEX_SQL = [
    "CREATE INDEX IF NOT EXISTS idx_type ON memories(type);",
    "CREATE INDEX IF NOT EXISTS idx_created ON memories(created_at);",
    "CREATE INDEX IF NOT EXISTS idx_relevance ON memories(relevance_score DESC);",
]


class MemoryStore:
    """SQLite-backed persistent memory storage.

    Stores procedural, episodic, and profile memories with
    full-text search and relevance scoring.
    """

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self._conn: sqlite3.Connection | None = None

    def _connect(self) -> sqlite3.Connection:
        """Get or create database connection."""
        if self._conn is None:
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row
            self._init_schema()
        return self._conn

    def _init_schema(self) -> None:
        """Initialize database schema."""
        conn = self._conn
        assert conn is not None
        conn.execute(CREATE_TABLE_SQL)
        for idx_sql in CREATE_INDEX_SQL:
            conn.execute(idx_sql)
        conn.commit()
        logger.info("Memory database initialized: %s", self.db_path)

    def save(self, entry: MemoryEntry) -> None:
        """Save or update a memory entry."""
        conn = self._connect()
        conn.execute(
            """
            INSERT OR REPLACE INTO memories
            (id, type, content, summary, tags, source_session,
             created_at, accessed_at, access_count, relevance_score, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                entry.id,
                entry.type.value,
                entry.content,
                entry.summary,
                json.dumps(entry.tags, ensure_ascii=False),
                entry.source_session,
                entry.created_at.isoformat(),
                entry.accessed_at.isoformat(),
                entry.access_count,
                entry.relevance_score,
                json.dumps(entry.metadata, ensure_ascii=False),
            ),
        )
        conn.commit()
        logger.debug("Saved memory: %s [%s]", entry.id, entry.type.value)

    def get(self, memory_id: str) -> MemoryEntry | None:
        """Get a memory entry by ID."""
        conn = self._connect()
        row = conn.execute(
            "SELECT * FROM memories WHERE id = ?", (memory_id,)
        ).fetchone()
        if row:
            return self._row_to_entry(row)
        return None

    def search(
        self,
        query: str,
        memory_type: MemoryType | None = None,
        tags: list[str] | None = None,
        limit: int = 10,
    ) -> list[MemorySearchResult]:
        """Search memories by content keywords and optional filters.

        Uses SQLite LIKE-based search (simple but effective for this scale).
        """
        conn = self._connect()

        conditions: list[str] = []
        params: list[Any] = []

        # Text search
        if query:
            query_words = query.lower().split()
            word_conditions = []
            for word in query_words[:5]:  # limit to 5 keywords
                word_conditions.append("LOWER(content) LIKE ?")
                params.append(f"%{word}%")
            conditions.append(f"({' AND '.join(word_conditions)})")

        # Type filter
        if memory_type:
            conditions.append("type = ?")
            params.append(memory_type.value)

        # Tag filter
        if tags:
            for tag in tags:
                conditions.append("tags LIKE ?")
                params.append(f"%{tag}%")

        where = " AND ".join(conditions) if conditions else "1=1"
        params.append(limit)

        rows = conn.execute(
            f"""
            SELECT * FROM memories
            WHERE {where}
            ORDER BY relevance_score DESC, accessed_at DESC
            LIMIT ?
            """,
            params,
        ).fetchall()

        results = []
        for row in rows:
            entry = self._row_to_entry(row)
            # Simple relevance score based on keyword matches
            score = entry.relevance_score
            if query:
                content_lower = entry.content.lower()
                for word in query.lower().split():
                    if word in content_lower:
                        score += 0.2
            results.append(MemorySearchResult(entry=entry, score=min(score, 1.0)))

        results.sort(key=lambda r: r.score, reverse=True)
        return results

    def get_by_type(
        self,
        memory_type: MemoryType,
        limit: int = 50,
    ) -> list[MemoryEntry]:
        """Get all memories of a specific type."""
        conn = self._connect()
        rows = conn.execute(
            "SELECT * FROM memories WHERE type = ? ORDER BY accessed_at DESC LIMIT ?",
            (memory_type.value, limit),
        ).fetchall()
        return [self._row_to_entry(row) for row in rows]

    def get_recent(self, limit: int = 20) -> list[MemoryEntry]:
        """Get most recently accessed memories."""
        conn = self._connect()
        rows = conn.execute(
            "SELECT * FROM memories ORDER BY accessed_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [self._row_to_entry(row) for row in rows]

    def delete(self, memory_id: str) -> bool:
        """Delete a memory entry."""
        conn = self._connect()
        cursor = conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        conn.commit()
        return cursor.rowcount > 0

    def count(self, memory_type: MemoryType | None = None) -> int:
        """Count total memories."""
        conn = self._connect()
        if memory_type:
            row = conn.execute(
                "SELECT COUNT(*) FROM memories WHERE type = ?",
                (memory_type.value,),
            ).fetchone()
        else:
            row = conn.execute("SELECT COUNT(*) FROM memories").fetchone()
        return row[0] if row else 0

    def decay_relevance(self, factor: float = 0.99) -> int:
        """Decay relevance scores over time (call periodically)."""
        conn = self._connect()
        cursor = conn.execute(
            "UPDATE memories SET relevance_score = relevance_score * ? WHERE relevance_score > 0.1",
            (factor,),
        )
        conn.commit()
        return cursor.rowcount

    def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    @staticmethod
    def _row_to_entry(row: sqlite3.Row) -> MemoryEntry:
        """Convert a database row to a MemoryEntry."""
        return MemoryEntry(
            id=row["id"],
            type=MemoryType.from_str(row["type"]),
            content=row["content"],
            summary=row["summary"] or "",
            tags=json.loads(row["tags"]) if row["tags"] else [],
            source_session=row["source_session"] or "",
            created_at=datetime.fromisoformat(row["created_at"]),
            accessed_at=datetime.fromisoformat(row["accessed_at"]),
            access_count=row["access_count"],
            relevance_score=row["relevance_score"],
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
        )
