"""Code Security Scan Skill - scans code for security vulnerabilities."""

from __future__ import annotations

from miniclaude.skills.base import BaseSkill, SkillContext, SkillMeta, SkillResult


class SecurityScanSkill(BaseSkill):
    """Scans code for security vulnerabilities and potential security issues."""

    @property
    def meta(self) -> SkillMeta:
        return SkillMeta(
            name="security_scan",
            description="Scan code for security vulnerabilities, potential exploits, and security best practices violations. "
                        "Identifies common security issues like injection, XSS, hardcoded secrets, and insecure configurations.",
            tags=[
                "security", "vulnerability", "scan", "audit", "penetration",
                "injection", "xss", "csrf", "authentication", "authorization",
                "encryption", "secret", "credential", "exploit", "malicious",
                "安全", "漏洞", "扫描", "审计", "注入", "认证", "授权", "加密",
                "密码", "秘钥", "攻击", "防护", "安全检查"
            ],
            examples=[
                "scan this code for security vulnerabilities",
                "check for security issues",
                "audit code security",
                "检查代码安全漏洞",
                "find hardcoded secrets in the code",
                "scan for SQL injection vulnerabilities",
                "check for XSS vulnerabilities",
                "review code for security best practices",
                "安全扫描这段代码",
                "查找硬编码的密码",
                "检查SQL注入漏洞",
                "审计代码安全性",
                "find potential security exploits",
                "check authentication implementation",
            ],
            applicable_when="User wants to identify security vulnerabilities or audit code security",
            tools_used=["read_file", "grep_search", "glob_files", "run_command"],
        )

    async def execute(self, context: SkillContext) -> SkillResult:
        return SkillResult(
            skill_name=self.name,
            success=True,
            instructions=self._get_instructions(),
            suggested_tools=["read_file", "grep_search", "glob_files", "run_command"],
        )

    def _get_instructions(self) -> str:
        return '''
## Code Security Scan Mode

You are now in security scanning mode. Follow this systematic approach to identify security vulnerabilities:

### 1. Security Scanning Methodology

#### Phase 1: Reconnaissance
- Understand the application type (web app, API, CLI tool, etc.)
- Identify the technology stack and frameworks
- Map the attack surface

#### Phase 2: Vulnerability Identification
Scan for common vulnerability categories:

**OWASP Top 10:**
1. Injection (SQL, NoSQL, OS, LDAP)
2. Broken Authentication
3. Sensitive Data Exposure
4. XML External Entities (XXE)
5. Broken Access Control
6. Security Misconfiguration
7. Cross-Site Scripting (XSS)
8. Insecure Deserialization
9. Using Components with Known Vulnerabilities
10. Insufficient Logging & Monitoring

### 2. Common Vulnerability Patterns

#### Hardcoded Secrets
```python
# VULNERABILITY: Hardcoded credentials
password = "super_secret_123"
api_key = "sk-1234567890abcdef"
database_url = "postgresql://user:password@localhost/db"

# SECURE: Use environment variables
import os
password = os.getenv("DB_PASSWORD")
api_key = os.getenv("API_KEY")
```

#### SQL Injection
```python
# VULNERABILITY: String concatenation in SQL
query = f"SELECT * FROM users WHERE id = {user_id}"
cursor.execute(query)

# SECURE: Parameterized queries
query = "SELECT * FROM users WHERE id = %s"
cursor.execute(query, (user_id,))
```

#### Command Injection
```python
# VULNERABILITY: Shell injection
import os
os.system(f"ping {user_input}")

# SECURE: Use subprocess with list arguments
import subprocess
subprocess.run(["ping", user_input], shell=False)
```

#### Path Traversal
```python
# VULNERABILITY: Unsanitized file path
file_path = os.path.join(base_dir, user_input)
with open(file_path) as f:
    data = f.read()

# SECURE: Validate and sanitize path
import os
safe_path = os.path.realpath(os.path.join(base_dir, user_input))
if not safe_path.startswith(os.path.realpath(base_dir)):
    raise ValueError("Invalid path")
```

#### Insecure Deserialization
```python
# VULNERABILITY: Pickle with untrusted data
import pickle
data = pickle.loads(user_input)  # Can execute arbitrary code

# SECURE: Use safe serialization
import json
data = json.loads(user_input)
```

### 3. Security Checklist

#### Authentication & Authorization
- [ ] Passwords are hashed (bcrypt, argon2)
- [ ] No hardcoded credentials
- [ ] Session management is secure
- [ ] JWT tokens are properly validated
- [ ] Role-based access control is implemented
- [ ] Password policies are enforced

#### Input Validation
- [ ] All user input is validated
- [ ] Input length limits are enforced
- [ ] Special characters are sanitized
- [ ] File uploads are validated
- [ ] Email addresses are validated

#### Data Protection
- [ ] Sensitive data is encrypted at rest
- [ ] Sensitive data is encrypted in transit (TLS)
- [ ] No sensitive data in logs
- [ ] PII is handled according to regulations
- [ ] Database connections use SSL

#### Error Handling
- [ ] Error messages don't leak sensitive info
- [ ] Stack traces are not exposed to users
- [ ] Logging doesn't include sensitive data
- [ ] Custom error pages are configured

### 4. Scanning Commands

```bash
# Python security tools
bandit -r .                    # Security linter
safety check                   # Check dependencies for vulnerabilities
pip-audit                      # Audit Python packages

# JavaScript security tools
npm audit                      # Check npm packages
yarn audit                     # Check yarn packages
eslint --plugin security       # Security linting

# General tools
trivy fs .                     # Filesystem vulnerability scanner
grype dir .                    # Vulnerability scanner
semgrep --config auto          # Static analysis
```

### 5. Output Format

Present findings as:

```
## Security Scan Report

### Summary
- **Critical**: [count] issues
- **High**: [count] issues
- **Medium**: [count] issues
- **Low**: [count] issues

### Critical Issues

#### 1. [Vulnerability Type]
**Location**: `file.py:line_number`
**Description**: [What the vulnerability is]
**Risk**: [Potential impact]
**Code**:
```python
[vulnerable code]
```
**Fix**:
```python
[secure code]
```

### Recommendations
1. [Priority 1 fix]
2. [Priority 2 fix]
3. [Priority 3 fix]

### Security Score
[Overall security assessment]
```

### 6. Best Practices
- Never trust user input
- Principle of least privilege
- Defense in depth
- Keep dependencies updated
- Regular security audits
- Security logging and monitoring
'''