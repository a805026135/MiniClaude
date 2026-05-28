"""Base Skill abstraction - high-level capabilities built on top of atomic tools."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class SkillMeta(BaseModel):
    """Metadata for a Skill, used for routing and indexing."""

    name: str
    description: str
    tags: list[str] = []
    examples: list[str] = []          # Example user queries that trigger this skill
    prerequisites: list[str] = []     # Conditions that must be met
    applicable_when: str = ""         # Natural language description of when to use
    tools_used: list[str] = []        # Atomic tools this skill depends on


class SkillContext(BaseModel):
    """Context passed to a Skill during execution."""

    user_query: str
    matched_files: list[str] = []
    conversation_history: list[dict[str, Any]] = []
    metadata: dict[str, Any] = {}

    model_config = {"arbitrary_types_allowed": True}


class SkillResult(BaseModel):
    """Result returned by a Skill execution."""

    skill_name: str
    success: bool
    instructions: str = ""   # Enhanced instructions to inject into the system prompt
    context: str = ""        # Additional context for the LLM
    suggested_tools: list[str] = []  # Tools the skill recommends using
    metadata: dict[str, Any] = {}


class BaseSkill(ABC):
    """Abstract base class for high-level Skills.

    Skills are higher-level capabilities that combine multiple atomic tools
    to accomplish complex tasks (e.g., code review, refactoring, debugging).

    A Skill doesn't execute tools directly — it provides enhanced instructions
    and context to the LLM, guiding it to use the right tools in the right order.
    """

    @property
    @abstractmethod
    def meta(self) -> SkillMeta:
        """Skill metadata for routing and indexing."""
        ...

    @property
    def name(self) -> str:
        return self.meta.name

    @property
    def description(self) -> str:
        return self.meta.description

    @property
    def tags(self) -> list[str]:
        return self.meta.tags

    @property
    def examples(self) -> list[str]:
        return self.meta.examples

    @abstractmethod
    async def execute(self, context: SkillContext) -> SkillResult:
        """Execute the skill and return enhanced instructions.

        Args:
            context: The skill execution context including user query.

        Returns:
            SkillResult with instructions for the LLM.
        """
        ...

    def can_handle(self, query: str) -> float:
        """Estimate how well this skill can handle a given query.

        Returns a score from 0.0 to 1.0. Default uses keyword matching.

        Args:
            query: The user's input query.

        Returns:
            Relevance score (0.0 = not relevant, 1.0 = highly relevant).
        """
        query_lower = query.lower()
        score = 0.0

        # Tag matching
        for tag in self.meta.tags:
            if tag.lower() in query_lower:
                score += 0.3

        # Example similarity (simple word overlap)
        query_words = set(query_lower.split())
        for example in self.meta.examples:
            example_words = set(example.lower().split())
            overlap = len(query_words & example_words)
            if overlap > 0:
                score += 0.2 * (overlap / max(len(example_words), 1))

        # Description keyword matching
        desc_words = set(self.meta.description.lower().split())
        overlap = len(query_words & desc_words)
        if overlap > 0:
            score += 0.1 * (overlap / max(len(desc_words), 1))

        return min(score, 1.0)

    def __repr__(self) -> str:
        return f"<Skill:{self.name}>"
