"""Code Review Skill - analyzes code quality and suggests improvements."""

from __future__ import annotations

from miniclaude.skills.base import BaseSkill, SkillContext, SkillMeta, SkillResult


class CodeReviewSkill(BaseSkill):
    """Performs comprehensive code review with quality analysis."""

    @property
    def meta(self) -> SkillMeta:
        return SkillMeta(
            name="code_review",
            description="Review code for quality, bugs, security issues, and style. "
                        "Provides structured feedback with severity levels.",
            tags=["review", "quality", "security", "code", "audit", "审查", "检查"],
            examples=[
                "review this code",
                "check the code quality",
                "review my changes",
                "审查这段代码",
                "look for bugs in this file",
                "any security issues in this code?",
            ],
            applicable_when="User wants to review code quality, find bugs, or check security",
            tools_used=["read_file", "grep_search", "glob_files"],
        )

    async def execute(self, context: SkillContext) -> SkillResult:
        return SkillResult(
            skill_name=self.name,
            success=True,
            instructions="""
## Code Review Mode

You are now in code review mode. Follow this systematic review process:

### 1. Understanding
- Read the relevant files completely
- Understand the purpose and context of the code

### 2. Review Criteria (check each)
- **Correctness**: Logic errors, edge cases, off-by-one errors
- **Security**: Injection vulnerabilities, hardcoded secrets, unsafe operations
- **Performance**: Inefficient algorithms, unnecessary allocations, N+1 queries
- **Maintainability**: Code clarity, naming, DRY violations, complexity
- **Error Handling**: Missing error cases, swallowed exceptions, proper cleanup
- **Testing**: Test coverage gaps, missing edge case tests

### 3. Output Format
Present findings as:
```
## Code Review Summary

### Issues Found
- 🔴 **Critical** (must fix): ...
- 🟡 **Warning** (should fix): ...
- 🔵 **Info** (consider): ...

### Positive Aspects
- ...

### Suggestions
- ...
```

Be specific: include file paths, line numbers, and concrete fix suggestions.
""",
            suggested_tools=["read_file", "grep_search", "glob_files"],
        )
