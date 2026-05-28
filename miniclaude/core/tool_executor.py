"""Tool execution engine - runs tool calls and collects results."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Any

from miniclaude.tools.base import BaseTool, ToolResult
from miniclaude.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


@dataclass
class ExecutionResult:
    """Result of executing a batch of tool calls."""

    results: list[ToolResult] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    total_time_ms: float = 0.0

    @property
    def all_success(self) -> bool:
        return all(r.success for r in self.results)

    @property
    def has_results(self) -> bool:
        return len(self.results) > 0


class ToolExecutor:
    """Executes tool calls from the LLM response.

    Handles:
    - Dispatching tool calls to the correct tool implementation
    - Error handling and timeouts
    - Execution timing and logging
    """

    def __init__(self, registry: ToolRegistry, config: Any = None) -> None:
        self.registry = registry

    async def execute_all(self, tool_calls: list[dict[str, Any]]) -> list[ToolResult]:
        """Execute all tool calls from an LLM response.

        Args:
            tool_calls: List of tool call dicts with 'id', 'name', 'input' keys.

        Returns:
            List of ToolResult, one per tool call.
        """
        results: list[ToolResult] = []

        for tc in tool_calls:
            call_id = tc.get("id", "unknown")
            name = tc.get("name", "")
            params = tc.get("input", {})

            result = await self.execute_single(name, params)
            result.metadata["call_id"] = call_id
            results.append(result)

        return results

    async def execute_single(self, name: str, params: dict[str, Any]) -> ToolResult:
        """Execute a single tool call by name.

        Args:
            name: Tool name.
            params: Tool parameters.

        Returns:
            ToolResult from the tool execution.
        """
        tool = self.registry.get(name)
        if tool is None:
            return ToolResult(
                tool_name=name,
                success=False,
                content=f"Unknown tool: '{name}'. Available: {', '.join(self.registry.get_names())}",
            )

        start_time = time.monotonic()

        try:
            logger.info("Executing tool: %s(%s)", name, _format_params(params))
            result = await tool.execute(**params)

            elapsed_ms = (time.monotonic() - start_time) * 1000
            result.metadata["execution_time_ms"] = round(elapsed_ms, 1)

            logger.info(
                "Tool %s: %s (%.0fms, %d chars)",
                name,
                "success" if result.success else "error",
                elapsed_ms,
                len(result.content),
            )
            return result

        except Exception as e:
            elapsed_ms = (time.monotonic() - start_time) * 1000
            logger.error("Tool %s crashed: %s (%.0fms)", name, e, elapsed_ms)
            return ToolResult(
                tool_name=name,
                success=False,
                content=f"Tool execution failed: {type(e).__name__}: {e}",
                metadata={"execution_time_ms": round(elapsed_ms, 1)},
            )


def _format_params(params: dict[str, Any], max_len: int = 100) -> str:
    """Format parameters for logging (truncate long values)."""
    parts = []
    for k, v in params.items():
        val_str = str(v)
        if len(val_str) > 50:
            val_str = val_str[:50] + "..."
        parts.append(f"{k}={val_str}")
    result = ", ".join(parts)
    if len(result) > max_len:
        result = result[:max_len] + "..."
    return result
