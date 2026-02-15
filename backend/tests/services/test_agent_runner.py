"""Integration Tests: AgentRunner — core flows, web_search, and state persistence.

Invariants:
    - Every run() yields at least context_usage and done events
    - Token accounting updates session.total_tokens_used cumulatively
    - message_history and forge_state_snapshot persisted on completion/pause
    - Tool errors never crash the agent loop
    - web_search results intercepted and recorded in ForgeState

Design Decisions:
    - Mock at Anthropic boundary (MockAnthropicClient), real ForgeState, real DB
    - ToolDispatch patched via mock_dispatch fixture (avoids 7 handler instantiations)
    - Resilience tests (language, cancellation, errors) split to test_agent_runner_resilience.py
"""

from app.core.forge_state import ForgeState
from app.services.agent_runner import AgentRunner

from tests.services.mock_anthropic import (
    MockAnthropicClient,
    text_response,
    tool_response,
    mixed_response,
    web_search_response,
)


# -- Helpers -------------------------------------------------------------------

async def _collect(runner, session, message, forge_state):
    """Collect all SSE events from an agent run."""
    events = []
    async for ev in runner.run(session, message, forge_state):
        events.append(ev)
    return events


def _events_of_type(events, t):
    return [e for e in events if e["type"] == t]


# ==============================================================================
# Core Flows
# ==============================================================================


async def test_text_response_yields_agent_text_and_done(
    test_db, seed_session, mock_dispatch,
):
    """Text-only end_turn → agent_text + context_usage + done(error=False)."""
    state = ForgeState()
    client = MockAnthropicClient([text_response("Analysis complete.")])
    runner = AgentRunner(test_db, client)

    events = await _collect(runner, seed_session, "Hello", state)

    texts = _events_of_type(events, "agent_text")
    assert len(texts) >= 1
    assert "Analysis complete." in texts[0]["data"]

    ctx = _events_of_type(events, "context_usage")
    assert len(ctx) == 1
    assert ctx[0]["data"]["tokens_used"] == 150  # 100 + 50

    done = _events_of_type(events, "done")
    assert len(done) == 1
    assert done[0]["data"]["error"] is False
    assert done[0]["data"]["awaiting_input"] is False


async def test_tool_call_executes_and_loops(
    test_db, seed_session, mock_dispatch,
):
    """Tool use → dispatch.execute → loop continues → end_turn."""
    state = ForgeState()
    client = MockAnthropicClient([
        tool_response("decompose_to_fundamentals", {"problem": "test"}),
        text_response("Done decomposing."),
    ])
    runner = AgentRunner(test_db, client)

    events = await _collect(runner, seed_session, "Decompose", state)

    # Tool events
    tool_calls = _events_of_type(events, "tool_call")
    assert len(tool_calls) == 1
    assert tool_calls[0]["data"]["tool"] == "decompose_to_fundamentals"

    tool_results = _events_of_type(events, "tool_result")
    assert len(tool_results) == 1

    # Dispatch was called
    assert len(mock_dispatch["log"]) == 1
    assert mock_dispatch["log"][0]["tool"] == "decompose_to_fundamentals"

    # 2 API calls: tool_use + end_turn
    assert len(client.calls) == 2

    # Final done
    done = _events_of_type(events, "done")
    assert done[0]["data"]["error"] is False


async def test_tool_error_yields_tool_error_and_continues(
    test_db, seed_session, mock_dispatch,
):
    """Tool returns error dict → tool_error SSE → loop continues."""
    mock_dispatch["results"]["extract_assumptions"] = {
        "status": "error",
        "error_code": "DECOMPOSE_INCOMPLETE",
        "message": "Missing fundamentals",
    }
    state = ForgeState()
    client = MockAnthropicClient([
        tool_response("extract_assumptions", {}),
        text_response("I see the error, let me fix it."),
    ])
    runner = AgentRunner(test_db, client)

    events = await _collect(runner, seed_session, "Extract", state)

    errors = _events_of_type(events, "tool_error")
    assert len(errors) == 1
    assert errors[0]["data"]["tool"] == "extract_assumptions"
    assert errors[0]["data"]["error_code"] == "DECOMPOSE_INCOMPLETE"

    # Loop continued — got done without error
    done = _events_of_type(events, "done")
    assert done[0]["data"]["error"] is False


async def test_multiple_tools_in_single_response(
    test_db, seed_session, mock_dispatch,
):
    """3 tool_use blocks in one response → all executed, all events emitted."""
    state = ForgeState()
    client = MockAnthropicClient([
        mixed_response("Running tools:", [
            {"name": "tool_a", "input": {"x": 1}},
            {"name": "tool_b", "input": {"y": 2}},
            {"name": "tool_c", "input": {"z": 3}},
        ]),
        text_response("All tools done."),
    ])
    runner = AgentRunner(test_db, client)

    events = await _collect(runner, seed_session, "Go", state)

    tool_calls = _events_of_type(events, "tool_call")
    assert len(tool_calls) >= 3  # text block_start + 3 tool block_starts

    tool_results = _events_of_type(events, "tool_result")
    assert len(tool_results) == 3

    assert len(mock_dispatch["log"]) == 3
    assert [d["tool"] for d in mock_dispatch["log"]] == [
        "tool_a", "tool_b", "tool_c",
    ]


async def test_pause_tool_saves_state_and_awaits_input(
    test_db, seed_session, mock_dispatch,
):
    """generate_knowledge_document returns paused=True → done(awaiting_input=True)."""
    mock_dispatch["results"]["generate_knowledge_document"] = {
        "status": "ok",
        "paused": True,
        "markdown": "# Knowledge Document",
    }
    state = ForgeState()
    client = MockAnthropicClient([
        tool_response("generate_knowledge_document", {}),
    ])
    runner = AgentRunner(test_db, client)

    events = await _collect(runner, seed_session, "Generate", state)

    done = _events_of_type(events, "done")
    assert len(done) == 1
    assert done[0]["data"]["awaiting_input"] is True
    assert done[0]["data"]["error"] is False

    # State persisted
    await test_db.refresh(seed_session)
    assert seed_session.message_history is not None
    assert len(seed_session.message_history) > 0
    assert seed_session.forge_state_snapshot is not None


# ==============================================================================
# web_search & pause_turn
# ==============================================================================


async def test_web_search_recorded_in_forge_state(
    test_db, seed_session, mock_dispatch,
):
    """web_search interception records in ForgeState + yields tool_result SSE."""
    state = ForgeState()
    client = MockAnthropicClient([
        web_search_response("quantum computing 2026", n_results=3),
        text_response("Research complete."),
    ])
    runner = AgentRunner(test_db, client)

    events = await _collect(runner, seed_session, "Research", state)

    # ForgeState updated
    assert len(state.web_searches_this_phase) == 1
    assert state.web_searches_this_phase[0]["query"] == "quantum computing 2026"

    # SSE event for web search result (web_search_detail with rich data)
    detail = _events_of_type(events, "web_search_detail")
    assert len(detail) == 1
    assert detail[0]["data"]["query"] == "quantum computing 2026"
    assert len(detail[0]["data"]["results"]) == 3


async def test_pause_turn_serializes_and_continues_loop(
    test_db, seed_session, mock_dispatch,
):
    """stop_reason=pause_turn → serialize → continue loop → end_turn."""
    state = ForgeState()
    client = MockAnthropicClient([
        web_search_response("test query", n_results=2),
        text_response("Search done."),
    ])
    runner = AgentRunner(test_db, client)

    events = await _collect(runner, seed_session, "Search", state)

    # 2 API calls (pause_turn + end_turn)
    assert len(client.calls) == 2

    # Final done
    done = _events_of_type(events, "done")
    assert done[0]["data"]["error"] is False


# ==============================================================================
# Token Accounting & State Persistence
# ==============================================================================


async def test_token_accounting_cumulative_across_iterations(
    test_db, seed_session, mock_dispatch,
):
    """Tokens accumulated across multiple API calls."""
    state = ForgeState()
    client = MockAnthropicClient([
        tool_response("tool_a", {}, tokens=(100, 50)),  # 150
        tool_response("tool_b", {}, tokens=(200, 75)),  # 275
        text_response("Done.", tokens=(80, 20)),  # 100
    ])
    runner = AgentRunner(test_db, client)

    events = await _collect(runner, seed_session, "Go", state)

    ctx_events = _events_of_type(events, "context_usage")
    assert len(ctx_events) == 3

    await test_db.refresh(seed_session)
    assert seed_session.total_tokens_used == 150 + 275 + 100
    assert seed_session.total_input_tokens == 100 + 200 + 80
    assert seed_session.total_output_tokens == 50 + 75 + 20

    # context_usage events include directional counters
    last_ctx = ctx_events[-1]["data"]
    assert last_ctx["input_tokens"] == 100 + 200 + 80
    assert last_ctx["output_tokens"] == 50 + 75 + 20


async def test_state_persisted_on_normal_completion(
    test_db, seed_session, mock_dispatch,
):
    """message_history + forge_state_snapshot saved on end_turn.

    Note: for text-only end_turn, agent_runner saves before appending
    assistant response (line 186-188). History contains user messages only.
    """
    state = ForgeState()
    client = MockAnthropicClient([text_response("Hello.")])
    runner = AgentRunner(test_db, client)

    await _collect(runner, seed_session, "Hi", state)

    await test_db.refresh(seed_session)
    assert isinstance(seed_session.message_history, list)
    assert len(seed_session.message_history) >= 1  # at least the user message
    assert seed_session.message_history[0]["role"] == "user"
    assert isinstance(seed_session.forge_state_snapshot, dict)


async def test_message_history_built_from_existing_plus_new(
    test_db, seed_session, mock_dispatch,
):
    """Pre-existing message_history is preserved, new message appended."""
    seed_session.message_history = [
        {"role": "user", "content": "Previous message"},
        {"role": "assistant", "content": [{"type": "text", "text": "Previous response"}]},
    ]
    await test_db.commit()

    state = ForgeState()
    client = MockAnthropicClient([text_response("New response.")])
    runner = AgentRunner(test_db, client)

    await _collect(runner, seed_session, "New message", state)

    # Verify first API call included existing history + new message
    # Note: _with_message_cache wraps last user content with cache_control
    msgs = client.calls[0]["messages"]
    assert msgs[0]["role"] == "user"
    assert msgs[0]["content"] == "Previous message"
    assert msgs[1]["role"] == "assistant"
    assert msgs[2]["role"] == "user"
    # Last user message wrapped by _with_message_cache into list with cache_control
    last_content = msgs[2]["content"]
    if isinstance(last_content, list):
        assert any(b.get("text") == "New message" for b in last_content)
    else:
        assert last_content == "New message"


# ==============================================================================
# Research Directives
# ==============================================================================


async def test_research_directives_injected_between_iterations(
    test_db, seed_session, mock_dispatch,
):
    """Directives queued in ForgeState are appended to tool_results message."""
    state = ForgeState()
    # Pre-queue a directive (simulates user clicking "Explore More" during stream)
    state.add_research_directive("explore_more", "biology TRIZ", "biology")
    client = MockAnthropicClient([
        tool_response("decompose_to_fundamentals", {"problem": "test"}),
        text_response("Done."),
    ])
    runner = AgentRunner(test_db, client)

    await _collect(runner, seed_session, "Decompose", state)

    # Second API call should include directive in the user message
    second_call_msgs = client.calls[1]["messages"]
    last_user_msg = [m for m in second_call_msgs if m["role"] == "user"][-1]
    content = last_user_msg["content"]
    # Content is a list (tool_results + directive text)
    directive_texts = [
        b for b in content
        if isinstance(b, dict) and b.get("type") == "text"
        and "RESEARCH DIRECTOR" in b.get("text", "")
    ]
    assert len(directive_texts) == 1
    assert "MORE depth on 'biology'" in directive_texts[0]["text"]
    # Directive consumed — no longer in ForgeState
    assert state.research_directives == []


async def test_research_directives_not_injected_when_empty(
    test_db, seed_session, mock_dispatch,
):
    """No directive text appended when ForgeState has no pending directives."""
    state = ForgeState()
    client = MockAnthropicClient([
        tool_response("decompose_to_fundamentals", {"problem": "test"}),
        text_response("Done."),
    ])
    runner = AgentRunner(test_db, client)

    await _collect(runner, seed_session, "Decompose", state)

    second_call_msgs = client.calls[1]["messages"]
    last_user_msg = [m for m in second_call_msgs if m["role"] == "user"][-1]
    content = last_user_msg["content"]
    directive_texts = [
        b for b in content
        if isinstance(b, dict) and b.get("type") == "text"
        and "RESEARCH DIRECTOR" in b.get("text", "")
    ]
    assert len(directive_texts) == 0


async def test_format_directives_skip_domain(
    test_db, seed_session, mock_dispatch,
):
    """Skip directive formatted correctly."""
    runner = AgentRunner(test_db, MockAnthropicClient([]))
    text = runner._format_directives([
        {"directive_type": "skip_domain", "query": "skip", "domain": "cooking"},
    ])
    assert "SKIP 'cooking'" in text


async def test_web_search_detail_event_emitted(
    test_db, seed_session, mock_dispatch,
):
    """web_search response emits web_search_detail SSE with results."""
    state = ForgeState()
    client = MockAnthropicClient([
        web_search_response("quantum computing 2026", n_results=3),
        text_response("Research complete."),
    ])
    runner = AgentRunner(test_db, client)

    events = await _collect(runner, seed_session, "Research", state)

    detail_events = _events_of_type(events, "web_search_detail")
    assert len(detail_events) == 1
    assert detail_events[0]["data"]["query"] == "quantum computing 2026"
    assert len(detail_events[0]["data"]["results"]) == 3
    assert detail_events[0]["data"]["results"][0]["url"] == "https://example.com/0"
