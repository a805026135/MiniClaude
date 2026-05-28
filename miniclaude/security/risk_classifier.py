"""AI-powered risk classifier for tool calls using the LLM itself."""

from __future__ import annotations

import logging
from typing import Any

from miniclaude.memory.types import RiskLevel

logger = logging.getLogger(__name__)

# System prompt for the risk classifier
RISK_CLASSIFIER_PROMPT = """You are a security classifier for an AI coding agent.
Your job is to evaluate whether a tool call is potentially dangerous.

Classify the risk level as one of:
- LOW: Safe operation, no risk of harm
- MEDIUM: Potentially impactful but likely intentional (e.g., writing new files)
- HIGH: Could cause data loss or system modification (e.g., deleting files, modifying configs)
- CRITICAL: Extremely dangerous, should never be executed without explicit approval

Consider:
- The tool being called
- The parameters (file paths, commands, content)
- Whether the operation is reversible
- Whether it could affect files outside the project
- Whether it involves sensitive data

Respond with ONLY a JSON object:
{"risk_level": "LOW|MEDIUM|HIGH|CRITICAL", "reason": "brief explanation"}
"""


class RiskClassifier:
    """AI-powered risk classification for tool calls.

    Uses the LLM itself to assess the risk of a tool call,
    providing a more nuanced evaluation than rule-based systems alone.

    Note: This is an optional enhancement - the system works without it.
    It adds latency (one extra LLM call) but improves safety.
    """

    def __init__(self, llm_client: Any = None) -> None:
        self._llm = llm_client
        self._enabled = llm_client is not None

    async def classify(
        self,
        tool_name: str,
        params: dict[str, Any],
    ) -> tuple[RiskLevel, str]:
        """Classify the risk of a tool call.

        Args:
            tool_name: Name of the tool being called.
            params: Tool parameters.

        Returns:
            Tuple of (RiskLevel, reason string).
        """
        if not self._enabled:
            return RiskLevel.LOW, "Risk classifier not available"

        import json

        prompt = (
            f"Tool: {tool_name}\n"
            f"Parameters: {json.dumps(params, indent=2, default=str)[:500]}\n\n"
            f"Classify the risk level."
        )

        try:
            response = await self._llm.chat(
                messages=[{"role": "user", "content": prompt}],
                system=RISK_CLASSIFIER_PROMPT,
                max_tokens=200,
                temperature=0.0,
            )

            if not response.text:
                return RiskLevel.LOW, "Empty response from classifier"

            # Parse response
            text = response.text.strip()
            # Try to extract JSON
            import re
            json_match = re.search(r'\{[^}]+\}', text)
            if json_match:
                data = json.loads(json_match.group())
                risk = RiskLevel.from_str(data.get("risk_level", "low"))
                reason = data.get("reason", "No reason provided")
                return risk, reason

            return RiskLevel.MEDIUM, f"Could not parse classifier output: {text[:100]}"

        except Exception as e:
            logger.warning("Risk classification failed: %s", e)
            return RiskLevel.LOW, f"Classification error: {e}"

    @property
    def enabled(self) -> bool:
        return self._enabled

    def disable(self) -> None:
        self._enabled = False

    def enable(self, llm_client: Any) -> None:
        self._llm = llm_client
        self._enabled = True
