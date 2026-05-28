"""Shell command execution tool."""

from __future__ import annotations

import asyncio
import logging
import os
import platform
import shlex
from typing import Any

from miniclaude.core.config import MiniClaudeConfig
from miniclaude.tools.base import BaseTool, ToolResult

logger = logging.getLogger(__name__)

# Commands that are always blocked
BLOCKED_COMMANDS = frozenset({
    "rm -rf /", "rm -rf /*", "mkfs", "dd if=", ":(){", "fork bomb",
})

# Patterns that require confirmation
DANGEROUS_PATTERNS = [
    "rm -rf",
    "rm -r",
    "DROP TABLE",
    "DROP DATABASE",
    "DELETE FROM",
    "sudo rm",
    "chmod 777",
    "> /dev/",
    "shutdown",
    "reboot",
    "format ",
    "git push --force",
    "git reset --hard",
]


class ShellTool(BaseTool):
    """Execute shell commands in a controlled environment."""

    def __init__(self, config: MiniClaudeConfig) -> None:
        self._config = config

    @property
    def name(self) -> str:
        return "run_command"

    @property
    def description(self) -> str:
        return (
            "Execute a shell command and return its output (stdout + stderr). "
            "Use for running tests, building projects, checking git status, etc. "
            "Commands are executed in the project directory. "
            "Timeout defaults to 120 seconds."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "command": {
                "type": "string",
                "description": "Shell command to execute",
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds. Default: 120",
            },
            "cwd": {
                "type": "string",
                "description": "Working directory for command. Default: project directory",
            },
        }

    def _get_required_params(self) -> list[str]:
        return ["command"]

    async def execute(self, **kwargs: Any) -> ToolResult:
        command = kwargs.get("command", "")
        timeout = kwargs.get("timeout", 120) or 120
        cwd = kwargs.get("cwd", "")

        if not command.strip():
            return self._error("Empty command")

        # Safety check: blocked commands
        cmd_lower = command.lower().strip()
        for blocked in BLOCKED_COMMANDS:
            if blocked in cmd_lower:
                return self._error(f"Command blocked for safety: contains '{blocked}'")

        # Safety check: dangerous patterns
        is_dangerous = any(p.lower() in cmd_lower for p in DANGEROUS_PATTERNS)
        if is_dangerous and self._config.confirm_dangerous:
            logger.warning("Dangerous command detected: %s", command)
            # In the actual flow, the permission manager handles confirmation
            # Here we just mark it
            return self._error(
                f"⚠️  Dangerous command detected and requires confirmation: {command}\n"
                f"Use the permission system to approve this command."
            )

        work_dir = cwd if cwd else str(self._config.effective_project_dir())

        logger.debug("Executing: %s (cwd=%s, timeout=%ds)", command, work_dir, timeout)

        try:
            # Determine shell based on platform
            if platform.system() == "Windows":
                shell_cmd = ["cmd", "/c", command]
            else:
                shell_cmd = ["bash", "-c", command]

            process = await asyncio.create_subprocess_exec(
                *shell_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=work_dir,
                env={**os.environ},
            )

            try:
                stdout, _ = await asyncio.wait_for(
                    process.communicate(), timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return self._error(
                    f"Command timed out after {timeout}s: {command}"
                )

            output = stdout.decode("utf-8", errors="replace").strip()
            exit_code = process.returncode or 0

            # Truncate very long output
            max_output = 50000
            truncated = False
            if len(output) > max_output:
                output = output[:max_output] + f"\n... (output truncated, {len(stdout)} bytes total)"
                truncated = True

            if exit_code == 0:
                content = output if output else "(command completed successfully with no output)"
            else:
                content = f"(exit code: {exit_code})\n{output}" if output else f"(exit code: {exit_code}, no output)"

            logger.debug("Command done: exit=%d, output=%d chars", exit_code, len(content))
            return self._success(
                content,
                truncated=truncated,
                metadata={"exit_code": exit_code, "command": command},
            )

        except FileNotFoundError:
            return self._error(f"Command not found: {command.split()[0]}")
        except PermissionError:
            return self._error(f"Permission denied: {command}")
        except Exception as e:
            return self._error(f"Command execution failed: {e}")
