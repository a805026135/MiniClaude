"""Token counting utilities using tiktoken."""

from __future__ import annotations

import logging
from functools import lru_cache

import tiktoken

logger = logging.getLogger(__name__)

# Claude models use a tokenizer close to cl100k_base
_FALLBACK_ENCODING = "cl100k_base"


@lru_cache(maxsize=4)
def _get_encoding(model: str = "claude") -> tiktoken.Encoding:
    """Get tiktoken encoding for approximate token counting."""
    try:
        return tiktoken.encoding_for_model(model)
    except KeyError:
        return tiktoken.get_encoding(_FALLBACK_ENCODING)


def count_tokens(text: str, model: str = "claude") -> int:
    """Count approximate tokens in a text string.

    Args:
        text: The text to count tokens for.
        model: Model name (used to select tokenizer).

    Returns:
        Approximate token count.
    """
    if not text:
        return 0
    enc = _get_encoding(model)
    return len(enc.encode(text))


def count_message_tokens(
    messages: list[dict],
    model: str = "claude",
) -> int:
    """Count approximate tokens in a list of messages.

    Each message has overhead for role/formatting. We estimate ~4 tokens
    per message for overhead.

    Args:
        messages: List of message dicts with 'role' and 'content'.
        model: Model name.

    Returns:
        Approximate total token count.
    """
    total = 0
    for msg in messages:
        total += 4  # message overhead
        content = msg.get("content", "")
        if isinstance(content, str):
            total += count_tokens(content, model)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict):
                    text = block.get("text", "")
                    if text:
                        total += count_tokens(text, model)
                elif isinstance(block, str):
                    total += count_tokens(block, model)
    return total


def truncate_to_tokens(text: str, max_tokens: int, model: str = "claude") -> str:
    """Truncate text to fit within a token budget.

    Args:
        text: Text to truncate.
        max_tokens: Maximum tokens allowed.
        model: Model name.

    Returns:
        Truncated text with '...' suffix if truncated.
    """
    if not text:
        return ""
    enc = _get_encoding(model)
    tokens = enc.encode(text)
    if len(tokens) <= max_tokens:
        return text
    truncated = enc.decode(tokens[:max_tokens])
    return truncated + "\n...[truncated]"
