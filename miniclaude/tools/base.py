"""Base tool abstraction for MiniClaude's atomic tool layer."""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class ToolResult(BaseModel):
    """Result returned by tool execution."""

    tool_name: str
    success: bool
    content: str
    truncated: bool = False
    external_path: str | None = None
    token_count: int = 0
    metadata: dict[str, Any] = {}

    def to_tool_result_block(self) -> dict[str, Any]:
        """Convert to Anthropic API tool_result content block."""
        return {
            "type": "tool_result",
            "tool_use_id": "",  # filled by caller
            "content": self.content if self.success else f"Error: {self.content}",
        }


class BaseTool(ABC):
    """Abstract base class for all MiniClaude tools.

    Subclasses must implement:
    - name: unique tool identifier
    - description: what the tool does (shown to the LLM)
    - parameters: JSON Schema for input parameters
    - execute(): the actual tool logic
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Unique tool name used in tool calls."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of what this tool does."""
        ...

    @property
    @abstractmethod
    def parameters(self) -> dict[str, Any]:
        """JSON Schema defining the tool's input parameters."""
        ...

    @abstractmethod
    async def execute(self, **kwargs: Any) -> ToolResult:
        """Execute the tool with the given parameters.

        Args:
            **kwargs: Tool parameters matching the JSON Schema.

        Returns:
            ToolResult with execution output.
        """
        ...

    def to_anthropic_schema(self) -> dict[str, Any]:
        """Convert this tool to Anthropic API tool definition format.

        Returns:
            Dict with 'name', 'description', and 'input_schema' keys.
        """
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": {
                "type": "object",
                "properties": self.parameters,
                "required": self._get_required_params(),
            },
        }

    def _get_required_params(self) -> list[str]:
        """Get list of required parameter names. Override if needed."""
        return []

    def _success(self, content: str, **kwargs: Any) -> ToolResult:
        """Helper to create a successful ToolResult."""
        return ToolResult(
            tool_name=self.name,
            success=True,
            content=content,
            **kwargs,
        )

    def _error(self, message: str, **kwargs: Any) -> ToolResult:
        """Helper to create an error ToolResult."""
        return ToolResult(
            tool_name=self.name,
            success=False,
            content=message,
            **kwargs,
        )

    def __repr__(self) -> str:
        return f"<Tool:{self.name}>"
