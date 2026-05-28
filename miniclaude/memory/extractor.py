"""Memory Extractor - reflects on interactions and extracts reusable memories.

Pipeline: Execute → Reflect → Distill → Classify → Store
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from typing import Any

from miniclaude.llm.client import ClaudeClient
from miniclaude.memory.models import MemoryEntry, ReflectionResult
from miniclaude.memory.store import MemoryStore
from miniclaude.memory.types import MemoryType

logger = logging.getLogger(__name__)

REFLECTION_PROMPT = """Analyze the following conversation and extract reusable knowledge.

User Query: {query}

Conversation Summary:
{conversation_summary}

Extract the following in JSON format:
{{
    "key_decisions": ["decision 1", "decision 2"],
    "lessons_learned": ["lesson 1", "lesson 2"],
    "user_preferences": ["preference 1"],
    "reusable_patterns": ["pattern 1"],
    "notable_events": ["event 1"]
}}

Focus on:
- Technical decisions and their rationale
- Patterns that could help with future similar tasks
- User preferences and working style
- Any debugging insights or solutions found
- File/project structure knowledge gained

Only extract genuinely useful, non-obvious information. Return empty arrays for categories with nothing notable.
"""

DISTILL_PROMPT = """Convert the following reflection into concise, reusable memory entries.

Reflection:
{reflection_json}

For each useful piece of knowledge, create a memory entry in JSON format:
{{
    "entries": [
        {{
            "type": "procedural|episodic|profile",
            "content": "Concise, self-contained description of the knowledge",
            "summary": "One-line summary",
            "tags": ["tag1", "tag2"]
        }}
    ]
}}

Rules:
- procedural: How-to knowledge, techniques, patterns
- episodic: What happened in this specific interaction
- profile: User preferences, style, working habits
- Each entry should be self-contained and understandable without context
- Keep content under 200 characters
- Use specific, searchable tags
"""


class MemoryExtractor:
    """Extracts reusable memories from completed interactions.

    Uses a two-step LLM process:
    1. Reflect on the interaction to identify key insights
    2. Distill insights into structured memory entries
    """

    def __init__(self, llm_client: ClaudeClient, store: MemoryStore) -> None:
        self.llm = llm_client
        self.store = store

    async def extract(
        self,
        query: str,
        messages: list[dict[str, Any]],
        response_text: str,
        session_id: str = "",
    ) -> list[MemoryEntry]:
        """Extract memories from a completed interaction.

        Args:
            query: The original user query.
            messages: The full conversation messages.
            response_text: The final assistant response.
            session_id: Current session identifier.

        Returns:
            List of newly created memory entries.
        """
        # Only extract if the interaction was substantial
        if len(messages) < 3:
            logger.debug("Interaction too short for memory extraction")
            return []

        try:
            # Step 1: Reflect
            reflection = await self._reflect(query, messages, response_text)
            if not reflection:
                return []

            # Step 2: Distill
            entries = await self._distill(reflection, session_id)

            # Step 3: Deduplicate against existing
            new_entries = self._deduplicate(entries)

            # Step 4: Store
            for entry in new_entries:
                self.store.save(entry)
                logger.info("Stored memory: [%s] %s", entry.type.value, entry.summary)

            return new_entries

        except Exception as e:
            logger.error("Memory extraction failed: %s", e, exc_info=True)
            return []

    async def _reflect(
        self,
        query: str,
        messages: list[dict[str, Any]],
        response_text: str,
    ) -> ReflectionResult | None:
        """Step 1: Reflect on the interaction."""
        # Build a concise conversation summary
        summary_parts = []
        for msg in messages[-10:]:  # Last 10 messages
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            if isinstance(content, str):
                summary_parts.append(f"{role}: {content[:300]}")
            elif isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        summary_parts.append(f"{role}: {block['text'][:300]}")

        conversation_summary = "\n".join(summary_parts)

        prompt = REFLECTION_PROMPT.format(
            query=query[:500],
            conversation_summary=conversation_summary[:3000],
        )

        response = await self.llm.chat(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000,
        )

        if not response.text:
            return None

        try:
            # Extract JSON from response
            json_text = self._extract_json(response.text)
            data = json.loads(json_text)
            return ReflectionResult(**data)
        except (json.JSONDecodeError, Exception) as e:
            logger.warning("Failed to parse reflection: %s", e)
            return None

    async def _distill(
        self,
        reflection: ReflectionResult,
        session_id: str,
    ) -> list[MemoryEntry]:
        """Step 2: Distill reflection into memory entries."""
        prompt = DISTILL_PROMPT.format(
            reflection_json=reflection.model_dump_json(indent=2),
        )

        response = await self.llm.chat(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1500,
        )

        if not response.text:
            return []

        try:
            json_text = self._extract_json(response.text)
            data = json.loads(json_text)

            entries = []
            for item in data.get("entries", []):
                entry = MemoryEntry(
                    type=MemoryType.from_str(item.get("type", "episodic")),
                    content=item.get("content", ""),
                    summary=item.get("summary", ""),
                    tags=item.get("tags", []),
                    source_session=session_id,
                )
                if entry.content:
                    entries.append(entry)

            return entries

        except (json.JSONDecodeError, Exception) as e:
            logger.warning("Failed to parse distilled memories: %s", e)
            return []

    def _deduplicate(self, entries: list[MemoryEntry]) -> list[MemoryEntry]:
        """Remove entries that are too similar to existing memories."""
        new_entries = []
        for entry in entries:
            # Search for similar existing memories
            results = self.store.search(
                entry.content[:100],
                memory_type=entry.type,
                limit=3,
            )

            # Check if any existing memory is very similar
            is_duplicate = False
            for result in results:
                if result.score > 0.8:
                    is_duplicate = True
                    # Touch the existing entry to boost its relevance
                    result.entry.touch()
                    self.store.save(result.entry)
                    break

            if not is_duplicate:
                new_entries.append(entry)

        return new_entries

    @staticmethod
    def _extract_json(text: str) -> str:
        """Extract JSON from LLM response (handles markdown code blocks)."""
        # Try to find JSON in code blocks
        import re
        json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?```', text, re.DOTALL)
        if json_match:
            return json_match.group(1).strip()

        # Try to find raw JSON
        start = text.find('{')
        end = text.rfind('}')
        if start != -1 and end != -1:
            return text[start:end + 1]

        return text
