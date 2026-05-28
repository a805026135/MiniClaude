"""Orchestrator - main agent's multi-agent coordination hub."""

from __future__ import annotations

import logging
from typing import Any

from miniclaude.agents.sub_agent import AgentResult, SubAgent, AGENT_PROFILES
from miniclaude.core.config import MiniClaudeConfig
from miniclaude.llm.client import ClaudeClient
from miniclaude.tools.base import BaseTool, ToolResult
from miniclaude.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class AgentTool(BaseTool):
    """Tool that spawns a sub-agent for delegated tasks.

    The main agent can call this tool to delegate a subtask
    to a specialized agent with its own constrained tool set.
    """

    def __init__(
        self,
        config: MiniClaudeConfig,
        llm_client: ClaudeClient,
        tool_registry: ToolRegistry,
    ) -> None:
        self._config = config
        self._llm_client = llm_client
        self._tool_registry = tool_registry

    @property
    def name(self) -> str:
        return "spawn_agent"

    @property
    def description(self) -> str:
        agent_types = "\n".join(
            f"  - {k}: {v['description']}" for k, v in AGENT_PROFILES.items()
        )
        return (
            "Spawn a specialized sub-agent to handle a subtask independently. "
            "The sub-agent has its own context and restricted tool access. "
            "Use this for complex tasks that benefit from focused execution.\n\n"
            f"Available agent types:\n{agent_types}"
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "task": {
                "type": "string",
                "description": "Detailed task description for the sub-agent",
            },
            "agent_type": {
                "type": "string",
                "enum": list(AGENT_PROFILES.keys()),
                "description": "Type of specialist agent to spawn",
            },
            "context": {
                "type": "string",
                "description": "Additional context (file paths, constraints, etc.)",
            },
        }

    def _get_required_params(self) -> list[str]:
        return ["task", "agent_type"]

    async def execute(self, **kwargs: Any) -> ToolResult:
        task = kwargs.get("task", "")
        agent_type = kwargs.get("agent_type", "")
        context_str = kwargs.get("context", "")

        if not task:
            return self._error("Empty task")
        if agent_type not in AGENT_PROFILES:
            return self._error(f"Unknown agent type: {agent_type}")

        try:
            agent = SubAgent(
                agent_type=agent_type,
                config=self._config,
                llm_client=self._llm_client,
                tool_registry=self._tool_registry,
            )

            context = {"additional": context_str} if context_str else None
            result = await agent.run(task, context)

            # Convert to tool result
            tool_result = result.to_tool_result()
            logger.info(
                "Agent [%s] completed: success=%s, tools=%d",
                agent_type, result.success, len(result.tools_called),
            )
            return tool_result

        except Exception as e:
            logger.error("Agent spawn failed: %s", e, exc_info=True)
            return self._error(f"Failed to spawn agent: {e}")


class Orchestrator:
    """Main agent's orchestration layer for multi-agent coordination.

    Manages:
    - Agent spawning and lifecycle
    - Task decomposition planning
    - Result aggregation
    - Quality control
    """

    def __init__(
        self,
        config: MiniClaudeConfig,
        llm_client: ClaudeClient,
        tool_registry: ToolRegistry,
    ) -> None:
        self.config = config
        self.llm_client = llm_client
        self.tool_registry = tool_registry
        self._active_agents: dict[str, SubAgent] = {}
        self._completed_results: list[AgentResult] = []

    def register_agent_tool(self) -> None:
        """Register the spawn_agent tool in the tool registry."""
        agent_tool = AgentTool(self.config, self.llm_client, self.tool_registry)
        self.tool_registry.register(agent_tool)
        logger.info("Registered agent spawning tool")

    async def spawn_agent(
        self,
        agent_type: str,
        task: str,
        context: dict[str, Any] | None = None,
    ) -> AgentResult:
        """Spawn a sub-agent for a specific task."""
        agent = SubAgent(
            agent_type=agent_type,
            config=self.config,
            llm_client=self.llm_client,
            tool_registry=self.tool_registry,
        )

        self._active_agents[agent.name] = agent

        try:
            result = await agent.run(task, context)
            self._completed_results.append(result)
            return result
        finally:
            self._active_agents.pop(agent.name, None)

    @property
    def active_agent_count(self) -> int:
        return len(self._active_agents)

    @property
    def total_agents_spawned(self) -> int:
        return len(self._completed_results)
