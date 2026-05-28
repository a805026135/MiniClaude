"""Security Auditor - logs all security-relevant events for review."""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class SecurityAuditor:
    """Logs security-relevant events to an audit trail.

    Tracks:
    - Tool calls and their permission check results
    - Prompt injection attempts
    - User confirmations/denials
    - Policy violations
    """

    def __init__(self, log_dir: Path | None = None) -> None:
        self.log_dir = log_dir or Path("data") / "security"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._log_file = self.log_dir / f"audit_{datetime.now().strftime('%Y%m%d')}.jsonl"
        self._events: list[dict[str, Any]] = []

    def log_tool_call(
        self,
        tool_name: str,
        params: dict[str, Any],
        allowed: bool,
        reason: str,
        risk_level: str = "low",
    ) -> None:
        """Log a tool call and its permission result."""
        event = {
            "timestamp": datetime.now().isoformat(),
            "event": "tool_call",
            "tool": tool_name,
            "params_summary": {k: str(v)[:100] for k, v in params.items()},
            "allowed": allowed,
            "reason": reason,
            "risk_level": risk_level,
        }
        self._write_event(event)

    def log_injection_attempt(
        self,
        input_text: str,
        patterns_matched: list[str],
        risk_level: str,
    ) -> None:
        """Log a prompt injection attempt."""
        event = {
            "timestamp": datetime.now().isoformat(),
            "event": "injection_attempt",
            "input_preview": input_text[:200],
            "patterns": patterns_matched,
            "risk_level": risk_level,
        }
        self._write_event(event)

    def log_user_decision(
        self,
        tool_name: str,
        decision: str,  # "approved" or "denied"
        params: dict[str, Any] | None = None,
    ) -> None:
        """Log a user confirmation/denial."""
        event = {
            "timestamp": datetime.now().isoformat(),
            "event": "user_decision",
            "tool": tool_name,
            "decision": decision,
        }
        if params:
            event["params_summary"] = {k: str(v)[:100] for k, v in params.items()}
        self._write_event(event)

    def log_policy_violation(
        self,
        rule_name: str,
        message: str,
        severity: str,
    ) -> None:
        """Log a policy violation."""
        event = {
            "timestamp": datetime.now().isoformat(),
            "event": "policy_violation",
            "rule": rule_name,
            "message": message,
            "severity": severity,
        }
        self._write_event(event)

    def _write_event(self, event: dict[str, Any]) -> None:
        """Write an event to the audit log."""
        self._events.append(event)

        try:
            with open(self._log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.error("Failed to write audit event: %s", e)

        # Also log to standard logger
        severity = event.get("risk_level", event.get("severity", "info"))
        logger.info("[AUDIT] %s: %s", event["event"], json.dumps(event, default=str)[:200])

    @property
    def event_count(self) -> int:
        return len(self._events)

    def get_events(
        self,
        event_type: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get logged events, optionally filtered by type."""
        events = self._events
        if event_type:
            events = [e for e in events if e.get("event") == event_type]
        return events[-limit:]
