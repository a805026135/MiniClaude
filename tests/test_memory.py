"""Tests for the memory system."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from miniclaude.memory.models import MemoryEntry
from miniclaude.memory.store import MemoryStore
from miniclaude.memory.types import MemoryType
from miniclaude.memory.retriever import MemoryRetriever


@pytest.fixture
def memory_store(tmp_path: Path) -> MemoryStore:
    """Create a temporary memory store."""
    db_path = tmp_path / "test_memory.db"
    store = MemoryStore(db_path)
    yield store
    store.close()


class TestMemoryStore:
    def test_save_and_get(self, memory_store: MemoryStore):
        entry = MemoryEntry(
            type=MemoryType.PROCEDURAL,
            content="Python projects use pytest for testing",
            summary="pytest is the standard test framework",
            tags=["python", "testing"],
        )
        memory_store.save(entry)

        retrieved = memory_store.get(entry.id)
        assert retrieved is not None
        assert retrieved.content == "Python projects use pytest for testing"
        assert retrieved.type == MemoryType.PROCEDURAL
        assert "python" in retrieved.tags

    def test_search(self, memory_store: MemoryStore):
        # Save multiple entries
        for content, tags in [
            ("Use pytest for Python testing", ["python", "testing"]),
            ("JavaScript uses Jest for testing", ["javascript", "testing"]),
            ("User prefers dark mode", ["preference", "ui"]),
        ]:
            entry = MemoryEntry(
                type=MemoryType.PROCEDURAL,
                content=content,
                tags=tags,
            )
            memory_store.save(entry)

        # Search for testing-related
        results = memory_store.search("testing Python")
        assert len(results) > 0
        assert any("pytest" in r.entry.content for r in results)

    def test_search_by_type(self, memory_store: MemoryStore):
        memory_store.save(MemoryEntry(
            type=MemoryType.PROCEDURAL, content="procedural memory"
        ))
        memory_store.save(MemoryEntry(
            type=MemoryType.EPISODIC, content="episodic memory"
        ))

        results = memory_store.search("", memory_type=MemoryType.PROCEDURAL)
        assert all(r.entry.type == MemoryType.PROCEDURAL for r in results)

    def test_delete(self, memory_store: MemoryStore):
        entry = MemoryEntry(type=MemoryType.EPISODIC, content="to be deleted")
        memory_store.save(entry)
        assert memory_store.get(entry.id) is not None

        memory_store.delete(entry.id)
        assert memory_store.get(entry.id) is None

    def test_count(self, memory_store: MemoryStore):
        assert memory_store.count() == 0
        memory_store.save(MemoryEntry(type=MemoryType.PROCEDURAL, content="a"))
        memory_store.save(MemoryEntry(type=MemoryType.EPISODIC, content="b"))
        assert memory_store.count() == 2
        assert memory_store.count(MemoryType.PROCEDURAL) == 1

    def test_decay_relevance(self, memory_store: MemoryStore):
        entry = MemoryEntry(type=MemoryType.EPISODIC, content="test", relevance_score=1.0)
        memory_store.save(entry)
        memory_store.decay_relevance(0.5)

        retrieved = memory_store.get(entry.id)
        assert retrieved is not None
        assert retrieved.relevance_score == 0.5


class TestMemoryRetriever:
    def test_retrieve_relevant(self, memory_store: MemoryStore):
        retriever = MemoryRetriever(memory_store)

        memory_store.save(MemoryEntry(
            type=MemoryType.PROCEDURAL,
            content="Use pytest for Python unit tests",
            tags=["python", "testing"],
        ))
        memory_store.save(MemoryEntry(
            type=MemoryType.PROFILE,
            content="User prefers concise code with type hints",
            tags=["preference"],
        ))

        results = retriever.retrieve("write tests for Python code")
        assert len(results) > 0

    def test_format_for_context(self, memory_store: MemoryStore):
        retriever = MemoryRetriever(memory_store)

        memory_store.save(MemoryEntry(
            type=MemoryType.PROCEDURAL,
            content="Use pytest for testing",
        ))

        entries = retriever.retrieve("testing")
        formatted = retriever.format_for_context(entries)
        assert "Procedural Knowledge" in formatted or "pytest" in formatted
