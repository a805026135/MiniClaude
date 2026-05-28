"""Permission Manager - multi-layer security check for tool calls."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable

from miniclaude.core.config import MiniClaudeConfig
from miniclaude.memory.types import RiskLevel
from miniclaude.security.prompt_guard import PromptGuard, ScanResult
from miniclaude.security.risk_classifier import RiskClassifier
from miniclaude.security.rules import RuleResult, SecurityRules

logger = logging.getLogger(__name__)


@dataclass
class PermissionResult:
    """Result of a permission check."""
    allowed: bool
    requires_confirmation: bool = False
    message: str = ""
    rule_results: list[RuleResult] | None = None
    injection_scan: ScanResult | None = None
    risk_level: RiskLevel = RiskLevel.LOW


class PermissionManager:
    """Multi-layer security check for tool execution.

    Security chain:
    1. Rule filtering (fast, deterministic)
    2. Tool self-check (tool-specific validation)
    3. Prompt injection scanning
    4. AI risk classification (optional, slower)
    5. Human confirmation (interactive)
    """

    def __init__(
        self,
        config: MiniClaudeConfig,
        risk_classifier: RiskClassifier | None = None,
    ) -> None:
        self.config = config
        self.rules = SecurityRules()
        self.prompt_guard = PromptGuard()
        self.risk_classifier = risk_classifier
        self._confirm_callback: Callable[[str, dict], bool] | None = None
        self._allowed_cache: set[str] = set()  # User-approved operations

    def set_confirm_callback(self, callback: Callable[[str, dict], bool]) -> None:
        """Set the callback for interactive confirmation prompts."""
        self._confirm_callback = callback

    async def check(
        self,
        tool_name: str,
        params: dict[str, Any],
        user_input: str = "",
    ) -> PermissionResult:
        """Run the full permission check chain.

        Args:
            tool_name: Name of the tool to execute.
            params: Tool parameters.
            user_input: Original user input (for injection scanning).

        Returns:
            PermissionResult indicating whether execution is allowed.
        """
        project_dir = str(self.config.effective_project_dir())

        # Layer 1: Rule-based filtering
        rule_results = self.rules.check_tool_call(tool_name, params, project_dir)

        if self.rules.is_blocked(rule_results):
            messages = [r.message for r in rule_results if not r.passed]
            logger.warning("Tool %s blocked by rules: %s", tool_name, messages)
            return PermissionResult(
                allowed=False,
                message=f"Blocked: {'; '.join(messages)}",
                rule_results=rule_results,
            )

        # Layer 2: Prompt injection scan (on user input)
        injection_result = None
        if user_input:
            injection_result = self.prompt_guard.scan_input(user_input)
            if not injection_result.safe and injection_result.risk_level in ("critical", "high"):
                logger.warning("Prompt injection detected: %s", injection_result.message)
                return PermissionResult(
                    allowed=False,
                    message=f"Security: {injection_result.message}",
                    injection_scan=injection_result,
                    risk_level=RiskLevel.from_str(injection_result.risk_level),
                )

        # Layer 3: AI Risk Classification (optional)
        risk_level = RiskLevel.LOW
        if self.risk_classifier and self.risk_classifier.enabled:
            risk_level, risk_reason = await self.risk_classifier.classify(tool_name, params)
            if risk_level == RiskLevel.CRITICAL:
                logger.warning("AI classifier: CRITICAL risk for %s: %s", tool_name, risk_reason)
                return PermissionResult(
                    allowed=False,
                    message=f"Critical risk: {risk_reason}",
                    risk_level=risk_level,
                )

        # Layer 4: Confirmation check
        needs_confirm = self._needs_confirmation(tool_name, params, risk_level)

        if needs_confirm:
            # Check cache (previously approved)
            cache_key = f"{tool_name}:{str(params)[:200]}"
            if cache_key in self._allowed_cache:
                return PermissionResult(
                    allowed=True,
                    message="Previously approved",
                    rule_results=rule_results,
                    risk_level=risk_level,
                )

            # Ask for confirmation
            if self._confirm_callback:
                approved = self._confirm_callback(tool_name, params)
                if approved:
                    self._allowed_cache.add(cache_key)
                    return PermissionResult(
                        allowed=True,
                        message="User approved",
                        rule_results=rule_results,
                        risk_level=risk_level,
                    )
                else:
                    return PermissionResult(
                        allowed=False,
                        message="User denied",
                        rule_results=rule_results,
                        risk_level=risk_level,
                    )

            # No callback — default deny for confirmation-required operations
            warnings = self.rules.get_warnings(rule_results)
            return PermissionResult(
                allowed=False,
                requires_confirmation=True,
                message=f"Confirmation required: {'; '.join(warnings) if warnings else tool_name}",
                rule_results=rule_results,
                risk_level=risk_level,
            )

        # All checks passed
        warnings = self.rules.get_warnings(rule_results)
        return PermissionResult(
            allowed=True,
            message="; ".join(warnings) if warnings else "Approved",
            rule_results=rule_results,
            risk_level=risk_level,
        )

    def _needs_confirmation(
        self,
        tool_name: str,
        params: dict[str, Any],
        risk_level: RiskLevel,
    ) -> bool:
        """Determine if a tool call needs user confirmation."""
        # Always confirm shell commands
        if tool_name == "run_command" and self.config.confirm_dangerous:
            return True

        # Confirm high-risk operations
        if risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
            return True

        # Confirm writes outside project directory
        if tool_name in ("write_file", "edit_file"):
            path = params.get("path", "")
            project = str(self.config.effective_project_dir())
            if path and project and not str(path).startswith(project):
                return True

        return False

    def approve_cached(self, tool_name: str, params: dict[str, Any]) -> None:
        """Pre-approve a tool call (add to cache)."""
        cache_key = f"{tool_name}:{str(params)[:200]}"
        self._allowed_cache.add(cache_key)

    def clear_cache(self) -> None:
        """Clear the approval cache."""
        self._allowed_cache.clear()
