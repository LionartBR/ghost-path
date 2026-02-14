"""Agent Runner — async agentic loop with streaming SSE delivery.

Invariants:
    - Max 50 iterations, tool errors never crash loop, pause tools halt loop
    - web_search results intercepted for ForgeState gate enforcement

Design Decisions:
    - Anthropic streaming API for real-time text/tool delivery (ADR: Day 4 polish)
    - get_final_message() for post-processing (avoids manual block reconstruction)
    - Language enforcement after stream (trade-off: user may briefly see wrong text)
    - Pure helpers extracted to agent_runner_helpers.py (ADR: ExMA 400-line limit)
"""

import asyncio
import json
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.tool_dispatch import ToolDispatch, PAUSE_TOOLS
from app.core.forge_state import ForgeState
from app.services.tools_registry import get_phase_tools
from app.services.system_prompt import build_system_prompt
from app.core.enforce_language import check_response_language
from app.infrastructure.anthropic_client import ResilientAnthropicClient
from app.core.errors import TrizError, AgentLoopExceededError, ErrorContext
from app.core.domain_types import Locale
from app.services.agent_runner_helpers import (
    done_event, tool_result_event, unexpected_error_event,
    get_context_usage, has_tool_use, serialize_content,
    process_stream_event, record_web_searches,
    with_system_cache, with_tools_cache, with_message_cache,
)

logger = logging.getLogger(__name__)


class AgentRunner:
    """Async agentic loop — streams SSE events for the TRIZ pipeline."""

    MAX_ITERATIONS = 50
    MAX_LANGUAGE_RETRIES = 2

    def __init__(
        self, db: AsyncSession, anthropic_client: ResilientAnthropicClient,
    ):
        self.client = anthropic_client
        self.model = "claude-opus-4-6"
        self.db = db

    async def run(
        self, session, user_message: str, forge_state: ForgeState,
    ):
        """Async generator yielding SSE events with real-time streaming."""
        system = build_system_prompt(forge_state.locale)
        messages = self._build_messages(session, user_message)
        ctx = ErrorContext(session_id=str(session.id))
        dispatch = ToolDispatch(self.db, forge_state, session.id)

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
            async for sse in self._stream_api_call(
                system, messages, forge_state, ctx,
            ):
                yield sse
            if self._last_response is None:
                return  # error/cancel events already yielded
            response = self._last_response

            self._account_tokens(session, response)
            yield {"type": "context_usage", "data": get_context_usage(session)}
            for sse in record_web_searches(response.content, dispatch):
                yield sse

            serialized = serialize_content(response)
            if response.stop_reason == "pause_turn":
                messages.append({"role": "assistant", "content": serialized})
                continue

            action, nudge = self._check_language(
                response, forge_state, lang_retries,
            )
            if action == "retry":
                lang_retries += 1
                messages.append({"role": "assistant", "content": serialized})
                messages.append({"role": "user", "content": nudge})
                continue

            if not has_tool_use(response):
                await self._save_state(session, messages, forge_state)
                yield done_event(error=False)
                return

            messages.append({"role": "assistant", "content": serialized})
            tool_msgs, pause, events = await self._execute_tool_blocks(
                dispatch, session, response.content, nudge,
            )
            for sse in events:
                yield sse
            messages.append({"role": "user", "content": tool_msgs})

            if pause:
                await self._save_state(session, messages, forge_state)
                yield done_event(error=False, awaiting_input=True)
                return

        # Max iterations exceeded
        error = AgentLoopExceededError(self.MAX_ITERATIONS, ctx)
        yield error.to_sse_event()
        yield done_event(error=True)

    async def _stream_api_call(self, system, messages, forge_state, ctx):
        """Async generator: yields SSE text events, sets self._last_response."""
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

    def _check_language(self, response, forge_state, retries):
        """Check response language. Returns (action, nudge_message)."""
        if retries >= self.MAX_LANGUAGE_RETRIES:
            return None, None
        if forge_state.locale == Locale.EN:
            return None, None

        text_blocks = [
            b.text for b in response.content
            if getattr(b, "type", None) == "text"
        ]
        if not text_blocks:
            return None, None

        lang_error = check_response_language(
            "".join(text_blocks), forge_state.locale,
        )
        if not lang_error:
            return None, None

        if not has_tool_use(response):
            logger.warning("Language retry %d/%d",
                retries + 1, self.MAX_LANGUAGE_RETRIES)
            return "retry", lang_error["message"]

        logger.warning("Language nudge %d/%d",
            retries + 1, self.MAX_LANGUAGE_RETRIES)
        return "nudge", lang_error["message"]

    async def _execute_tool_blocks(
        self, dispatch, session, content_blocks, lang_nudge,
    ):
        """Execute tool_use blocks. Returns (msgs, should_pause, events)."""
        tool_results = []
        sse_events = []
        should_pause = False

        for block in content_blocks:
            if getattr(block, "type", None) != "tool_use":
                continue
            result = await self._execute_tool_safe(
                dispatch, session, block.name, block.input,
            )
            sse_events.append(tool_result_event(block.name, result))
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

    def _account_tokens(self, session, response):
        """Add token usage from response to session."""
        session.total_tokens_used += (
            response.usage.input_tokens + response.usage.output_tokens
        )

    async def _save_state(self, session, messages, forge_state):
        """Save message history + ForgeState snapshot. Never crashes."""
        try:
            session.message_history = messages
            session.forge_state_snapshot = forge_state.to_snapshot()
            await self.db.commit()
        except Exception as e:
            logger.error("Failed to save state: %s", e)

    async def _execute_tool_safe(
        self, dispatch: ToolDispatch, session: object,
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

    def _build_messages(self, session: object, user_message: str) -> list:
        """Build message array from history + new user message."""
        messages = list(session.message_history or [])
        messages.append({"role": "user", "content": user_message})
        return messages
