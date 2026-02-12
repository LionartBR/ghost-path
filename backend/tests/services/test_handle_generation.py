"""Generation Handlers — tests for gate-checked premise creation.

Tests cover:
    - generate_premise returns error when gates not satisfied
    - generate_premise succeeds after all gates
    - Buffer fills correctly across 3 calls
    - Buffer rejects 4th premise
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.core.session_state import SessionState
from app.core.domain_types import AnalysisGate
from app.services.handle_generation import GenerationHandlers


def _make_mock_db():
    db = AsyncMock()
    return db


def _make_mock_session():
    session = MagicMock()
    session.id = "test-session-id"
    return session


def _make_satisfied_state() -> SessionState:
    state = SessionState()
    state.completed_gates = {
        AnalysisGate.DECOMPOSE,
        AnalysisGate.CONVENTIONAL,
        AnalysisGate.AXIOMS,
    }
    return state


@pytest.mark.asyncio
async def test_generate_premise_returns_error_when_gates_not_satisfied():
    state = SessionState()
    handlers = GenerationHandlers(_make_mock_db(), state)
    result = await handlers.generate_premise(
        _make_mock_session(),
        {"title": "X", "body": "Y", "premise_type": "initial"},
    )
    assert result["status"] == "error"
    assert result["error_code"] == "GATES_NOT_SATISFIED"


@pytest.mark.asyncio
async def test_generate_premise_succeeds_with_all_gates():
    state = _make_satisfied_state()
    handlers = GenerationHandlers(_make_mock_db(), state)
    result = await handlers.generate_premise(
        _make_mock_session(),
        {"title": "X", "body": "Y", "premise_type": "initial"},
    )
    assert result["status"] == "ok"
    assert result["premise_index"] == 0
    assert result["premises_in_buffer"] == 1
    assert result["premises_remaining"] == 2


@pytest.mark.asyncio
async def test_buffer_fills_correctly_across_3_calls():
    state = _make_satisfied_state()
    handlers = GenerationHandlers(_make_mock_db(), state)
    session = _make_mock_session()

    for i in range(3):
        result = await handlers.generate_premise(
            session,
            {"title": f"P{i}", "body": "Body", "premise_type": "initial"},
        )
        assert result["status"] == "ok"
        assert result["premise_index"] == i
        assert result["premises_in_buffer"] == i + 1

    assert state.premises_in_buffer == 3
    assert state.premises_remaining == 0


@pytest.mark.asyncio
async def test_buffer_rejects_4th_premise():
    state = _make_satisfied_state()
    handlers = GenerationHandlers(_make_mock_db(), state)
    session = _make_mock_session()

    for i in range(3):
        await handlers.generate_premise(
            session,
            {"title": f"P{i}", "body": "Body", "premise_type": "initial"},
        )

    result = await handlers.generate_premise(
        session,
        {"title": "P3", "body": "Body", "premise_type": "initial"},
    )
    assert result["status"] == "error"
    assert result["error_code"] == "ROUND_BUFFER_FULL"


@pytest.mark.asyncio
async def test_mutate_premise_validates_gates():
    state = SessionState()
    handlers = GenerationHandlers(_make_mock_db(), state)
    result = await handlers.mutate_premise(
        _make_mock_session(),
        {
            "source_title": "X", "title": "Y", "body": "Z",
            "premise_type": "conservative", "mutation_strength": 0.5,
        },
    )
    assert result["status"] == "error"
    assert result["error_code"] == "GATES_NOT_SATISFIED"


@pytest.mark.asyncio
async def test_cross_pollinate_validates_gates():
    state = SessionState()
    handlers = GenerationHandlers(_make_mock_db(), state)
    result = await handlers.cross_pollinate(
        _make_mock_session(),
        {
            "primary_title": "X", "title": "Y", "body": "Z",
            "premise_type": "combination", "synthesis_strategy": "merge",
        },
    )
    assert result["status"] == "error"
    assert result["error_code"] == "GATES_NOT_SATISFIED"


@pytest.mark.asyncio
async def test_radical_requires_axiom_challenge():
    state = _make_satisfied_state()
    handlers = GenerationHandlers(_make_mock_db(), state)
    result = await handlers.generate_premise(
        _make_mock_session(),
        {"title": "Radical", "body": "Body", "premise_type": "radical"},
    )
    assert result["status"] == "error"
    assert result["error_code"] == "AXIOM_NOT_CHALLENGED"


@pytest.mark.asyncio
async def test_round_2_requires_negative_context():
    state = _make_satisfied_state()
    state.current_round_number = 1
    handlers = GenerationHandlers(_make_mock_db(), state)
    result = await handlers.generate_premise(
        _make_mock_session(),
        {"title": "X", "body": "Y", "premise_type": "initial"},
    )
    assert result["status"] == "error"
    assert result["error_code"] == "NEGATIVE_CONTEXT_MISSING"
