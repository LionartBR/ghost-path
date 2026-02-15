"""Research Agent Tests — mock Haiku responses, verify JSON parsing and error handling.

Invariants:
    - execute() always returns a dict with summary, sources, result_count, empty
    - _parse_haiku_json handles direct JSON, markdown-wrapped, and raw text
    - API failures return empty result (never raise)
    - pause_turn handled with continuation loop

Design Decisions:
    - Mock at create_message_raw boundary (no real API calls)
    - Test _parse_haiku_json directly (pure function, no mock needed)
    - Test _build_system_prompt for each purpose (ensures prompt completeness)
"""

import pytest

from app.services.research_agent import (
    ResearchAgent,
    _parse_haiku_json,
    _build_system_prompt,
    _build_user_message,
)


# -- _parse_haiku_json (pure tests) -------------------------------------------


def test_parse_direct_json():
    """Valid JSON parsed directly."""
    raw = '{"summary": "Test", "sources": [], "result_count": 0, "empty": true}'
    result = _parse_haiku_json(raw)
    assert result["summary"] == "Test"
    assert result["empty"] is True


def test_parse_markdown_wrapped_json():
    """JSON wrapped in ```json ... ``` extracted correctly."""
    raw = '```json\n{"summary": "Wrapped", "sources": [{"id": 1}]}\n```'
    result = _parse_haiku_json(raw)
    assert result["summary"] == "Wrapped"
    assert len(result["sources"]) == 1


def test_parse_json_with_preamble():
    """JSON preceded by text still extracted."""
    raw = 'Here are the results:\n{"summary": "Found", "sources": []}'
    result = _parse_haiku_json(raw)
    assert result["summary"] == "Found"


def test_parse_invalid_json_returns_raw_text():
    """Non-JSON text returned as summary with empty sources."""
    raw = "I found some results about TRIZ methods."
    result = _parse_haiku_json(raw)
    assert "TRIZ" in result["summary"]
    assert result["sources"] == []
    assert result["empty"] is True


def test_parse_empty_string():
    """Empty string returns empty result."""
    result = _parse_haiku_json("")
    assert result["empty"] is True


# -- _build_system_prompt (pure tests) ----------------------------------------


def test_system_prompt_contains_purpose_instructions():
    """Each purpose injects specific search strategy."""
    for purpose in [
        "state_of_art", "evidence_for", "evidence_against",
        "cross_domain", "novelty_check", "falsification",
    ]:
        prompt = _build_system_prompt(purpose, 3)
        assert f'purpose="{purpose}"' in prompt
        assert "MAX 3 SOURCES" in prompt


def test_system_prompt_max_results_injected():
    """max_results appears in the prompt."""
    prompt = _build_system_prompt("state_of_art", 5)
    assert "MAX 5 SOURCES" in prompt


def test_system_prompt_unknown_purpose_falls_back():
    """Unknown purpose falls back to state_of_art instructions."""
    prompt = _build_system_prompt("unknown_purpose", 3)
    assert "CURRENT state" in prompt


# -- _build_user_message (pure tests) -----------------------------------------


def test_user_message_contains_query_and_purpose():
    msg = _build_user_message("TRIZ methods", "state_of_art", None, 3)
    assert "TRIZ methods" in msg
    assert "state_of_art" in msg
    assert "3" in msg


def test_user_message_includes_instructions_when_provided():
    msg = _build_user_message("query", "evidence_for", "Focus on AI", 3)
    assert "Focus on AI" in msg
    assert "investigator" in msg


def test_user_message_omits_instructions_when_none():
    msg = _build_user_message("query", "evidence_for", None, 3)
    assert "investigator" not in msg


# -- ResearchAgent.execute (async tests with mock) ----------------------------


class _MockBlock:
    def __init__(self, type, text=None, **kwargs):
        self.type = type
        self.text = text
        for k, v in kwargs.items():
            setattr(self, k, v)

    def model_dump(self, exclude_none=False):
        d = {"type": self.type}
        if self.text is not None:
            d["text"] = self.text
        return d


class _MockUsage:
    def __init__(self):
        self.input_tokens = 50
        self.output_tokens = 30
        self.cache_creation_input_tokens = 0
        self.cache_read_input_tokens = 0


class _MockResponse:
    def __init__(self, text, stop_reason="end_turn"):
        self.content = [_MockBlock("text", text=text)]
        self.stop_reason = stop_reason
        self.usage = _MockUsage()


class _MockClient:
    """Mock ResilientAnthropicClient for research agent tests."""

    def __init__(self, responses):
        self._responses = responses
        self._idx = 0
        self.calls = []

    async def create_message_raw(self, **kwargs):
        self.calls.append(kwargs)
        if self._idx >= len(self._responses):
            raise RuntimeError("No more mock responses")
        resp = self._responses[self._idx]
        self._idx += 1
        if isinstance(resp, Exception):
            raise resp
        return resp


@pytest.mark.asyncio
async def test_execute_returns_parsed_json():
    """Haiku returns valid JSON → parsed and returned."""
    json_text = (
        '{"summary": "TRIZ has evolved", '
        '"sources": [{"id": 1, "url": "https://example.com", '
        '"title": "TRIZ 2025", "finding": "New methods", "date": "2025"}], '
        '"result_count": 1, "empty": false}'
    )
    client = _MockClient([_MockResponse(json_text)])
    agent = ResearchAgent(client)
    result = await agent.execute("TRIZ methods", "state_of_art")

    assert result["summary"] == "TRIZ has evolved"
    assert len(result["sources"]) == 1
    assert result["sources"][0]["url"] == "https://example.com"
    assert result["empty"] is False


@pytest.mark.asyncio
async def test_execute_handles_empty_results():
    """Haiku reports no results → empty result returned."""
    json_text = (
        '{"summary": "No relevant results found.", '
        '"sources": [], "result_count": 0, "empty": true}'
    )
    client = _MockClient([_MockResponse(json_text)])
    agent = ResearchAgent(client)
    result = await agent.execute("nonexistent topic 2099", "novelty_check")

    assert result["empty"] is True
    assert result["sources"] == []


@pytest.mark.asyncio
async def test_execute_handles_api_failure():
    """API error → returns empty result, never raises."""
    client = _MockClient([RuntimeError("API down")])
    agent = ResearchAgent(client)
    result = await agent.execute("test", "state_of_art")

    assert result["empty"] is True
    assert "unavailable" in result["summary"].lower() or "retry" in result["summary"].lower()


@pytest.mark.asyncio
async def test_execute_handles_non_json_response():
    """Haiku returns plain text → treated as summary."""
    client = _MockClient([_MockResponse("TRIZ is widely used in engineering.")])
    agent = ResearchAgent(client)
    result = await agent.execute("TRIZ usage", "state_of_art")

    assert "TRIZ" in result["summary"]
    assert result["sources"] == []
    assert result["empty"] is True


@pytest.mark.asyncio
async def test_execute_handles_pause_turn():
    """pause_turn (web_search server-side) → continues loop."""
    pause_resp = _MockResponse("", stop_reason="pause_turn")
    # Pause response has no text, just server_tool_use blocks
    pause_resp.content = [_MockBlock("server_tool_use", name="web_search", input={"query": "test"})]

    final_resp = _MockResponse(
        '{"summary": "Found it", "sources": [], "result_count": 0, "empty": true}',
    )
    client = _MockClient([pause_resp, final_resp])
    agent = ResearchAgent(client)
    result = await agent.execute("test", "state_of_art")

    assert client.calls[1]  # Second call made after pause
    # The final response should be parsed
    assert result["summary"] == "Found it"


@pytest.mark.asyncio
async def test_execute_normalizes_missing_fields():
    """JSON with missing fields gets defaults filled in."""
    json_text = '{"summary": "Partial result"}'
    client = _MockClient([_MockResponse(json_text)])
    agent = ResearchAgent(client)
    result = await agent.execute("test", "state_of_art")

    assert result["summary"] == "Partial result"
    assert result["sources"] == []
    assert result["result_count"] == 0
    assert result["empty"] is True


@pytest.mark.asyncio
async def test_execute_uses_correct_model():
    """ResearchAgent uses configured model for Haiku calls."""
    json_text = '{"summary": "OK", "sources": [], "result_count": 0, "empty": true}'
    client = _MockClient([_MockResponse(json_text)])
    agent = ResearchAgent(client, model="claude-haiku-4-5-20251001")
    await agent.execute("test", "state_of_art")

    assert client.calls[0]["model"] == "claude-haiku-4-5-20251001"
    assert "web-search-2025-03-05" in client.calls[0]["betas"]


@pytest.mark.asyncio
async def test_execute_passes_instructions_in_user_message():
    """instructions from Opus appear in Haiku's user message."""
    json_text = '{"summary": "OK", "sources": [], "result_count": 0, "empty": true}'
    client = _MockClient([_MockResponse(json_text)])
    agent = ResearchAgent(client)
    await agent.execute(
        "test", "state_of_art",
        instructions="Focus on AI-augmented methods",
    )

    user_msg = client.calls[0]["messages"][0]["content"]
    assert "Focus on AI-augmented methods" in user_msg


@pytest.mark.asyncio
async def test_execute_tracks_haiku_tokens():
    """Result includes haiku_tokens from API response usage."""
    json_text = '{"summary": "OK", "sources": [], "result_count": 0, "empty": true}'
    client = _MockClient([_MockResponse(json_text)])
    agent = ResearchAgent(client)
    result = await agent.execute("test", "state_of_art")

    # MockResponse has input_tokens=50, output_tokens=30 → 80 total
    assert result["haiku_tokens"] == 80


@pytest.mark.asyncio
async def test_execute_tracks_tokens_across_pause_turns():
    """Multiple pause_turn responses → tokens summed."""
    pause_resp = _MockResponse("", stop_reason="pause_turn")
    pause_resp.content = [_MockBlock("server_tool_use", name="web_search", input={"query": "t"})]

    final_resp = _MockResponse(
        '{"summary": "OK", "sources": [], "result_count": 0, "empty": true}',
    )
    client = _MockClient([pause_resp, final_resp])
    agent = ResearchAgent(client)
    result = await agent.execute("test", "state_of_art")

    # 2 responses × 80 tokens each = 160
    assert result["haiku_tokens"] == 160
