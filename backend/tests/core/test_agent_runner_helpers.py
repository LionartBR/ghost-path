"""Agent Runner Helpers tests — pure tests for SSE event builders and web_search extraction.

Tests cover:
    - _extract_search_results: dict-based and object-based result blocks
    - record_web_searches: web_search_detail event emission with results
    - Limit enforcement (max 5 results)
"""

from app.services.agent_runner_helpers import (
    _extract_search_results,
    record_web_searches,
)


# -- Mock helpers (lightweight, no external dependency) -----------------------

class _Block:
    """Minimal mock block for testing."""

    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class _FakeDispatch:
    """Minimal mock dispatch that records web_search calls."""

    def __init__(self):
        self.searches = []

    def record_web_search(self, query, summary):
        self.searches.append({"query": query, "summary": summary})


# -- _extract_search_results --------------------------------------------------

def test_extract_search_results_from_dict_content():
    """Extract results when content items are plain dicts."""
    block = _Block(content=[
        {"type": "web_search_result", "url": "https://a.com", "title": "A"},
        {"type": "web_search_result", "url": "https://b.com", "title": "B"},
    ])
    results = _extract_search_results(block)
    assert len(results) == 2
    assert results[0] == {"url": "https://a.com", "title": "A"}
    assert results[1] == {"url": "https://b.com", "title": "B"}


def test_extract_search_results_from_object_content():
    """Extract results when content items are SDK-like objects."""
    block = _Block(content=[
        _Block(type="web_search_result", url="https://c.com", title="C"),
    ])
    results = _extract_search_results(block)
    assert len(results) == 1
    assert results[0] == {"url": "https://c.com", "title": "C"}


def test_extract_search_results_skips_non_results():
    """Non web_search_result items are ignored."""
    block = _Block(content=[
        {"type": "text", "text": "some text"},
        {"type": "web_search_result", "url": "https://d.com", "title": "D"},
    ])
    results = _extract_search_results(block)
    assert len(results) == 1
    assert results[0]["url"] == "https://d.com"


def test_extract_search_results_max_five():
    """Only top 5 results returned even if more exist."""
    block = _Block(content=[
        {"type": "web_search_result", "url": f"https://{i}.com", "title": f"R{i}"}
        for i in range(10)
    ])
    results = _extract_search_results(block)
    assert len(results) == 5


def test_extract_search_results_empty_content():
    """Empty content list returns empty results."""
    block = _Block(content=[])
    results = _extract_search_results(block)
    assert results == []


def test_extract_search_results_no_content_attr():
    """Block without content attribute returns empty results."""
    block = _Block()
    results = _extract_search_results(block)
    assert results == []


# -- record_web_searches (emits web_search_detail) ----------------------------

def test_record_web_searches_emits_web_search_detail():
    """web_search_tool_result block → web_search_detail SSE event."""
    blocks = [
        _Block(type="server_tool_use", input={"query": "test query"}),
        _Block(type="web_search_tool_result", content=[
            {"type": "web_search_result", "url": "https://a.com", "title": "A"},
            {"type": "web_search_result", "url": "https://b.com", "title": "B"},
        ]),
    ]
    dispatch = _FakeDispatch()
    events = record_web_searches(blocks, dispatch)

    assert len(events) == 1
    assert events[0]["type"] == "web_search_detail"
    assert events[0]["data"]["query"] == "test query"
    assert len(events[0]["data"]["results"]) == 2

    # ForgeState recording still works
    assert len(dispatch.searches) == 1
    assert dispatch.searches[0]["query"] == "test query"


def test_record_web_searches_multiple_searches():
    """Multiple web_search calls in one response each emit their own event."""
    blocks = [
        _Block(type="server_tool_use", input={"query": "first"}),
        _Block(type="web_search_tool_result", content=[
            {"type": "web_search_result", "url": "https://1.com", "title": "1"},
        ]),
        _Block(type="server_tool_use", input={"query": "second"}),
        _Block(type="web_search_tool_result", content=[
            {"type": "web_search_result", "url": "https://2.com", "title": "2"},
        ]),
    ]
    dispatch = _FakeDispatch()
    events = record_web_searches(blocks, dispatch)

    assert len(events) == 2
    assert events[0]["data"]["query"] == "first"
    assert events[1]["data"]["query"] == "second"
    assert len(dispatch.searches) == 2
