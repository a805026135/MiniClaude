"""Memory type definitions."""

from __future__ import annotations

from enum import Enum


class MemoryType(str, Enum):
    """Types of memories stored by the system."""

    PROCEDURAL = "procedural"    # How to do things (skills, patterns, techniques)
    EPISODIC = "episodic"        # Past interactions (what happened, decisions made)
    PROFILE = "profile"          # User preferences and characteristics

    @classmethod
    def from_str(cls, value: str) -> "MemoryType":
        """Parse from string, defaulting to EPISODIC."""
        try:
            return cls(value.lower())
        except ValueError:
            return cls.EPISODIC


class RiskLevel(str, Enum):
    """Risk levels for security classification."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
