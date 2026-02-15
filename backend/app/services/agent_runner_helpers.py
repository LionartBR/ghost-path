"""Agent Runner Helpers — pure SSE event builders, stream processing, and caching.

Invariants:
    - All functions are pure (stateless, deterministic) except record_web_searches (mutates ForgeState)
    - SSE event dicts follow the TRIZ SSE protocol (type + data keys)
    - Prompt caching tags last block in each cacheable segment (system, tools, last-user-message)

Design Decisions:
    - Extracted from agent_runner.py to stay under ExMA 400-line limit per file
    - _process_stream_event returns (event_or_None, text_lstrip) — caller decides yield timing
    - Prompt caching saves ~90% input tokens (ADR: Anthropic ephemeral cache_control)
"""

from typing import Any

from app.core.domain_types import Locale
from app.core.enforce_language import check_response_language
from app.core.errors import ErrorSeverity
from app.core.forge_state import ForgeState
from app.core.forge_state_snapshot import forge_state_to_snapshot
from app.core.repository_protocols import SessionLike


# -- SSE event builders --------------------------------------------------------

def done_event(error: bool = False, awaiting_input: bool = False) -> dict:
    return {
        "type": "done",
        "data": {"error": error, "awaiting_input": awaiting_input},
    }


def tool_call_event(name: str, preview: str) -> dict:
    return {
        "type": "tool_call",
        "data": {"tool": name, "input_preview": preview},
    }


def tool_result_event(name: str, result: dict) -> dict:
    """Build SSE event for tool result or error."""
    if result.get("status") == "error":
        return {
            "type": "tool_error",
            "data": {
                "tool": name,
                "error_code": result.get("error_code"),
                "message": result.get("message"),
            },
        }
    return {
        "type": "tool_result",
        "data": {"tool": name, "result_preview": str(result)[:300]},
    }


def unexpected_error_event() -> dict:
    return {
        "type": "error",
        "data": {
            "code": "INTERNAL_ERROR",
            "message": "An unexpected error occurred",
            "severity": ErrorSeverity.CRITICAL.value,
            "recoverable": False,
        },
    }


def get_context_usage(session: SessionLike) -> dict:
    max_t = 1_000_000
    used = session.total_tokens_used
    return {
        "tokens_used": used,
        "tokens_limit": max_t,
        "tokens_remaining": max_t - used,
        "usage_percentage": round((used / max_t) * 100, 2),
        "input_tokens": session.total_input_tokens,
        "output_tokens": session.total_output_tokens,
        "cache_creation_tokens": session.total_cache_creation_tokens,
        "cache_read_tokens": session.total_cache_read_tokens,
    }


# -- Response introspection ----------------------------------------------------

def has_tool_use(response: Any) -> bool:
    return any(
        getattr(b, "type", None) == "tool_use"
        for b in response.content
    )


def serialize_content(response: Any) -> list[dict]:
    return [b.model_dump(exclude_none=True) for b in response.content]


# -- Stream event processing ---------------------------------------------------

def process_stream_event(
    event: Any, text_lstrip: bool,
) -> tuple[dict | None, bool]:
    """Process a single stream event. Returns (sse_or_None, new_text_lstrip)."""
    etype = getattr(event, "type", None)

    if etype == "content_block_start":
        return _handle_block_start(event.content_block, text_lstrip)

    if etype == "content_block_delta":
        return _handle_block_delta(event.delta, text_lstrip)

    return None, text_lstrip


def _handle_block_start(
    cb: Any, text_lstrip: bool,
) -> tuple[dict | None, bool]:
    bt = getattr(cb, "type", None)
    if bt == "text":
        return None, True
    if bt == "tool_use":
        return tool_call_event(cb.name, ""), text_lstrip
    if bt == "server_tool_use":
        q = getattr(cb, "input", {}).get("query", "")
        name = getattr(cb, "name", "web_search")
        return tool_call_event(name, q), text_lstrip
    return None, text_lstrip


def _handle_block_delta(
    delta: Any, text_lstrip: bool,
) -> tuple[dict | None, bool]:
    dt = getattr(delta, "type", None)
    if dt == "text_delta" and delta.text:
        txt = delta.text
        if text_lstrip:
            txt = txt.lstrip()
            if not txt:
                return None, True
        return {"type": "agent_text", "data": txt}, False
    return None, text_lstrip


# -- Research detail (replaces record_web_searches) ---------------------------

def web_search_detail_from_research(
    tool_input: dict, tool_result: dict,
) -> dict | None:
    """Build web_search_detail SSE event from research tool result.

    Compatible with frontend's existing web_search_detail handler.
    Returns None if result is empty or error.
    """
    sources = tool_result.get("sources", [])
    if not sources:
        return None
    query = tool_input.get("query", "unknown query")
    results = [
        {"url": s.get("url", ""), "title": s.get("title", "")}
        for s in sources[:5]
    ]
    return {
        "type": "web_search_detail",
        "data": {"query": query, "results": results},
    }


# -- Prompt Caching (ADR: 90% input token savings) ----------------------------

_CACHE = {"type": "ephemeral"}


def with_system_cache(system: str) -> list[dict]:
    return [{"type": "text", "text": system, "cache_control": _CACHE}]


def with_tools_cache(tools: list[dict]) -> list[dict]:
    if not tools:
        return tools
    cached = list(tools)
    cached[-1] = {**cached[-1], "cache_control": _CACHE}
    return cached


def with_message_cache(messages: list[dict]) -> list[dict]:
    if not messages:
        return messages
    cached = [dict(m) for m in messages]
    for i in range(len(cached) - 1, -1, -1):
        if cached[i].get("role") == "user":
            content = cached[i].get("content")
            if isinstance(content, str):
                cached[i]["content"] = [
                    {"type": "text", "text": content,
                     "cache_control": _CACHE},
                ]
            elif isinstance(content, list) and content:
                last = {**content[-1], "cache_control": _CACHE}
                cached[i]["content"] = content[:-1] + [last]
            break
    return cached


# -- Extracted from AgentRunner (ADR: ExMA ~7 methods per class) ---------------

def check_language(
    response, forge_state: ForgeState, retries: int,
    max_retries: int,
) -> tuple[str | None, str | None]:
    """Check response language. Returns (action, nudge_message)."""
    if retries >= max_retries:
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
        return "retry", lang_error["message"]
    return "nudge", lang_error["message"]


def account_tokens(session: SessionLike, response) -> None:
    """Add token usage from response to session totals.

    With prompt caching, Anthropic splits input tokens into three:
    - input_tokens: non-cached (base rate)
    - cache_creation_input_tokens: written to cache (1.25x)
    - cache_read_input_tokens: read from cache (0.1x)
    """
    usage = response.usage
    cache_create = getattr(usage, "cache_creation_input_tokens", 0) or 0
    cache_read = getattr(usage, "cache_read_input_tokens", 0) or 0
    inp = usage.input_tokens + cache_create + cache_read
    out = usage.output_tokens
    session.total_tokens_used += inp + out
    session.total_input_tokens += inp
    session.total_output_tokens += out
    session.total_cache_creation_tokens += cache_create
    session.total_cache_read_tokens += cache_read


def format_directives(directives: list[dict]) -> str:
    """Format research directives as natural language for agent."""
    parts = ["[RESEARCH DIRECTOR] The user has provided guidance:"]
    for d in directives:
        dtype = d.get("directive_type", "")
        domain = d.get("domain", "")
        if dtype == "explore_more":
            parts.append(f"- User wants MORE depth on '{domain}'")
        elif dtype == "skip_domain":
            parts.append(f"- User wants to SKIP '{domain}'")
        else:
            parts.append(f"- User directive: {dtype} on '{domain}'")
    return "\n".join(parts)


def build_messages(
    session: SessionLike, user_message: str,
) -> list[dict]:
    """Build message array from history + new user message."""
    messages = list(session.message_history or [])
    messages.append({"role": "user", "content": user_message})
    return messages


async def save_state(
    session: SessionLike, messages: list,
    forge_state: ForgeState, db,
) -> None:
    """Save message history + ForgeState snapshot. Never crashes."""
    import logging
    try:
        session.message_history = messages
        session.forge_state_snapshot = forge_state_to_snapshot(forge_state)
        await db.commit()
    except Exception as e:
        logging.getLogger(__name__).error("Failed to save state: %s", e)
