"""Tool Dispatch — tests for explicit tool routing.

Tests cover:
    - Known tools route to correct handler
    - Unknown tools return UNKNOWN_TOOL error
    - All 17 tools are registered
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.core.session_state import SessionState
from app.core.domain_types import AnalysisGate
from app.services.tool_dispatch import ToolDispatch


def _make_mock_db():
    """Create a mock AsyncSession with required methods."""
    db = AsyncMock()
    db.commit = AsyncMock()
    db.flush = AsyncMock()
    db.add = MagicMock()
    db.execute = AsyncMock()
    db.rollback = AsyncMock()
    return db


def _make_mock_session():
    """Create a mock session object."""
    session = MagicMock()
    session.id = "test-session-id"
    session.total_tokens_used = 0
    session.rounds = []
    session.message_history = []
    session.status = "active"
    return session


@pytest.mark.asyncio
async def test_dispatch_returns_error_for_unknown_tool():
    state = SessionState()
    db = _make_mock_db()
    dispatch = ToolDispatch(db, state)
    result = await dispatch.execute("nonexistent_tool", _make_mock_session(), {})
    assert result["error_code"] == "UNKNOWN_TOOL"


@pytest.mark.asyncio
async def test_dispatch_routes_to_decompose_problem():
    state = SessionState()
    db = _make_mock_db()
    dispatch = ToolDispatch(db, state)
    result = await dispatch.execute(
        "decompose_problem",
        _make_mock_session(),
        {"problem_statement": "test", "dimensions": ["a"]},
    )
    assert result["status"] == "ok"
    assert AnalysisGate.DECOMPOSE in state.completed_gates


@pytest.mark.asyncio
async def test_dispatch_routes_to_get_context_usage():
    state = SessionState()
    db = _make_mock_db()
    dispatch = ToolDispatch(db, state)
    session = _make_mock_session()
    result = await dispatch.execute("get_context_usage", session, {})
    assert result["status"] == "ok"
    assert "tokens_used" in result


@pytest.mark.asyncio
async def test_dispatch_has_all_17_tools():
    state = SessionState()
    db = _make_mock_db()
    dispatch = ToolDispatch(db, state)
    expected_tools = [
        "decompose_problem", "map_conventional_approaches",
        "extract_hidden_axioms",
        "generate_premise", "mutate_premise", "cross_pollinate",
        "challenge_axiom", "import_foreign_domain",
        "obviousness_test", "invert_problem",
        "ask_user", "present_round", "generate_final_spec",
        "store_premise", "query_premises",
        "get_negative_context", "get_context_usage",
    ]
    for tool in expected_tools:
        assert tool in dispatch._handlers, f"Missing tool: {tool}"
    assert len(dispatch._handlers) == 17


@pytest.mark.asyncio
async def test_generate_premise_returns_error_when_gates_not_satisfied():
    state = SessionState()
    db = _make_mock_db()
    dispatch = ToolDispatch(db, state)
    result = await dispatch.execute(
        "generate_premise",
        _make_mock_session(),
        {"title": "X", "body": "Y", "premise_type": "initial"},
    )
    assert result["status"] == "error"
    assert result["error_code"] == "GATES_NOT_SATISFIED"
