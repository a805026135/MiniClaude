"""Configuration management using Pydantic Settings."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings


class MiniClaudeConfig(BaseSettings):
    """Central configuration for MiniClaude, loaded from env vars and .env file."""

    model_config = {"env_prefix": "MINICLAUDE_", "env_file": ".env", "extra": "ignore"}

    # ── LLM Settings ──────────────────────────────────────────────
    model: str = Field(
        default="mimo-v2.5-pro",
        description="Model identifier (e.g. mimo-v2.5-pro)",
    )
    max_tokens: int = Field(default=8192, description="Max output tokens per response")
    temperature: float = Field(default=0.6, description="Sampling temperature")

    # ── API Settings ──────────────────────────────────────────────
    api_base_url: str = Field(
        default="https://token-plan-cn.xiaomimimo.com/v1",
        description="OpenAI-compatible API base URL",
    )

    @property
    def api_key(self) -> str:
        """Read API key from environment."""
        key = os.getenv("MINICLAUDE_API_KEY", "") or os.getenv("MIMO_API_KEY", "")
        if not key:
            raise ValueError(
                "API key not set. Please set MINICLAUDE_API_KEY or MIMO_API_KEY "
                "in your .env file or shell environment."
            )
        return key

    # ── Context & Budget ──────────────────────────────────────────
    context_limit: int = Field(
        default=131072,
        description="Maximum context window in tokens",
    )
    externalize_threshold: int = Field(
        default=2000,
        description="Character count threshold to externalize tool results",
    )
    reserved_output_tokens: int = Field(
        default=16_000,
        description="Tokens reserved for model output",
    )

    # ── Security ──────────────────────────────────────────────────
    allow_shell: bool = Field(
        default=True,
        description="Whether shell command execution is allowed",
    )
    confirm_dangerous: bool = Field(
        default=True,
        description="Whether to prompt user for confirmation on dangerous ops",
    )
    project_dir: Optional[str] = Field(
        default=None,
        description="Root directory for file operations (boundary)",
    )

    # ── Memory ────────────────────────────────────────────────────
    memory_db: str = Field(
        default="data/memory/miniclaude.db",
        description="Path to the SQLite memory database",
    )
    memory_enabled: bool = Field(
        default=True,
        description="Whether the memory system is active",
    )

    # ── Logging ───────────────────────────────────────────────────
    log_level: str = Field(default="INFO", description="Logging level")

    # ── Paths ─────────────────────────────────────────────────────
    @property
    def base_dir(self) -> Path:
        """Base directory of the MiniClaude installation."""
        return Path(__file__).resolve().parent.parent.parent

    @property
    def data_dir(self) -> Path:
        """Data directory for runtime artifacts."""
        d = self.base_dir / "data"
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def externalized_dir(self) -> Path:
        """Directory for externalized large tool results."""
        d = self.data_dir / "externalized"
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def sessions_dir(self) -> Path:
        """Directory for session history."""
        d = self.data_dir / "sessions"
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def memory_db_path(self) -> Path:
        """Full path to the memory database."""
        p = self.base_dir / self.memory_db
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    def effective_project_dir(self) -> Path:
        """Return the effective project directory boundary."""
        if self.project_dir:
            return Path(self.project_dir).resolve()
        return Path.cwd().resolve()


# Singleton instance
_config: MiniClaudeConfig | None = None


def get_config() -> MiniClaudeConfig:
    """Get or create the global config singleton."""
    global _config
    if _config is None:
        _config = MiniClaudeConfig()
    return _config


def reset_config() -> None:
    """Reset the config singleton (useful for testing)."""
    global _config
    _config = None
