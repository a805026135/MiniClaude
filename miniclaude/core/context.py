"""Conversation context management."""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any

from miniclaude.core.config import MiniClaudeConfig

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_TEMPLATE = """You are MiniClaude, an AI coding assistant. You help users with software development tasks including:
- Reading, writing, and editing code files
- Searching codebases (file patterns and content search)
- Running shell commands (tests, builds, git operations)
- Analyzing code quality and suggesting improvements

## Guidelines
1. Always think step-by-step before acting
2. Read relevant files before making changes
3. Prefer editing existing files over creating new ones
4. Test changes when possible
5. Be concise but thorough in explanations
6. Ask for clarification when the task is ambiguous

## Safety Rules
- Never modify files outside the project directory without explicit permission
- Always confirm before running destructive commands
- Do not expose secrets, credentials, or API keys
- Explain what you plan to do before making significant changes

{memory_context}

{skill_context}
"""


class ConversationContext:
    """Manages the conversation message history and system prompt.

    Handles:
    - System prompt construction with memory/skill injection
    - Message history management
    - Session persistence
    """

    def __init__(self, config: MiniClaudeConfig) -> None:
        self.config = config
        self.session_id = str(uuid.uuid4())[:8]
        self.messages: list[dict[str, Any]] = []
        self._memory_context: str = ""
        self._skill_context: str = ""
        self._system_prompt: str = ""

    def build_system_prompt(
        self,
        memory_context: str = "",
        skill_context: str = "",
    ) -> str:
        """Build the system prompt with injected context."""
        self._memory_context = memory_context
        self._skill_context = skill_context
        self._system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            memory_context=memory_context,
            skill_context=skill_context,
        )
        return self._system_prompt

    @property
    def system_prompt(self) -> str:
        """Get the current system prompt."""
        if not self._system_prompt:
            self.build_system_prompt()
        return self._system_prompt

    def add_user_message(self, content: str) -> None:
        """Add a user message to the conversation."""
        self.messages.append({"role": "user", "content": content})

    def add_assistant_message(self, content: str | list[dict[str, Any]]) -> None:
        """Add an assistant message to the conversation."""
        self.messages.append({"role": "assistant", "content": content})

    def add_raw_message(self, message: dict[str, Any]) -> None:
        """Add a raw message dict directly to the conversation.

        Used for OpenAI-format messages that include tool_calls,
        tool role messages, etc.
        """
        self.messages.append(message)

    def add_tool_results(self, results: list[dict[str, Any]]) -> None:
        """Add tool result messages to the conversation.

        In OpenAI format, these are individual 'tool' role messages.
        """
        for result_msg in results:
            self.messages.append(result_msg)

    def get_messages(self) -> list[dict[str, Any]]:
        """Get all conversation messages."""
        return list(self.messages)

    def get_last_n_messages(self, n: int) -> list[dict[str, Any]]:
        """Get the last N messages."""
        return self.messages[-n:] if n > 0 else []

    def clear(self) -> None:
        """Clear conversation history but keep system prompt."""
        self.messages.clear()
        self.session_id = str(uuid.uuid4())[:8]
        logger.info("Conversation cleared. New session: %s", self.session_id)

    def save_session(self, path: Path | None = None) -> Path:
        """Save conversation to disk."""
        save_dir = path or self.config.sessions_dir
        save_path = save_dir / f"session_{self.session_id}.json"

        data = {
            "session_id": self.session_id,
            "timestamp": datetime.now().isoformat(),
            "system_prompt": self._system_prompt,
            "messages": self.messages,
        }

        save_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info("Session saved: %s", save_path)
        return save_path

    def load_session(self, session_path: Path) -> None:
        """Load a conversation from disk."""
        data = json.loads(session_path.read_text(encoding="utf-8"))
        self.session_id = data["session_id"]
        self._system_prompt = data.get("system_prompt", "")
        self.messages = data.get("messages", [])
        logger.info("Session loaded: %s (%d messages)", self.session_id, len(self.messages))

    @property
    def message_count(self) -> int:
        return len(self.messages)

    def __len__(self) -> int:
        return len(self.messages)
