<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue?logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/License-MIT-green" alt="License">
  <img src="https://img.shields.io/badge/Model-MiMo--v2.5--Pro-purple" alt="Model">
</p>

# MiniClaude

**参考 Claude Code 架构设计的 AI Coding Agent**，基于 Query Loop + Tool Use 构建任务执行闭环，重点实现了 Skill 路由、自进化记忆沉淀、分层上下文压缩、多 Agent 协作与权限安全审查等机制。

<!-- 📸 在这里替换为你自己的截图 -->
<p align="center">
  <img src="docs/screenshot_launcher.png" width="320" alt="Launcher">
  &nbsp;&nbsp;
  <img src="docs/screenshot_desktop.png" width="560" alt="Desktop GUI">
</p>

---

## ✨ 项目特色

| 特性 | 说明 |
|------|------|
| **Skill 分层路由** | 三层架构（Atomic Tool → High-level Skill → Catalog），二阶段召回+精排，降低检索噪声与 Token 成本 |
| **自进化记忆沉淀** | 执行→反思→提炼→分类存储→索引更新→按需复用，程序性经验、情景记忆、用户画像自动沉淀 |
| **分层上下文压缩** | 大结果外置化 + 缓存友好占位压缩 + 结构化笔记摘要，四层策略控制上下文窗口 |
| **多 Agent 协作** | 中心化编排，子 Agent 以 Tool Call 方式受控执行，支持 4 种专业角色 |
| **权限与安全审查** | 规则过滤 + 工具自检 + Prompt 注入防御（中英文） + 人工确认的多层审查链路 |
| **三种界面** | 终端 REPL（Rich）、桌面 GUI（Tkinter）、双击启动器，按需选择 |

---

## 🏗️ 架构概览

```
┌──────────────────────────────────────────────────────────────────┐
│  UI Layer — REPL (Rich) / Desktop GUI (Tkinter) / Launcher       │
├──────────────────────────────────────────────────────────────────┤
│  QueryLoop — User → LLM → Tool Calls → Results → Loop           │
│  ┌────────────┐ ┌────────────┐ ┌──────────────────────────────┐  │
│  │ LLM Client │ │ Tool       │ │ Context Manager              │  │
│  │ (OpenAI    │ │ Executor   │ │ (Budget / Externalizer /     │  │
│  │  Compat)   │ │            │ │  Placeholder / Compressor)   │  │
│  └────────────┘ └────────────┘ └──────────────────────────────┘  │
├──────────────────────────────────────────────────────────────────┤
│  ┌────────────┐ ┌────────────┐ ┌──────────────────────────────┐  │
│  │ Skill      │ │ Memory     │ │ Multi-Agent                  │  │
│  │ Router     │ │ System     │ │ Orchestrator                 │  │
│  │ (2-stage)  │ │ (SQLite)   │ │ (4 agent profiles)           │  │
│  └────────────┘ └────────────┘ └──────────────────────────────┘  │
├──────────────────────────────────────────────────────────────────┤
│  Security — Rule Filter + Prompt Guard + Risk Classifier + Audit │
└──────────────────────────────────────────────────────────────────┘
```

---

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/<你的用户名>/MiniClaudecode.git
cd MiniClaudecode
```

### 2. 安装依赖

```bash
pip install -e .
```

### 3. 配置 API Key

```bash
cp .env.example .env
# 编辑 .env，填入你的 API Key
```

```env
MINICLAUDE_API_KEY=your-api-key-here
MINICLAUDE_API_BASE_URL=https://token-plan-cn.xiaomimimo.com/v1
MINICLAUDE_MODEL=mimo-v2.5-pro
```

### 4. 启动

```bash
# 🖥️ 桌面 GUI（推荐）
python run.pyw          # 双击 run.pyw 亦可

# 💻 终端 REPL
python -m miniclaude

# 📋 直接查询
python -m miniclaude "列出当前目录所有 Python 文件"

# 🖥️ 通过命令行参数启动 GUI
python -m miniclaude --gui
```

---

## 🖼️ 界面展示

<!-- 📸 请在以下位置替换为你自己的截图 -->

### 模式选择启动器

<!-- 截图：双击 run.pyw 后弹出的模式选择窗口 -->
<p align="center">
  <img src="docs/screenshot_launcher.png" width="400" alt="Mode Selection Launcher">
</p>

### 桌面客户端

<!-- 截图：Desktop GUI 的完整界面，展示聊天、工具调用、输入框 -->
<p align="center">
  <img src="docs/screenshot_desktop.png" width="700" alt="Desktop GUI Client">
</p>

### 终端 REPL

<!-- 截图：终端中的 REPL 交互界面 -->
<p align="center">
  <img src="docs/screenshot_repl.png" width="600" alt="Terminal REPL">
</p>

### 工具调用演示

<!-- 截图：AI 调用 read_file / glob_files 等工具的过程 -->
<p align="center">
  <img src="docs/screenshot_tool_call.png" width="600" alt="Tool Calling Demo">
</p>

---

## 📁 项目结构

```
miniclaude/
├── core/               # 核心引擎
│   ├── config.py       # 配置管理（Pydantic Settings）
│   ├── loop.py         # Query Loop 主循环
│   ├── tool_executor.py
│   └── context.py      # 对话上下文管理
├── llm/                # LLM 接口层
│   ├── client.py       # OpenAI 兼容客户端
│   ├── message_builder.py
│   └── token_counter.py
├── tools/              # 原子工具（6 个内置 + 2 个记忆工具）
│   ├── file_tools.py   # read / write / edit / glob / grep
│   ├── shell_tools.py  # 命令执行（带安全过滤）
│   └── memory_tools.py
├── skills/             # 高层 Skill 层
│   ├── router.py       # 二阶段路由器
│   ├── catalog.py      # Skill 目录
│   └── builtin/        # 5 个内置 Skill
│       ├── code_review.py
│       ├── refactor.py
│       ├── debug.py
│       ├── test_gen.py
│       ├── explain.py
│       └── code_gen.py
├── memory/             # 自进化记忆系统
│   ├── store.py        # SQLite 持久化
│   ├── extractor.py    # 记忆提取器（LLM 反思）
│   ├── retriever.py    # 记忆检索器
│   └── compressor.py   # 记忆压缩
├── context/            # 分层上下文压缩
│   ├── manager.py      # 上下文管理器
│   ├── externalizer.py # 大结果外置化
│   ├── compressor.py   # 历史消息压缩
│   └── budget.py       # Token 预算管理
├── agents/             # 多 Agent 协作
│   ├── orchestrator.py # 中心化编排器
│   ├── sub_agent.py    # 子 Agent（4 种角色）
│   └── team.py         # Agent Team
├── security/           # 权限与安全审查
│   ├── permission.py   # 多层权限检查
│   ├── rules.py        # 规则过滤器
│   ├── prompt_guard.py # Prompt 注入防御
│   └── auditor.py      # 审计日志
└── ui/                 # 用户界面
    ├── repl.py         # 终端 REPL（Rich）
    ├── desktop.py      # 桌面 GUI（Tkinter）
    └── launcher.py     # 模式选择启动器
```

---

## 🛠️ 技术栈

| 组件 | 技术 |
|------|------|
| LLM 后端 | OpenAI 兼容 API（MiMo-v2.5-pro） |
| 工具调用 | Function Calling（OpenAI 格式） |
| 数据模型 | Pydantic v2 |
| 持久化 | SQLite（aiosqlite） |
| 终端 UI | Rich |
| 桌面 UI | Tkinter |
| CLI | Typer |
| Token 计数 | tiktoken |

---

## ⚙️ 配置说明

所有配置通过 `.env` 文件或环境变量设置，前缀 `MINICLAUDE_`：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `MINICLAUDE_API_KEY` | - | API 密钥（必填） |
| `MINICLAUDE_API_BASE_URL` | `https://token-plan-cn.xiaomimimo.com/v1` | API 端点 |
| `MINICLAUDE_MODEL` | `mimo-v2.5-pro` | 模型标识 |
| `MINICLAUDE_MAX_TOKENS` | `8192` | 单次最大输出 Token |
| `MINICLAUDE_TEMPERATURE` | `0.6` | 采样温度 |
| `MINICLAUDE_CONTEXT_LIMIT` | `131072` | 上下文窗口大小 |
| `MINICLAUDE_MEMORY_ENABLED` | `true` | 是否启用记忆系统 |
| `MINICLAUDE_ALLOW_SHELL` | `true` | 是否允许 Shell 命令 |

---

## 🧪 测试

```bash
pip install -e ".[dev]"
python -m pytest tests/ -v
```

---

## 📄 License

MIT

---

## 截图指南

> **给开发者**：截取以下 4 张图放入 `docs/` 目录，README 中的图片会自动显示。
>
> 1. **`docs/screenshot_launcher.png`** — 双击 `run.pyw` 后的模式选择窗口
> 2. **`docs/screenshot_desktop.png`** — Desktop GUI 完整对话界面（发送一条消息，展示工具调用）
> 3. **`docs/screenshot_repl.png`** — 终端 REPL 中的一次完整交互
> 4. **`docs/screenshot_tool_call.png`** — 展示 AI 调用 `read_file` / `glob_files` 的过程
>
> 建议用 Windows 截图工具（Win+Shift+S）截取，保持暗色主题，分辨率 150% 效果最佳。
