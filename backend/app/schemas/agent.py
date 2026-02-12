"""Agent Schemas — Pydantic models for SSE event data shapes.

Invariants:
    - SSE events have consistent type + data structure
    - Context usage always includes tokens_used, tokens_limit, usage_percentage

Design Decisions:
    - Separate from session schemas: agent events are internal to the streaming flow,
      session schemas are for the REST API boundary (ADR: responsibility separation)
"""

from pydantic import BaseModel


class ContextUsage(BaseModel):
    """Token usage stats for context window monitoring."""
    tokens_used: int
    tokens_limit: int
    tokens_remaining: int
    usage_percentage: float
    estimated_rounds_left: int


class ToolCallEvent(BaseModel):
    """SSE event for tool invocation."""
    tool: str
    input_preview: str


class ToolErrorEvent(BaseModel):
    """SSE event for tool error."""
    tool: str
    error_code: str | None
    message: str | None
