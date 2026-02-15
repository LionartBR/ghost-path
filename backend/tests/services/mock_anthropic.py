"""Mock Anthropic Client — simulates streaming API for agent_runner integration tests.

Invariants:
    - _Block supports model_dump(exclude_none) matching Anthropic SDK Pydantic models
    - MockAnthropicClient sequences responses (one per stream_message call)
    - Builder helpers produce realistic Anthropic response structures
    - _Stream supports both `async for event` and `await get_final_message()`

Design Decisions:
    - Flat mock classes (no inheritance): simple, explicit, easy to debug
    - Builders return (_Stream, _Message) pairs: events for streaming, message for post-processing
    - web_search uses server_tool_use + web_search_tool_result block pairs (Anthropic server-side pattern)
    - _Block stores raw dict for model_dump: avoids maintaining parallel attribute + dict structures
"""

from contextlib import asynccontextmanager


# -- Mock Anthropic SDK objects ------------------------------------------------


class _Block:
    """Mock content block with model_dump support (text, tool_use, server_tool_use, etc.)."""

    def __init__(self, **kwargs):
        self._data = kwargs
        for k, v in kwargs.items():
            setattr(self, k, v)

    def model_dump(self, exclude_none=False):
        d = dict(self._data)
        if exclude_none:
            d = {k: v for k, v in d.items() if v is not None}
        return d

    def __repr__(self):
        return f"_Block({self._data})"


class _Usage:
    """Mock token usage (includes prompt caching fields)."""

    def __init__(
        self, input_tokens=100, output_tokens=50,
        cache_creation_input_tokens=0, cache_read_input_tokens=0,
    ):
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.cache_creation_input_tokens = cache_creation_input_tokens
        self.cache_read_input_tokens = cache_read_input_tokens


class _Message:
    """Mock Message returned by stream.get_final_message()."""

    def __init__(
        self, content, stop_reason="end_turn", input_tokens=100, output_tokens=50,
        cache_creation=0, cache_read=0,
    ):
        self.content = content
        self.stop_reason = stop_reason
        self.usage = _Usage(
            input_tokens, output_tokens,
            cache_creation, cache_read,
        )


class _StreamEvent:
    """Mock stream delta event (content_block_start, content_block_delta)."""

    def __init__(self, type, content_block=None, delta=None):
        self.type = type
        self.content_block = content_block
        self.delta = delta


class _Delta:
    """Mock delta object for content_block_delta events."""

    def __init__(self, type, text=None):
        self.type = type
        self.text = text


class _Stream:
    """Mock async iterable stream with get_final_message()."""

    def __init__(self, events, message):
        self._events = events
        self._message = message
        self._idx = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._idx >= len(self._events):
            raise StopAsyncIteration
        ev = self._events[self._idx]
        self._idx += 1
        return ev

    async def get_final_message(self):
        return self._message


class MockAnthropicClient:
    """Replaces ResilientAnthropicClient. Sequences pre-configured responses."""

    def __init__(self, responses):
        self._responses = responses
        self._idx = 0
        self.calls = []

    @asynccontextmanager
    async def stream_message(self, **kwargs):
        self.calls.append(kwargs)
        if self._idx >= len(self._responses):
            raise RuntimeError(
                f"MockAnthropicClient: no response at index {self._idx} "
                f"(configured {len(self._responses)})",
            )
        stream = self._responses[self._idx]
        self._idx += 1
        yield stream


# -- Builder helpers -----------------------------------------------------------


def text_response(text, stop_reason="end_turn", tokens=(100, 50), cache=(0, 0)):
    """Build a text-only response stream. cache=(creation, read)."""
    text_block = _Block(type="text", text=text)
    events = [
        _StreamEvent(
            "content_block_start",
            content_block=_Block(type="text", text=""),
        ),
        _StreamEvent(
            "content_block_delta",
            delta=_Delta("text_delta", text=text),
        ),
    ]
    message = _Message(
        [text_block], stop_reason, tokens[0], tokens[1],
        cache[0], cache[1],
    )
    return _Stream(events, message)


def tool_response(name, tool_input, stop_reason="tool_use", tokens=(150, 80), cache=(0, 0)):
    """Build a single tool_use response stream. cache=(creation, read)."""
    tool_id = f"toolu_{name}_test"
    tool_block = _Block(type="tool_use", id=tool_id, name=name, input=tool_input)
    events = [
        _StreamEvent(
            "content_block_start",
            content_block=_Block(type="tool_use", id=tool_id, name=name, input={}),
        ),
    ]
    message = _Message(
        [tool_block], stop_reason, tokens[0], tokens[1],
        cache[0], cache[1],
    )
    return _Stream(events, message)


def mixed_response(text, tools, stop_reason="tool_use", tokens=(200, 120), cache=(0, 0)):
    """Build a response with text + multiple tool_use blocks. cache=(creation, read)."""
    text_block = _Block(type="text", text=text)
    events = [
        _StreamEvent(
            "content_block_start",
            content_block=_Block(type="text", text=""),
        ),
        _StreamEvent(
            "content_block_delta",
            delta=_Delta("text_delta", text=text),
        ),
    ]
    content = [text_block]
    for t in tools:
        tid = f"toolu_{t['name']}_test"
        content.append(
            _Block(type="tool_use", id=tid, name=t["name"], input=t["input"]),
        )
        events.append(
            _StreamEvent(
                "content_block_start",
                content_block=_Block(type="tool_use", id=tid, name=t["name"], input={}),
            ),
        )
    message = _Message(
        content, stop_reason, tokens[0], tokens[1],
        cache[0], cache[1],
    )
    return _Stream(events, message)


def web_search_response(query, n_results=3, tokens=(100, 300), cache=(0, 0)):
    """Build a web_search server-side tool response (pause_turn). cache=(creation, read)."""
    search_results = [
        {"type": "web_search_result", "url": f"https://example.com/{i}", "title": f"Result {i}"}
        for i in range(n_results)
    ]
    content = [
        _Block(type="server_tool_use", name="web_search", input={"query": query}),
        _Block(type="web_search_tool_result", content=search_results),
    ]
    # web_search events are server-side — no content_block_start for server_tool_use in stream
    events = [
        _StreamEvent(
            "content_block_start",
            content_block=_Block(type="server_tool_use", name="web_search", input={"query": query}),
        ),
    ]
    message = _Message(
        content, "pause_turn", tokens[0], tokens[1],
        cache[0], cache[1],
    )
    return _Stream(events, message)
