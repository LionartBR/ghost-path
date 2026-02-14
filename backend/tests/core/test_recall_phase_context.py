"""Recall Phase Context handler tests — verify artifact retrieval from completed phases.

Tests cover:
    - Successful retrieval of fundamentals, analogies, claims, graph nodes
    - Error on uncompleted phase (current or future)
    - Error on invalid phase name
    - Error on invalid artifact for valid phase

Design Decisions:
    - Handler tested directly by instantiating CrossCuttingHandlers with mock db
    - ForgeState populated inline per test, phase set to simulate completed phases
    - Uses unittest.mock.AsyncMock for db (handler is read-only, no DB calls)
"""

import pytest
from unittest.mock import AsyncMock

from app.core.domain_types import Phase
from app.core.forge_state import ForgeState
from app.services.handle_cross_cutting import CrossCuttingHandlers


class FakeSession:
    total_tokens_used = 0


@pytest.fixture
def db():
    return AsyncMock()


def _make_handler(state: ForgeState, db) -> CrossCuttingHandlers:
    return CrossCuttingHandlers(db, state)


@pytest.mark.asyncio
async def test_recall_fundamentals_from_decompose(db):
    state = ForgeState()
    state.current_phase = Phase.EXPLORE  # decompose completed
    state.fundamentals = ["latency", "consistency"]
    handler = _make_handler(state, db)
    result = await handler.recall_phase_context(
        FakeSession(), {"phase": "decompose", "artifact": "fundamentals"},
    )
    assert result["status"] == "ok"
    assert result["data"] == ["latency", "consistency"]


@pytest.mark.asyncio
async def test_recall_analogies_from_explore(db):
    state = ForgeState()
    state.current_phase = Phase.SYNTHESIZE  # explore completed
    state.cross_domain_analogies = [
        {"domain": "Biology", "description": "Immune system"},
    ]
    handler = _make_handler(state, db)
    result = await handler.recall_phase_context(
        FakeSession(), {"phase": "explore", "artifact": "analogies"},
    )
    assert result["status"] == "ok"
    assert len(result["data"]) == 1
    assert result["data"][0]["domain"] == "Biology"


@pytest.mark.asyncio
async def test_recall_claims_from_synthesize(db):
    state = ForgeState()
    state.current_phase = Phase.VALIDATE  # synthesize completed
    state.current_round_claims = [{"claim_text": "Novel caching"}]
    handler = _make_handler(state, db)
    result = await handler.recall_phase_context(
        FakeSession(), {"phase": "synthesize", "artifact": "claims"},
    )
    assert result["status"] == "ok"
    assert result["data"][0]["claim_text"] == "Novel caching"


@pytest.mark.asyncio
async def test_recall_graph_nodes_from_build(db):
    state = ForgeState()
    state.current_phase = Phase.CRYSTALLIZE  # build completed
    state.knowledge_graph_nodes = [
        {"id": "n1", "claim_text": "Validated claim"},
    ]
    handler = _make_handler(state, db)
    result = await handler.recall_phase_context(
        FakeSession(), {"phase": "build", "artifact": "graph_nodes"},
    )
    assert result["status"] == "ok"
    assert result["data"][0]["id"] == "n1"


@pytest.mark.asyncio
async def test_recall_error_phase_not_completed(db):
    """Current=explore, request=synthesize -> error (not yet completed)."""
    state = ForgeState()
    state.current_phase = Phase.EXPLORE
    handler = _make_handler(state, db)
    result = await handler.recall_phase_context(
        FakeSession(), {"phase": "synthesize", "artifact": "claims"},
    )
    assert result["status"] == "error"
    assert result["error_code"] == "PHASE_NOT_COMPLETED"


@pytest.mark.asyncio
async def test_recall_current_phase_allowed(db):
    """Requesting current phase is allowed — agent needs its own data."""
    state = ForgeState()
    state.current_phase = Phase.EXPLORE
    state.cross_domain_analogies = [{"domain": "Physics"}]
    handler = _make_handler(state, db)
    result = await handler.recall_phase_context(
        FakeSession(), {"phase": "explore", "artifact": "analogies"},
    )
    assert result["status"] == "ok"
    assert result["data"][0]["domain"] == "Physics"


@pytest.mark.asyncio
async def test_recall_error_invalid_phase(db):
    state = ForgeState()
    state.current_phase = Phase.BUILD
    handler = _make_handler(state, db)
    result = await handler.recall_phase_context(
        FakeSession(), {"phase": "nonexistent", "artifact": "fundamentals"},
    )
    assert result["status"] == "error"
    assert result["error_code"] == "INVALID_PHASE"


@pytest.mark.asyncio
async def test_recall_error_artifact_not_found(db):
    """Valid phase, invalid artifact -> error."""
    state = ForgeState()
    state.current_phase = Phase.SYNTHESIZE
    handler = _make_handler(state, db)
    result = await handler.recall_phase_context(
        FakeSession(), {"phase": "decompose", "artifact": "nonexistent"},
    )
    assert result["status"] == "error"
    assert result["error_code"] == "ARTIFACT_NOT_FOUND"


# --- Round 2+ cyclic access tests -------------------------------------------


@pytest.mark.asyncio
async def test_recall_build_artifacts_in_round2_synthesize(db):
    """Round 2+: agent loops back to SYNTHESIZE but BUILD data exists."""
    state = ForgeState()
    state.current_phase = Phase.SYNTHESIZE
    state.current_round = 1  # second round
    state.knowledge_graph_nodes = [{"id": "n1", "claim_text": "Round 1 claim"}]
    handler = _make_handler(state, db)
    result = await handler.recall_phase_context(
        FakeSession(), {"phase": "build", "artifact": "graph_nodes"},
    )
    assert result["status"] == "ok"
    assert result["data"][0]["id"] == "n1"


@pytest.mark.asyncio
async def test_recall_validate_artifacts_in_round2_synthesize(db):
    """Round 2+: validate phase was completed in round 1."""
    state = ForgeState()
    state.current_phase = Phase.SYNTHESIZE
    state.current_round = 1
    state.current_round_claims = [{"claim_text": "Carried over"}]
    handler = _make_handler(state, db)
    result = await handler.recall_phase_context(
        FakeSession(), {"phase": "validate", "artifact": "claims"},
    )
    assert result["status"] == "ok"


@pytest.mark.asyncio
async def test_recall_negative_knowledge_in_round2_synthesize(db):
    """Round 2+: negative knowledge from BUILD accessible in SYNTHESIZE."""
    state = ForgeState()
    state.current_phase = Phase.SYNTHESIZE
    state.current_round = 1
    state.negative_knowledge = [{"claim_text": "Rejected in round 1"}]
    handler = _make_handler(state, db)
    result = await handler.recall_phase_context(
        FakeSession(), {"phase": "build", "artifact": "negative_knowledge"},
    )
    assert result["status"] == "ok"
    assert len(result["data"]) == 1


@pytest.mark.asyncio
async def test_recall_crystallize_blocked_in_round2(db):
    """Round 2+: crystallize never visited, still blocked."""
    state = ForgeState()
    state.current_phase = Phase.SYNTHESIZE
    state.current_round = 1
    handler = _make_handler(state, db)
    result = await handler.recall_phase_context(
        FakeSession(), {"phase": "crystallize", "artifact": "fundamentals"},
    )
    assert result["status"] == "error"
    assert result["error_code"] == "PHASE_NOT_COMPLETED"
