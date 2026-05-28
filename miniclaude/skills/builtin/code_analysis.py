"""Code Analysis Skill - analyzes code structure, complexity, and quality."""

from __future__ import annotations

from miniclaude.skills.base import BaseSkill, SkillContext, SkillMeta, SkillResult


class CodeAnalysisSkill(BaseSkill):
    """Analyzes code for structure, complexity, quality, and potential issues."""

    @property
    def meta(self) -> SkillMeta:
        return SkillMeta(
            name="code_analysis",
            description="Analyze code structure, complexity, quality metrics, and identify potential issues. "
                        "Provides insights on code maintainability, readability, and potential bugs.",
            tags=[
                "analyze", "analysis", "complexity", "quality", "metrics",
                "inspect", "examine", "review", "audit", "assess",
                "分析", "复杂度", "质量", "检查", "评估", "审查", "代码审查",
                "structure", "结构", "readability", "可读性", "maintainability", "可维护性"
            ],
            examples=[
                "analyze this code for complexity",
                "check code quality of this module",
                "review the code structure",
                "分析这段代码的复杂度",
                "inspect code for potential issues",
                "assess the maintainability of this code",
                "audit this codebase for quality",
                "examine the code for bad practices",
                "检查代码质量",
                "评估代码的可读性",
                "analyze function complexity",
                "code metrics for this file",
                "分析代码结构",
                "查看代码复杂度指标",
            ],
            applicable_when="User wants to understand code quality, complexity metrics, or identify potential issues",
            tools_used=["read_file", "grep_search", "glob_files", "run_command"],
        )

    async def execute(self, context: SkillContext) -> SkillResult:
        return SkillResult(
            skill_name=self.name,
            success=True,
            instructions="""
## Code Analysis Mode

You are now in code analysis mode. Follow this systematic approach to analyze code quality:

### 1. Initial Assessment
Before diving into details, get an overview:
- Read the entire file/module to understand its purpose
- Identify the programming language and framework
- Note the overall structure and organization

### 2. Code Structure Analysis

#### Module/File Level
- **Organization**: Is the code well-organized with clear sections?
- **Imports**: Are imports clean, organized, and minimal?
- **Constants/Config**: Are magic numbers extracted to constants?
- **Module Size**: Is the file too large? Should it be split?

#### Class Level
- **Single Responsibility**: Does each class have one clear purpose?
- **Cohesion**: Are class methods related to the class's responsibility?
- **Coupling**: How tightly coupled is this class to others?
- **Inheritance**: Is inheritance used appropriately (favor composition)?

#### Function/Method Level
- **Size**: Is the function too long (>20-30 lines)?
- **Parameters**: Too many parameters? Use objects/kwargs for many params.
- **Single Purpose**: Does each function do one thing well?
- **Naming**: Are names descriptive and follow conventions?

### 3. Complexity Metrics

#### Cyclomatic Complexity
Evaluate decision points:
```
Complexity = 1 + (number of decision points)

Decision points:
- if/elif/else
- for/while loops
- try/except blocks
- Boolean operators (and, or)
- Ternary operators
```

**Complexity Rating:**
- 1-10: Simple, easy to test
- 11-20: Moderate complexity
- 21-50: Complex, consider refactoring
- 50+: Very complex, needs refactoring

#### Cognitive Complexity
How hard is the code to understand?
- Nesting depth (deep nesting = high complexity)
- Flow breaks (continue, break, return in middle)
- Boolean logic complexity

### 4. Code Quality Checklist

#### Naming Conventions
- [ ] Variables: descriptive, lowercase_with_underscores (Python) or camelCase (JS)
- [ ] Functions: verb + noun (e.g., get_user, calculate_total)
- [ ] Classes: PascalCase, noun phrases
- [ ] Constants: UPPER_SNAKE_CASE
- [ ] Avoid single letter names (except loop counters)

#### Code Smells to Detect
- **Long Methods**: Functions doing too many things
- **Large Classes**: God objects with too many responsibilities
- **Long Parameter Lists**: Too many function arguments
- **Duplicated Code**: Copy-paste patterns
- **Dead Code**: Unused variables, imports, functions
- **Magic Numbers**: Hard-coded values without explanation
- **Deep Nesting**: More than 3-4 levels of indentation
- **Complex Conditionals**: Hard-to-understand if statements

#### Error Handling
- [ ] Are exceptions caught specifically (not bare except)?
- [ ] Are errors handled appropriately (not silently swallowed)?
- [ ] Are resources cleaned up (context managers, finally blocks)?
- [ ] Are error messages helpful for debugging?

### 5. Security Quick Scan
Look for common security issues:
- Hardcoded credentials or secrets
- SQL injection vulnerabilities (string concatenation in queries)
- Command injection (os.system, subprocess with shell=True)
- Path traversal vulnerabilities
- Insecure deserialization (pickle.loads on untrusted data)
- Missing input validation

### 6. Performance Indicators
- N+1 query patterns
- Unnecessary loops or iterations
- Missing caching opportunities
- Inefficient data structures
- Blocking I/O in async code

### 7. Documentation & Comments
- [ ] Module docstring explaining purpose
- [ ] Class docstrings
- [ ] Function docstrings with parameters and return types
- [ ] Complex logic has explanatory comments
- [ ] No outdated or misleading comments

### 8. Output Format

Present the analysis as:

```
## Code Analysis Report

### Overview
- **File**: [filename]
- **Language**: [language]
- **Lines**: [line count]
- **Purpose**: [brief description]

### Structure Score: [A/B/C/D/F]
[Brief assessment of code structure]

### Complexity Analysis
| Function | Complexity | Rating |
|----------|------------|--------|
| func_name | 15 | Moderate |

### Quality Issues

#### 🔴 Critical Issues
- [Issue description and location]

#### 🟡 Warnings
- [Issue description and location]

#### 🔵 Suggestions
- [Improvement suggestions]

### Metrics Summary
- **Average Complexity**: [number]
- **Max Nesting Depth**: [number]
- **Duplicate Code**: [percentage or None]
- **Test Coverage**: [if available]

### Recommendations
1. [Top priority improvement]
2. [Second priority]
3. [Third priority]
```

### 9. Analysis Tools
When available, use static analysis tools:
```bash
# Python
pylint <file>           # General linting
flake8 <file>           # Style checking
mypy <file>             # Type checking
radon cc <file>         # Cyclomatic complexity
radon mi <file>         # Maintainability index
vulture <file>          # Dead code detection

# JavaScript/TypeScript
eslint <file>           # Linting
tsc --noEmit            # Type checking
```

### 10. Best Practices
- Be specific about line numbers and issues
- Provide examples of how to fix issues
- Prioritize issues by severity
- Acknowledge what's done well (positive feedback)
- Focus on actionable improvements
""",
            suggested_tools=["read_file", "grep_search", "glob_files", "run_command"],
        )