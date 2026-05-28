"""Refactor Skill - guides code refactoring with best practices."""

from __future__ import annotations

from miniclaude.skills.base import BaseSkill, SkillContext, SkillMeta, SkillResult


class RefactorSkill(BaseSkill):
    """Provides structured refactoring guidance."""

    @property
    def meta(self) -> SkillMeta:
        return SkillMeta(
            name="refactor",
            description="Refactor code for better structure, readability, and maintainability. "
                        "Applies design patterns and clean code principles.",
            tags=["refactor", "restructure", "clean", "重构", "重写", "优化"],
            examples=[
                "refactor this function",
                "clean up this code",
                "重构这个模块",
                "make this code more readable",
                "apply design patterns here",
                "improve the structure of this file",
            ],
            applicable_when="User wants to improve code structure without changing behavior",
            tools_used=["read_file", "write_file", "edit_file", "grep_search"],
        )

    async def execute(self, context: SkillContext) -> SkillResult:
        return SkillResult(
            skill_name=self.name,
            success=True,
            instructions="""
## Refactoring Mode

You are in refactoring mode. Follow this disciplined approach:

### 1. Analyze First
- Read the target code thoroughly
- Identify code smells: long methods, deep nesting, duplication, poor naming
- Understand dependencies and callers

### 2. Refactoring Strategy
- **Extract Method**: Break long functions into smaller, focused ones
- **Rename**: Use clear, descriptive names for variables, functions, classes
- **Simplify Conditionals**: Reduce nesting with early returns, guard clauses
- **DRY**: Eliminate duplication by extracting common logic
- **Single Responsibility**: Each function/class should do one thing well
- **Dependency Direction**: High-level modules shouldn't depend on low-level details

### 3. Safety Rules
- Make ONE change at a time
- Preserve existing behavior exactly
- Read surrounding code before editing
- Check for callers/references before renaming or moving

### 4. Output
Explain what you're refactoring and why before each change.
""",
            suggested_tools=["read_file", "edit_file", "grep_search", "glob_files"],
        )
