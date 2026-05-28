"""Rich-based terminal renderer for MiniClaude output."""

from __future__ import annotations

import logging
from typing import Any

from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
from rich.theme import Theme

logger = logging.getLogger(__name__)

# Custom theme
MINICLAUDE_THEME = Theme({
    "info": "cyan",
    "success": "green",
    "warning": "yellow",
    "error": "red bold",
    "tool_name": "bold blue",
    "tool_param": "dim cyan",
    "thinking": "dim italic",
    "user_input": "bold white",
    "assistant": "white",
    "banner": "bold magenta",
})


class Renderer:
    """Renders MiniClaude output to the terminal using Rich."""

    def __init__(self) -> None:
        self.console = Console(theme=MINICLAUDE_THEME, highlight=True)

    def print_banner(self) -> None:
        """Print the MiniClaude startup banner."""
        banner = """
[bold cyan]  __  __ _       _    ____ _                 _[/bold cyan]
[bold cyan] |  \\/  (_)_ __ (_)  / ___| | __ ___      _| |[/bold cyan]
[bold cyan] | |\\/| | | '_ \\| | | |   | |/ _` \\ \\ /\\ / / |[/bold cyan]
[bold cyan] | |  | | | | | | | | |___| | (_| |\\ V  V /| |[/bold cyan]
[bold cyan] |_|  |_|_|_| |_|_|  \\____|_|\\__,_| \\_/\\_/ |_|[/bold cyan]
[dim]  AI Coding Agent v0.1.0 — Powered by Claude[/dim]
"""
        self.console.print(banner)

    def print_welcome(self) -> None:
        """Print welcome message with instructions."""
        self.console.print(
            Panel(
                "[bold]Welcome to MiniClaude![/bold]\n\n"
                "I'm your AI coding assistant. I can:\n"
                "  [cyan]•[/cyan] Read, write, and edit files\n"
                "  [cyan]•[/cyan] Search codebases with grep and glob\n"
                "  [cyan]•[/cyan] Run shell commands\n"
                "  [cyan]•[/cyan] Help with code review, refactoring, and debugging\n\n"
                "[dim]Type your request and press Enter. "
                "Use /help for commands, Ctrl+C to exit.[/dim]",
                title="MiniClaude",
                border_style="cyan",
            )
        )

    def print_user_input(self, text: str) -> None:
        """Display the user's input."""
        self.console.print()
        self.console.print(f"[bold white]> {text}[/bold white]")

    def print_thinking(self, text: str) -> None:
        """Display the assistant's thinking/reasoning text."""
        if not text.strip():
            return
        self.console.print()
        # Use markdown rendering for the response
        self.console.print(Markdown(text))

    def print_tool_start(self, tool_name: str, params: dict[str, Any]) -> None:
        """Display tool execution start."""
        # Format parameters concisely
        param_parts = []
        for k, v in params.items():
            val = str(v)
            if len(val) > 60:
                val = val[:60] + "..."
            param_parts.append(f"{k}={val}")
        param_str = ", ".join(param_parts)

        self.console.print(
            f"  [tool_name]⚙ {tool_name}[/tool_name]"
            f"[tool_param]({param_str})[/tool_param]",
            end="",
        )

    def print_tool_end(self, tool_name: str, success: bool, preview: str) -> None:
        """Display tool execution result."""
        if success:
            self.console.print(f" [success]✓[/success]")
            if preview:
                # Show a brief preview
                first_line = preview.split("\n")[0]
                if len(first_line) > 80:
                    first_line = first_line[:80] + "..."
                self.console.print(f"    [dim]{first_line}[/dim]")
        else:
            self.console.print(f" [error]✗[/error]")
            if preview:
                self.console.print(f"    [error]{preview}[/error]")

    def print_error(self, message: str) -> None:
        """Display an error message."""
        self.console.print(Panel(f"[error]{message}[/error]", title="Error", border_style="red"))

    def print_info(self, message: str) -> None:
        """Display an info message."""
        self.console.print(f"[info]{message}[/info]")

    def print_goodbye(self) -> None:
        """Display goodbye message."""
        self.console.print()
        self.console.print("[dim]Goodbye! Session saved.[/dim]")

    def print_stats(self, token_usage: dict[str, int], message_count: int) -> None:
        """Display session statistics."""
        table = Table(title="Session Stats", show_header=False, border_style="dim")
        table.add_column("Metric", style="dim")
        table.add_column("Value")
        table.add_row("Input Tokens", f"{token_usage.get('input_tokens', 0):,}")
        table.add_row("Output Tokens", f"{token_usage.get('output_tokens', 0):,}")
        table.add_row("Total Tokens", f"{token_usage.get('total_tokens', 0):,}")
        table.add_row("Messages", str(message_count))
        self.console.print(table)

    def prompt_input(self) -> str:
        """Get input from the user with a prompt."""
        try:
            return self.console.input("[bold cyan]❯[/bold cyan] ")
        except EOFError:
            return ""
