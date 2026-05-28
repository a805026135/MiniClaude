"""Tests for the tool system."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from miniclaude.tools.file_tools import ReadFileTool, WriteFileTool, EditFileTool, GlobTool, GrepTool
from miniclaude.tools.shell_tools import ShellTool


class TestReadFileTool:
    @pytest.mark.asyncio
    async def test_read_existing_file(self, config, tmp_project: Path):
        tool = ReadFileTool(config)
        result = await tool.execute(path=str(tmp_project / "hello.py"))
        assert result.success
        assert "Hello, World!" in result.content
        assert "print" in result.content

    @pytest.mark.asyncio
    async def test_read_nonexistent_file(self, config, tmp_project: Path):
        tool = ReadFileTool(config)
        result = await tool.execute(path=str(tmp_project / "nope.py"))
        assert not result.success
        assert "not found" in result.content.lower()

    @pytest.mark.asyncio
    async def test_read_with_offset_limit(self, config, tmp_project: Path):
        tool = ReadFileTool(config)
        result = await tool.execute(path=str(tmp_project / "utils.py"), offset=0, limit=2)
        assert result.success
        # Should have the 2 numbered lines + possibly a truncation indicator
        numbered_lines = [l for l in result.content.strip().split("\n") if l.strip() and not l.strip().startswith("...")]
        assert len(numbered_lines) <= 2


class TestWriteFileTool:
    @pytest.mark.asyncio
    async def test_write_new_file(self, config, tmp_project: Path):
        tool = WriteFileTool(config)
        new_file = tmp_project / "new.py"
        result = await tool.execute(path=str(new_file), content="x = 1\n")
        assert result.success
        assert new_file.exists()
        assert new_file.read_text() == "x = 1\n"

    @pytest.mark.asyncio
    async def test_write_creates_dirs(self, config, tmp_project: Path):
        tool = WriteFileTool(config)
        new_file = tmp_project / "deep" / "nested" / "file.py"
        result = await tool.execute(path=str(new_file), content="# deep\n")
        assert result.success
        assert new_file.exists()


class TestEditFileTool:
    @pytest.mark.asyncio
    async def test_edit_file(self, config, tmp_project: Path):
        tool = EditFileTool(config)
        path = str(tmp_project / "hello.py")
        result = await tool.execute(
            path=path,
            old_string='print("Hello, World!")',
            new_string='print("Hi, MiniClaude!")',
        )
        assert result.success
        assert "Hi, MiniClaude!" in (tmp_project / "hello.py").read_text()

    @pytest.mark.asyncio
    async def test_edit_nonexistent(self, config, tmp_project: Path):
        tool = EditFileTool(config)
        result = await tool.execute(
            path=str(tmp_project / "nope.py"),
            old_string="x",
            new_string="y",
        )
        assert not result.success


class TestGlobTool:
    @pytest.mark.asyncio
    async def test_glob_py_files(self, config, tmp_project: Path):
        tool = GlobTool(config)
        result = await tool.execute(pattern="**/*.py", path=str(tmp_project))
        assert result.success
        assert "hello.py" in result.content
        assert "utils.py" in result.content

    @pytest.mark.asyncio
    async def test_glob_no_match(self, config, tmp_project: Path):
        tool = GlobTool(config)
        result = await tool.execute(pattern="**/*.xyz", path=str(tmp_project))
        assert result.success
        assert "No files found" in result.content


class TestGrepTool:
    @pytest.mark.asyncio
    async def test_grep_search(self, config, tmp_project: Path):
        tool = GrepTool(config)
        result = await tool.execute(pattern="def ", path=str(tmp_project))
        assert result.success
        assert "add" in result.content
        assert "multiply" in result.content

    @pytest.mark.asyncio
    async def test_grep_with_glob(self, config, tmp_project: Path):
        tool = GrepTool(config)
        result = await tool.execute(pattern="x = 42", glob="*.py", path=str(tmp_project))
        assert result.success
        assert "nested.py" in result.content


class TestShellTool:
    @pytest.mark.asyncio
    async def test_echo_command(self, config, tmp_project: Path):
        tool = ShellTool(config)
        result = await tool.execute(command="echo hello", cwd=str(tmp_project))
        assert result.success
        assert "hello" in result.content

    @pytest.mark.asyncio
    async def test_blocked_command(self, config, tmp_project: Path):
        tool = ShellTool(config)
        result = await tool.execute(command="rm -rf /", cwd=str(tmp_project))
        assert not result.success

    @pytest.mark.asyncio
    async def test_dangerous_command(self, config, tmp_project: Path):
        tool = ShellTool(config)
        result = await tool.execute(command="rm -rf /tmp/test", cwd=str(tmp_project))
        assert not result.success
        assert "dangerous" in result.content.lower() or "blocked" in result.content.lower()
