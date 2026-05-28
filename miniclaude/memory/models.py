"""Memory data models using Pydantic."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from miniclaude.memory.types import MemoryType


class MemoryEntry(BaseModel):
    """A single memory entry stored in the system."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:12])
    type: MemoryType
    content: str
    summary: str = ""                     # Short summary for display
    tags: list[str] = Field(default_factory=list)
    source_session: str = ""
    created_at: datetime = Field(default_factory=datetime.now)
    accessed_at: datetime = Field(default_factory=datetime.now)
    access_count: int = 0
    relevance_score: float = 1.0          # Decays over time
    metadata: dict[str, Any] = Field(default_factory=dict)

    def touch(self) -> None:
        """Update access tracking."""
        self.accessed_at = datetime.now()
        self.access_count += 1

    def to_context_string(self) -> str:
        """Format memory for injection into system prompt."""
        parts = [f"[{self.type.value}] {self.content}"]
        if self.tags:
            parts.append(f"  (tags: {', '.join(self.tags)})")
        return "\n".join(parts)


class MemorySearchResult(BaseModel):
    """A memory entry with its search relevance score."""

    entry: MemoryEntry
    score: float


class ReflectionResult(BaseModel):
    """Output from the memory reflection/extraction process."""

    key_decisions: list[str] = Field(default_factory=list)
    lessons_learned: list[str] = Field(default_factory=list)
    user_preferences: list[str] = Field(default_factory=list)
    reusable_patterns: list[str] = Field(default_factory=list)
    notable_events: list[str] = Field(default_factory=list)
