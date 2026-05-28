"""File operation tools: read, write, edit, glob, grep."""

from __future__ import annotations

import fnmatch
import logging
import os
import re
from pathlib import Path
from typing import Any

from miniclaude.core.config import MiniClaudeConfig
from miniclaude.tools.base import BaseTool, ToolResult

logger = logging.getLogger(__name__)


def _resolve_path(path: str, config: MiniClaudeConfig) -> Path:
    """Resolve and validate a file path against the project boundary."""
    p = Path(path).resolve()
    project_dir = config.effective_project_dir()
    # Allow absolute paths within project, or resolve relative to project
    if not p.is_relative_to(project_dir) and not path.startswith("/"):
        p = (project_dir / path).resolve()
    return p


class ReadFileTool(BaseTool):
    """Read the contents of a file."""

    def __init__(self, config: MiniClaudeConfig) -> None:
        self._config = config

    @property
    def name(self) -> str:
        return "read_file"

    @property
    def description(self) -> str:
        return (
            "Read the contents of a file at the given path. "
            "Supports optional offset and limit for reading specific line ranges. "
            "Returns file content with line numbers."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "path": {
                "type": "string",
                "description": "Absolute or relative file path to read",
            },
            "offset": {
                "type": "integer",
                "description": "Line number to start reading from (0-indexed). Default: 0",
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of lines to read. Default: 2000",
            },
        }

    def _get_required_params(self) -> list[str]:
        return ["path"]

    async def execute(self, **kwargs: Any) -> ToolResult:
        path = kwargs.get("path", "")
        offset = kwargs.get("offset", 0) or 0
        limit = kwargs.get("limit", 2000) or 2000

        p = _resolve_path(path, self._config)

        if not p.exists():
            return self._error(f"File not found: {p}")
        if not p.is_file():
            return self._error(f"Not a file: {p}")

        try:
            lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
            total = len(lines)
            selected = lines[offset : offset + limit]

            # Format with line numbers
            numbered = []
            for i, line in enumerate(selected, start=offset + 1):
                numbered.append(f"{i:6d}\t{line}")

            content = "\n".join(numbered)

            if offset + limit < total:
                content += f"\n... ({total - offset - limit} more lines, total {total} lines)"

            logger.debug("Read %s: lines %d-%d of %d", p.name, offset, offset + len(selected), total)
            return self._success(content, metadata={"total_lines": total, "path": str(p)})

        except Exception as e:
            return self._error(f"Failed to read {p}: {e}")


class WriteFileTool(BaseTool):
    """Write content to a file, creating directories if needed."""

    def __init__(self, config: MiniClaudeConfig) -> None:
        self._config = config

    @property
    def name(self) -> str:
        return "write_file"

    @property
    def description(self) -> str:
        return (
            "Write content to a file. Creates the file and any parent directories "
            "if they don't exist. Overwrites existing files."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "path": {
                "type": "string",
                "description": "File path to write to",
            },
            "content": {
                "type": "string",
                "description": "Content to write to the file",
            },
        }

    def _get_required_params(self) -> list[str]:
        return ["path", "content"]

    async def execute(self, **kwargs: Any) -> ToolResult:
        path = kwargs.get("path", "")
        content = kwargs.get("content", "")

        p = _resolve_path(path, self._config)

        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            line_count = content.count("\n") + 1 if content else 0
            logger.debug("Wrote %s: %d bytes, %d lines", p.name, len(content), line_count)
            return self._success(
                f"Successfully wrote {len(content)} bytes ({line_count} lines) to {p}",
                metadata={"bytes": len(content), "lines": line_count, "path": str(p)},
            )
        except Exception as e:
            return self._error(f"Failed to write {p}: {e}")


class EditFileTool(BaseTool):
    """Edit a file by replacing an exact string match."""

    def __init__(self, config: MiniClaudeConfig) -> None:
        self._config = config

    @property
    def name(self) -> str:
        return "edit_file"

    @property
    def description(self) -> str:
        return (
            "Edit a file by replacing an exact string match with new text. "
            "The old_string must be unique within the file. "
            "Use replace_all=true to replace all occurrences."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "path": {
                "type": "string",
                "description": "File path to edit",
            },
            "old_string": {
                "type": "string",
                "description": "Exact string to find and replace (must be unique unless replace_all=true)",
            },
            "new_string": {
                "type": "string",
                "description": "Replacement string",
            },
            "replace_all": {
                "type": "boolean",
                "description": "If true, replace all occurrences. Default: false",
            },
        }

    def _get_required_params(self) -> list[str]:
        return ["path", "old_string", "new_string"]

    async def execute(self, **kwargs: Any) -> ToolResult:
        path = kwargs.get("path", "")
        old_string = kwargs.get("old_string", "")
        new_string = kwargs.get("new_string", "")
        replace_all = kwargs.get("replace_all", False)

        p = _resolve_path(path, self._config)

        if not p.exists():
            return self._error(f"File not found: {p}")

        try:
            content = p.read_text(encoding="utf-8")

            if old_string not in content:
                return self._error(f"old_string not found in {p}")

            if not replace_all:
                count = content.count(old_string)
                if count > 1:
                    return self._error(
                        f"old_string appears {count} times in {p}. "
                        f"Provide more context to make it unique, or use replace_all=true."
                    )

            new_content = content.replace(old_string, new_string) if replace_all else content.replace(old_string, new_string, 1)
            p.write_text(new_content, encoding="utf-8")

            occurrences = content.count(old_string) if replace_all else 1
            logger.debug("Edited %s: replaced %d occurrence(s)", p.name, occurrences)
            return self._success(
                f"Successfully edited {p}: replaced {occurrences} occurrence(s) of the target string.",
                metadata={"occurrences": occurrences, "path": str(p)},
            )
        except Exception as e:
            return self._error(f"Failed to edit {p}: {e}")


class GlobTool(BaseTool):
    """Search for files matching a glob pattern."""

    def __init__(self, config: MiniClaudeConfig) -> None:
        self._config = config

    @property
    def name(self) -> str:
        return "glob_files"

    @property
    def description(self) -> str:
        return (
            "Find files matching a glob pattern (e.g. '**/*.py', 'src/**/*.ts'). "
            "Returns matching file paths sorted by modification time."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "pattern": {
                "type": "string",
                "description": "Glob pattern to match (e.g. '**/*.py', '*.json')",
            },
            "path": {
                "type": "string",
                "description": "Directory to search in. Default: current project directory",
            },
        }

    def _get_required_params(self) -> list[str]:
        return ["pattern"]

    async def execute(self, **kwargs: Any) -> ToolResult:
        pattern = kwargs.get("pattern", "")
        search_path = kwargs.get("path", "")

        base = Path(search_path).resolve() if search_path else self._config.effective_project_dir()

        if not base.exists():
            return self._error(f"Directory not found: {base}")

        try:
            matches = sorted(
                base.glob(pattern),
                key=lambda p: p.stat().st_mtime if p.exists() else 0,
                reverse=True,
            )

            # Limit to 200 results
            max_results = 200
            truncated = len(matches) > max_results
            matches = matches[:max_results]

            paths = [str(m.relative_to(base)) for m in matches if m.is_file()]
            content = "\n".join(paths) if paths else "No files found."

            if truncated:
                content += f"\n... (showing first {max_results} of {len(matches)} matches)"

            logger.debug("Glob '%s' in %s: %d matches", pattern, base, len(paths))
            return self._success(
                content,
                metadata={"match_count": len(paths), "truncated": truncated},
            )
        except Exception as e:
            return self._error(f"Glob search failed: {e}")


class GrepTool(BaseTool):
    """Search file contents using regex patterns."""

    def __init__(self, config: MiniClaudeConfig) -> None:
        self._config = config

    @property
    def name(self) -> str:
        return "grep_search"

    @property
    def description(self) -> str:
        return (
            "Search file contents using a regex pattern. "
            "Returns matching lines with file paths and line numbers. "
            "Supports filtering by file glob (e.g. '*.py')."
        )

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "pattern": {
                "type": "string",
                "description": "Regex pattern to search for",
            },
            "path": {
                "type": "string",
                "description": "File or directory to search in. Default: project directory",
            },
            "glob": {
                "type": "string",
                "description": "File glob filter (e.g. '*.py', '*.{ts,tsx}')",
            },
            "case_insensitive": {
                "type": "boolean",
                "description": "Case-insensitive search. Default: false",
            },
        }

    def _get_required_params(self) -> list[str]:
        return ["pattern"]

    async def execute(self, **kwargs: Any) -> ToolResult:
        pattern = kwargs.get("pattern", "")
        search_path = kwargs.get("path", "")
        file_glob = kwargs.get("glob", "")
        case_insensitive = kwargs.get("case_insensitive", False)

        base = Path(search_path).resolve() if search_path else self._config.effective_project_dir()

        if not base.exists():
            return self._error(f"Directory not found: {base}")

        try:
            flags = re.IGNORECASE if case_insensitive else 0
            regex = re.compile(pattern, flags)
        except re.error as e:
            return self._error(f"Invalid regex pattern: {e}")

        results: list[str] = []
        max_results = 100
        files_searched = 0

        try:
            if base.is_file():
                files = [base]
            else:
                if file_glob:
                    files = sorted(base.rglob(file_glob))
                else:
                    # Default: search common code files
                    files = []
                    for ext in ["*.py", "*.js", "*.ts", "*.jsx", "*.tsx", "*.java",
                                "*.go", "*.rs", "*.c", "*.cpp", "*.h", "*.hpp",
                                "*.rb", "*.php", "*.swift", "*.kt", "*.scala",
                                "*.md", "*.txt", "*.json", "*.yaml", "*.yml",
                                "*.toml", "*.cfg", "*.ini"]:
                        files.extend(base.rglob(ext))

            for fpath in files:
                if not fpath.is_file():
                    continue
                # Skip binary files and large files
                try:
                    if fpath.stat().st_size > 1_000_000:
                        continue
                    text = fpath.read_text(encoding="utf-8", errors="ignore")
                except (OSError, PermissionError):
                    continue

                files_searched += 1
                for line_num, line in enumerate(text.splitlines(), 1):
                    if regex.search(line):
                        rel = str(fpath.relative_to(base))
                        results.append(f"{rel}:{line_num}: {line.strip()}")
                        if len(results) >= max_results:
                            break
                if len(results) >= max_results:
                    break

            content = "\n".join(results) if results else "No matches found."
            if len(results) >= max_results:
                content += f"\n... (showing first {max_results} matches)"

            logger.debug(
                "Grep '%s': %d matches in %d files",
                pattern, len(results), files_searched,
            )
            return self._success(
                content,
                metadata={
                    "match_count": len(results),
                    "files_searched": files_searched,
                },
            )
        except Exception as e:
            return self._error(f"Grep search failed: {e}")
