"""Context Compaction tests — pure tests for token optimization functions.

Tests cover:
    - trim_old_tool_results: replace old tool_result content with [ok]/[error:CODE]
    - compact_messages: drop middle messages, insert summary pair
    - trim_old_web_search_results: strip old web_search_tool_result to url+title
    - optimize_context: orchestrator chains all three
"""

import copy
import json

from app.core.context_compaction import (
    compact_messages,
    optimize_context,
    should_compact,
    trim_old_tool_results,
    trim_old_web_search_results,
)


# --- Helpers: build realistic Anthropic message structures --------------------

def _user_msg(text: str) -> dict:
    return {"role": "user", "content": text}


def _assistant_msg(text: str) -> dict:
    return {"role": "assistant", "content": [{"type": "text", "text": text}]}


def _tool_result_msg(tool_use_id: str, result: dict) -> dict:
    """User message containing a tool_result block (Anthropic format)."""
    return {
        "role": "user",
        "content": [
            {
                "type": "tool_result",
                "tool_use_id": tool_use_id,
                "content": json.dumps(result, ensure_ascii=False),
            },
        ],
    }


def _tool_result_msg_multi(blocks: list[tuple[str, dict]]) -> dict:
    """User message with multiple tool_result blocks."""
    return {
        "role": "user",
        "content": [
            {
                "type": "tool_result",
                "tool_use_id": tid,
                "content": json.dumps(res, ensure_ascii=False),
            }
            for tid, res in blocks
        ],
    }


def _assistant_with_web_search(text: str, ws_results: list[dict]) -> dict:
    """Assistant message with text + web_search_tool_result block."""
    return {
        "role": "assistant",
        "content": [
            {"type": "text", "text": text},
            {
                "type": "web_search_tool_result",
                "content": ws_results,
            },
        ],
    }


def _ws_result_block(
    url: str = "https://example.com",
    title: str = "Example",
    page_content: str = "Long content...",
    encrypted_content: str = "enc123",
    page_age: str = "2d",
) -> dict:
    return {
        "type": "web_search_result",
        "url": url,
        "title": title,
        "page_content": page_content,
        "encrypted_content": encrypted_content,
        "page_age": page_age,
    }


# === trim_old_tool_results ====================================================

class TestTrimOldToolResults:

    def test_preserves_tool_use_id(self):
        """tool_use_id must remain intact after trimming."""
        msgs = [
            _user_msg("problem"),
            _tool_result_msg("tu_1", {"status": "ok", "data": "big"}),
            _tool_result_msg("tu_2", {"status": "ok", "data": "big2"}),
            _tool_result_msg("tu_3", {"status": "ok", "data": "big3"}),
        ]
        result = trim_old_tool_results(msgs, preserve_last_n=1)
        for msg in result:
            if msg["role"] != "user":
                continue
            content = msg.get("content")
            if not isinstance(content, list):
                continue
            for block in content:
                if block.get("type") == "tool_result":
                    assert "tool_use_id" in block

    def test_replaces_ok_content_with_bracket(self):
        """Old tool results with status=ok become '[ok]'."""
        msgs = [
            _user_msg("problem"),
            _tool_result_msg("tu_1", {"status": "ok", "fundamentals": ["A", "B"]}),
            _tool_result_msg("tu_2", {"status": "ok", "count": 42}),
            _tool_result_msg("tu_3", {"status": "ok", "latest": True}),
        ]
        result = trim_old_tool_results(msgs, preserve_last_n=1)
        # First two tool msgs should be trimmed, last preserved
        block_1 = result[1]["content"][0]
        assert block_1["content"] == "[ok]"
        block_2 = result[2]["content"][0]
        assert block_2["content"] == "[ok]"
        # Last tool msg preserved
        block_3 = result[3]["content"][0]
        assert "latest" in block_3["content"]

    def test_replaces_error_with_code(self):
        """Old tool error results become '[error:CODE]'."""
        msgs = [
            _user_msg("problem"),
            _tool_result_msg("tu_1", {
                "status": "error", "error_code": "DECOMPOSE_INCOMPLETE",
                "message": "long explanation",
            }),
            _tool_result_msg("tu_2", {"status": "ok", "data": "ok"}),
        ]
        result = trim_old_tool_results(msgs, preserve_last_n=1)
        block = result[1]["content"][0]
        assert block["content"] == "[error:DECOMPOSE_INCOMPLETE]"

    def test_preserves_last_n_user_messages(self):
        """Last N user messages with tool_results keep full content."""
        big_result = {"status": "ok", "data": "x" * 500}
        msgs = [
            _user_msg("problem"),
            _tool_result_msg("tu_1", big_result),
            _tool_result_msg("tu_2", big_result),
            _tool_result_msg("tu_3", big_result),
        ]
        result = trim_old_tool_results(msgs, preserve_last_n=2)
        # tu_1 trimmed, tu_2 and tu_3 preserved
        assert result[1]["content"][0]["content"] == "[ok]"
        assert "x" in result[2]["content"][0]["content"]
        assert "x" in result[3]["content"][0]["content"]

    def test_noop_when_fewer_than_preserve_n(self):
        """When user msgs with tools <= preserve_n, nothing changes."""
        msgs = [
            _user_msg("problem"),
            _tool_result_msg("tu_1", {"status": "ok", "data": "big"}),
        ]
        result = trim_old_tool_results(msgs, preserve_last_n=2)
        assert result[1]["content"][0]["content"] == json.dumps(
            {"status": "ok", "data": "big"}, ensure_ascii=False,
        )

    def test_handles_malformed_json(self):
        """Non-JSON string content falls back to '[ok]'."""
        msgs = [
            _user_msg("problem"),
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": "tu_x",
                        "content": "this is not json",
                    },
                ],
            },
            _tool_result_msg("tu_2", {"status": "ok"}),
        ]
        result = trim_old_tool_results(msgs, preserve_last_n=1)
        assert result[1]["content"][0]["content"] == "[ok]"


# === compact_messages =========================================================

class TestCompactMessages:

    def test_preserves_first_and_last_n(self):
        """First user message + last N messages kept."""
        msgs = [_user_msg("problem")]
        for i in range(20):
            msgs.append(_assistant_msg(f"resp {i}"))
            msgs.append(_user_msg(f"input {i}"))
        result = compact_messages(msgs, keep_last_n=8)
        # First message preserved
        assert result[0]["content"] == "problem"
        # Last 8 preserved
        assert result[-1] == msgs[-1]
        assert result[-8] == msgs[-8]
        # Total: first(1) + summary(2) + last(8) = 11
        assert len(result) == 11

    def test_inserts_summary_pair(self):
        """Summary assistant + user pair inserted between first and last."""
        msgs = [_user_msg("problem")]
        for i in range(20):
            msgs.append(_assistant_msg(f"resp {i}"))
            msgs.append(_user_msg(f"input {i}"))
        result = compact_messages(msgs, keep_last_n=8)
        # result[1] is summary assistant, result[2] is summary user
        assert result[1]["role"] == "assistant"
        assert "__COMPACTED__" in str(result[1]["content"])
        assert result[2]["role"] == "user"

    def test_noop_when_under_threshold(self):
        """10 messages → unchanged (default threshold 20)."""
        msgs = [_user_msg("problem")]
        for i in range(4):
            msgs.append(_assistant_msg(f"resp {i}"))
            msgs.append(_user_msg(f"input {i}"))
        assert len(msgs) == 9
        result = compact_messages(msgs, keep_last_n=8)
        assert result == msgs

    def test_idempotent_with_marker(self):
        """Already compacted messages → no double summary."""
        msgs = [_user_msg("problem")]
        for i in range(20):
            msgs.append(_assistant_msg(f"resp {i}"))
            msgs.append(_user_msg(f"input {i}"))
        first_pass = compact_messages(msgs, keep_last_n=8)
        second_pass = compact_messages(first_pass, keep_last_n=8)
        assert len(second_pass) == len(first_pass)

    def test_handles_empty_list(self):
        """Empty list → empty list."""
        assert compact_messages([], keep_last_n=8) == []


# === trim_old_web_search_results ==============================================

class TestTrimOldWebSearchResults:

    def test_keeps_only_url_and_title(self):
        """Old web_search results stripped to url + title only."""
        ws = _ws_result_block(
            url="https://a.com", title="A",
            page_content="huge", encrypted_content="enc",
        )
        msgs = [
            _user_msg("problem"),
            _assistant_with_web_search("text1", [ws]),
            _assistant_with_web_search("text2", [ws]),
            _assistant_with_web_search("text3", [ws]),
        ]
        result = trim_old_web_search_results(msgs, preserve_last_n=1)
        # First two assistant msgs trimmed
        old_ws = result[1]["content"][1]["content"][0]
        assert old_ws["url"] == "https://a.com"
        assert old_ws["title"] == "A"
        assert "page_content" not in old_ws
        assert "encrypted_content" not in old_ws
        assert "page_age" not in old_ws
        # Last assistant preserved in full
        last_ws = result[3]["content"][1]["content"][0]
        assert "page_content" in last_ws

    def test_preserves_last_n_assistant_messages(self):
        """Last N assistant messages with web_search keep full content."""
        ws = _ws_result_block()
        msgs = [
            _user_msg("problem"),
            _assistant_with_web_search("t1", [ws]),
            _assistant_with_web_search("t2", [ws]),
            _assistant_with_web_search("t3", [ws]),
        ]
        result = trim_old_web_search_results(msgs, preserve_last_n=2)
        # First trimmed, last two preserved
        old = result[1]["content"][1]["content"][0]
        assert "page_content" not in old
        kept_2 = result[2]["content"][1]["content"][0]
        assert "page_content" in kept_2
        kept_3 = result[3]["content"][1]["content"][0]
        assert "page_content" in kept_3

    def test_noop_when_no_web_search(self):
        """Messages without web_search blocks → unchanged."""
        msgs = [
            _user_msg("problem"),
            _assistant_msg("text only"),
            _user_msg("more"),
        ]
        result = trim_old_web_search_results(msgs, preserve_last_n=2)
        assert result == msgs

    def test_handles_mixed_assistant_content(self):
        """Text + tool_use + web_search → only ws trimmed, others intact."""
        ws = _ws_result_block(url="https://b.com", title="B")
        msgs = [
            _user_msg("problem"),
            {
                "role": "assistant",
                "content": [
                    {"type": "text", "text": "analysis"},
                    {"type": "tool_use", "id": "tu_1", "name": "decompose",
                     "input": {"x": 1}},
                    {"type": "web_search_tool_result", "content": [ws]},
                ],
            },
            _assistant_with_web_search("last", [ws]),
        ]
        result = trim_old_web_search_results(msgs, preserve_last_n=1)
        mixed = result[1]["content"]
        # Text and tool_use untouched
        assert mixed[0] == {"type": "text", "text": "analysis"}
        assert mixed[1]["type"] == "tool_use"
        # web_search trimmed
        trimmed_ws = mixed[2]["content"][0]
        assert "page_content" not in trimmed_ws

    def test_handles_missing_url_or_title(self):
        """Search results missing url/title → keeps what exists."""
        ws = {"type": "web_search_result", "page_content": "big data"}
        msgs = [
            _user_msg("problem"),
            _assistant_with_web_search("text", [ws]),
            _assistant_with_web_search("last", [_ws_result_block()]),
        ]
        result = trim_old_web_search_results(msgs, preserve_last_n=1)
        trimmed = result[1]["content"][1]["content"][0]
        assert trimmed == {"type": "web_search_result"}


# === optimize_context =========================================================

class TestOptimizeContext:

    def test_applies_all_three(self):
        """30 msgs with tools + ws → trimmed + compacted."""
        ws = _ws_result_block()
        msgs = [_user_msg("problem")]
        for i in range(15):
            msgs.append(_assistant_with_web_search(f"resp {i}", [ws]))
            msgs.append(
                _tool_result_msg(f"tu_{i}", {"status": "ok", "big": "x" * 200}),
            )
        assert len(msgs) == 31
        result = optimize_context(
            msgs, "decompose", "en",
            compact_threshold=20, compact_keep_n=8,
        )
        # Should be compacted (fewer messages)
        assert len(result) < len(msgs)
        # Tool results should be trimmed (except last 2)
        # Web search should be trimmed (except last 2)

    def test_only_trims_when_under_threshold(self):
        """10 msgs → trim only, no compact."""
        ws = _ws_result_block()
        msgs = [
            _user_msg("problem"),
            _assistant_with_web_search("r1", [ws]),
            _tool_result_msg("tu_1", {"status": "ok", "data": "big"}),
            _assistant_with_web_search("r2", [ws]),
            _tool_result_msg("tu_2", {"status": "ok", "data": "big2"}),
            _assistant_with_web_search("r3", [ws]),
            _tool_result_msg("tu_3", {"status": "ok", "data": "big3"}),
        ]
        result = optimize_context(
            msgs, "decompose", "en",
            compact_threshold=20, compact_keep_n=8,
        )
        # Same count (no compaction), but old content trimmed
        assert len(result) == len(msgs)

    def test_preserves_tool_use_id_matching(self):
        """tool_use.id == tool_result.tool_use_id must hold after optimization."""
        msgs = [_user_msg("problem")]
        for i in range(12):
            msgs.append({
                "role": "assistant",
                "content": [
                    {"type": "tool_use", "id": f"tu_{i}", "name": "test",
                     "input": {}},
                ],
            })
            msgs.append(
                _tool_result_msg(f"tu_{i}", {"status": "ok", "i": i}),
            )
        result = optimize_context(
            msgs, "decompose", "en",
            compact_threshold=30, compact_keep_n=8,
        )
        # All tool_result blocks must still have tool_use_id
        for msg in result:
            if msg["role"] != "user":
                continue
            content = msg.get("content")
            if not isinstance(content, list):
                continue
            for block in content:
                if block.get("type") == "tool_result":
                    assert "tool_use_id" in block

    def test_returns_new_list(self):
        """Original list must not be mutated."""
        msgs = [
            _user_msg("problem"),
            _tool_result_msg("tu_1", {"status": "ok", "data": "big"}),
            _tool_result_msg("tu_2", {"status": "ok", "data": "big2"}),
            _tool_result_msg("tu_3", {"status": "ok", "data": "big3"}),
        ]
        original = copy.deepcopy(msgs)
        optimize_context(msgs, "decompose", "en")
        assert msgs == original
