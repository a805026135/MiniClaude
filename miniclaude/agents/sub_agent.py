"""Sub-Agent - a constrained agent that runs as a tool call within the main agent."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import Any

from miniclaude.core.config import MiniClaudeConfig
from miniclaude.llm.client import ClaudeClient, LLMResponse
from miniclaude.llm.message_builder import MessageBuilder
from miniclaude.tools.base import ToolResult
from miniclaude.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)

# Maximum iterations for a sub-agent
SUB_AGENT_MAX_ITERATIONS = 20


@dataclass
class AgentResult:
    """Result from a sub-agent execution."""

    agent_name: str
    task: str
    output: str = ""
    tools_called: list[dict[str, Any]] = field(default_factory=list)
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    iterations: int = 0
    success: bool = True
    error: str | None = None

    @property
    def token_usage(self) -> dict[str, int]:
        return {
            "input_tokens": self.total_input_tokens,
            "output_tokens": self.total_output_tokens,
        }

    def to_tool_result(self) -> ToolResult:
        """Convert to a ToolResult for the parent agent."""
        content = self.output
        if self.error:
            content = f"Agent error: {self.error}\nPartial output: {self.output}"

        # Add tool usage summary
        if self.tools_called:
            tool_summary = ", ".join(tc.get("name", "?") for tc in self.tools_called)
            content += f"\n\n[Tools used: {tool_summary} ({self.iterations} iterations)]"

        return ToolResult(
            tool_name=f"agent:{self.agent_name}",
            success=self.success,
            content=content,
            metadata={
                "agent_name": self.agent_name,
                "iterations": self.iterations,
                "tools_called": len(self.tools_called),
                "token_usage": self.token_usage,
            },
        )


# Pre-defined agent types with their system prompts and tool restrictions
AGENT_PROFILES = {
    "code_analyst": {
        "role": "Code Analyst",
        "system_prompt": (
            "You are a code analysis specialist. Your job is to read and analyze code, "
            "identify patterns, issues, and provide detailed reports. "
            "Be thorough but concise. Focus on reading files and searching code."
        ),
        "allowed_tools": ["read_file", "glob_files", "grep_search"],
        "description": "Analyzes code structure, patterns, and quality",
    },
    "test_generator": {
        "role": "Test Generator",
        "system_prompt": (
            "You are a test generation specialist. Your job is to read source code "
            "and create comprehensive test suites. Use pytest style. "
            "Cover happy paths, edge cases, and error scenarios."
        ),
        "allowed_tools": ["read_file", "write_file", "glob_files", "grep_search"],
        "description": "Generates comprehensive test suites",
    },
    "refactor_expert": {
        "role": "Refactoring Expert",
        "system_prompt": (
            "You are a code refactoring specialist. Your job is to improve code structure "
            "without changing behavior. Apply clean code principles and design patterns. "
            "Make one change at a time and preserve existing functionality."
        ),
        "allowed_tools": ["read_file", "write_file", "edit_file", "grep_search", "glob_files"],
        "description": "Refactors code with clean code principles",
    },
    "debug_specialist": {
        "role": "Debug Specialist",
        "system_prompt": (
            "You are a debugging specialist. Your job is to investigate errors, "
            "trace execution paths, and identify root causes. "
            "Be systematic: reproduce, investigate, hypothesize, fix, verify."
        ),
        "allowed_tools": ["read_file", "grep_search", "glob_files", "run_command"],
        "description": "Systematically debugs errors and issues",
    },
}


class SubAgent:
    """A constrained sub-agent that runs as a tool call.

    Sub-agents:
    - Have their own conversation context (isolated from main agent)
    - Are restricted to a specific set of tools
    - Operate within a path boundary
    - Return compressed results to the main agent
    - Never modify the main agent's conversation
    """

    def __init__(
        self,
        agent_type: str,
        config: MiniClaudeConfig,
        llm_client: ClaudeClient,
        tool_registry: ToolRegistry,
    ) -> None:
        profile = AGENT_PROFILES.get(agent_type)
        if not profile:
            raise ValueError(f"Unknown agent type: {agent_type}. Available: {list(AGENT_PROFILES.keys())}")

        self.agent_type = agent_type
        self.name = f"agent:{agent_type}"
        self.role = profile["role"]
        self.system_prompt = profile["system_prompt"]
        self.allowed_tools = profile["allowed_tools"]
        self.config = config
        self.llm_client = llm_client
        self.tool_registry = tool_registry
        self._messages: list[dict[str, Any]] = []
        self._all_tool_calls: list[dict[str, Any]] = []

    async def run(self, task: str, context: dict[str, Any] | None = None) -> AgentResult:
        """Run the sub-agent on a task.

        Args:
            task: The task description.
            context: Optional additional context (file paths, constraints).

        Returns:
            AgentResult with the agent's output.
        """
        logger.info("Sub-agent [%s] starting task: %s", self.role, task[:100])

        result = AgentResult(agent_name=self.agent_type, task=task)

        # Build task message with context
        task_msg = task
        if context:
            task_msg += f"\n\nAdditional context:\n{context}"

        self._messages = [{"role": "user", "content": task_msg}]

        # Get filtered tool schemas
        tool_schemas = self._get_filtered_tools()

        # Run mini loop
        for iteration in range(SUB_AGENT_MAX_ITERATIONS):
            result.iterations = iteration + 1

            try:
                response = await self.llm_client.chat(
                    messages=self._messages,
                    system=self.system_prompt,
                    tools=tool_schemas,
                )
            except Exception as e:
                result.success = False
                result.error = f"LLM error: {e}"
                break

            result.total_input_tokens += response.input_tokens
            result.total_output_tokens += response.output_tokens

            # No tool calls - done
            if not response.has_tool_use:
                result.output = response.text
                break

            # Track tool calls
            result.tools_called.extend(response.tool_calls)
            self._all_tool_calls.extend(response.tool_calls)

            # Execute tools (reusing the main executor with filtered tools)
            from miniclaude.core.tool_executor import ToolExecutor
            executor = ToolExecutor(self.tool_registry, self.config)

            # Add assistant message
            assistant_msg = MessageBuilder.build_assistant_with_tool_use(
                response.text, response.tool_calls
            )
            self._messages.append(assistant_msg)

            # Execute and add results
            tool_results = await executor.execute_all(response.tool_calls)
            result_msg = MessageBuilder.tool_results_to_message(
                response.tool_calls, tool_results
            )
            self._messages.append(result_msg)

        else:
            result.success = False
            result.error = f"Reached max iterations ({SUB_AGENT_MAX_ITERATIONS})"
            # Get whatever text we have
            if response and response.text:
                result.output = response.text

        logger.info(
            "Sub-agent [%s] finished: success=%s, iterations=%d, tools=%d",
            self.role, result.success, result.iterations, len(result.tools_called),
        )

        return result

    def _get_filtered_tools(self) -> list[dict[str, Any]]:
        """Get tool schemas filtered to only allowed tools."""
        all_schemas = self.tool_registry.get_anthropic_schemas()
        return [s for s in all_schemas if s["name"] in self.allowed_tools]
