"""MiniClaude application class - wires all subsystems together."""

from __future__ import annotations

import logging
from typing import Any

from miniclaude.agents.orchestrator import Orchestrator
from miniclaude.context.manager import ContextManager
from miniclaude.core.config import get_config, MiniClaudeConfig
from miniclaude.core.context import ConversationContext
from miniclaude.core.loop import QueryLoop
from miniclaude.core.tool_executor import ToolExecutor
from miniclaude.llm.client import ClaudeClient
from miniclaude.memory.compressor import MemoryCompressor
from miniclaude.memory.extractor import MemoryExtractor
from miniclaude.memory.retriever import MemoryRetriever
from miniclaude.memory.store import MemoryStore
from miniclaude.security.auditor import SecurityAuditor
from miniclaude.security.permission import PermissionManager
from miniclaude.skills.catalog import SkillCatalog
from miniclaude.skills.router import SkillRouter
from miniclaude.tools.registry import ToolRegistry
from miniclaude.tools.memory_tools import MemorySaveTool, MemorySearchTool
from miniclaude.ui.repl import REPL

logger = logging.getLogger(__name__)


class MiniClaudeApp:
    """Main application that orchestrates all 8 subsystems.

    Architecture:
    ┌─────────────────────────────────────────────────┐
    │  REPL (UI)                                      │
    ├─────────────────────────────────────────────────┤
    │  QueryLoop (Core Engine)                        │
    │  ┌──────────┐ ┌──────────┐ ┌─────────────────┐ │
    │  │ LLM      │ │ Tool     │ │ Context         │ │
    │  │ Client   │ │ Executor │ │ Manager         │ │
    │  └──────────┘ └──────────┘ └─────────────────┘ │
    ├─────────────────────────────────────────────────┤
    │  ┌──────────┐ ┌──────────┐ ┌─────────────────┐ │
    │  │ Skill    │ │ Memory   │ │ Multi-Agent     │ │
    │  │ Router   │ │ System   │ │ Orchestrator    │ │
    │  └──────────┘ └──────────┘ └─────────────────┘ │
    ├─────────────────────────────────────────────────┤
    │  Security & Permissions Layer                   │
    └─────────────────────────────────────────────────┘
    """

    def __init__(self, config: MiniClaudeConfig | None = None) -> None:
        self.config = config or get_config()

        # Core components
        self.llm_client: ClaudeClient | None = None
        self.tool_registry: ToolRegistry | None = None
        self.tool_executor: ToolExecutor | None = None
        self.context: ConversationContext | None = None
        self.query_loop: QueryLoop | None = None

        # Skill system
        self.skill_catalog: SkillCatalog | None = None
        self.skill_router: SkillRouter | None = None

        # Memory system
        self.memory_store: MemoryStore | None = None
        self.memory_retriever: MemoryRetriever | None = None
        self.memory_extractor: MemoryExtractor | None = None
        self.memory_compressor: MemoryCompressor | None = None

        # Context management
        self.context_manager: ContextManager | None = None

        # Multi-agent
        self.orchestrator: Orchestrator | None = None

        # Security
        self.permission_manager: PermissionManager | None = None
        self.auditor: SecurityAuditor | None = None

        # UI
        self.repl: REPL | None = None

        self._initialized = False

    async def initialize(self) -> None:
        """Initialize all subsystems in dependency order."""
        if self._initialized:
            return

        logger.info("Initializing MiniClaude v0.1.0 ...")
        logger.info("Model: %s, Context limit: %d", self.config.model, self.config.context_limit)

        # === 1. LLM Client ===
        self.llm_client = ClaudeClient(self.config)
        logger.info("✓ LLM Client initialized")

        # === 2. Tool Registry + Tools ===
        self.tool_registry = ToolRegistry(self.config)
        self.tool_registry.register_all()
        logger.info("✓ Tool Registry: %d tools", len(self.tool_registry))

        # === 3. Memory System ===
        if self.config.memory_enabled:
            self.memory_store = MemoryStore(self.config.memory_db_path)
            self.memory_retriever = MemoryRetriever(self.memory_store)
            self.memory_extractor = MemoryExtractor(self.llm_client, self.memory_store)
            self.memory_compressor = MemoryCompressor(self.memory_store)

            # Register memory tools
            self.tool_registry.register(MemorySaveTool(self.config, self.memory_store))
            self.tool_registry.register(MemorySearchTool(self.config, self.memory_store))
            logger.info("✓ Memory System enabled (DB: %s)", self.config.memory_db_path)
        else:
            logger.info("○ Memory System disabled")

        # === 4. Skill System ===
        self.skill_catalog = SkillCatalog()
        self.skill_catalog.register_all_builtin()
        self.skill_router = SkillRouter(self.skill_catalog)
        logger.info("✓ Skill System: %d skills loaded", self.skill_catalog.skill_count)

        # === 5. Context Manager ===
        self.context_manager = ContextManager(self.config)
        logger.info("✓ Context Manager initialized")

        # === 6. Multi-Agent Orchestrator ===
        self.orchestrator = Orchestrator(self.config, self.llm_client, self.tool_registry)
        self.orchestrator.register_agent_tool()
        logger.info("✓ Multi-Agent Orchestrator initialized")

        # === 7. Security ===
        self.auditor = SecurityAuditor()
        self.permission_manager = PermissionManager(self.config)
        logger.info("✓ Security layer initialized")

        # === 8. Tool Executor ===
        self.tool_executor = ToolExecutor(self.tool_registry, self.config)

        # === 9. Conversation Context ===
        self.context = ConversationContext(self.config)

        # === 10. Query Loop (core engine) ===
        self.query_loop = QueryLoop(
            llm_client=self.llm_client,
            tool_executor=self.tool_executor,
            context=self.context,
            config=self.config,
        )

        # === 11. REPL ===
        self.repl = REPL(self.query_loop, self.context)

        self._initialized = True
        total_tools = len(self.tool_registry)
        logger.info("═" * 50)
        logger.info("MiniClaude initialized successfully!")
        logger.info("  Tools: %d | Skills: %d | Memory: %s",
                    total_tools,
                    self.skill_catalog.skill_count,
                    "ON" if self.config.memory_enabled else "OFF")
        logger.info("═" * 50)

    async def run_query(self, query: str) -> str:
        """Run a single query and return the response."""
        if not self._initialized:
            await self.initialize()
        assert self.query_loop is not None
        return await self.query_loop.run(query)

    async def run_repl(self) -> None:
        """Start the interactive REPL."""
        if not self._initialized:
            await self.initialize()
        assert self.repl is not None
        await self.repl.run()

    async def shutdown(self) -> None:
        """Clean up all resources."""
        logger.info("Shutting down MiniClaude ...")

        # Close memory store
        if self.memory_store:
            self.memory_store.close()

        # Close LLM client
        if self.llm_client:
            await self.llm_client.close()

        logger.info("Shutdown complete.")
