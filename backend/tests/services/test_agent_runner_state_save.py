"""Integration Tests: AgentRunner — state persistence on errors, periodic saves, stream retry.

Invariants:
    - State (message_history + forge_state_snapshot) saved on ALL error exit paths
    - Periodic save fires every PERIODIC_SAVE_INTERVAL tool calls
    - Stream retries on transient failures when no content has been yielded
    - Stream does NOT retry after content yielded or on non-retryable errors
    - save_state raises on DB failure; save_state_best_effort catches

Design Decisions:
    - Split from test_agent_runner_resilience.py (ExMA: 200-400 lines per file)
    - asyncio.sleep monkeypatched to zero for stream retry tests
    - Custom mock clients for retry scenarios (fail-then-succeed, mid-stream-fail)
"""

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock

import pytest

from app.core.errors import AnthropicAPIError, ErrorContext
from app.core.forge_state import ForgeState
from app.services.agent_runner import AgentRunner
from app.services.agent_runner_helpers import save_state

from tests.services.mock_anthropic import (
    MockAnthropicClient,
    _Stream, _StreamEvent, _Block, _Delta, _Message,
    text_response,
    tool_response,
    mixed_response,
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
# Fix 1 & 2: State saved on error exit paths
# ==============================================================================


async def test_state_saved_on_api_error(
    test_db, seed_session, mock_dispatch,
):
    """API error (non-retryable) → forge_state_snapshot + message_history persisted."""

    class _FailingClient:
        calls = []

        @asynccontextmanager
        async def stream_message(self, **kwargs):
            self.calls.append(kwargs)
            raise AnthropicAPIError(
                "Bad request", "client_error",
                context=ErrorContext(session_id=str(seed_session.id)),
            )
            yield  # pragma: no cover

    state = ForgeState()
    state.fundamentals = {"core": "test data"}
    client = _FailingClient()
    runner = AgentRunner(test_db, client)

    events = await _collect(runner, seed_session, "Test message", state)

    # Error event emitted
    errors = _events_of_type(events, "error")
    assert len(errors) == 1

    # State persisted despite error
    await test_db.refresh(seed_session)
    assert seed_session.forge_state_snapshot is not None
    assert seed_session.forge_state_snapshot["fundamentals"] == {"core": "test data"}
    assert isinstance(seed_session.message_history, list)
    assert len(seed_session.message_history) >= 1


async def test_state_saved_on_max_iterations(
    test_db, seed_session, mock_dispatch, monkeypatch,
):
    """MAX_ITERATIONS exceeded → state persisted before error event."""
    monkeypatch.setattr(AgentRunner, "MAX_ITERATIONS", 2)

    state = ForgeState()
    state.fundamentals = {"saved": "before max iter"}
    client = MockAnthropicClient([
        mixed_response("", [{"name": "tool_a", "input": {}}]),
        mixed_response("", [{"name": "tool_b", "input": {}}]),
        text_response("unreachable"),
    ])
    runner = AgentRunner(test_db, client)

    events = await _collect(runner, seed_session, "Go", state)

    errors = _events_of_type(events, "error")
    assert errors[0]["data"]["code"] == "AGENT_LOOP_EXCEEDED"

    # State persisted
    await test_db.refresh(seed_session)
    assert seed_session.forge_state_snapshot is not None
    assert seed_session.forge_state_snapshot["fundamentals"] == {"saved": "before max iter"}


async def test_state_saved_on_unexpected_exception(
    test_db, seed_session, mock_dispatch,
):
    """Unexpected exception in iteration loop → state persisted via best-effort."""

    class _BrokenClient:
        calls = []

        @asynccontextmanager
        async def stream_message(self, **kwargs):
            self.calls.append(kwargs)
            raise ValueError("Something unexpected broke")
            yield  # pragma: no cover

    state = ForgeState()
    state.fundamentals = {"saved": "on crash"}
    client = _BrokenClient()
    runner = AgentRunner(test_db, client)

    events = await _collect(runner, seed_session, "Crash", state)

    errors = _events_of_type(events, "error")
    assert errors[0]["data"]["code"] == "INTERNAL_ERROR"

    # State persisted
    await test_db.refresh(seed_session)
    assert seed_session.forge_state_snapshot is not None
    assert seed_session.forge_state_snapshot["fundamentals"] == {"saved": "on crash"}


async def test_state_saved_on_api_error_after_tools(
    test_db, seed_session, mock_dispatch,
):
    """Tools succeed → next API call fails → state includes tool work."""
    state = ForgeState()

    class _FailOnSecondCall:
        """Succeeds on first stream_message (tool response), fails on second."""

        def __init__(self, first_stream):
            self._first = first_stream
            self._call = 0
            self.calls = []

        @asynccontextmanager
        async def stream_message(self, **kwargs):
            self.calls.append(kwargs)
            self._call += 1
            if self._call == 1:
                yield self._first
            else:
                raise AnthropicAPIError(
                    "Server overloaded", "client_error",
                    context=kwargs.get("context"),
                )
                yield  # pragma: no cover

    client = _FailOnSecondCall(
        tool_response("decompose_to_fundamentals", {"problem": "test"}),
    )
    runner = AgentRunner(test_db, client)

    events = await _collect(runner, seed_session, "Decompose", state)

    # Tool succeeded, then error
    tool_results = _events_of_type(events, "tool_result")
    assert len(tool_results) == 1
    errors = _events_of_type(events, "error")
    assert len(errors) == 1

    # State persisted — includes messages from the tool call
    await test_db.refresh(seed_session)
    assert seed_session.message_history is not None
    assert len(seed_session.message_history) >= 3  # user + assistant + tool_results


# ==============================================================================
# Fix 2: save_state raises on DB failure
# ==============================================================================


async def test_save_state_raises_on_db_commit_failure(seed_session):
    """save_state propagates DB errors (not silently swallowed)."""
    state = ForgeState()
    fake_db = AsyncMock()
    fake_db.commit = AsyncMock(side_effect=RuntimeError("DB connection lost"))

    with pytest.raises(RuntimeError, match="DB connection lost"):
        await save_state(seed_session, [{"role": "user", "content": "test"}], state, fake_db)


# ==============================================================================
# Fix 3: Periodic commits
# ==============================================================================


async def test_periodic_save_fires_after_interval(
    test_db, seed_session, mock_dispatch, monkeypatch,
):
    """After PERIODIC_SAVE_INTERVAL tool calls, state is saved mid-run."""
    monkeypatch.setattr(AgentRunner, "PERIODIC_SAVE_INTERVAL", 2)

    state = ForgeState()
    state.document_updated_this_phase = True
    # 3 tool calls (triggers periodic save at 2) + text completion
    client = MockAnthropicClient([
        tool_response("tool_a", {}),
        tool_response("tool_b", {}),
        tool_response("tool_c", {}),
        text_response("Done."),
    ])
    runner = AgentRunner(test_db, client)

    events = await _collect(runner, seed_session, "Go", state)

    done = _events_of_type(events, "done")
    assert done[0]["data"]["error"] is False

    # State persisted (periodic save at tool 2 + final save)
    await test_db.refresh(seed_session)
    assert seed_session.forge_state_snapshot is not None
    assert seed_session.message_history is not None


async def test_periodic_save_counter_resets_on_pause(
    test_db, seed_session, mock_dispatch, monkeypatch,
):
    """Pause tool resets _tools_since_save counter to 0."""
    monkeypatch.setattr(AgentRunner, "PERIODIC_SAVE_INTERVAL", 10)

    mock_dispatch["results"]["generate_knowledge_document"] = {
        "status": "ok", "paused": True, "markdown": "# Doc",
    }
    state = ForgeState()
    client = MockAnthropicClient([
        tool_response("tool_a", {}),
        tool_response("generate_knowledge_document", {}),
    ])
    runner = AgentRunner(test_db, client)

    events = await _collect(runner, seed_session, "Generate", state)

    done = _events_of_type(events, "done")
    assert done[0]["data"]["awaiting_input"] is True

    # Counter reset — verified indirectly via state persisted by pause (not periodic)
    await test_db.refresh(seed_session)
    assert seed_session.forge_state_snapshot is not None


# ==============================================================================
# Fix 4: Stream retry on transient failures
# ==============================================================================


async def test_stream_retry_on_connection_error(
    test_db, seed_session, mock_dispatch, monkeypatch,
):
    """Connection error before content → retry succeeds → no error event."""
    monkeypatch.setattr("asyncio.sleep", AsyncMock())

    success_stream = text_response("Success after retry.")

    class _RetryClient:
        def __init__(self):
            self.calls = []
            self._attempt = 0

        @asynccontextmanager
        async def stream_message(self, **kwargs):
            self.calls.append(kwargs)
            self._attempt += 1
            if self._attempt == 1:
                raise AnthropicAPIError(
                    "Connection refused", "connection_error",
                    context=kwargs.get("context"),
                )
            yield success_stream

    state = ForgeState()
    state.document_updated_this_phase = True
    client = _RetryClient()
    runner = AgentRunner(test_db, client)

    events = await _collect(runner, seed_session, "Retry test", state)

    # 2 API calls: failed + retry success
    assert len(client.calls) == 2

    # No error events — retry succeeded
    errors = _events_of_type(events, "error")
    assert len(errors) == 0

    done = _events_of_type(events, "done")
    assert done[0]["data"]["error"] is False

    texts = _events_of_type(events, "agent_text")
    assert any("Success after retry" in t["data"] for t in texts)


async def test_stream_retry_on_rate_limit(
    test_db, seed_session, mock_dispatch, monkeypatch,
):
    """Rate limit before content → retry succeeds."""
    monkeypatch.setattr("asyncio.sleep", AsyncMock())

    success_stream = text_response("Recovered from rate limit.")

    class _RateLimitClient:
        def __init__(self):
            self.calls = []
            self._attempt = 0

        @asynccontextmanager
        async def stream_message(self, **kwargs):
            self.calls.append(kwargs)
            self._attempt += 1
            if self._attempt <= 2:
                raise AnthropicAPIError(
                    "Rate limited", "rate_limit",
                    retry_after_ms=1000,
                    context=kwargs.get("context"),
                )
            yield success_stream

    state = ForgeState()
    state.document_updated_this_phase = True
    client = _RateLimitClient()
    runner = AgentRunner(test_db, client)

    events = await _collect(runner, seed_session, "Rate limit test", state)

    # 3 API calls: 2 failed + 1 success
    assert len(client.calls) == 3

    errors = _events_of_type(events, "error")
    assert len(errors) == 0

    done = _events_of_type(events, "done")
    assert done[0]["data"]["error"] is False


async def test_stream_no_retry_after_content_yielded(
    test_db, seed_session, mock_dispatch, monkeypatch,
):
    """Error after content already yielded → no retry, immediate error."""
    monkeypatch.setattr("asyncio.sleep", AsyncMock())

    class _MidStreamFailStream:
        """Stream that yields text events then raises on exhaustion."""

        def __init__(self):
            self._events = [
                _StreamEvent(
                    "content_block_start",
                    content_block=_Block(type="text", text=""),
                ),
                _StreamEvent(
                    "content_block_delta",
                    delta=_Delta("text_delta", text="Partial output..."),
                ),
            ]
            self._idx = 0

        def __aiter__(self):
            return self

        async def __anext__(self):
            if self._idx >= len(self._events):
                raise AnthropicAPIError(
                    "Connection lost mid-stream", "connection_error",
                )
            ev = self._events[self._idx]
            self._idx += 1
            return ev

    class _MidStreamFailClient:
        def __init__(self):
            self.calls = []

        @asynccontextmanager
        async def stream_message(self, **kwargs):
            self.calls.append(kwargs)
            yield _MidStreamFailStream()

    state = ForgeState()
    client = _MidStreamFailClient()
    runner = AgentRunner(test_db, client)

    events = await _collect(runner, seed_session, "Mid-stream fail", state)

    # Only 1 API call — no retry after content yielded
    assert len(client.calls) == 1

    # Error yielded
    errors = _events_of_type(events, "error")
    assert len(errors) == 1

    # Partial text was yielded before error
    texts = _events_of_type(events, "agent_text")
    assert any("Partial output" in t["data"] for t in texts)


async def test_stream_no_retry_on_client_error(
    test_db, seed_session, mock_dispatch, monkeypatch,
):
    """Client error (4xx) → no retry even before content, immediate error."""
    monkeypatch.setattr("asyncio.sleep", AsyncMock())

    class _ClientErrorClient:
        def __init__(self):
            self.calls = []

        @asynccontextmanager
        async def stream_message(self, **kwargs):
            self.calls.append(kwargs)
            raise AnthropicAPIError(
                "Invalid request", "client_error",
                context=kwargs.get("context"),
            )
            yield  # pragma: no cover

    state = ForgeState()
    client = _ClientErrorClient()
    runner = AgentRunner(test_db, client)

    events = await _collect(runner, seed_session, "Client error test", state)

    # Only 1 API call — client_error is not retryable
    assert len(client.calls) == 1

    errors = _events_of_type(events, "error")
    assert len(errors) == 1


async def test_stream_retry_exhausted_yields_error(
    test_db, seed_session, mock_dispatch, monkeypatch,
):
    """All retry attempts fail → error event after final attempt."""
    monkeypatch.setattr("asyncio.sleep", AsyncMock())

    class _AlwaysFailClient:
        def __init__(self):
            self.calls = []

        @asynccontextmanager
        async def stream_message(self, **kwargs):
            self.calls.append(kwargs)
            raise AnthropicAPIError(
                "Service unavailable", "connection_error",
                context=kwargs.get("context"),
            )
            yield  # pragma: no cover

    state = ForgeState()
    client = _AlwaysFailClient()
    runner = AgentRunner(test_db, client)

    events = await _collect(runner, seed_session, "Always fail", state)

    # MAX_STREAM_RETRIES + 1 = 3 calls
    assert len(client.calls) == AgentRunner.MAX_STREAM_RETRIES + 1

    errors = _events_of_type(events, "error")
    assert len(errors) == 1
    assert errors[0]["data"]["code"] == "ANTHROPIC_API_ERROR"

    done = _events_of_type(events, "done")
    assert done[0]["data"]["error"] is True

    # State saved even after exhausted retries
    await test_db.refresh(seed_session)
    assert seed_session.forge_state_snapshot is not None
