"""Context Compaction — pure functions to reduce token growth in message_history.

Invariants:
    - All functions are pure (no IO, no async, no DB)
    - Returns NEW lists — never mutates input
    - tool_use_id always preserved (Anthropic API requirement)
    - __COMPACTED__ marker prevents double compaction (idempotency)

Design Decisions:
    - Static summary (not model-generated) to avoid extra API call (ADR: hackathon speed)
    - Preserve last N messages to keep agent's working memory intact
    - Three-stage pipeline: trim tools → compact → trim web_search
"""

import copy
import json


_COMPACTED_MARKER = "__COMPACTED__"


# === Public API ===============================================================

def optimize_context(
    messages: list[dict], phase: str, locale: str,
    *, preserve_tool_n: int = 2, preserve_ws_n: int = 2,
    compact_threshold: int = 20, compact_keep_n: int = 8,
) -> list[dict]:
    """Orchestrator: trim tools → compact if needed → trim web_search.

    Returns new list — original not mutated.
    """
    result = copy.deepcopy(messages)
    result = trim_old_tool_results(result, preserve_last_n=preserve_tool_n)
    if should_compact(result, max_messages=compact_threshold):
        result = compact_messages(result, keep_last_n=compact_keep_n)
    result = trim_old_web_search_results(result, preserve_last_n=preserve_ws_n)
    return result


def trim_old_tool_results(
    messages: list[dict], preserve_last_n: int = 2,
) -> list[dict]:
    """Replace old tool_result content with [ok] or [error:CODE].

    Preserves last N user messages that contain tool_result blocks.
    tool_use_id always kept (Anthropic API requirement).
    """
    tr_indices = _find_user_tool_result_indices(messages)
    if len(tr_indices) <= preserve_last_n:
        return messages

    to_trim = set(tr_indices[:-preserve_last_n])
    result = []
    for i, msg in enumerate(messages):
        if i in to_trim:
            result.append(_trim_tool_result_msg(msg))
        else:
            result.append(msg)
    return result


def trim_old_web_search_results(
    messages: list[dict], preserve_last_n: int = 2,
) -> list[dict]:
    """Strip old web_search_tool_result blocks to url+title only.

    Preserves last N assistant messages that contain web_search_tool_result.
    """
    ws_indices = _find_assistant_web_search_indices(messages)
    if len(ws_indices) <= preserve_last_n:
        return messages

    to_trim = set(ws_indices[:-preserve_last_n])
    result = []
    for i, msg in enumerate(messages):
        if i in to_trim:
            result.append(_trim_web_search_msg(msg))
        else:
            result.append(msg)
    return result


def compact_messages(
    messages: list[dict], keep_last_n: int = 8,
) -> list[dict]:
    """Drop middle messages, insert summary pair.

    Keeps: first_user + summary_pair + last_N.
    Idempotent: __COMPACTED__ marker prevents double compaction.
    """
    if not messages:
        return []

    # Already compacted or too few messages — noop
    min_needed = 1 + 2 + keep_last_n  # first + summary pair + last N
    if len(messages) <= min_needed:
        return messages
    if _already_compacted(messages):
        return messages

    first = messages[0]
    last_n = messages[-keep_last_n:]
    dropped = len(messages) - 1 - keep_last_n

    summary_assistant = {
        "role": "assistant",
        "content": [
            {
                "type": "text",
                "text": (
                    f"[{_COMPACTED_MARKER}] Prior {dropped} messages"
                    " compacted. Key context preserved in recent messages."
                ),
            },
        ],
    }
    summary_user = {
        "role": "user",
        "content": "Acknowledged. Continue with the current task.",
    }
    return [first, summary_assistant, summary_user] + last_n


def should_compact(messages: list[dict], *, max_messages: int = 20) -> bool:
    """Pure threshold check on message count."""
    return len(messages) > max_messages


# === Private helpers ==========================================================

def _find_user_tool_result_indices(messages: list[dict]) -> list[int]:
    """Return indices of user messages containing tool_result blocks."""
    indices = []
    for i, msg in enumerate(messages):
        if msg.get("role") != "user":
            continue
        content = msg.get("content")
        if not isinstance(content, list):
            continue
        if any(b.get("type") == "tool_result" for b in content):
            indices.append(i)
    return indices


def _find_assistant_web_search_indices(messages: list[dict]) -> list[int]:
    """Return indices of assistant messages containing web_search_tool_result."""
    indices = []
    for i, msg in enumerate(messages):
        if msg.get("role") != "assistant":
            continue
        content = msg.get("content")
        if not isinstance(content, list):
            continue
        if any(b.get("type") == "web_search_tool_result" for b in content):
            indices.append(i)
    return indices


def _trim_tool_result_msg(msg: dict) -> dict:
    """Replace tool_result content with compact status. Preserves tool_use_id."""
    content = msg.get("content")
    if not isinstance(content, list):
        return msg

    new_content = []
    for block in content:
        if block.get("type") == "tool_result":
            new_content.append({
                "type": "tool_result",
                "tool_use_id": block["tool_use_id"],
                "content": _extract_status(block.get("content", "")),
            })
        else:
            new_content.append(block)
    return {**msg, "content": new_content}


def _trim_web_search_msg(msg: dict) -> dict:
    """Strip web_search_tool_result blocks to url+title only."""
    content = msg.get("content")
    if not isinstance(content, list):
        return msg

    new_content = []
    for block in content:
        if block.get("type") == "web_search_tool_result":
            new_content.append({
                "type": "web_search_tool_result",
                "content": [
                    _trim_search_result(r) for r in block.get("content", [])
                ],
            })
        else:
            new_content.append(block)
    return {**msg, "content": new_content}


def _extract_status(content_str: str) -> str:
    """Parse tool_result JSON content and return compact status string.

    Returns:
        '[ok]' for successful results
        '[error:CODE]' for error results
        '[ok]' as fallback for non-JSON content
    """
    try:
        parsed = json.loads(content_str)
    except (json.JSONDecodeError, TypeError):
        return "[ok]"

    if isinstance(parsed, dict) and parsed.get("status") == "error":
        code = parsed.get("error_code", "UNKNOWN")
        return f"[error:{code}]"
    return "[ok]"


def _trim_search_result(result: dict) -> dict:
    """Keep only type + url + title from a web_search_result."""
    trimmed: dict[str, str] = {"type": "web_search_result"}
    if "url" in result:
        trimmed["url"] = result["url"]
    if "title" in result:
        trimmed["title"] = result["title"]
    return trimmed


def _already_compacted(messages: list[dict]) -> bool:
    """Check if messages already contain the compaction marker."""
    for msg in messages:
        content = msg.get("content")
        if isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and _COMPACTED_MARKER in block.get("text", ""):
                    return True
        elif isinstance(content, str) and _COMPACTED_MARKER in content:
            return True
    return False
