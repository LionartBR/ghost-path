"""Agent Runner Helpers tests — pure tests for SSE event builders and research detail.

Tests cover:
    - web_search_detail_from_research: SSE event from research tool result
    - Edge cases: empty sources, missing fields
"""

from app.services.agent_runner_helpers import (
    web_search_detail_from_research,
)


# -- web_search_detail_from_research ------------------------------------------

def test_research_detail_builds_event_from_sources():
    """Research result with sources → web_search_detail SSE event."""
    tool_input = {"query": "TRIZ methods", "purpose": "state_of_art"}
    tool_result = {
        "status": "ok",
        "summary": "Found methods",
        "sources": [
            {"id": 1, "url": "https://a.com", "title": "Result A", "finding": "A"},
            {"id": 2, "url": "https://b.com", "title": "Result B", "finding": "B"},
        ],
        "result_count": 2,
        "empty": False,
    }
    event = web_search_detail_from_research(tool_input, tool_result)

    assert event is not None
    assert event["type"] == "web_search_detail"
    assert event["data"]["query"] == "TRIZ methods"
    assert len(event["data"]["results"]) == 2
    assert event["data"]["results"][0]["url"] == "https://a.com"
    assert event["data"]["results"][0]["title"] == "Result A"


def test_research_detail_returns_none_for_empty_sources():
    """Empty sources → None (no SSE event emitted)."""
    tool_input = {"query": "test"}
    tool_result = {
        "status": "ok",
        "summary": "No results",
        "sources": [],
        "empty": True,
    }
    event = web_search_detail_from_research(tool_input, tool_result)
    assert event is None


def test_research_detail_returns_none_when_no_sources_key():
    """Missing sources key → None."""
    tool_input = {"query": "test"}
    tool_result = {"status": "ok", "summary": "Error"}
    event = web_search_detail_from_research(tool_input, tool_result)
    assert event is None


def test_research_detail_limits_to_five_results():
    """Max 5 results in SSE event even if more sources exist."""
    tool_input = {"query": "test"}
    tool_result = {
        "sources": [
            {"id": i, "url": f"https://{i}.com", "title": f"R{i}"}
            for i in range(10)
        ],
    }
    event = web_search_detail_from_research(tool_input, tool_result)
    assert event is not None
    assert len(event["data"]["results"]) == 5


def test_research_detail_uses_query_from_input():
    """Query comes from tool_input, not tool_result."""
    tool_input = {"query": "specific query", "purpose": "evidence_for"}
    tool_result = {
        "sources": [{"url": "https://a.com", "title": "A"}],
    }
    event = web_search_detail_from_research(tool_input, tool_result)
    assert event["data"]["query"] == "specific query"


def test_research_detail_handles_missing_url_title():
    """Sources with missing url/title default to empty string."""
    tool_input = {"query": "test"}
    tool_result = {"sources": [{"id": 1}]}
    event = web_search_detail_from_research(tool_input, tool_result)
    assert event["data"]["results"][0]["url"] == ""
    assert event["data"]["results"][0]["title"] == ""
