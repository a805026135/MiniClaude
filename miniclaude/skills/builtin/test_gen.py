"""Test Generation Skill - generates comprehensive tests."""

from __future__ import annotations

from miniclaude.skills.base import BaseSkill, SkillContext, SkillMeta, SkillResult


class TestGenSkill(BaseSkill):
    """Generates comprehensive tests for existing code."""

    @property
    def meta(self) -> SkillMeta:
        return SkillMeta(
            name="test_gen",
            description="Generate unit tests, integration tests, and edge case tests for code. "
                        "Supports pytest, unittest, Jest, and other frameworks.",
            tags=["test", "testing", "unit test", "spec", "测试", "单元测试"],
            examples=[
                "generate tests for this function",
                "write unit tests for this class",
                "为这个模块写测试",
                "add tests for edge cases",
                "create test suite for this module",
                "write tests for this API endpoint",
            ],
            applicable_when="User wants to create tests for existing code",
            tools_used=["read_file", "write_file", "grep_search", "run_command"],
        )

    async def execute(self, context: SkillContext) -> SkillResult:
        return SkillResult(
            skill_name=self.name,
            success=True,
            instructions="""
## Test Generation Mode

Generate comprehensive tests following these guidelines:

### 1. Analyze the Target
- Read the source code thoroughly
- Identify all public functions/methods/classes
- Understand inputs, outputs, side effects, and error conditions

### 2. Test Categories
Generate tests for:
- **Happy Path**: Normal, expected inputs and behaviors
- **Edge Cases**: Empty inputs, boundary values, maximum/minimum values
- **Error Cases**: Invalid inputs, missing required fields, type mismatches
- **Integration**: How the code interacts with dependencies

### 3. Test Structure
Follow the Arrange-Act-Assert pattern:
```python
def test_descriptive_name():
    # Arrange: set up test data and dependencies
    # Act: call the function under test
    # Assert: verify expected outcomes
```

### 4. Best Practices
- Each test should test ONE thing
- Use descriptive test names that explain the scenario
- Prefer pytest style (functions + assertions)
- Mock external dependencies (databases, APIs, file system)
- Include docstrings explaining what each test verifies

### 5. Detection
- Look for existing test files to match the project's test style and framework
- Check for existing test infrastructure (conftest.py, fixtures, etc.)
""",
            suggested_tools=["read_file", "write_file", "grep_search", "run_command"],
        )
