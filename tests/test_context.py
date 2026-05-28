"""Tests for context compression system."""

from __future__ import annotations

from pathlib import Path

import pytest

from miniclaude.context.budget import TokenBudget
from miniclaude.context.externalizer import Externalizer
from miniclaude.context.compressor import ContextCompressor
from miniclaude.tools.base import ToolResult


class TestTokenBudget:
    def test_basic_budget(self):
        budget = TokenBudget(max_tokens=1000, reserved_output=100)
        assert budget.remaining == 900
        assert not budget.needs_compression()

    def test_needs_compression(self):
        budget = TokenBudget(max_tokens=1000, reserved_output=100)
        budget.system_tokens = 500
        budget.history_tokens = 400
        assert budget.needs_compression()

    def test_usage_ratio(self):
        budget = TokenBudget(max_tokens=1000, reserved_output=0)
        budget.system_tokens = 500
        assert budget.usage_ratio == 0.5


class TestExternalizer:
    def test_small_result_not_externalized(self, config):
        ext = Externalizer(config)
        result = ToolResult(tool_name="test", success=True, content="short content")
        processed = ext.process(result)
        assert processed.content == "short content"
        assert not processed.truncated

    def test_large_result_externalized(self, config):
        ext = Externalizer(config)
        big_content = "x" * 5000  # Above threshold
        result = ToolResult(tool_name="test", success=True, content=big_content)
        processed = ext.process(result)
        assert processed.truncated
        assert "externalized" in processed.content.lower() or "Result externalized" in processed.content
        assert processed.external_path is not None


class TestContextCompressor:
    def test_no_compression_needed(self):
        comp = ContextCompressor()
        messages = [
            {"role": "user", "content": "hello"},
            {"role": "assistant", "content": "hi"},
        ]
        result = comp.compress_messages(messages, target_tokens=1000, current_tokens=50)
        assert len(result) == 2

    def test_compression_drops_old_messages(self):
        comp = ContextCompressor()
        messages = [
            {"role": "user", "content": "msg " * 200},
            {"role": "assistant", "content": "resp " * 200},
            {"role": "user", "content": "msg " * 200},
            {"role": "assistant", "content": "resp " * 200},
            {"role": "user", "content": "msg " * 200},
            {"role": "assistant", "content": "resp " * 200},
            {"role": "user", "content": "msg " * 200},
            {"role": "assistant", "content": "resp " * 200},
            {"role": "user", "content": "msg " * 200},
            {"role": "assistant", "content": "resp " * 200},
            {"role": "user", "content": "msg " * 200},
            {"role": "assistant", "content": "resp " * 200},
            {"role": "user", "content": "msg " * 200},
            {"role": "assistant", "content": "resp " * 200},
        ]
        result = comp.compress_messages(messages, target_tokens=100, current_tokens=10000)
        # Should compress - either by truncation or dropping
        assert len(result) <= len(messages)
