"""Query Loop - the core agent execution loop.

This is the heart of MiniClaude: User Query → LLM → Tool Calls → Results → Loop
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from miniclaude.core.config import MiniClaudeConfig
from miniclaude.core.context import ConversationContext
from miniclaude.core.tool_executor import ToolExecutor
from miniclaude.llm.client import ClaudeClient, LLMResponse
from miniclaude.llm.message_builder import MessageBuilder

logger = logging.getLogger(__name__)

# Maximum tool-call iterations before forcing a text response
MAX_ITERATIONS = 50


class QueryLoop:
    """Core agent loop: Query → LLM Reasoning → Tool Execution → Loop.

    Flow:
    1. User input → build messages
    2. Send to LLM with tool definitions
    3. If LLM returns tool_calls → execute tools → feed results back → go to 2
    4. If LLM returns text only → done, return to user
    """

    def __init__(
        self,
        llm_client: ClaudeClient,
        tool_executor: ToolExecutor,
        context: ConversationContext,
        config: MiniClaudeConfig,
    ) -> None:
        self.llm_client = llm_client
        self.tool_executor = tool_executor
        self.context = context
        self.config = config
        self._on_tool_start: Callable[[str, dict], None] | None = None
        self._on_tool_end: Callable[[str, bool, str], None] | None = None
        self._on_thinking: Callable[[str], None] | None = None
        self._iteration_count = 0

    def set_callbacks(
        self,
        on_tool_start: Callable[[str, dict], None] | None = None,
        on_tool_end: Callable[[str, bool, str], None] | None = None,
        on_thinking: Callable[[str], None] | None = None,
    ) -> None:
        """Set UI callback functions for progress reporting."""
        self._on_tool_start = on_tool_start
        self._on_tool_end = on_tool_end
        self._on_thinking = on_thinking

    async def run(self, user_input: str) -> str:
        """Run the agent loop for a single user query.

        Args:
            user_input: The user's text input/query.

        Returns:
            Final text response from the LLM.
        """
        logger.info("=== New Query ===")
        logger.info("User: %s", user_input[:200])

        # Add user message to context
        self.context.add_user_message(user_input)
        self._iteration_count = 0

        # Build tool schemas (in Anthropic format, client will convert to OpenAI)
        tools_schema = self.tool_executor.registry.get_anthropic_schemas()

        # Main loop
        final_text = ""
        response: LLMResponse | None = None

        while self._iteration_count < MAX_ITERATIONS:
            self._iteration_count += 1
            logger.debug("Iteration %d/%d", self._iteration_count, MAX_ITERATIONS)

            # Get messages from context
            messages = self.context.get_messages()

            # Call LLM
            response = await self.llm_client.chat(
                messages=messages,
                system=self.context.system_prompt,
                tools=tools_schema,
            )

            # Report thinking text
            if response.text and self._on_thinking:
                self._on_thinking(response.text)

            # If no tool calls, we're done
            if not response.has_tool_use:
                final_text = response.text
                # Save assistant response to context
                self.context.add_assistant_message(response.text)
                logger.info(
                    "Agent finished in %d iterations. Response: %d chars",
                    self._iteration_count, len(final_text),
                )
                break

            # Has tool calls - build assistant message with tool_calls and add to context
            assistant_msg = MessageBuilder.build_assistant_with_tool_use(
                response.text, response.tool_calls
            )
            self.context.add_raw_message(assistant_msg)

            # Execute tool calls
            for tc in response.tool_calls:
                if self._on_tool_start:
                    self._on_tool_start(tc["name"], tc["input"])

            results = await self.tool_executor.execute_all(response.tool_calls)

            for tc, result in zip(response.tool_calls, results):
                if self._on_tool_end:
                    self._on_tool_end(
                        tc["name"],
                        result.success,
                        result.content[:200] if result.content else "",
                    )

            # Convert results to OpenAI message format and add to context
            tool_messages = MessageBuilder.tool_results_to_message(
                response.tool_calls, results
            )
            # tool_messages[0] is the assistant message with tool_calls
            # tool_messages[1:] are the tool result messages
            # We already added the assistant message, so just add the tool results
            for msg in tool_messages[1:]:  # Skip assistant msg, already added
                self.context.add_raw_message(msg)

            logger.debug(
                "Iteration %d: %d tool calls executed",
                self._iteration_count, len(results),
            )

        else:
            # Hit max iterations
            final_text = (
                f"I've reached the maximum number of tool call iterations ({MAX_ITERATIONS}). "
                f"Here's what I've done so far:\n\n"
            )
            if response and response.text:
                final_text += response.text
            self.context.add_assistant_message(final_text)
            logger.warning("Hit max iterations (%d)", MAX_ITERATIONS)

        return final_text

    @property
    def iteration_count(self) -> int:
        return self._iteration_count

    @property
    def token_usage(self) -> dict[str, int]:
        """Get cumulative token usage."""
        return {
            "input_tokens": self.llm_client.total_input_tokens,
            "output_tokens": self.llm_client.total_output_tokens,
            "total_tokens": self.llm_client.total_tokens,
        }
