"""Integration Tests: AgentRunner — async agentic loop with streaming SSE.

Invariants:
    - Every run() yields at least context_usage and done events
    - Token accounting updates session.total_tokens_used cumulatively
    - message_history and forge_state_snapshot persisted on completion/pause
    - Cancellation checked at loop start AND mid-stream
    - Tool errors never crash the agent loop
    - Language enforcement limited to MAX_LANGUAGE_RETRIES

Design Decisions:
    - Mock at Anthropic boundary (MockAnthropicClient), real ForgeState, real DB
    - ToolDispatch patched via mock_dispatch fixture (avoids 7 handler instantiations)
    - Language tests use >50-char English text + Locale.PT_BR to trigger enforcement
    - Max iterations test patches MAX_ITERATIONS to 3 (avoids 50 iterations)
"""

from contextlib import asynccontextmanager

from app.core.domain_types import Locale, Phase
from app.core.errors import AnthropicAPIError, ErrorContext
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

    # SSE event for web search result
    results = _events_of_type(events, "tool_result")
    web_results = [r for r in results if isinstance(r["data"], str) and "Web search" in r["data"]]
    assert len(web_results) == 1
    assert "3 result(s)" in web_results[0]["data"]


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
# Language Enforcement
# ==============================================================================


async def test_language_retry_on_text_only_wrong_locale(
    test_db, seed_session, mock_dispatch,
):
    """PT_BR session gets English text-only → retry with corrective message."""
    state = ForgeState()
    state.locale = Locale.PT_BR
    # >50 chars of English to trigger check_response_language
    english_text = (
        "This is a comprehensive analysis of the problem that "
        "demonstrates clear English language output from the agent."
    )
    client = MockAnthropicClient([
        text_response(english_text),
        text_response("Análise completa do problema com resultados detalhados em português."),
    ])
    runner = AgentRunner(test_db, client)

    events = await _collect(runner, seed_session, "Olá", state)

    # 2 API calls: original + retry
    assert len(client.calls) == 2

    # Retry message injected as user message
    retry_msgs = client.calls[1]["messages"]
    last_user_msg = retry_msgs[-1]
    assert last_user_msg["role"] == "user"


async def test_language_nudge_on_tool_interleaved_wrong_locale(
    test_db, seed_session, mock_dispatch,
):
    """PT_BR + English text with tools → nudge injected alongside tool_results."""
    state = ForgeState()
    state.locale = Locale.PT_BR
    english_text = (
        "Let me decompose this problem into its fundamental components "
        "to understand the underlying structure of the challenge."
    )
    client = MockAnthropicClient([
        mixed_response(english_text, [
            {"name": "decompose_to_fundamentals", "input": {"p": "test"}},
        ]),
        text_response("Agora em português, a decomposição está completa com resultados."),
    ])
    runner = AgentRunner(test_db, client)

    events = await _collect(runner, seed_session, "Decompor", state)

    # 2 API calls: mixed + follow-up
    assert len(client.calls) == 2

    # Nudge text block injected in tool_results message
    second_msgs = client.calls[1]["messages"]
    last_msg = second_msgs[-1]
    assert last_msg["role"] == "user"
    # Should contain tool_results + text nudge
    content = last_msg["content"]
    assert isinstance(content, list)
    text_blocks = [b for b in content if b.get("type") == "text"]
    assert len(text_blocks) >= 1  # At least the nudge


# ==============================================================================
# Cancellation
# ==============================================================================


async def test_cancellation_before_stream(
    test_db, seed_session, mock_dispatch,
):
    """forge_state.cancelled=True before loop → cancelled message + done."""
    state = ForgeState()
    state.cancelled = True
    client = MockAnthropicClient([])
    runner = AgentRunner(test_db, client)

    events = await _collect(runner, seed_session, "Anything", state)

    texts = _events_of_type(events, "agent_text")
    assert any("cancelled" in t["data"].lower() for t in texts)

    done = _events_of_type(events, "done")
    assert len(done) == 1
    assert done[0]["data"]["error"] is False

    # No API calls made
    assert len(client.calls) == 0


async def test_cancellation_mid_stream(
    test_db, seed_session, mock_dispatch,
):
    """Cancellation during stream iteration → stops + yields cancelled."""
    state = ForgeState()

    # Custom stream that sets cancelled mid-iteration
    from tests.services.mock_anthropic import (
        _Stream, _StreamEvent, _Block, _Delta, _Message,
    )

    class _CancellingStream(_Stream):
        def __init__(self, forge_state):
            events = [
                _StreamEvent(
                    "content_block_start",
                    content_block=_Block(type="text", text=""),
                ),
                _StreamEvent(
                    "content_block_delta",
                    delta=_Delta("text_delta", text="Starting..."),
                ),
            ]
            msg = _Message(
                [_Block(type="text", text="Starting...")],
                "end_turn",
            )
            super().__init__(events, msg)
            self._fs = forge_state

        async def __anext__(self):
            result = await super().__anext__()
            # Cancel after first event
            self._fs.cancelled = True
            return result

    client = MockAnthropicClient([_CancellingStream(state)])
    runner = AgentRunner(test_db, client)

    events = await _collect(runner, seed_session, "Start", state)

    texts = _events_of_type(events, "agent_text")
    assert any("cancelled" in t["data"].lower() for t in texts)

    done = _events_of_type(events, "done")
    assert len(done) == 1
    assert done[0]["data"]["error"] is False


# ==============================================================================
# Error Handling
# ==============================================================================


async def test_anthropic_api_error_yields_error_event(
    test_db, seed_session, mock_dispatch,
):
    """TrizError from stream_message → error SSE + done(error=True)."""

    class _FailingClient:
        calls = []

        @asynccontextmanager
        async def stream_message(self, **kwargs):
            self.calls.append(kwargs)
            raise AnthropicAPIError(
                "Rate limit exceeded", "rate_limit",
                context=ErrorContext(session_id=str(seed_session.id)),
            )
            yield  # pragma: no cover

    client = _FailingClient()
    state = ForgeState()
    runner = AgentRunner(test_db, client)

    events = await _collect(runner, seed_session, "Message", state)

    errors = _events_of_type(events, "error")
    assert len(errors) == 1
    assert errors[0]["data"]["code"] == "ANTHROPIC_API_ERROR"

    done = _events_of_type(events, "done")
    assert done[0]["data"]["error"] is True


async def test_unexpected_exception_yields_internal_error(
    test_db, seed_session, mock_dispatch,
):
    """Non-TrizError exception → INTERNAL_ERROR + done(error=True)."""

    class _BrokenClient:
        calls = []

        @asynccontextmanager
        async def stream_message(self, **kwargs):
            self.calls.append(kwargs)
            raise ValueError("Something unexpected broke")
            yield  # pragma: no cover

    client = _BrokenClient()
    state = ForgeState()
    runner = AgentRunner(test_db, client)

    events = await _collect(runner, seed_session, "Message", state)

    errors = _events_of_type(events, "error")
    assert len(errors) == 1
    assert errors[0]["data"]["code"] == "INTERNAL_ERROR"
    assert errors[0]["data"]["severity"] == "critical"

    done = _events_of_type(events, "done")
    assert done[0]["data"]["error"] is True


async def test_max_iterations_exceeded(
    test_db, seed_session, mock_dispatch, monkeypatch,
):
    """MAX_ITERATIONS reached → AgentLoopExceededError + done(error=True)."""
    monkeypatch.setattr(AgentRunner, "MAX_ITERATIONS", 3)

    state = ForgeState()
    # 4 responses: loop should stop at iteration 3
    client = MockAnthropicClient([
        tool_response("tool_a", {}),
        tool_response("tool_b", {}),
        tool_response("tool_c", {}),
        text_response("Should not reach this."),
    ])
    runner = AgentRunner(test_db, client)

    events = await _collect(runner, seed_session, "Go", state)

    errors = _events_of_type(events, "error")
    assert len(errors) == 1
    assert errors[0]["data"]["code"] == "AGENT_LOOP_EXCEEDED"

    done = _events_of_type(events, "done")
    assert done[0]["data"]["error"] is True

    # Only 3 API calls (not 4)
    assert len(client.calls) == 3
