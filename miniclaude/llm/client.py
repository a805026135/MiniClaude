"""OpenAI-compatible LLM client for MiMo-v2.5-pro and other models."""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field
from typing import Any

import openai

from miniclaude.core.config import get_config, MiniClaudeConfig

logger = logging.getLogger(__name__)


@dataclass
class LLMResponse:
    """Structured response from the LLM."""

    text: str = ""
    tool_calls: list[dict[str, Any]] = field(default_factory=list)
    stop_reason: str = ""
    usage: dict[str, int] = field(default_factory=dict)
    raw_message: Any = None

    @property
    def has_tool_use(self) -> bool:
        return len(self.tool_calls) > 0

    @property
    def input_tokens(self) -> int:
        return self.usage.get("input_tokens", 0) or self.usage.get("prompt_tokens", 0)

    @property
    def output_tokens(self) -> int:
        return self.usage.get("output_tokens", 0) or self.usage.get("completion_tokens", 0)


class ClaudeClient:
    """OpenAI-compatible async client with tool-use support.

    Works with MiMo-v2.5-pro and any OpenAI-compatible API endpoint.
    Handles tool calls in OpenAI function-calling format.
    """

    def __init__(self, config: MiniClaudeConfig | None = None) -> None:
        self.config = config or get_config()
        self._client = openai.AsyncOpenAI(
            api_key=self.config.api_key,
            base_url=self.config.api_base_url,
        )
        self._total_input_tokens = 0
        self._total_output_tokens = 0

    async def chat(
        self,
        messages: list[dict[str, Any]],
        system: str = "",
        tools: list[dict[str, Any]] | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        tool_choice: str | dict[str, Any] | None = None,
    ) -> LLMResponse:
        """Send a chat request with optional tool definitions.

        Args:
            messages: Conversation messages in OpenAI format.
            system: System prompt (prepended as system message).
            tools: Tool definitions in OpenAI function-calling format.
            temperature: Override config temperature.
            max_tokens: Override config max_tokens.
            tool_choice: Force a specific tool choice strategy.

        Returns:
            LLMResponse with parsed text, tool calls, and usage stats.
        """
        # Build full message list with system prompt
        full_messages: list[dict[str, Any]] = []

        if system:
            full_messages.append({
                "role": "system",
                "content": system,
            })

        full_messages.extend(messages)

        kwargs: dict[str, Any] = {
            "model": self.config.model,
            "max_tokens": max_tokens or self.config.max_tokens,
            "temperature": temperature if temperature is not None else self.config.temperature,
            "messages": full_messages,
        }

        # Add tools in OpenAI function-calling format
        if tools:
            openai_tools = self._convert_tools_to_openai(tools)
            kwargs["tools"] = openai_tools
            if tool_choice:
                kwargs["tool_choice"] = tool_choice

        logger.debug(
            "Sending request: model=%s, messages=%d, tools=%d",
            kwargs["model"],
            len(full_messages),
            len(tools) if tools else 0,
        )

        try:
            response = await self._client.chat.completions.create(**kwargs)
        except openai.APIError as e:
            logger.error("API error: %s", e)
            raise

        # Parse response
        choice = response.choices[0]
        message = choice.message

        result = LLMResponse(
            stop_reason=choice.finish_reason or "stop",
            raw_message=response,
        )

        # Parse usage
        if response.usage:
            result.usage = {
                "prompt_tokens": response.usage.prompt_tokens or 0,
                "completion_tokens": response.usage.completion_tokens or 0,
                "total_tokens": response.usage.total_tokens or 0,
            }

        self._total_input_tokens += result.input_tokens
        self._total_output_tokens += result.output_tokens

        # Extract text content
        if message.content:
            result.text = message.content

        # Extract tool calls (OpenAI format)
        if message.tool_calls:
            for tc in message.tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except (json.JSONDecodeError, TypeError):
                    args = {"raw": tc.function.arguments}

                result.tool_calls.append({
                    "id": tc.id,
                    "name": tc.function.name,
                    "input": args,
                })

        logger.debug(
            "Response: stop=%s, text_len=%d, tools=%d, tokens=%d+%d",
            result.stop_reason,
            len(result.text),
            len(result.tool_calls),
            result.input_tokens,
            result.output_tokens,
        )

        return result

    @staticmethod
    def _convert_tools_to_openai(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Convert tool definitions to OpenAI function-calling format.

        Input format (Anthropic-style):
        {"name": "...", "description": "...", "input_schema": {...}}

        Output format (OpenAI-style):
        {"type": "function", "function": {"name": "...", "description": "...", "parameters": {...}}}
        """
        openai_tools = []
        for tool in tools:
            if "function" in tool:
                # Already in OpenAI format
                openai_tools.append(tool)
            else:
                # Convert from Anthropic format
                openai_tools.append({
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool.get("description", ""),
                        "parameters": tool.get("input_schema", tool.get("parameters", {})),
                    },
                })
        return openai_tools

    @property
    def total_input_tokens(self) -> int:
        return self._total_input_tokens

    @property
    def total_output_tokens(self) -> int:
        return self._total_output_tokens

    @property
    def total_tokens(self) -> int:
        return self._total_input_tokens + self._total_output_tokens

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        await self._client.close()
