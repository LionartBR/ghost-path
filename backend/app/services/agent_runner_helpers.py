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

from app.core.errors import ErrorSeverity


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


def get_context_usage(session: object) -> dict:
    max_t = 1_000_000
    used = session.total_tokens_used
    return {
        "tokens_used": used,
        "tokens_limit": max_t,
        "tokens_remaining": max_t - used,
        "usage_percentage": round((used / max_t) * 100, 2),
    }


# -- Response introspection ----------------------------------------------------

def has_tool_use(response) -> bool:
    return any(
        getattr(b, "type", None) == "tool_use"
        for b in response.content
    )


def serialize_content(response) -> list[dict]:
    return [b.model_dump(exclude_none=True) for b in response.content]


# -- Stream event processing ---------------------------------------------------

def process_stream_event(event, text_lstrip: bool):
    """Process a single stream event. Returns (sse_or_None, new_text_lstrip)."""
    etype = getattr(event, "type", None)

    if etype == "content_block_start":
        return _handle_block_start(event.content_block, text_lstrip)

    if etype == "content_block_delta":
        return _handle_block_delta(event.delta, text_lstrip)

    return None, text_lstrip


def _handle_block_start(cb, text_lstrip: bool):
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


def _handle_block_delta(delta, text_lstrip: bool):
    dt = getattr(delta, "type", None)
    if dt == "text_delta" and delta.text:
        txt = delta.text
        if text_lstrip:
            txt = txt.lstrip()
            if not txt:
                return None, True
        return {"type": "agent_text", "data": txt}, False
    return None, text_lstrip


# -- web_search recording -----------------------------------------------------

def record_web_searches(content_blocks: list, dispatch) -> list:
    """Record web_search in ForgeState, return SSE events."""
    events = []
    last_query = "unknown query"
    for block in content_blocks:
        btype = getattr(block, "type", None)
        if btype == "server_tool_use":
            last_query = getattr(block, "input", {}).get(
                "query", "unknown query",
            )
        elif btype == "web_search_tool_result":
            n = _count_search_results(block)
            dispatch.record_web_search(last_query, f"{n} result(s)")
            events.append({
                "type": "tool_result",
                "data": f"Web search returned {n} result(s)",
            })
    return events


def _count_search_results(block) -> int:
    content_list = getattr(block, "content", [])
    return sum(
        1 for r in content_list
        if (isinstance(r, dict) and r.get("type") == "web_search_result")
        or getattr(r, "type", None) == "web_search_result"
    )


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
