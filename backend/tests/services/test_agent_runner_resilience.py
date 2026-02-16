"""Integration Tests: AgentRunner — resilience, language enforcement, and error handling.

Invariants:
    - Language enforcement retries text-only wrong-locale responses (max retries)
    - Language enforcement nudges tool-interleaved wrong-locale responses
    - Cancellation (pre-stream and mid-stream) yields cancelled text + done
    - TrizError yields typed error SSE + done(error=True)
    - Unexpected exceptions yield INTERNAL_ERROR + done(error=True)
    - MAX_ITERATIONS exceeded yields AGENT_LOOP_EXCEEDED + done(error=True)

Design Decisions:
    - Split from test_agent_runner.py (ExMA: 200-400 lines per file)
    - Covers edge cases and failure modes; core happy-path tests live in test_agent_runner.py
"""

from contextlib import asynccontextmanager

from app.core.domain_types import Locale
from app.core.errors import AnthropicAPIError, ErrorContext
from app.core.forge_state import ForgeState
from app.services.agent_runner import AgentRunner

from tests.services.mock_anthropic import (
    MockAnthropicClient,
    text_response,
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
# Language Enforcement
# ==============================================================================


async def test_language_retry_on_text_only_wrong_locale(
    test_db, seed_session, mock_dispatch,
):
    """PT_BR session gets French text-only → retry with corrective message."""
    state = ForgeState()
    state.locale = Locale.PT_BR
    state.document_updated_this_phase = True  # bypass document gate
    # >50 chars of French (not English, not Portuguese) to trigger mismatch
    french_text = (
        "Le developpement de l'intelligence artificielle a fondamentalement "
        "change notre approche de la resolution de problemes complexes."
    )
    client = MockAnthropicClient([
        text_response(french_text),
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
    """PT_BR + French text with tools → nudge injected alongside tool_results."""
    state = ForgeState()
    state.locale = Locale.PT_BR
    state.document_updated_this_phase = True  # bypass document gate
    french_text = (
        "Je vais decomposer ce probleme en composants fondamentaux "
        "pour comprendre la structure sous-jacente de ce defi complexe."
    )
    client = MockAnthropicClient([
        mixed_response(french_text, [
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
                "Bad request", "client_error",  # non-retryable
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
        mixed_response("", [{"name": "tool_a", "input": {}}]),
        mixed_response("", [{"name": "tool_b", "input": {}}]),
        mixed_response("", [{"name": "tool_c", "input": {}}]),
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


# ==============================================================================
# Malformed Model Output (ValueError from Anthropic SDK)
# ==============================================================================


async def test_malformed_json_retried_then_succeeds(
    test_db, seed_session, mock_dispatch,
):
    """SDK ValueError on first attempt → retry → success on second."""
    from tests.services.mock_anthropic import _Stream, _Message, _Block

    class _MalformedStream(_Stream):
        """Stream that raises ValueError simulating SDK JSON parse failure."""

        def __init__(self):
            super().__init__([], _Message([], "end_turn"))

        async def __anext__(self):
            raise ValueError(
                "Unable to parse tool parameter JSON from model. "
                "Error: control character found. JSON: {\"phase\": \"synthesize\""
            )

    state = ForgeState()
    state.document_updated_this_phase = True

    class _RetryClient:
        """First call yields malformed stream, second call succeeds."""

        def __init__(self):
            self.calls = []
            self._idx = 0

        @asynccontextmanager
        async def stream_message(self, **kwargs):
            self.calls.append(kwargs)
            self._idx += 1
            if self._idx == 1:
                yield _MalformedStream()
            else:
                yield text_response("Recovered after retry.")

    client = _RetryClient()
    runner = AgentRunner(test_db, client)

    events = await _collect(runner, seed_session, "Go", state)

    # 2 API calls: failed + retry
    assert len(client.calls) == 2

    texts = _events_of_type(events, "agent_text")
    assert any("Recovered" in t["data"] for t in texts)

    done = _events_of_type(events, "done")
    assert done[0]["data"]["error"] is False


async def test_malformed_json_exhausts_retries(
    test_db, seed_session, mock_dispatch,
):
    """SDK ValueError on all attempts → MALFORMED_MODEL_OUTPUT + done(error=True)."""
    from tests.services.mock_anthropic import _Stream, _Message

    class _AlwaysMalformedStream(_Stream):
        def __init__(self):
            super().__init__([], _Message([], "end_turn"))

        async def __anext__(self):
            raise ValueError(
                "Unable to parse tool parameter JSON from model. "
                "Error: control character found."
            )

    state = ForgeState()

    class _AlwaysFailClient:
        def __init__(self):
            self.calls = []

        @asynccontextmanager
        async def stream_message(self, **kwargs):
            self.calls.append(kwargs)
            yield _AlwaysMalformedStream()

    client = _AlwaysFailClient()
    runner = AgentRunner(test_db, client)

    events = await _collect(runner, seed_session, "Go", state)

    # MAX_STREAM_RETRIES + 1 = 3 attempts
    assert len(client.calls) == 3

    errors = _events_of_type(events, "error")
    assert len(errors) == 1
    assert errors[0]["data"]["code"] == "MALFORMED_MODEL_OUTPUT"
    assert errors[0]["data"]["recoverable"] is True

    done = _events_of_type(events, "done")
    assert done[0]["data"]["error"] is True


async def test_non_sdk_valueerror_still_bubbles_up(
    test_db, seed_session, mock_dispatch,
):
    """ValueError NOT from SDK JSON parse → bubbles to outer handler as INTERNAL_ERROR."""
    from tests.services.mock_anthropic import _Stream, _Message

    class _OtherValueErrorStream(_Stream):
        def __init__(self):
            super().__init__([], _Message([], "end_turn"))

        async def __anext__(self):
            raise ValueError("Something completely different broke")

    state = ForgeState()

    class _OtherFailClient:
        def __init__(self):
            self.calls = []

        @asynccontextmanager
        async def stream_message(self, **kwargs):
            self.calls.append(kwargs)
            yield _OtherValueErrorStream()

    client = _OtherFailClient()
    runner = AgentRunner(test_db, client)

    events = await _collect(runner, seed_session, "Go", state)

    # Bubbles to outer exception handler → INTERNAL_ERROR
    errors = _events_of_type(events, "error")
    assert len(errors) == 1
    assert errors[0]["data"]["code"] == "INTERNAL_ERROR"

    done = _events_of_type(events, "done")
    assert done[0]["data"]["error"] is True
