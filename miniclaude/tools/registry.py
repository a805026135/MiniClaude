"""Tool registry - central registration and management of all tools."""

from __future__ import annotations

import logging
from typing import Any

from miniclaude.core.config import MiniClaudeConfig
from miniclaude.tools.base import BaseTool

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Central registry for all available tools.

    Manages tool registration, lookup, and Anthropic schema generation.
    """

    def __init__(self, config: MiniClaudeConfig) -> None:
        self.config = config
        self._tools: dict[str, BaseTool] = {}
        self._disabled: set[str] = set()

    def register(self, tool: BaseTool) -> None:
        """Register a single tool."""
        if tool.name in self._tools:
            logger.warning("Tool '%s' already registered, overwriting.", tool.name)
        self._tools[tool.name] = tool
        logger.debug("Registered tool: %s", tool.name)

    def register_all(self) -> None:
        """Register all built-in tools."""
        from miniclaude.tools.file_tools import (
            ReadFileTool,
            WriteFileTool,
            EditFileTool,
            GlobTool,
            GrepTool,
        )
        from miniclaude.tools.shell_tools import ShellTool

        # File operations
        self.register(ReadFileTool(self.config))
        self.register(WriteFileTool(self.config))
        self.register(EditFileTool(self.config))
        self.register(GlobTool(self.config))
        self.register(GrepTool(self.config))

        # Shell
        if self.config.allow_shell:
            self.register(ShellTool(self.config))

        logger.info("Registered %d built-in tools.", len(self._tools))

    def get(self, name: str) -> BaseTool | None:
        """Get a tool by name."""
        if name in self._disabled:
            return None
        return self._tools.get(name)

    def disable(self, name: str) -> None:
        """Disable a tool by name."""
        self._disabled.add(name)

    def enable(self, name: str) -> None:
        """Re-enable a disabled tool."""
        self._disabled.discard(name)

    def get_all(self) -> list[BaseTool]:
        """Get all enabled tools."""
        return [t for name, t in self._tools.items() if name not in self._disabled]

    def get_anthropic_schemas(self) -> list[dict[str, Any]]:
        """Get all enabled tools in Anthropic API schema format."""
        return [t.to_anthropic_schema() for t in self.get_all()]

    def get_names(self) -> list[str]:
        """Get names of all enabled tools."""
        return [t.name for t in self.get_all()]

    def __len__(self) -> int:
        return len([n for n in self._tools if n not in self._disabled])

    def __contains__(self, name: str) -> bool:
        return name in self._tools and name not in self._disabled

    def __repr__(self) -> str:
        return f"ToolRegistry({len(self)} tools: {', '.join(self.get_names())})"
