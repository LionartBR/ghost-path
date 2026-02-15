"""Agent Runner — async agentic loop with streaming SSE delivery.

Invariants:
    - Max 50 iterations, tool errors never crash loop, pause tools halt loop
    - web_search results intercepted for ForgeState gate enforcement

Design Decisions:
    - Anthropic streaming API for real-time text/tool delivery (ADR: Day 4 polish)
    - get_final_message() for post-processing (avoids manual block reconstruction)
    - Language enforcement after stream (trade-off: user may briefly see wrong text)
    - Pure helpers extracted to agent_runner_helpers.py (ADR: ExMA ~7 methods / class)
"""

import asyncio
import json
import logging

from app.core.context_compaction import optimize_context
from app.core.domain_types import SessionId
from app.services.tool_dispatch import ToolDispatch, PAUSE_TOOLS
from app.core.forge_state import ForgeState
from app.core.repository_protocols import SessionLike
from app.infrastructure.anthropic_client import ResilientAnthropicClient
from app.core.errors import TrizError, AgentLoopExceededError, ErrorContext
from app.services.agent_runner_helpers import (
    done_event, tool_result_event, unexpected_error_event,
    get_context_usage, has_tool_use, serialize_content,
    process_stream_event, web_search_detail_from_research,
    with_system_cache, with_tools_cache, with_message_cache,
    check_language, account_tokens, format_directives,
    build_messages, save_state,
)
from app.services.tools_registry import get_phase_tools
from app.services.system_prompt import build_system_prompt

logger = logging.getLogger(__name__)


class AgentRunner:
    """Async agentic loop — streams SSE events for the TRIZ pipeline.

    Methods: __init__, run, _iteration_loop, _stream_api_call,
    _execute_tool_blocks, _execute_tool_safe (6 methods — ExMA ~7 limit).
    Helpers extracted to agent_runner_helpers.py.
    """

    MAX_ITERATIONS = 50
    MAX_LANGUAGE_RETRIES = 2

    def __init__(
        self, db, anthropic_client: ResilientAnthropicClient,
    ) -> None:
        self.client = anthropic_client
        self.model = "claude-opus-4-6"
        self.db = db

    async def run(
        self, session: SessionLike, user_message: str,
        forge_state: ForgeState,
    ):
        """Async generator yielding SSE events."""
        system = build_system_prompt(forge_state.locale)
        messages = build_messages(session, user_message)
        ctx = ErrorContext(session_id=str(session.id))
        dispatch = ToolDispatch(
            self.db, forge_state, SessionId(session.id), self.client,
        )

        try:
            async for event in self._iteration_loop(
                session, forge_state, system, messages, ctx, dispatch,
            ):
                yield event
        except asyncio.CancelledError:
            logger.info("Stream cancelled (client disconnect)",
                extra={"session_id": str(session.id)})
            raise
        except Exception as e:
            logger.error("Unexpected error in agent runner: %s", e,
                extra={"session_id": str(session.id)}, exc_info=True)
            yield unexpected_error_event()
            yield done_event(error=True)

    async def _iteration_loop(
        self, session, forge_state, system, messages, ctx, dispatch,
    ):
        """Main iteration loop — yields SSE events."""
        lang_retries = 0
        for _ in range(self.MAX_ITERATIONS):
            if forge_state.cancelled:
                yield {"type": "agent_text", "data": "Session cancelled."}
                yield done_event(error=False)
                return
            self._last_response = None
            # Context optimization before each API call (ADR: always-on, reduces token growth)
            optimized = optimize_context(
                messages, forge_state.current_phase.value, forge_state.locale.value,
            )
            if len(optimized) < len(messages):
                messages.clear()
                messages.extend(optimized)
            async for sse in self._stream_api_call(
                system, messages, forge_state, ctx,
            ):
                yield sse
            if self._last_response is None:
                return
            response = self._last_response
            account_tokens(session, response)
            yield {"type": "context_usage", "data": get_context_usage(session)}
            serialized = serialize_content(response)
            if response.stop_reason == "pause_turn":
                messages.append({"role": "assistant", "content": serialized})
                continue
            action, nudge = check_language(
                response, forge_state, lang_retries, self.MAX_LANGUAGE_RETRIES,
            )
            if action == "retry":
                lang_retries += 1
                messages.append({"role": "assistant", "content": serialized})
                messages.append({"role": "user", "content": nudge})
                continue
            if not has_tool_use(response):
                await save_state(session, messages, forge_state, self.db)
                yield done_event(error=False)
                return
            messages.append({"role": "assistant", "content": serialized})
            async for sse in self._process_tools(
                dispatch, session, forge_state, response, messages, nudge,
            ):
                yield sse
                if sse.get("type") == "done":
                    return
        yield AgentLoopExceededError(self.MAX_ITERATIONS, ctx).to_sse_event()
        yield done_event(error=True)

    async def _process_tools(
        self, dispatch, session, forge_state, response, messages, nudge,
    ):
        """Execute tools, inject directives, handle pause."""
        tool_msgs, pause, events = await self._execute_tool_blocks(
            dispatch, session, response.content, nudge,
        )
        for sse in events:
            yield sse
        directives = forge_state.consume_research_directives()
        if directives:
            tool_msgs.append({"type": "text", "text": format_directives(directives)})
        messages.append({"role": "user", "content": tool_msgs})
        if pause:
            await save_state(session, messages, forge_state, self.db)
            yield done_event(error=False, awaiting_input=True)

    async def _stream_api_call(self, system, messages, forge_state, ctx):
        """Yields SSE text events, sets self._last_response."""
        try:
            text_lstrip = True
            async with self.client.stream_message(
                model=self.model, max_tokens=16384,
                system=with_system_cache(system),
                tools=with_tools_cache(
                    get_phase_tools(forge_state.current_phase),
                ),
                messages=with_message_cache(messages),
                context=ctx,
            ) as stream:
                async for event in stream:
                    if forge_state.cancelled:
                        break
                    sse, text_lstrip = process_stream_event(
                        event, text_lstrip,
                    )
                    if sse:
                        yield sse

                if forge_state.cancelled:
                    yield {"type": "agent_text", "data": "Session cancelled."}
                    yield done_event(error=False)
                    return

                self._last_response = await stream.get_final_message()

        except TrizError as e:
            logger.error("Anthropic API error: %s", e.message)
            yield e.to_sse_event()
            yield done_event(error=True)

    async def _execute_tool_blocks(
        self, dispatch: ToolDispatch, session: SessionLike,
        content_blocks, lang_nudge: str | None,
    ) -> tuple[list, bool, list]:
        """Execute tool_use blocks. Returns (msgs, pause, events)."""
        tool_results: list[dict] = []
        sse_events: list[dict] = []
        should_pause = False

        for block in content_blocks:
            if getattr(block, "type", None) != "tool_use":
                continue
            result = await self._execute_tool_safe(
                dispatch, session, block.name, block.input,
            )
            sse_events.append(tool_result_event(block.name, result))
            if block.name == "research":
                detail = web_search_detail_from_research(block.input, result)
                if detail:
                    sse_events.append(detail)
            if block.name in PAUSE_TOOLS and result.get("paused"):
                should_pause = True
            tool_results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": json.dumps(result, ensure_ascii=False),
            })

        if lang_nudge:
            tool_results.append({"type": "text", "text": lang_nudge})
        return tool_results, should_pause, sse_events

    async def _execute_tool_safe(
        self, dispatch: ToolDispatch, session: SessionLike,
        tool_name: str, tool_input: dict,
    ) -> dict:
        """Execute tool with error boundary — never raises."""
        try:
            return await dispatch.execute(tool_name, session, tool_input)
        except TrizError as e:
            logger.warning("Tool error: %s", e.message,
                extra={"tool_name": tool_name, "error_code": e.code})
            return e.to_response()
        except Exception as e:
            logger.error("Unexpected error in tool '%s': %s",
                tool_name, e, exc_info=True)
            return {
                "status": "error", "error_code": "TOOL_EXECUTION_ERROR",
                "message": f"Internal error executing {tool_name}",
            }
