"""REPL (Read-Eval-Print Loop) interactive interface."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from miniclaude.core.context import ConversationContext
from miniclaude.core.loop import QueryLoop
from miniclaude.ui.renderer import Renderer

logger = logging.getLogger(__name__)


class REPL:
    """Interactive REPL for MiniClaude.

    Commands:
        /help    - Show help
        /clear   - Clear conversation
        /stats   - Show session statistics
        /save    - Save session to file
        /quit    - Exit
    """

    def __init__(self, query_loop: QueryLoop, context: ConversationContext) -> None:
        self.query_loop = query_loop
        self.context = context
        self.renderer = Renderer()
        self._running = False

    async def run(self) -> None:
        """Start the REPL loop."""
        self.renderer.print_banner()
        self.renderer.print_welcome()

        # Set up tool execution callbacks for UI feedback
        self.query_loop.set_callbacks(
            on_tool_start=self.renderer.print_tool_start,
            on_tool_end=self.renderer.print_tool_end,
            on_thinking=self.renderer.print_thinking,
        )

        self._running = True

        while self._running:
            try:
                user_input = self.renderer.prompt_input().strip()
            except (KeyboardInterrupt, EOFError):
                break

            if not user_input:
                continue

            # Handle commands
            if user_input.startswith("/"):
                self._handle_command(user_input)
                continue

            # Display user input
            self.renderer.print_user_input(user_input)

            # Run the query loop
            try:
                response = await self.query_loop.run(user_input)
            except KeyboardInterrupt:
                self.renderer.print_info("\n[Interrupted]")
                continue
            except Exception as e:
                logger.error("Query failed: %s", e, exc_info=True)
                self.renderer.print_error(str(e))
                continue

        # Cleanup
        self._cleanup()

    def _handle_command(self, command: str) -> None:
        """Handle REPL commands."""
        cmd = command.lower().strip()

        if cmd in ("/help", "/h", "/?"):
            self._show_help()

        elif cmd in ("/clear", "/cls"):
            self.context.clear()
            self.renderer.print_info("Conversation cleared.")

        elif cmd in ("/stats", "/s"):
            self.renderer.print_stats(
                self.query_loop.token_usage,
                self.context.message_count,
            )

        elif cmd in ("/save",):
            path = self.context.save_session()
            self.renderer.print_info(f"Session saved to: {path}")

        elif cmd in ("/quit", "/exit", "/q"):
            self._running = False

        elif cmd.startswith("/model "):
            model = cmd.split(" ", 1)[1].strip()
            self.query_loop.llm_client.config.model = model
            self.renderer.print_info(f"Model changed to: {model}")

        else:
            self.renderer.print_error(f"Unknown command: {command}")
            self._show_help()

    def _show_help(self) -> None:
        """Display help information."""
        help_text = """
[bold]Available Commands:[/bold]
  [cyan]/help[/cyan]     Show this help message
  [cyan]/clear[/cyan]    Clear conversation history
  [cyan]/stats[/cyan]    Show session statistics
  [cyan]/save[/cyan]     Save current session
  [cyan]/quit[/cyan]     Exit MiniClaude

[bold]Tips:[/bold]
  • Ask me to read, write, or edit files
  • Use glob patterns to find files (e.g., "find all .py files")
  • Ask me to run commands (tests, git, etc.)
  • I'll remember context throughout our conversation
"""
        self.renderer.console.print(help_text)

    def _cleanup(self) -> None:
        """Clean up on exit."""
        # Auto-save session
        try:
            self.context.save_session()
        except Exception:
            pass
        self.renderer.print_goodbye()
