"""Code Generation Skill - generates code based on requirements and specifications."""

from __future__ import annotations

from miniclaude.skills.base import BaseSkill, SkillContext, SkillMeta, SkillResult


class CodeGenSkill(BaseSkill):
    """Generates code based on user requirements and specifications."""

    @property
    def meta(self) -> SkillMeta:
        return SkillMeta(
            name="code_gen",
            description="Generate code based on requirements, specifications, or descriptions. "
                        "Supports multiple programming languages and code structures.",
            tags=["generate", "code", "create", "write", "implement", "生成", "代码", "编写", "实现", "开发", "编程"],
            examples=[
                "generate a Python function to sort a list",
                "create a REST API endpoint",
                "write a class for handling user authentication",
                "生成一个数据库连接工具",
                "implement a binary search algorithm",
                "create a React component for a login form",
                "write a function to parse CSV files",
                "generate unit test framework",
                "create a command-line argument parser",
                "write a file compression utility",
                "生成一个日志记录器",
                "implement a caching mechanism",
                "create a database migration script",
                "write a configuration file parser",
            ],
            applicable_when="User wants to generate new code based on requirements or specifications",
            tools_used=["write_file", "read_file", "grep_search"],
        )

    async def execute(self, context: SkillContext) -> SkillResult:
        return SkillResult(
            skill_name=self.name,
            success=True,
            instructions="""
## Code Generation Mode

You are now in code generation mode. Follow these guidelines to generate high-quality code:

### 1. Requirements Analysis
- Carefully read and understand the user's requirements
- Identify the programming language, framework, and specific needs
- Clarify any ambiguous requirements before generating code

### 2. Code Structure Planning
- Plan the code structure before writing
- Consider modularity, reusability, and maintainability
- Identify necessary imports and dependencies

### 3. Code Generation Guidelines
Follow these best practices:
- **Clean Code**: Use meaningful names, proper indentation, and consistent formatting
- **Documentation**: Include docstrings, comments for complex logic
- **Error Handling**: Add appropriate error handling and validation
- **Type Hints**: Include type annotations where applicable
- **DRY Principle**: Avoid code duplication
- **SOLID Principles**: Follow object-oriented design principles

### 4. Language-Specific Best Practices
Adapt to the target language:
- **Python**: PEP 8, type hints, context managers, generators
- **JavaScript/TypeScript**: ES6+ features, async/await, proper error handling
- **Java**: SOLID principles, proper exception handling, design patterns
- **C++**: RAII, memory management, modern C++ features
- **Go**: Error handling, goroutines, interfaces

### 5. Output Format
Present the generated code with:
```
## Generated Code

### Description
Brief description of what the code does and its purpose.

### Dependencies
List any required imports or dependencies.

### Implementation
```[language]
// Generated code here
```

### Usage Example
```[language]
// Example of how to use the generated code
```

### Notes
- Any important considerations
- Potential improvements
- Performance considerations
```

### 6. Quality Assurance
- Verify the code compiles/runs without syntax errors
- Check for potential bugs or security issues
- Ensure proper error handling
- Validate edge cases
""",
            suggested_tools=["write_file", "read_file", "grep_search"],
        )