"""Rule-based security filtering for tool calls and user input."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class RuleResult:
    """Result of a rule check."""
    passed: bool
    rule_name: str
    message: str = ""
    severity: str = "info"  # info, warning, error, critical


class SecurityRules:
    """Rule-based security filtering system.

    Evaluates tool calls and user input against a set of configurable rules
    to detect and prevent dangerous operations.
    """

    def __init__(self) -> None:
        self._rules: list[SecurityRule] = self._default_rules()

    def check_tool_call(
        self,
        tool_name: str,
        params: dict[str, Any],
        project_dir: str = "",
    ) -> list[RuleResult]:
        """Run all applicable rules against a tool call."""
        results = []
        for rule in self._rules:
            if rule.applies_to(tool_name):
                result = rule.evaluate(tool_name, params, project_dir)
                results.append(result)
        return results

    def is_blocked(self, results: list[RuleResult]) -> bool:
        """Check if any rule result blocks execution."""
        return any(not r.passed and r.severity in ("error", "critical") for r in results)

    def get_warnings(self, results: list[RuleResult]) -> list[str]:
        """Get warning messages from results."""
        return [r.message for r in results if not r.passed and r.severity == "warning"]

    @staticmethod
    def _default_rules() -> list["SecurityRule"]:
        """Define the default security rules."""
        return [
            PathBoundaryRule(),
            DangerousCommandRule(),
            SensitiveFileRule(),
            BinaryFileRule(),
            SizeLimitRule(),
        ]


class SecurityRule:
    """Base class for security rules."""

    def applies_to(self, tool_name: str) -> bool:
        """Check if this rule applies to the given tool."""
        return True

    def evaluate(
        self,
        tool_name: str,
        params: dict[str, Any],
        project_dir: str,
    ) -> RuleResult:
        """Evaluate the rule. Override in subclasses."""
        return RuleResult(passed=True, rule_name="base")


class PathBoundaryRule(SecurityRule):
    """Ensures file operations stay within the project boundary."""

    BLOCKED_PATHS = [
        "/etc/", "/proc/", "/sys/", "/dev/",
        "~/.ssh/", "~/.aws/", "~/.gnupg/",
        "C:\\Windows\\", "C:\\Users\\All Users",
    ]

    def applies_to(self, tool_name: str) -> bool:
        return tool_name in ("read_file", "write_file", "edit_file", "glob_files", "grep_search")

    def evaluate(self, tool_name: str, params: dict[str, Any], project_dir: str) -> RuleResult:
        path = params.get("path", "")
        if not path:
            return RuleResult(passed=True, rule_name="path_boundary")

        # Check blocked paths
        path_lower = path.lower().replace("\\", "/")
        for blocked in self.BLOCKED_PATHS:
            if blocked.lower().replace("\\", "/") in path_lower:
                return RuleResult(
                    passed=False,
                    rule_name="path_boundary",
                    message=f"Access to system path blocked: {path}",
                    severity="critical",
                )

        # Check project boundary (if configured)
        if project_dir:
            from pathlib import Path
            resolved = Path(path).resolve()
            project = Path(project_dir).resolve()
            if not str(resolved).startswith(str(project)):
                # Allow with warning
                return RuleResult(
                    passed=True,
                    rule_name="path_boundary",
                    message=f"Path is outside project directory: {path}",
                    severity="warning",
                )

        return RuleResult(passed=True, rule_name="path_boundary")


class DangerousCommandRule(SecurityRule):
    """Blocks known dangerous shell commands."""

    BLOCKED_PATTERNS = [
        (r'\brm\s+-rf\s+/', "Recursive delete from root"),
        (r'\bmkfs\b', "Filesystem formatting"),
        (r'\bdd\s+if=', "Direct disk write"),
        (r':\(\)\{.*fork\s*bomb', "Fork bomb"),
        (r'\bshutdown\b', "System shutdown"),
        (r'\breboot\b', "System reboot"),
        (r'\bformat\s+[a-zA-Z]:', "Disk format"),
        (r'>\s*/dev/sd', "Direct device write"),
        (r'\bchmod\s+777', "Overly permissive permissions"),
        (r'\bkill\s+-9\s+1\b', "Kill init process"),
    ]

    DANGEROUS_PATTERNS = [
        (r'\brm\s+-r\b', "Recursive delete"),
        (r'\bDROP\s+TABLE\b', "SQL table drop"),
        (r'\bDROP\s+DATABASE\b', "SQL database drop"),
        (r'\bDELETE\s+FROM\b', "SQL delete"),
        (r'\bTRUNCATE\b', "SQL truncate"),
        (r'\bgit\s+push\s+--force\b', "Force push"),
        (r'\bgit\s+reset\s+--hard\b', "Hard reset"),
        (r'\bgit\s+clean\s+-f\b', "Force clean"),
        (r'\bpip\s+install\b', "Package install"),
        (r'\bnpm\s+install\b', "Package install"),
    ]

    def applies_to(self, tool_name: str) -> bool:
        return tool_name == "run_command"

    def evaluate(self, tool_name: str, params: dict[str, Any], project_dir: str) -> RuleResult:
        command = params.get("command", "")
        if not command:
            return RuleResult(passed=True, rule_name="dangerous_command")

        # Check blocked patterns
        for pattern, desc in self.BLOCKED_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                return RuleResult(
                    passed=False,
                    rule_name="dangerous_command",
                    message=f"Blocked dangerous command ({desc}): {command}",
                    severity="critical",
                )

        # Check dangerous patterns (warn but don't block)
        for pattern, desc in self.DANGEROUS_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                return RuleResult(
                    passed=False,
                    rule_name="dangerous_command",
                    message=f"Dangerous command detected ({desc}): {command}",
                    severity="warning",
                )

        return RuleResult(passed=True, rule_name="dangerous_command")


class SensitiveFileRule(SecurityRule):
    """Prevents access to sensitive configuration files."""

    SENSITIVE_PATTERNS = [
        r'\.env$',
        r'\.env\.',
        r'credentials',
        r'secret',
        r'\.pem$',
        r'\.key$',
        r'private_key',
        r'\.htpasswd',
        r'id_rsa',
        r'id_ed25519',
    ]

    def applies_to(self, tool_name: str) -> bool:
        return tool_name in ("read_file", "write_file", "edit_file")

    def evaluate(self, tool_name: str, params: dict[str, Any], project_dir: str) -> RuleResult:
        path = params.get("path", "")
        for pattern in self.SENSITIVE_PATTERNS:
            if re.search(pattern, path, re.IGNORECASE):
                if tool_name == "read_file":
                    return RuleResult(
                        passed=False,
                        rule_name="sensitive_file",
                        message=f"Reading potentially sensitive file: {path}",
                        severity="warning",
                    )
                else:
                    return RuleResult(
                        passed=False,
                        rule_name="sensitive_file",
                        message=f"Writing to sensitive file blocked: {path}",
                        severity="error",
                    )

        return RuleResult(passed=True, rule_name="sensitive_file")


class BinaryFileRule(SecurityRule):
    """Prevents reading/writing binary files."""

    BINARY_EXTENSIONS = {
        '.exe', '.dll', '.so', '.dylib', '.bin', '.dat',
        '.zip', '.tar', '.gz', '.rar', '.7z',
        '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.ico',
        '.mp3', '.mp4', '.avi', '.mov',
        '.pdf', '.doc', '.docx', '.xls', '.xlsx',
    }

    def applies_to(self, tool_name: str) -> bool:
        return tool_name in ("read_file", "write_file")

    def evaluate(self, tool_name: str, params: dict[str, Any], project_dir: str) -> RuleResult:
        path = params.get("path", "")
        from pathlib import Path
        ext = Path(path).suffix.lower()
        if ext in self.BINARY_EXTENSIONS:
            return RuleResult(
                passed=False,
                rule_name="binary_file",
                message=f"Binary file not supported: {path} ({ext})",
                severity="warning",
            )
        return RuleResult(passed=True, rule_name="binary_file")


class SizeLimitRule(SecurityRule):
    """Prevents excessively large file operations."""

    MAX_WRITE_SIZE = 1_000_000  # 1MB

    def applies_to(self, tool_name: str) -> bool:
        return tool_name == "write_file"

    def evaluate(self, tool_name: str, params: dict[str, Any], project_dir: str) -> RuleResult:
        content = params.get("content", "")
        if len(content) > self.MAX_WRITE_SIZE:
            return RuleResult(
                passed=False,
                rule_name="size_limit",
                message=f"Content too large: {len(content)} bytes (max: {self.MAX_WRITE_SIZE})",
                severity="error",
            )
        return RuleResult(passed=True, rule_name="size_limit")
