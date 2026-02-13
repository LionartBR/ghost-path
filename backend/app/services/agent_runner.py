"""Agent Runner — async agentic loop orchestrating Claude tool calls and SSE delivery.

Invariants:
    - Max 50 iterations per run (AgentLoopExceededError if exceeded)
    - Tool errors never crash the loop — _execute_tool_safe catches all exceptions
    - Phase review tools pause the loop (agent yields SSE review event + 'done')
    - web_search results are intercepted and recorded in ForgeState for gate enforcement
    - Message history saved to DB on pause for session resumption

Design Decisions:
    - Anthropic messages.create (not streaming API): SSE delivery to frontend is separate
      from Anthropic API streaming (ADR: hackathon simplicity)
    - ToolDispatch instantiated per-iteration: fresh dispatch with current DB session
    - pause_turn handling: web_search may cause Anthropic to return pause_turn,
      we continue the loop transparently (ADR: web_search integration)
"""

import asyncio
import json
import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.tool_dispatch import ToolDispatch, PAUSE_TOOLS
from app.core.forge_state import ForgeState
from app.services.tools_registry import ALL_TOOLS
from app.services.system_prompt import AGENT_SYSTEM_PROMPT
from app.infrastructure.anthropic_client import ResilientAnthropicClient
from app.core.errors import (
    TrizError, AgentLoopExceededError,
    ErrorContext, ErrorSeverity,
)

logger = logging.getLogger(__name__)


class AgentRunner:
    """Async agentic loop — yields SSE events for the TRIZ pipeline."""

    MAX_ITERATIONS = 50

    def __init__(
        self, db: AsyncSession, anthropic_client: ResilientAnthropicClient,
    ):
        self.client = anthropic_client
        self.model = "claude-opus-4-6"
        self.db = db

    async def run(
        self, session, user_message: str, forge_state: ForgeState,
    ):
        """Async generator yielding SSE events."""
        iteration = 0

        try:
            messages = self._build_messages(session, user_message)

            while iteration < self.MAX_ITERATIONS:
                iteration += 1

                # -- Call Anthropic API (with retry in client) --
                try:
                    response = await self.client.create_message(
                        model=self.model,
                        max_tokens=16384,
                        system=AGENT_SYSTEM_PROMPT,
                        tools=ALL_TOOLS,
                        messages=messages,
                        context=ErrorContext(
                            session_id=str(session.id),
                        ),
                    )
                except TrizError as e:
                    logger.error(
                        f"Anthropic API error: {e.message}",
                        extra={"session_id": str(session.id)},
                    )
                    yield e.to_sse_event()
                    yield _done_event(error=True)
                    return

                # -- Update token usage --
                try:
                    tokens = (
                        response.usage.input_tokens
                        + response.usage.output_tokens
                    )
                    session.total_tokens_used += tokens
                    await self.db.commit()
                except Exception as e:
                    logger.error(f"Failed to update token usage: {e}")

                yield {
                    "type": "context_usage",
                    "data": _get_context_usage(session),
                }

                # -- Process response blocks --
                assistant_content = []
                has_tool_use = False
                should_pause = False
                dispatch = ToolDispatch(self.db, forge_state)

                for block in response.content:
                    assistant_content.append(block)

                    if block.type == "text":
                        yield {"type": "agent_text", "data": block.text}

                    elif block.type == "tool_use":
                        has_tool_use = True
                        yield {
                            "type": "tool_call",
                            "data": {
                                "tool": block.name,
                                "input_preview": str(block.input)[:300],
                            },
                        }

                    elif block.type == "server_tool_use":
                        # web_search initiated by Anthropic
                        yield {
                            "type": "tool_call",
                            "data": {
                                "tool": block.name,
                                "input_preview": str(block.input)[:300],
                            },
                        }

                    elif block.type == "web_search_tool_result":
                        # Intercept web_search results for ForgeState tracking
                        content_list = getattr(block, "content", [])
                        result_count = sum(
                            1 for r in content_list
                            if isinstance(r, dict)
                            and r.get("type") == "web_search_result"
                        )
                        # Record in ForgeState for gate enforcement
                        query = _extract_web_search_query(assistant_content)
                        dispatch.record_web_search(
                            query, f"{result_count} result(s)",
                        )
                        yield {
                            "type": "tool_result",
                            "data": f"Web search returned {result_count} result(s)",
                        }

                # Handle pause_turn (long-running web search)
                if response.stop_reason == "pause_turn":
                    serialized = [
                        block.model_dump() for block in assistant_content
                    ]
                    messages.append({
                        "role": "assistant", "content": serialized,
                    })
                    continue

                if not has_tool_use:
                    yield _done_event(error=False)
                    return

                # -- Execute custom tools with error isolation --
                serialized = [
                    block.model_dump() for block in assistant_content
                ]
                messages.append({
                    "role": "assistant", "content": serialized,
                })
                tool_results = []

                for block in assistant_content:
                    if block.type != "tool_use":
                        continue

                    result = await self._execute_tool_safe(
                        dispatch, session, block.name, block.input,
                    )

                    # Emit appropriate SSE event based on result
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

                    # Check if this tool pauses the agent loop
                    if block.name in PAUSE_TOOLS and result.get("paused"):
                        should_pause = True

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(
                            result, ensure_ascii=False,
                        ),
                    })

                messages.append({"role": "user", "content": tool_results})

                # -- Pause for user interaction --
                if should_pause:
                    try:
                        session.message_history = messages
                        await self.db.commit()
                    except Exception as e:
                        logger.error(f"Failed to save message history: {e}")
                    yield _done_event(error=False, awaiting_input=True)
                    return

            # -- Max iterations exceeded --
            error = AgentLoopExceededError(
                self.MAX_ITERATIONS,
                ErrorContext(session_id=str(session.id)),
            )
            logger.error(
                f"Agent loop exceeded: {iteration} iterations",
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
                f"Unexpected error in agent runner: {e}",
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

    async def _execute_tool_safe(
        self, dispatch: ToolDispatch, session: object,
        tool_name: str, tool_input: dict,
    ) -> dict:
        """Execute tool with error boundary — never raises."""
        try:
            return await dispatch.execute(tool_name, session, tool_input)
        except TrizError as e:
            logger.warning(
                f"Tool error: {e.message}",
                extra={"tool_name": tool_name, "error_code": e.code},
            )
            return e.to_response()
        except Exception as e:
            logger.error(
                f"Unexpected error in tool '{tool_name}': {e}",
                exc_info=True,
            )
            return {
                "status": "error",
                "error_code": "TOOL_EXECUTION_ERROR",
                "message": f"Internal error executing {tool_name}",
            }

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


def _get_context_usage(session: object) -> dict:
    max_t = 1_000_000
    used = session.total_tokens_used
    return {
        "tokens_used": used,
        "tokens_limit": max_t,
        "tokens_remaining": max_t - used,
        "usage_percentage": round((used / max_t) * 100, 2),
    }


def _extract_web_search_query(blocks: list) -> str:
    """Extract the web_search query from the most recent server_tool_use block."""
    for block in reversed(blocks):
        if getattr(block, "type", None) == "server_tool_use":
            input_data = getattr(block, "input", {})
            return input_data.get("query", "unknown query")
    return "unknown query"
