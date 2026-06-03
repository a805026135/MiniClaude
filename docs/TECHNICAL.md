# MiniClaude 技术文档

> 详细说明项目工作流程与五大关键技术的实现原理。

---

## 目录

1. [整体工作流程](#一整体工作流程)
2. [关键技术一：Skill 分层路由](#二关键技术一skill-分层路由)
3. [关键技术二：自进化记忆沉淀](#三关键技术二自进化记忆沉淀)
4. [关键技术三：分层上下文压缩](#四关键技术三分层上下文压缩)
5. [关键技术四：中心化多 Agent 协作](#五关键技术四中心化多-agent-协作)
6. [关键技术五：权限与安全审查](#六关键技术五权限与安全审查)

---

## 一、整体工作流程

### 1.1 系统启动流程

```
用户启动程序
     ↓
┌──────────────────────────────────────────────────────┐
│ 1. 配置加载 (config.py)                              │
│    从 .env 读取 API Key、模型名、上下文限制等         │
└──────────────────────────────────────────────────────┘
     ↓
┌──────────────────────────────────────────────────────┐
│ 2. 子系统初始化 (app.py → initialize())              │
│    按依赖顺序依次构建 11 个子系统：                   │
│    LLM Client → Tool Registry → Memory Store         │
│    → Skill Catalog → Context Manager                 │
│    → Orchestrator → Permission Manager               │
│    → Tool Executor → Context → Query Loop → REPL     │
└──────────────────────────────────────────────────────┘
     ↓
┌──────────────────────────────────────────────────────┐
│ 3. 启动 UI                                           │
│    CLI模式: Rich REPL 交互循环                       │
│    GUI模式: Tkinter 桌面客户端                       │
└──────────────────────────────────────────────────────┘
```

### 1.2 单次查询执行流程（Query Loop）

这是 MiniClaude 的核心工作循环，实现了 **User → LLM → Tool Call → Result → Loop** 的任务执行闭环。

```
用户输入: "读取 hello.py 并解释"
     ↓
┌─────────────────────────────────────────────────────────────────────┐
│ Step 1: 预处理                                                       │
│   ① 检索相关记忆 (MemoryRetriever.retrieve)                          │
│   ② 检查上下文预算 (TokenBudget.needs_compression)                   │
│   ③ Skill 路由 (SkillRouter.route) → 匹配 explain Skill             │
│   ④ 构建 system prompt = 角色定义 + 记忆上下文 + Skill 指南          │
└─────────────────────────────────────────────────────────────────────┘
     ↓
┌─────────────────────────────────────────────────────────────────────┐
│ Step 2: Query Loop 迭代 (core/loop.py → QueryLoop.run)              │
│                                                                      │
│   ┌──────────────────────────────────────────────────────────────┐   │
│   │ Iteration 1:                                                  │   │
│   │   调用 LLM (messages + system + tools)                       │   │
│   │   ← LLM 返回: tool_call: read_file(path="hello.py")         │   │
│   │   执行工具: 读取文件内容                                      │   │
│   │   工具结果 → 加入 messages                                    │   │
│   ├──────────────────────────────────────────────────────────────┤   │
│   │ Iteration 2:                                                  │   │
│   │   调用 LLM (含工具结果的 messages)                           │   │
│   │   ← LLM 返回: 纯文本解释 (无 tool_call)                      │   │
│   │   → 循环结束                                                  │   │
│   └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
     ↓
┌─────────────────────────────────────────────────────────────────────┐
│ Step 3: 后处理                                                       │
│   ① 返回最终文本响应给用户                                           │
│   ② 异步触发记忆提取 (MemoryExtractor.extract)                       │
│   ③ 保存会话到磁盘 (ConversationContext.save_session)                │
└─────────────────────────────────────────────────────────────────────┘
```

**核心代码路径**：`app.py` → `core/loop.py::QueryLoop.run()` → `llm/client.py::ClaudeClient.chat()` → `core/tool_executor.py::ToolExecutor.execute_all()`

### 1.3 消息格式（OpenAI 兼容）

```python
# 系统消息（带 cache_control 标记）
{"role": "system", "content": "你是 MiniClaude..."}

# 用户消息
{"role": "user", "content": "读取 hello.py 并解释"}

# 助手消息（含工具调用）
{"role": "assistant", "content": null,
 "tool_calls": [{"id": "call_1", "type": "function",
                  "function": {"name": "read_file", "arguments": "{\"path\": \"hello.py\"}"}}]}

# 工具结果消息
{"role": "tool", "tool_call_id": "call_1", "content": "     1\tprint(\"Hello, World!\")"}
```

---

## 二、关键技术一：Skill 分层路由

### 2.1 要解决的问题

当 Skill 数量增长时（本项目已实现 9 个内置 Skill），将所有 Skill 的使用指南全部注入 system prompt 会带来三个问题：
- **检索噪声**：无关 Skill 的指南干扰 LLM 推理
- **功能重叠**：多个 Skill 可能适用于同一任务，需要择优
- **Token 成本**：每个 Skill 指南约 200-500 tokens，全量注入浪费严重

### 2.2 三层架构设计

```
┌─────────────────────────────────────────────────────────────┐
│ Skill Catalog (skills/catalog.py)                           │
│   - 全局索引，管理所有 Skill 的元信息                       │
│   - 支持按名称、标签、关键词检索                            │
│   - 自动从 builtin/ 包发现并注册 Skill                      │
├─────────────────────────────────────────────────────────────┤
│ High-level Skills (skills/builtin/*.py)                     │
│   9 个内置 Skill，每个包含：                                │
│   - SkillMeta: name, description, tags, examples,           │
│     prerequisites, applicable_when, tools_used              │
│   - execute(): 返回增强指令，指导 LLM 使用特定工具组合      │
│   - can_handle(): 基于关键词匹配的初步评分                  │
├─────────────────────────────────────────────────────────────┤
│ Atomic Tools (tools/*.py)                                   │
│   9 个原子工具：read_file, write_file, edit_file,           │
│   glob_files, grep_search, run_command,                     │
│   memory_save, memory_search, spawn_agent                   │
│   - 始终注入 tool schema，无需路由                          │
└─────────────────────────────────────────────────────────────┘
```

### 2.3 二阶段路由实现

**实现文件**：`miniclaude/skills/router.py` — `SkillRouter` 类

#### Stage 1：粗召回 (Coarse Recall)

```python
def _recall(self, user_input: str) -> list[BaseSkill]:
    # 1. 提取关键词（中英文混合，过滤停用词）
    keywords = self._extract_keywords(user_input)
    # → "读取 hello.py 并解释" → ["读取", "hello.py", "解释"]

    # 2. 基于关键词在 Catalog 中搜索
    candidates = self.catalog.search_by_keywords(keywords)

    # 3. 遍历所有 Skill，补充 can_handle 评分 > 0.1 的
    for skill in self.catalog.get_all():
        if skill not in candidates:
            score = skill.can_handle(user_input)
            if score > 0.1:
                candidates.append(skill)

    # 4. 去重 + 截取 top-10
    return unique[:self.recall_top_k]  # 默认 10
```

**关键词提取**（`_extract_keywords`）：
- 使用正则 `r'[\w一-鿿]+'` 匹配英文单词和中文字符
- 过滤 130+ 个中英文停用词（如 "的", "了", "the", "is"）
- 过滤长度 ≤ 1 的 token

**粗召回特点**：O(N) 时间复杂度，毫秒级响应，宁可多召回不漏召回。

#### Stage 2：精排 (Fine Ranking)

```python
def _rank(self, user_input: str, candidates: list[BaseSkill]) -> list[BaseSkill]:
    for skill in candidates:
        # 综合评分 = 基础分 + 标签加分 + 示例加分 + 意图加分
        total_score = (
            base_score      # skill.can_handle() 基于词重叠的评分
            + tag_bonus     # 标签在查询中出现 → +0.2/标签
            + example_bonus # 示例与查询有 ≥2 词重叠 → +0.3
            + intent_bonus  # 意图关键词命中 → +0.3
        )

    # 按分数降序排列，返回 top-3 且分数 > 0.1 的
    return scored[:self.rank_top_k]
```

**意图关键词映射**（9 种意图，中英文双语）：

| Skill 意图 | 英文关键词 | 中文关键词 |
|-----------|-----------|-----------|
| `review` | review, check | 审查, 检查 |
| `refactor` | refactor, rewrite | 重构, 重写 |
| `debug` | debug, fix, bug, error | 调试, 错误 |
| `test` | test, spec | 测试, 单元测试 |
| `explain` | explain, what does, how does | 解释, 说明 |
| `code_gen` | generate, create, write, implement | 生成, 创建, 编写 |
| `code_analysis` | analyze, complexity, quality, metrics | 分析, 复杂度, 质量 |
| `code_document` | document, docstring, readme | 文档, 注释 |
| `security_scan` | security, vulnerability, xss, csrf | 安全, 漏洞, 扫描 |

**评分示例**：

用户输入 `"帮我审查这段代码"` → 关键词 `["帮", "审查", "这段", "代码"]`

| Skill | base | tag | example | intent | total |
|-------|------|-----|---------|--------|-------|
| code_review | 0.2 | +0.2 (审查) | +0.3 | +0.3 (审查) | **1.0** |
| security_scan | 0.1 | 0 | 0 | 0 | 0.1 |
| explain | 0.1 | 0 | 0 | 0 | 0.1 |

→ 路由结果：注入 `code_review` Skill 的使用指南到 system prompt

---

## 三、关键技术二：自进化记忆沉淀

### 3.1 要解决的问题

- **跨会话遗忘**：每次新会话都从零开始，无法利用之前的编程经验
- **重复推理**：相同的项目结构偏好、技术选型决策每次都要重新推导
- **用户偏好丢失**：用户喜欢什么样的代码风格、注释方式等无法积累

### 3.2 闭环设计

```
                    ┌────────────────────┐
                    │    跨会话复用       │
                    │  下次对话启动时     │
                    │  检索相关记忆注入   │
                    └─────────┬──────────┘
                              │
┌─────────────────────────────┼─────────────────────────────┐
│                             │                              │
│  执行完成 ──→ 反思 ──→ 提炼 ──→ 去重 ──→ 分类存储        │
│              (LLM)    (LLM)   (比对)   (SQLite)           │
│                                                           │
└───────────────────────────────────────────────────────────┘
```

### 3.3 各步骤实现细节

**实现文件**：`miniclaude/memory/extractor.py` — `MemoryExtractor` 类

#### Step 1：反思 (Reflect)

```python
async def _reflect(self, query, messages, response_text):
    # 取最近 10 条消息，每条截断 300 字符
    conversation_summary = "\n".join(
        f"{msg['role']}: {msg['content'][:300]}"
        for msg in messages[-10:]
    )

    # 调用 LLM 进行反思分析
    prompt = REFLECTION_PROMPT.format(
        query=query[:500],
        conversation_summary=conversation_summary[:3000],
    )
    response = await self.llm.chat(messages=[...], max_tokens=1000)

    # 解析为结构化结果
    return ReflectionResult(
        key_decisions=["使用 pytest 框架", "选择策略模式重构"],
        lessons_learned=["该项目已有 conftest.py 配置"],
        user_preferences=["偏好中文注释"],
        reusable_patterns=["项目的测试在 tests/ 目录下"],
        notable_events=["首次分析该代码库结构"],
    )
```

**反思 Prompt 设计要点**：
- 要求 LLM 提取 5 类信息：关键决策、经验教训、用户偏好、可复用模式、重要事件
- 限制输出为 JSON 格式，便于后续解析
- 只提取真正有价值的非显而易见信息

#### Step 2：提炼 (Distill)

```python
async def _distill(self, reflection, session_id):
    # 将反思结果转化为独立的、自含上下文的记忆条目
    prompt = DISTILL_PROMPT.format(reflection_json=reflection.model_dump_json())
    response = await self.llm.chat(messages=[...], max_tokens=1500)

    # 每条记忆包含：类型、内容、摘要、标签
    entries = [
        MemoryEntry(
            type=MemoryType.PROCEDURAL,
            content="该项目使用 pytest 进行测试，测试文件在 tests/ 目录",
            summary="pytest 测试结构",
            tags=["python", "testing", "project-structure"],
        ),
        MemoryEntry(
            type=MemoryType.PROFILE,
            content="用户偏好中文注释和简洁的代码风格",
            summary="代码风格偏好",
            tags=["preference", "style"],
        ),
    ]
```

**提炼规则**：
- 每条记忆 < 200 字符，自含上下文（脱离对话仍可理解）
- 自动判断类型：`procedural`（怎么做）、`episodic`（发生了什么）、`profile`（用户偏好）
- 使用具体、可搜索的标签

#### Step 3：去重 (Deduplicate)

```python
def _deduplicate(self, entries):
    new_entries = []
    for entry in entries:
        # 在已有记忆中搜索相似条目
        results = self.store.search(
            entry.content[:100],  # 用前 100 字符搜索
            memory_type=entry.type,
            limit=3,
        )

        # 相似度 > 0.8 则视为重复
        is_duplicate = any(r.score > 0.8 for r in results)

        if is_duplicate:
            # 不创建新条目，而是更新已有条目的访问时间
            existing.touch()
            self.store.save(existing)
        else:
            new_entries.append(entry)

    return new_entries
```

#### Step 4：分类存储 (Store)

**SQLite Schema**：
```sql
CREATE TABLE memories (
    id TEXT PRIMARY KEY,           -- UUID 前 12 位
    type TEXT NOT NULL,            -- procedural / episodic / profile
    content TEXT NOT NULL,         -- 记忆内容（< 200 字符）
    summary TEXT DEFAULT '',       -- 一行摘要
    tags TEXT DEFAULT '[]',        -- JSON 数组
    source_session TEXT DEFAULT '',-- 来源会话 ID
    created_at TEXT NOT NULL,      -- ISO 时间戳
    accessed_at TEXT NOT NULL,     -- 最近访问时间
    access_count INTEGER DEFAULT 0,-- 访问计数
    relevance_score REAL DEFAULT 1.0, -- 相关性分数（衰减用）
    metadata TEXT DEFAULT '{}'     -- JSON 扩展字段
);
-- 索引：type, created_at, relevance_score DESC
```

#### Step 5：按需复用 (Retrieve)

```python
class MemoryRetriever:
    def retrieve(self, query, limit=10):
        results = {}

        # 1. 基于查询关键词搜索
        for r in self.store.search(query, limit=limit):
            results[r.entry.id] = r.entry

        # 2. 始终注入用户画像记忆
        for m in self.store.get_by_type(MemoryType.PROFILE, limit=3):
            results[m.id] = m

        # 3. 注入最近访问的程序性记忆
        for m in self.store.get_by_type(MemoryType.PROCEDURAL, limit=3):
            if m.access_count > 0:
                results[m.id] = m

        return sorted(results.values(), key=lambda e: e.relevance_score, reverse=True)[:limit]

    def format_for_context(self, memories):
        # 格式化为 system prompt 注入段
        # "## Relevant Memories\n
        #  ### Procedural Knowledge\n
        #  - 该项目使用 pytest...\n
        #  ### User Profile\n
        #  - 用户偏好中文注释..."
```

### 3.4 记忆生命周期管理

```python
class MemoryCompressor:
    def cleanup(self):
        # 1. 衰减相关性分数（每次 ×0.95）
        self.store.decay_relevance(0.95)

        # 2. 清理低相关性 + 低访问的记忆
        for entry in all_memories:
            if entry.relevance_score < 0.3 and entry.access_count < 2:
                self.store.delete(entry.id)
```

---

## 四、关键技术三：分层上下文压缩

### 4.1 要解决的问题

LLM 的上下文窗口有限（MiMo-v2.5-pro 为 131K tokens），在长对话中会遇到：
- 工具返回大量文件内容，迅速占满上下文
- 历史消息累积，Token 预算耗尽
- Prompt Cache 命中率下降（前缀变化导致缓存失效）

### 4.2 四层压缩策略

```
Token 使用率
  0%                                                                100%
  ├──────────────┤──────────────┤──────────────┤───────────────────┤
  │  正常运行     │ Level 1:     │ Level 2:     │ Level 3:          │
  │              │ 摘要预览     │ 占位替换     │ 超限兜底          │
  │              │ 大结果截断   │ 外置到磁盘   │ 丢弃旧消息        │
  ├──────────────┤──────────────┤──────────────┤───────────────────┤
  0%            85%            92%            98%               100%
                ↑ 告警         ↑ 压缩         ↑ 临界
```

### 4.3 各层实现细节

#### Token 预算管理 (`context/budget.py`)

```python
@dataclass
class TokenBudget:
    max_tokens: int = 131_072      # 模型上下文窗口
    reserved_output: int = 16_000  # 预留给模型输出
    warning_threshold: float = 0.85

    # 可用预算 = 总量 - 输出预留 - 系统提示 - 工具Schema
    @property
    def available_for_history(self) -> int:
        return self.max_tokens - self.reserved_output - self.system_tokens - self.tool_schema_tokens

    def needs_compression(self) -> bool:
        return self.usage_ratio > 0.85  # 使用率超 85% 触发压缩
```

#### Level 1：大结果外置化 (`context/externalizer.py`)

当单个工具结果超过阈值（默认 2000 字符）时，自动外置到磁盘：

```python
class Externalizer:
    THRESHOLD = 2000

    def process(self, result: ToolResult) -> ToolResult:
        if len(result.content) <= self.THRESHOLD:
            return result  # 小结果直接返回

        # 1. 生成内容哈希作为文件名
        content_hash = hashlib.md5(result.content.encode()).hexdigest()[:12]
        save_path = self.config.externalized_dir / f"{result.tool_name}_{content_hash}.md"

        # 2. 保存全文到磁盘
        save_path.write_text(result.content, encoding="utf-8")

        # 3. 生成摘要（前 10 行，最多 500 字符）
        summary = self._generate_summary(result.content)

        # 4. 替换为占位符
        result.content = (
            f"[结果已外置: {save_path.name}]\n"
            f"[内容: {len(result.content)} 字符, {lines} 行]\n\n"
            f"摘要预览:\n{summary}\n\n"
            f"[使用 read_file 工具读取完整内容]"
        )
        result.truncated = True
        result.external_path = str(save_path)
        return result
```

**效果**：一个 5000 字符的 `read_file` 结果被替换为约 200 字符的占位符，节省 96% Token。

#### Level 2：历史消息压缩 (`context/compressor.py`)

当整体 Token 使用率超过 85% 时，按三级策略压缩：

```python
class ContextCompressor:
    MAX_TOOL_RESULT_TOKENS = 2000  # 单个工具结果上限
    SUMMARY_TOKENS = 200           # 摘要目标长度

    def compress_messages(self, messages, target_tokens, current_tokens):
        # 策略 1: 截断过长的工具结果
        messages, reduced = self._truncate_tool_results(messages, remaining)
        # → 将 5000 token 的工具结果截断为 2000 token

        # 策略 2: 摘要化旧的助手消息
        messages, reduced = self._summarize_old_messages(messages, remaining)
        # → 将早期的长回复替换为 "[已摘要] 第一句话..."

        # 策略 3: 丢弃最旧的消息（最后手段）
        messages = self._drop_old_messages(messages, target_tokens)
        # → 保留首条 + 最后 6 条，中间全部丢弃
```

**压缩顺序**（优先级从高到低）：
1. 工具结果截断（影响最小，工具结果可以重新获取）
2. 旧消息摘要（保留语义，丢失细节）
3. 丢弃旧消息（最后手段，保留最近上下文）

#### Level 3：Prompt Cache 优化

```python
# system prompt 使用 cache_control 标记
kwargs["system"] = [{
    "type": "text",
    "text": system_prompt,
    "cache_control": {"type": "ephemeral"},  # 启用 Prompt Cache
}]

# 工具 schema 保持稳定，不随对话变化
# → 每次请求的前缀（system + tools）保持一致
# → 最大化缓存命中，减少重复 Token 计费
```

---

## 五、关键技术四：中心化多 Agent 协作

### 5.1 要解决的问题

复杂任务（如"为这个模块写测试并审查安全性"）需要多种专业能力，单 Agent 难以在一次推理中兼顾。

### 5.2 架构设计

```
┌───────────────────────────────────────────────────────────────┐
│                    主 Agent (Orchestrator)                     │
│                                                                │
│  职责:                                                         │
│  - 统一规划：将复杂任务分解为子任务                            │
│  - 审批质量：检查子 Agent 结果是否满足要求                     │
│  - 结果整合：汇总多个子任务的结果，补充上下文                  │
│  - 控制权保持：始终由主 Agent 决定下一步操作                   │
│                                                                │
│  调用方式:                                                     │
│  spawn_agent(task="生成测试", agent_type="test_generator")    │
│                                                                │
├───────────────────────────────────────────────────────────────┤
│               子 Agent 池 (4 种专业角色)                       │
│                                                                │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐          │
│  │ code_analyst  │ │test_generator│ │refactor_expert│          │
│  │ 代码分析      │ │ 测试生成     │ │ 重构专家      │          │
│  │ Tools: 3个    │ │ Tools: 4个   │ │ Tools: 5个    │          │
│  └──────────────┘ └──────────────┘ └──────────────┘          │
│  ┌──────────────┐                                             │
│  │debug_specialist│                                           │
│  │ 调试专家      │                                            │
│  │ Tools: 4个    │                                            │
│  └──────────────┘                                             │
└───────────────────────────────────────────────────────────────┘
```

### 5.3 实现细节

**实现文件**：`miniclaude/agents/orchestrator.py` + `miniclaude/agents/sub_agent.py`

#### Agent Tool — 将子 Agent 暴露为工具

```python
class AgentTool(BaseTool):
    name = "spawn_agent"
    parameters = {
        "task": "子任务描述",
        "agent_type": "code_analyst | test_generator | refactor_expert | debug_specialist",
        "context": "额外上下文（可选）",
    }

    async def execute(self, **kwargs):
        # 1. 创建子 Agent 实例
        agent = SubAgent(agent_type=agent_type, config=..., llm_client=..., tool_registry=...)

        # 2. 运行子 Agent（独立的 mini loop）
        result = await agent.run(task, context)

        # 3. 返回结果给主 Agent
        return result.to_tool_result()
```

#### 子 Agent 隔离执行

```python
class SubAgent:
    SUB_AGENT_MAX_ITERATIONS = 20  # 子 Agent 最多 20 轮迭代

    async def run(self, task, context):
        # 1. 构建任务消息
        self._messages = [{"role": "user", "content": task + context}]

        # 2. 获取受限工具集（白名单过滤）
        tool_schemas = self._get_filtered_tools()
        # → code_analyst 只能用: read_file, glob_files, grep_search

        # 3. 独立的 mini loop
        for iteration in range(SUB_AGENT_MAX_ITERATIONS):
            response = await self.llm_client.chat(
                messages=self._messages,
                system=self.system_prompt,  # 子 Agent 有自己的 system prompt
                tools=tool_schemas,
            )

            if not response.has_tool_use:
                result.output = response.text  # 完成
                break

            # 执行工具并收集结果
            results = await executor.execute_all(response.tool_calls)
            # ... 将结果加入 self._messages，继续循环

        return result
```

#### 安全约束

| 约束 | 实现方式 |
|------|---------|
| **不移交控制权** | 子 Agent 以 Tool Call 方式调用，结果返回主 Agent 后主 Agent 继续决策 |
| **工具权限约束** | 每种子 Agent 有白名单，如 `code_analyst` 不能写文件 |
| **路径边界** | 子 Agent 继承主 Agent 的 `project_dir` 配置 |
| **结果压缩** | 子 Agent 结果经过 Externalizer 处理后再返回 |
| **迭代上限** | 最多 20 轮，防止无限循环 |

### 5.4 Agent Team — 并行执行

```python
class AgentTeam:
    async def execute_parallel(self, tasks: list[TeamTask]):
        # 多个子任务并发执行
        coros = [self.orchestrator.spawn_agent(t.agent_type, t.task) for t in tasks]
        results = await asyncio.gather(*coros, return_exceptions=True)

    async def execute_sequential(self, tasks: list[TeamTask]):
        # 有依赖关系的任务串行执行
        # 前一个任务的结果作为下一个任务的上下文
        for task in self._topological_sort(tasks):
            result = await self.orchestrator.spawn_agent(...)
```

---

## 六、关键技术五：权限与安全审查

### 6.1 要解决的问题

AI Agent 在真实开发环境中具有文件读写和命令执行能力，面临以下风险：
- **误操作**：LLM 可能执行破坏性命令（`rm -rf`、`DROP TABLE`）
- **越权访问**：读取 `.env`、`.ssh/id_rsa` 等敏感文件
- **Prompt 注入**：恶意文件内容可能包含注入指令，操纵 Agent 行为

### 6.2 五层审查链路

```
工具调用请求
     ↓
┌─────────────────────────────────────────────────────────┐
│ Layer 1: 规则过滤 (security/rules.py)                   │
│   5 个规则引擎并行检查：                                │
│   ┌─────────────────────────────────────────────────┐   │
│   │ PathBoundaryRule    │ 阻止访问系统路径           │   │
│   │ DangerousCommandRule│ 阻止危险 Shell 命令        │   │
│   │ SensitiveFileRule   │ 阻止写入敏感文件           │   │
│   │ BinaryFileRule      │ 阻止读写二进制文件         │   │
│   │ SizeLimitRule       │ 阻止过大的文件写入 (1MB)   │   │
│   └─────────────────────────────────────────────────┘   │
│   严重程度: critical → 阻断 / warning → 警告 / pass     │
└─────────────────────────────────────────────────────────┘
     ↓ 通过
┌─────────────────────────────────────────────────────────┐
│ Layer 2: Prompt 注入防御 (security/prompt_guard.py)     │
│   27 个注入模式正则匹配 + 6 个可疑模式检测              │
│   覆盖: 英文注入、中文注入、Prompt 泄露、编码混淆       │
│   风险等级: critical/high → 阻断 / medium → 警告        │
└─────────────────────────────────────────────────────────┘
     ↓ 通过
┌─────────────────────────────────────────────────────────┐
│ Layer 3: AI 风险分类 (security/risk_classifier.py)      │
│   调用 LLM 评估操作风险等级（可选，增加一次 LLM 调用）  │
│   输出: LOW / MEDIUM / HIGH / CRITICAL                  │
│   CRITICAL → 阻断                                       │
└─────────────────────────────────────────────────────────┘
     ↓ 通过
┌─────────────────────────────────────────────────────────┐
│ Layer 4: 确认检查 (permission.py)                       │
│   以下操作需人工确认：                                  │
│   - run_command（所有 Shell 命令）                       │
│   - HIGH/CRITICAL 风险操作                              │
│   - 写入项目目录外的文件                                │
│   已审批操作缓存，避免重复确认                           │
└─────────────────────────────────────────────────────────┘
     ↓ 用户确认
┌─────────────────────────────────────────────────────────┐
│ Layer 5: 审计日志 (security/auditor.py)                 │
│   记录所有安全事件到 data/security/audit_YYYYMMDD.jsonl │
│   包括: 工具调用、注入尝试、用户决策、策略违规           │
└─────────────────────────────────────────────────────────┘
     ↓
工具执行
```

### 6.3 各层实现细节

#### Layer 1：规则过滤 (`security/rules.py`)

**PathBoundaryRule**：
```python
BLOCKED_PATHS = [
    "/etc/", "/proc/", "/sys/", "/dev/",    # Linux 系统路径
    "~/.ssh/", "~/.aws/", "~/.gnupg/",      # 密钥目录
    "C:\\Windows\\", "C:\\Users\\All Users", # Windows 系统路径
]
# → 命中任一 → severity="critical" → 阻断
# → 路径在项目目录外 → severity="warning" → 警告
```

**DangerousCommandRule**：
```python
BLOCKED_PATTERNS = [        # 10 个，severity="critical"
    "rm -rf /", "mkfs", "dd if=", ":(){", "fork bomb",
    "shutdown", "reboot", "format ", "> /dev/", "chmod 777", "kill -9 1"
]
DANGEROUS_PATTERNS = [      # 10 个，severity="warning"
    "rm -r", "DROP TABLE", "DROP DATABASE", "DELETE FROM", "TRUNCATE",
    "git push --force", "git reset --hard", "git clean -f",
    "pip install", "npm install"
]
```

**SensitiveFileRule**：
```python
SENSITIVE_PATTERNS = [
    r'\.env$', r'\.env\.', r'credentials', r'secret',
    r'\.pem$', r'\.key$', r'private_key', r'id_rsa',
]
# 读取 → warning（允许但记录）
# 写入 → error（阻断）
```

#### Layer 2：Prompt 注入防御 (`security/prompt_guard.py`)

```python
class PromptGuard:
    # 27 个注入模式，覆盖中英文
    INJECTION_PATTERNS = [
        # 英文
        (r'ignore\s+(previous|all|above)\s+(instructions|prompts|rules)', "ignore_instructions"),
        (r'you\s+are\s+now\s+(a|an|the)', "role_override"),
        # 中文
        (r'忽略(之前|上面|以上)(的)?(所有|全部)?(的)?(指令|提示|规则|要求)', "ignore_cn"),
        (r'(系统|提示词|system\s*prompt)', "system_probe_cn"),
        # Prompt 泄露
        (r'(show|reveal|print)\s+(your|the)\s+(system|original)\s+(prompt|instructions)', "prompt_leak"),
        # 编码混淆
        (r'base64\s+(decode|encode)', "encoding_trick"),
    ]

    # 同时扫描工具返回内容（防止文件内容注入）
    def scan_tool_result(self, content: str) -> ScanResult:
        return self._scan(content)  # 攻击者可能在文件中嵌入注入指令
```

#### Layer 4：确认机制

```python
async def check(self, tool_name, params, user_input):
    # ... Layer 1-3 通过后 ...

    if self._needs_confirmation(tool_name, params, risk_level):
        # 检查缓存（之前已审批的操作）
        cache_key = f"{tool_name}:{str(params)[:200]}"
        if cache_key in self._allowed_cache:
            return PermissionResult(allowed=True, message="Previously approved")

        # 调用确认回调（终端弹窗或 GUI 对话框）
        if self._confirm_callback:
            approved = self._confirm_callback(tool_name, params)
            if approved:
                self._allowed_cache.add(cache_key)  # 缓存审批结果
                return PermissionResult(allowed=True)
            else:
                return PermissionResult(allowed=False, message="User denied")
```

---

## 附录：测试覆盖

| 测试文件 | 测试数 | 覆盖范围 |
|---------|--------|---------|
| `test_tools.py` | 18 | 文件读写、编辑、搜索、Shell 执行、安全命令拦截 |
| `test_memory.py` | 8 | 记忆存储、搜索、类型过滤、删除、衰减、检索 |
| `test_context.py` | 4 | Token 预算、外置化、历史压缩 |
| `test_security.py` | 12 | 路径边界、危险命令、敏感文件、Prompt 注入（中英文） |
| **总计** | **42** | |
