"""Shared test fixtures for MiniClaude tests."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from miniclaude.core.config import MiniClaudeConfig, reset_config


@pytest.fixture
def tmp_project(tmp_path: Path) -> Path:
    """Create a temporary project directory with some test files."""
    # Create test files
    (tmp_path / "hello.py").write_text('print("Hello, World!")\n')
    (tmp_path / "utils.py").write_text(
        'def add(a, b):\n    return a + b\n\ndef multiply(a, b):\n    return a * b\n'
    )
    (tmp_path / "subdir").mkdir()
    (tmp_path / "subdir" / "nested.py").write_text("# nested file\nx = 42\n")
    return tmp_path


@pytest.fixture
def config(tmp_project: Path, monkeypatch: pytest.MonkeyPatch) -> MiniClaudeConfig:
    """Create a test configuration."""
    monkeypatch.setenv("MINICLAUDE_API_KEY", "test-key-for-testing")
    monkeypatch.setenv("MINICLAUDE_PROJECT_DIR", str(tmp_project))
    monkeypatch.setenv("MINICLAUDE_MEMORY_ENABLED", "false")
    monkeypatch.setenv("MINICLAUDE_ALLOW_SHELL", "true")
    reset_config()
    cfg = MiniClaudeConfig()
    yield cfg
    reset_config()


@pytest.fixture
def mock_llm_client() -> AsyncMock:
    """Create a mock LLM client."""
    client = AsyncMock()
    client.total_input_tokens = 0
    client.total_output_tokens = 0
    client.total_tokens = 0
    return client
