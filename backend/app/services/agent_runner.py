"""Agent Runner — async agentic loop with streaming SSE delivery.

Invariants:
    - Max 50 iterations, tool errors never crash loop, pause tools halt loop
    - web_search results intercepted for ForgeState gate enforcement

Design Decisions:
    - Anthropic streaming API for real-time text/tool delivery (ADR: Day 4 polish)
    - get_final_message() for post-processing (avoids manual block reconstruction)
    - Language enforcement after stream (trade-off: user may briefly see wrong text)
"""

import asyncio
import json
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.tool_dispatch import ToolDispatch, PAUSE_TOOLS
from app.core.domain_types import Locale
from app.core.forge_state import ForgeState
from app.services.tools_registry import get_phase_tools
from app.services.system_prompt import build_system_prompt
from app.core.enforce_language import check_response_language
from app.infrastructure.anthropic_client import ResilientAnthropicClient
from app.core.errors import (
    TrizError, AgentLoopExceededError,
    ErrorContext, ErrorSeverity,
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
        iteration = 0
        language_retries = 0
        system = build_system_prompt(forge_state.locale)

        try:
            messages = self._build_messages(session, user_message)
            ctx = ErrorContext(session_id=str(session.id))
            dispatch = ToolDispatch(self.db, forge_state, session.id)

            while iteration < self.MAX_ITERATIONS:
                iteration += 1

                if forge_state.cancelled:
                    yield {"type": "agent_text", "data": "Session cancelled."}
                    yield _done_event(error=False)
                    return

                # === STREAM: real-time SSE to frontend ===
                try:
                    text_lstrip = True
                    async with self.client.stream_message(
                        model=self.model, max_tokens=16384,
                        system=_with_system_cache(system),
                        tools=_with_tools_cache(get_phase_tools(forge_state.current_phase)),
                        messages=_with_message_cache(messages),
                        context=ctx,
                    ) as stream:
                        async for event in stream:
                            if forge_state.cancelled:
                                break
                            etype = getattr(event, "type", None)
                            if etype == "content_block_start":
                                cb = event.content_block
                                bt = getattr(cb, "type", None)
                                if bt == "text":
                                    text_lstrip = True
                                elif bt == "tool_use":
                                    yield _tool_call_event(cb.name, "")
                                elif bt == "server_tool_use":
                                    q = getattr(cb, "input", {}).get(
                                        "query", "",
                                    )
                                    yield _tool_call_event(
                                        getattr(cb, "name", "web_search"), q,
                                    )
                            elif etype == "content_block_delta":
                                dt = getattr(event.delta, "type", None)
                                if dt == "text_delta" and event.delta.text:
                                    txt = event.delta.text
                                    if text_lstrip:
                                        txt = txt.lstrip()
                                        if txt:
                                            text_lstrip = False
                                    if txt:
                                        yield {
                                            "type": "agent_text",
                                            "data": txt,
                                        }

                        if forge_state.cancelled:
                            yield {
                                "type": "agent_text",
                                "data": "Session cancelled.",
                            }
                            yield _done_event(error=False)
                            return

                        response = await stream.get_final_message()

                except TrizError as e:
                    logger.error(
                        "Anthropic API error: %s", e.message,
                        extra={"session_id": str(session.id)},
                    )
                    yield e.to_sse_event()
                    yield _done_event(error=True)
                    return

                # === POST-PROCESS: tokens, web_search, content serialization ===
                session.total_tokens_used += (
                    response.usage.input_tokens
                    + response.usage.output_tokens
                )

                yield {
                    "type": "context_usage",
                    "data": _get_context_usage(session),
                }

                for sse in _record_web_searches(response.content, dispatch):
                    yield sse

                serialized = [
                    b.model_dump(exclude_none=True)
                    for b in response.content
                ]

                if response.stop_reason == "pause_turn":
                    messages.append({"role": "assistant", "content": serialized})
                    continue

                has_tool_use = any(
                    getattr(b, "type", None) == "tool_use"
                    for b in response.content
                )
                _lang_nudge = None
                text_blocks = [
                    b.text for b in response.content
                    if getattr(b, "type", None) == "text"
                ]
                if (
                    text_blocks
                    and language_retries < self.MAX_LANGUAGE_RETRIES
                    and forge_state.locale != Locale.EN
                ):
                    full_text = "".join(text_blocks)
                    lang_error = check_response_language(
                        full_text, forge_state.locale,
                    )
                    if lang_error:
                        language_retries += 1
                        if not has_tool_use:
                            logger.warning("Language retry %d/%d",
                                language_retries, self.MAX_LANGUAGE_RETRIES)
                            messages.append({"role": "assistant", "content": serialized})
                            messages.append({"role": "user", "content": lang_error["message"]})
                            continue
                        logger.warning("Language nudge %d/%d",
                            language_retries, self.MAX_LANGUAGE_RETRIES)
                        _lang_nudge = lang_error["message"]

                if not has_tool_use:
                    await self._save_state(session, messages, forge_state)
                    yield _done_event(error=False)
                    return

                messages.append({"role": "assistant", "content": serialized})
                tool_results = []
                should_pause = False

                for block in response.content:
                    if getattr(block, "type", None) != "tool_use":
                        continue
                    result = await self._execute_tool_safe(
                        dispatch, session, block.name, block.input,
                    )
                    if result.get("status") == "error":
                        yield {
                            "type": "tool_error",
                            "data": {
                                "tool": block.name,
                                "error_code": result.get("error_code"),
                                "message": result.get("message"),
                            },
                        }
                    else:
                        yield {
                            "type": "tool_result",
                            "data": {
                                "tool": block.name,
                                "result_preview": str(result)[:300],
                            },
                        }
                    if block.name in PAUSE_TOOLS and result.get("paused"):
                        should_pause = True
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(
                            result, ensure_ascii=False,
                        ),
                    })

                if _lang_nudge:
                    tool_results.append({"type": "text", "text": _lang_nudge})
                messages.append({"role": "user", "content": tool_results})

                if should_pause:
                    await self._save_state(session, messages, forge_state)
                    yield _done_event(error=False, awaiting_input=True)
                    return

            # Max iterations exceeded
            error = AgentLoopExceededError(
                self.MAX_ITERATIONS,
                ErrorContext(session_id=str(session.id)),
            )
            logger.error(
                "Agent loop exceeded: %d iterations", iteration,
                extra={"session_id": str(session.id)},
            )
            yield error.to_sse_event()
            yield _done_event(error=True)

        except asyncio.CancelledError:
            logger.info(
                "Stream cancelled (client disconnect)",
                extra={"session_id": str(session.id)},
            )
            raise

        except Exception as e:
            logger.error(
                "Unexpected error in agent runner: %s", e,
                extra={"session_id": str(session.id)},
                exc_info=True,
            )
            yield {
                "type": "error",
                "data": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred",
                    "severity": ErrorSeverity.CRITICAL.value,
                    "recoverable": False,
                },
            }
            yield _done_event(error=True)

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
            return {"status": "error", "error_code": "TOOL_EXECUTION_ERROR",
                "message": f"Internal error executing {tool_name}"}

    def _build_messages(self, session: object, user_message: str) -> list:
        """Build message array from history + new user message."""
        messages = list(session.message_history or [])
        messages.append({"role": "user", "content": user_message})
        return messages


# -- Helpers (module-level, pure) -----------------------------------------------

def _done_event(error: bool = False, awaiting_input: bool = False) -> dict:
    return {
        "type": "done",
        "data": {"error": error, "awaiting_input": awaiting_input},
    }


def _tool_call_event(name: str, preview: str) -> dict:
    return {
        "type": "tool_call",
        "data": {"tool": name, "input_preview": preview},
    }


def _get_context_usage(session: object) -> dict:
    max_t = 1_000_000
    used = session.total_tokens_used
    return {
        "tokens_used": used,
        "tokens_limit": max_t,
        "tokens_remaining": max_t - used,
        "usage_percentage": round((used / max_t) * 100, 2),
    }


def _record_web_searches(content_blocks: list, dispatch: ToolDispatch) -> list:
    """Record web_search in ForgeState, return SSE events. Handles multi-search."""
    events = []
    last_query = "unknown query"
    for block in content_blocks:
        btype = getattr(block, "type", None)
        if btype == "server_tool_use":
            last_query = getattr(block, "input", {}).get(
                "query", "unknown query",
            )
        elif btype == "web_search_tool_result":
            content_list = getattr(block, "content", [])
            n = sum(
                1 for r in content_list
                if (isinstance(r, dict) and r.get("type") == "web_search_result")
                or getattr(r, "type", None) == "web_search_result"
            )
            dispatch.record_web_search(last_query, f"{n} result(s)")
            events.append({
                "type": "tool_result",
                "data": f"Web search returned {n} result(s)",
            })
    return events


# -- Prompt Caching helpers (ADR: 90% input token savings) ---------------------

_CACHE_CONTROL = {"type": "ephemeral"}


def _with_system_cache(system: str) -> list[dict]:
    return [{"type": "text", "text": system, "cache_control": _CACHE_CONTROL}]


def _with_tools_cache(tools: list[dict]) -> list[dict]:
    if not tools:
        return tools
    cached = list(tools)
    cached[-1] = {**cached[-1], "cache_control": _CACHE_CONTROL}
    return cached


def _with_message_cache(messages: list[dict]) -> list[dict]:
    if not messages:
        return messages
    cached = [dict(m) for m in messages]
    for i in range(len(cached) - 1, -1, -1):
        if cached[i].get("role") == "user":
            content = cached[i].get("content")
            if isinstance(content, str):
                cached[i]["content"] = [
                    {"type": "text", "text": content, "cache_control": _CACHE_CONTROL},
                ]
            elif isinstance(content, list) and content:
                last_block = {**content[-1], "cache_control": _CACHE_CONTROL}
                cached[i]["content"] = content[:-1] + [last_block]
            break
    return cached
