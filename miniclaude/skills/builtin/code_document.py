"""Code Documentation Skill - generates and improves code documentation."""

from __future__ import annotations

from miniclaude.skills.base import BaseSkill, SkillContext, SkillMeta, SkillResult


class CodeDocumentSkill(BaseSkill):
    """Generates and improves code documentation including docstrings, comments, and README files."""

    @property
    def meta(self) -> SkillMeta:
        return SkillMeta(
            name="code_document",
            description="Generate, improve, and maintain code documentation including docstrings, "
                        "inline comments, type hints, and README files.",
            tags=[
                "document", "documentation", "docstring", "comment", "readme",
                "docs", "javadoc", "jsdoc", "pydoc", "type hint", "annotation",
                "文档", "注释", "说明", "帮助文档", "使用说明", "API文档",
                "generate docs", "improve docs", "add comments"
            ],
            examples=[
                "add docstrings to this code",
                "generate documentation for this module",
                "improve code comments",
                "为这段代码添加注释",
                "create a README for this project",
                "add type hints to these functions",
                "write API documentation",
                "document this class",
                "为这个模块生成文档",
                "add inline comments to explain the logic",
                "generate usage examples",
                "create documentation for the API",
                "添加类型注解",
                "编写使用说明",
            ],
            applicable_when="User wants to add or improve code documentation, comments, or type hints",
            tools_used=["read_file", "write_file", "edit_file", "grep_search", "glob_files"],
        )

    async def execute(self, context: SkillContext) -> SkillResult:
        return SkillResult(
            skill_name=self.name,
            success=True,
            instructions=self._get_instructions(),
            suggested_tools=["read_file", "write_file", "edit_file", "grep_search", "glob_files"],
        )

    def _get_instructions(self) -> str:
        return '''
## Code Documentation Mode

You are now in code documentation mode. Follow these guidelines to create excellent documentation:

### 1. Documentation Philosophy
Good documentation should be:
- **Clear**: Easy to understand
- **Complete**: Covers all important aspects
- **Concise**: No unnecessary verbosity
- **Current**: Stays up-to-date with code changes
- **Consistent**: Follows project conventions

### 2. Docstring Standards

#### Python (Google Style)
```python
def function_name(param1: str, param2: int = 0) -> bool:
    """Short summary of the function.

    Longer description if needed. Explain the purpose, behavior,
    and any important details.

    Args:
        param1: Description of param1.
        param2: Description of param2. Default is 0.

    Returns:
        Description of return value.

    Raises:
        ValueError: When param1 is empty.
        TypeError: When param2 is not an integer.

    Examples:
        >>> function_name("test", 42)
        True
    """
```

#### JavaScript/TypeScript (JSDoc)
```javascript
/**
 * Short summary of the function.
 *
 * @param {string} param1 - Description of param1.
 * @param {number} [param2=0] - Description of param2.
 * @returns {boolean} Description of return value.
 * @throws {Error} When param1 is empty.
 *
 * @example
 * functionName("test", 42); // returns true
 */
```

### 3. Documentation Levels

#### Module/File Level
Every file should have a module docstring explaining:
- What this module/file does
- Key classes/functions it contains
- Any important usage notes

```python
"""
Module: user_authentication

This module handles user authentication and authorization.
It provides functions for login, logout, and token management.

Key Classes:
    - AuthManager: Main authentication handler
    - TokenService: JWT token management

Key Functions:
    - login(): Authenticate user credentials
    - logout(): Invalidate user session
    - verify_token(): Validate JWT tokens
"""
```

#### Class Level
```python
class UserService:
    """Service for managing user operations.
    
    This service handles CRUD operations for users and manages
    user-related business logic.
    
    Attributes:
        db: Database connection instance.
        cache: Cache manager for user data.
    
    Example:
        >>> service = UserService(db, cache)
        >>> user = service.get_user(123)
    """
```

### 4. Inline Comments

#### When to Add Comments
- **Complex logic**: Explain *why*, not *what*
- **Workarounds**: Explain why this approach was chosen
- **Algorithms**: Brief explanation of the algorithm
- **Magic numbers**: Explain the significance
- **Regex patterns**: Explain what the pattern matches

#### Comment Best Practices
```python
# Good: Explains WHY
# Retry up to 3 times because the API is occasionally flaky
for attempt in range(3):
    try:
        call_api()
        break
    except ApiError:
        continue

# Bad: Explains WHAT (obvious from code)
# Loop 3 times
for attempt in range(3):
    call_api()
```

### 5. Type Hints

#### Python Type Hints
```python
from typing import Optional, List, Dict, Union

def process_data(
    items: List[str],
    config: Optional[Dict[str, any]] = None
) -> Union[str, None]:
    """Process a list of items with optional configuration."""
    pass
```

### 6. README Structure

A good README includes:
```markdown
# Project Name

Brief description of the project.

## Features
- Feature 1
- Feature 2

## Installation
```bash
pip install package-name
```

## Quick Start
```python
from package import MyClass

obj = MyClass()
obj.do_something()
```

## API Reference
Brief overview of main classes/functions.

## Configuration
Environment variables and configuration options.

## Contributing
How to contribute to the project.

## License
Project license information.
```

### 7. Best Practices
- Keep docstrings in sync with code changes
- Use consistent style throughout the project
- Document public API thoroughly
- Add examples for complex functions
- Don't document the obvious
- Use meaningful parameter names to reduce need for docs
'''