"""Explain Skill - explains code clearly and thoroughly."""

from __future__ import annotations

from miniclaude.skills.base import BaseSkill, SkillContext, SkillMeta, SkillResult


class ExplainSkill(BaseSkill):
    """Explains code, concepts, and architecture clearly."""

    @property
    def meta(self) -> SkillMeta:
        return SkillMeta(
            name="explain",
            description="Explain code behavior, architecture, design patterns, and concepts "
                        "clearly and thoroughly with examples.",
            tags=["explain", "understand", "what", "how", "why", "解释", "说明", "怎么"],
            examples=[
                "explain this code",
                "what does this function do",
                "解释这段代码",
                "how does this work",
                "what is this design pattern",
                "walk me through this file",
            ],
            applicable_when="User wants to understand how code works or learn about concepts",
            tools_used=["read_file", "grep_search", "glob_files"],
        )

    async def execute(self, context: SkillContext) -> SkillResult:
        return SkillResult(
            skill_name=self.name,
            success=True,
            instructions="""
## Explanation Mode

Explain code or concepts clearly, adapting to the user's apparent level:

### Structure
1. **High-Level Overview**: What does this code do in 1-2 sentences?
2. **Key Components**: List the main parts (functions, classes, modules)
3. **Flow**: How do the parts connect? What's the execution path?
4. **Important Details**: Non-obvious logic, design decisions, trade-offs
5. **Context**: How does this fit into the larger codebase?

### Guidelines
- Use clear, simple language
- Provide concrete examples when explaining abstract concepts
- Use analogies for complex ideas
- Include code snippets to illustrate key points
- Point out patterns: "This uses the Observer pattern where..."
- Highlight potential gotchas or common misconceptions

### For Architecture Questions
- Draw ASCII diagrams for component relationships
- Explain data flow through the system
- Note key design decisions and their rationale
""",
            suggested_tools=["read_file", "grep_search", "glob_files"],
        )
