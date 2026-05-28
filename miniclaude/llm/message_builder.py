"""Message builder - constructs OpenAI-compatible message arrays."""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class MessageBuilder:
    """Builds and formats messages for the OpenAI-compatible API.

    Handles:
    - Converting tool results to OpenAI's expected format
    - Building content blocks for multi-part messages
    """

    @staticmethod
    def tool_results_to_message(
        tool_calls: list[dict[str, Any]],
        results: list[Any],
    ) -> list[dict[str, Any]]:
        """Convert tool execution results to OpenAI-compatible messages.

        In OpenAI format, we need:
        1. An assistant message with tool_calls
        2. One tool message per tool call result

        Args:
            tool_calls: Original tool call dicts from the assistant.
            results: ToolResult objects from execution.

        Returns:
            List of message dicts (assistant + tool results).
        """
        messages: list[dict[str, Any]] = []

        # 1. Assistant message with tool_calls
        assistant_tool_calls = []
        for tc in tool_calls:
            assistant_tool_calls.append({
                "id": tc["id"],
                "type": "function",
                "function": {
                    "name": tc["name"],
                    "arguments": _serialize_args(tc.get("input", {})),
                },
            })

        messages.append({
            "role": "assistant",
            "tool_calls": assistant_tool_calls,
        })

        # 2. Tool result messages (one per tool call)
        for tc, result in zip(tool_calls, results):
            content = result.content if result.success else f"Error: {result.content}"
            messages.append({
                "role": "tool",
                "tool_call_id": tc["id"],
                "content": content,
            })

        return messages

    @staticmethod
    def build_assistant_with_tool_use(
        text: str,
        tool_calls: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Build an assistant message containing tool calls.

        In OpenAI format, the assistant message has both content and tool_calls.

        Args:
            text: Text content from the assistant.
            tool_calls: Tool call dicts with 'id', 'name', 'input'.

        Returns:
            Assistant message dict.
        """
        assistant_tc = []
        for tc in tool_calls:
            assistant_tc.append({
                "id": tc["id"],
                "type": "function",
                "function": {
                    "name": tc["name"],
                    "arguments": _serialize_args(tc.get("input", {})),
                },
            })

        msg: dict[str, Any] = {
            "role": "assistant",
            "content": text or None,
            "tool_calls": assistant_tc,
        }
        return msg

    @staticmethod
    def build_user_message(text: str) -> dict[str, Any]:
        """Build a simple user text message."""
        return {"role": "user", "content": text}


def _serialize_args(args: dict[str, Any]) -> str:
    """Serialize tool arguments to JSON string."""
    import json
    try:
        return json.dumps(args, ensure_ascii=False)
    except (TypeError, ValueError):
        return str(args)
