"""Worktree - isolated workspace for parallel agent work."""

from __future__ import annotations

import logging
import shutil
import tempfile
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class Worktree:
    """Provides an isolated working directory for agent operations.

    Creates a temporary copy of the project directory so agents
    can work independently without interfering with each other.

    This is a lightweight alternative to git worktrees for cases
    where git isn't available or practical.
    """

    def __init__(
        self,
        source_dir: Path,
        name: str = "",
        copy_mode: bool = False,
    ) -> None:
        """
        Args:
            source_dir: The project directory to create a worktree from.
            name: Optional name for the worktree directory.
            copy_mode: If True, copy files. If False, use symlinks where possible.
        """
        self.source_dir = source_dir.resolve()
        self.name = name or f"worktree_{id(self)}"
        self.copy_mode = copy_mode
        self.work_dir: Path | None = None
        self._created = False

    def create(self) -> Path:
        """Create the worktree directory.

        Returns:
            Path to the working directory.
        """
        if self._created:
            return self.work_dir  # type: ignore

        base = Path(tempfile.gettempdir()) / "miniclaude_worktrees"
        base.mkdir(parents=True, exist_ok=True)
        self.work_dir = base / self.name

        if self.copy_mode:
            # Full copy mode (slower but fully isolated)
            if self.work_dir.exists():
                shutil.rmtree(self.work_dir)
            shutil.copytree(
                self.source_dir,
                self.work_dir,
                ignore=shutil.ignore_patterns(
                    ".git", "__pycache__", "*.pyc", "node_modules",
                    ".venv", "venv", "data",
                ),
            )
            logger.info("Worktree created (copy): %s", self.work_dir)
        else:
            # Symlink mode (faster, shares files)
            self.work_dir.mkdir(parents=True, exist_ok=True)
            for item in self.source_dir.iterdir():
                if item.name in (".git", "__pycache__", "node_modules", ".venv", "venv", "data"):
                    continue
                link = self.work_dir / item.name
                if not link.exists():
                    try:
                        link.symlink_to(item, target_is_directory=item.is_dir())
                    except OSError:
                        # Fall back to copy if symlinks not supported (Windows)
                        if item.is_dir():
                            shutil.copytree(item, link, ignore=shutil.ignore_patterns("__pycache__"))
                        else:
                            shutil.copy2(item, link)
            logger.info("Worktree created (symlink): %s", self.work_dir)

        self._created = True
        return self.work_dir

    def cleanup(self) -> None:
        """Remove the worktree directory."""
        if self.work_dir and self.work_dir.exists():
            try:
                shutil.rmtree(self.work_dir)
                logger.info("Worktree cleaned up: %s", self.work_dir)
            except Exception as e:
                logger.warning("Failed to cleanup worktree: %s", e)
        self._created = False

    def __enter__(self) -> "Worktree":
        self.create()
        return self

    def __exit__(self, *args: Any) -> None:
        self.cleanup()

    def __repr__(self) -> str:
        status = "created" if self._created else "not created"
        return f"Worktree({self.name}, {status}, {self.work_dir})"
