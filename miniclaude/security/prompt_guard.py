"""Prompt Injection Guard - detects and blocks prompt injection attempts."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ScanResult:
    """Result of a prompt injection scan."""
    safe: bool
    risk_level: str  # low, medium, high, critical
    patterns_matched: list[str]
    message: str = ""


class PromptGuard:
    """Detects prompt injection attempts in user input and tool results.

    Uses a combination of:
    - Regex pattern matching (fast, catches known patterns)
    - Heuristic analysis (catches variations)
    """

    # Known prompt injection patterns
    INJECTION_PATTERNS = [
        # English patterns
        (r'ignore\s+(previous|all|above)\s+(instructions|prompts|rules)', "ignore_instructions"),
        (r'forget\s+(everything|all|previous)', "forget_instructions"),
        (r'you\s+are\s+now\s+(a|an|the)', "role_override"),
        (r'system\s*:\s*', "system_injection"),
        (r'<\s*system\s*>', "system_tag"),
        (r'<\s*/?\s*assistant\s*>', "assistant_tag"),
        (r'new\s+instructions?\s*:', "new_instructions"),
        (r'override\s+(your|the)\s+(instructions|rules|settings)', "override"),
        (r'act\s+as\s+if\s+you\s+(are|were)', "role_play_attack"),
        (r'do\s+not\s+(follow|obey|listen to)', "disobey"),
        (r'disregard\s+(previous|all|above)', "disregard"),
        (r'pretend\s+(you|that|to be)', "pretend"),
        (r'imagine\s+you\s+(are|were|have)', "imagine_override"),

        # Chinese patterns
        (r'忽略(之前|上面|以上)(的)?(所有|全部)?(的)?(指令|提示|规则|要求)', "ignore_cn"),
        (r'(所有|全部)(的)?(指令|提示|规则)(都)?(忽略|忘|不要)', "ignore_cn"),
        (r'忘记(之前|上面|以上)(的)?(所有|全部)?(的)?(指令|提示|规则)', "forget_cn"),
        (r'(无视|不要|别)(遵循|遵守|执行|理会)', "disobey_cn"),
        (r'你现在是', "role_override_cn"),
        (r'(新的|以下)(指令|规则|要求)是', "new_instructions_cn"),
        (r'(假装|假设|假设你)是', "pretend_cn"),
        (r'(系统|提示词|system\s*prompt)', "system_probe_cn"),

        # Prompt leaking attempts
        (r'(show|reveal|print|output|display)\s+(your|the)\s+(system|original)\s+(prompt|instructions)', "prompt_leak"),
        (r'(show|reveal|print|output|display)\s+(your|the)\s+system\s+prompt', "prompt_leak"),
        (r'what\s+(is|are)\s+your\s+(system\s+)?(prompt|instructions)', "prompt_probe"),
        (r'repeat\s+(the\s+)?(above|previous|system)\s+(text|prompt|message)', "repeat_prompt"),
        (r'(show|reveal|tell|give)\s+.*?(system\s+prompt|instructions)', "prompt_leak_general"),

        # Encoded/obfuscated attempts
        (r'base64\s+(decode|encode)', "encoding_trick"),
        (r'(ROT13|rot13)', "encoding_trick"),
    ]

    # Suspicious patterns that warrant a warning
    SUSPICIOUS_PATTERNS = [
        (r'<\|im_start\|>', "chat_template_injection"),
        (r'<\|im_end\|>', "chat_template_injection"),
        (r'\[INST\]', "llama_template"),
        (r'\[/INST\]', "llama_template"),
        (r'<<SYS>>', "llama_system_tag"),
        (r'<</SYS>>', "llama_system_tag"),
    ]

    def scan_input(self, user_input: str) -> ScanResult:
        """Scan user input for prompt injection attempts.

        Args:
            user_input: The user's text input.

        Returns:
            ScanResult with safety assessment.
        """
        return self._scan(user_input)

    def scan_tool_result(self, content: str) -> ScanResult:
        """Scan tool result content for injected prompts.

        Attackers might embed instructions in file contents
        that get read by the agent.
        """
        return self._scan(content)

    def _scan(self, text: str) -> ScanResult:
        """Perform the actual scan."""
        text_lower = text.lower()
        matched_patterns: list[str] = []

        # Check injection patterns
        for pattern, name in self.INJECTION_PATTERNS:
            if re.search(pattern, text_lower, re.IGNORECASE):
                matched_patterns.append(name)

        # Check suspicious patterns
        for pattern, name in self.SUSPICIOUS_PATTERNS:
            if re.search(pattern, text, re.IGNORECASE):
                matched_patterns.append(f"suspicious:{name}")

        # Assess risk level
        if not matched_patterns:
            return ScanResult(safe=True, risk_level="low", patterns_matched=[])

        critical_patterns = {"ignore_instructions", "system_injection", "system_tag",
                           "ignore_cn", "new_instructions", "new_instructions_cn"}
        high_patterns = {"forget_instructions", "role_override", "override",
                        "disobey", "disregard", "forget_cn", "disobey_cn"}

        matched_set = set(matched_patterns)

        if matched_set & critical_patterns:
            risk = "critical"
            msg = "Critical prompt injection attempt detected"
        elif matched_set & high_patterns:
            risk = "high"
            msg = "High-risk prompt injection pattern detected"
        elif any(p.startswith("suspicious:") for p in matched_patterns):
            risk = "medium"
            msg = "Suspicious template patterns detected"
        else:
            risk = "medium"
            msg = "Potential prompt injection pattern detected"

        logger.warning("Prompt injection scan: risk=%s, patterns=%s", risk, matched_patterns)

        return ScanResult(
            safe=False,
            risk_level=risk,
            patterns_matched=matched_patterns,
            message=msg,
        )
