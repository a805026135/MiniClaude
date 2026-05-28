"""Debug Skill - systematic debugging methodology."""

from __future__ import annotations

from miniclaude.skills.base import BaseSkill, SkillContext, SkillMeta, SkillResult


class DebugSkill(BaseSkill):
    """Guides systematic debugging with root cause analysis."""

    @property
    def meta(self) -> SkillMeta:
        return SkillMeta(
            name="debug",
            description="Systematically debug errors, exceptions, and unexpected behavior. "
                        "Follows a structured debugging methodology.",
            tags=["debug", "fix", "error", "bug", "issue", "调试", "错误", "修复"],
            examples=[
                "debug this error",
                "fix this bug",
                "this code is broken",
                "修复这个错误",
                "why is this not working",
                "there's an exception in this function",
            ],
            applicable_when="User has an error, bug, or unexpected behavior to investigate",
            tools_used=["read_file", "grep_search", "run_command", "glob_files"],
        )

    async def execute(self, context: SkillContext) -> SkillResult:
        return SkillResult(
            skill_name=self.name,
            success=True,
            instructions="""
## Debugging Mode

Follow this systematic debugging methodology:

### 1. Reproduce & Understand
- Identify the exact error message, stack trace, or unexpected behavior
- Ask: What should happen vs. what actually happens?
- Find the minimal reproduction steps

### 2. Investigate
- Read the error location and surrounding code
- Trace the execution path: who calls this? what data flows in?
- Check recent changes: `git log`, `git diff`
- Search for similar patterns: does this work elsewhere?

### 3. Hypothesize & Test
- Form hypotheses about the root cause
- Test each hypothesis systematically:
  - Add debug prints / logging
  - Check variable values at key points
  - Verify assumptions about data types, ranges, nullability

### 4. Fix
- Fix the ROOT cause, not just symptoms
- Make the minimal change that addresses the issue
- Verify the fix works with the original reproduction case

### 5. Prevent
- Add a test that would have caught this bug
- Check if the same pattern exists elsewhere

Be methodical. Don't guess — investigate.
""",
            suggested_tools=["read_file", "grep_search", "run_command", "glob_files"],
        )
