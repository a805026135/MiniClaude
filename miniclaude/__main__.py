"""CLI entry point for MiniClaude: python -m miniclaude."""

from __future__ import annotations

import asyncio
import logging
import sys
from pathlib import Path

import typer
from dotenv import load_dotenv

app = typer.Typer(help="MiniClaude - AI Coding Agent")


@app.command()
def main(
    query: str | None = typer.Argument(None, help="Direct query (skip REPL)"),
    model: str = typer.Option("", "--model", "-m", help="Model to use"),
    project_dir: str = typer.Option("", "--dir", "-d", help="Project directory"),
    no_memory: bool = typer.Option(False, "--no-memory", help="Disable memory system"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose logging"),
    gui: bool = typer.Option(False, "--gui", "-g", help="Launch desktop GUI mode"),
) -> None:
    """MiniClaude - A Claude Code-like AI Coding Agent."""
    # Load .env from project root
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)

    # Setup logging
    log_level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    # Apply CLI overrides
    import os
    if model:
        os.environ["MINICLAUDE_MODEL"] = model
    if project_dir:
        os.environ["MINICLAUDE_PROJECT_DIR"] = project_dir
    if no_memory:
        os.environ["MINICLAUDE_MEMORY_ENABLED"] = "false"

    # GUI mode
    if gui:
        from miniclaude.ui.desktop import launch_desktop
        launch_desktop()
        return

    asyncio.run(_async_main(query))


async def _async_main(query: str | None) -> None:
    """Async entry point."""
    from miniclaude.app import MiniClaudeApp

    mini_app = MiniClaudeApp()

    try:
        await mini_app.initialize()

        if query:
            # Direct query mode
            response = await mini_app.run_query(query)
            print(response)
        else:
            # REPL mode
            await mini_app.run_repl()
    except KeyboardInterrupt:
        print("\n\nGoodbye!")
    except Exception as e:
        logging.getLogger(__name__).error("Fatal error: %s", e, exc_info=True)
        sys.exit(1)
    finally:
        await mini_app.shutdown()


if __name__ == "__main__":
    app()
