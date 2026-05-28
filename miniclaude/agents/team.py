"""Agent Team - coordinates multiple sub-agents working on related tasks."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

from miniclaude.agents.orchestrator import Orchestrator

logger = logging.getLogger(__name__)


@dataclass
class TeamTask:
    """A task assigned to a specific agent type."""

    agent_type: str
    task: str
    context: str = ""
    depends_on: list[str] = field(default_factory=list)  # task names this depends on


@dataclass
class TeamResult:
    """Aggregated results from a team of agents."""

    results: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    total_iterations: int = 0
    success: bool = True


class AgentTeam:
    """Coordinates multiple sub-agents working on related tasks.

    Supports:
    - Parallel execution of independent tasks
    - Sequential execution with dependency ordering
    - Result aggregation
    """

    def __init__(self, orchestrator: Orchestrator) -> None:
        self.orchestrator = orchestrator

    async def execute_parallel(
        self,
        tasks: list[TeamTask],
    ) -> TeamResult:
        """Execute multiple independent tasks in parallel.

        Args:
            tasks: List of tasks to execute concurrently.

        Returns:
            Aggregated results from all agents.
        """
        logger.info("Team: executing %d tasks in parallel", len(tasks))

        team_result = TeamResult()

        # Launch all tasks concurrently
        coros = []
        for task in tasks:
            coros.append(
                self.orchestrator.spawn_agent(
                    agent_type=task.agent_type,
                    task=task.task,
                    context={"additional": task.context} if task.context else None,
                )
            )

        results = await asyncio.gather(*coros, return_exceptions=True)

        for task, result in zip(tasks, results):
            if isinstance(result, Exception):
                team_result.errors.append(f"{task.agent_type}: {result}")
                team_result.success = False
            else:
                team_result.results[task.agent_type] = result
                team_result.total_iterations += result.iterations

        logger.info(
            "Team parallel: %d/%d succeeded, %d errors",
            len(team_result.results),
            len(tasks),
            len(team_result.errors),
        )

        return team_result

    async def execute_sequential(
        self,
        tasks: list[TeamTask],
    ) -> TeamResult:
        """Execute tasks sequentially with dependency ordering.

        Args:
            tasks: List of tasks (dependencies are resolved via topological sort).

        Returns:
            Aggregated results.
        """
        logger.info("Team: executing %d tasks sequentially", len(tasks))

        team_result = TeamResult()
        completed: dict[str, Any] = {}

        # Simple topological sort
        ordered = self._topological_sort(tasks)

        for task in ordered:
            # Build context from dependencies
            context_parts = []
            if task.context:
                context_parts.append(task.context)
            for dep_name in task.depends_on:
                if dep_name in completed:
                    dep_result = completed[dep_name]
                    context_parts.append(f"Result from {dep_name}: {dep_result.output[:500]}")

            try:
                result = await self.orchestrator.spawn_agent(
                    agent_type=task.agent_type,
                    task=task.task,
                    context={"additional": "\n".join(context_parts)} if context_parts else None,
                )
                # Use task identifier as key
                task_id = f"{task.agent_type}_{len(completed)}"
                completed[task_id] = result
                team_result.results[task_id] = result
                team_result.total_iterations += result.iterations
            except Exception as e:
                team_result.errors.append(f"{task.agent_type}: {e}")
                team_result.success = False

        return team_result

    @staticmethod
    def _topological_sort(tasks: list[TeamTask]) -> list[TeamTask]:
        """Sort tasks based on dependencies."""
        task_map = {}
        for i, task in enumerate(tasks):
            name = f"{task.agent_type}_{i}"
            task_map[name] = task

        # Simple approach: tasks with no deps first, then by dependency
        no_deps = [t for t in tasks if not t.depends_on]
        has_deps = [t for t in tasks if t.depends_on]
        return no_deps + has_deps
