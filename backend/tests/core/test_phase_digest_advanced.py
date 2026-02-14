"""Phase Digest Builders — tests for validation, continue, and crystallize contexts.

Tests cover:
    - Phase 4: verdicts from raw input, scores, graph size for round > 0
    - Continue: recent graph nodes, negative knowledge, gaps
    - Crystallize: all sections, no truncation on nodes, PT_BR labels
    - Empty state returns empty string for all builders

Design Decisions:
    - Split from test_phase_digest.py (ExMA: 200-400 lines per file)
    - Covers phases 4-6 + continue; phases 1-3 live in test_phase_digest.py
    - ForgeState populated inline per test (no shared fixtures to avoid coupling)
"""

from app.core.domain_types import Locale
from app.core.forge_state import ForgeState
from app.core.phase_digest import (
    build_phase4_context,
    build_continue_context,
    build_crystallize_context,
)


# ---------------------------------------------------------------------------
# Phase 4 (VALIDATE -> BUILD)
# ---------------------------------------------------------------------------

def test_phase4_includes_verdicts_from_input():
    state = ForgeState()
    state.current_round_claims = [
        {"claim_text": "Claim zero", "scores": {}},
        {"claim_text": "Claim one", "scores": {}},
    ]
    verdicts = [
        {"claim_index": 0, "verdict": "accept"},
        {"claim_index": 1, "verdict": "reject"},
    ]
    result = build_phase4_context(state, Locale.EN, verdicts=verdicts)
    assert "accept" in result
    assert "reject" in result
    assert "Validation complete:" in result


def test_phase4_includes_scores():
    state = ForgeState()
    state.current_round_claims = [
        {
            "claim_text": "Scored claim",
            "scores": {"novelty": 0.8, "groundedness": 0.6},
        },
    ]
    result = build_phase4_context(state, Locale.EN)
    assert "novelty=0.8" in result
    assert "groundedness=0.6" in result


def test_phase4_shows_graph_size_when_round_gt_0():
    state = ForgeState()
    state.current_round = 1
    state.knowledge_graph_nodes = [{"id": "n1"}, {"id": "n2"}]
    state.knowledge_graph_edges = [{"source": "n1", "target": "n2", "type": "supports"}]
    state.current_round_claims = [
        {"claim_text": "R2 claim", "scores": {}},
    ]
    result = build_phase4_context(state, Locale.EN)
    assert "2 nodes" in result
    assert "1 edges" in result


def test_phase4_empty_claims_returns_empty():
    state = ForgeState()
    result = build_phase4_context(state, Locale.EN)
    assert result == ""


def test_phase4_handles_pydantic_like_verdicts():
    """Verdicts can be Pydantic-like objects with .claim_index/.verdict attrs."""
    state = ForgeState()
    state.current_round_claims = [
        {"claim_text": "Some claim", "scores": {}},
    ]

    class FakeVerdict:
        claim_index = 0
        verdict = "qualify"

    result = build_phase4_context(state, Locale.EN, verdicts=[FakeVerdict()])
    assert "qualify" in result


# ---------------------------------------------------------------------------
# Continue context (BUILD -> SYNTHESIZE, round 2+)
# ---------------------------------------------------------------------------

def test_continue_includes_recent_graph_nodes():
    state = ForgeState()
    state.knowledge_graph_nodes = [
        {"claim_text": f"Node {i}", "status": "validated"} for i in range(7)
    ]
    result = build_continue_context(state, Locale.EN)
    # Last 5: nodes 2-6
    assert "Node 6" in result
    assert "Node 2" in result
    assert "Node 1" not in result


def test_continue_includes_negative_knowledge():
    state = ForgeState()
    state.negative_knowledge = [
        {"claim_text": "Rejected A", "rejection_reason": "Too speculative"},
    ]
    result = build_continue_context(state, Locale.EN)
    assert "Rejected A" in result
    assert "Too speculative" in result


def test_continue_includes_gaps():
    state = ForgeState()
    state.gaps = ["Missing data on X", "Needs validation of Y"]
    result = build_continue_context(state, Locale.EN)
    assert "Missing data on X" in result
    assert "Needs validation of Y" in result


def test_continue_empty_state_returns_empty():
    state = ForgeState()
    result = build_continue_context(state, Locale.EN)
    assert result == ""


def test_continue_shows_round_number():
    state = ForgeState()
    state.current_round = 2
    state.knowledge_graph_nodes = [{"claim_text": "X", "status": "validated"}]
    result = build_continue_context(state, Locale.EN)
    assert "round 3" in result


def test_continue_pt_br():
    state = ForgeState()
    state.gaps = ["Lacuna X"]
    result = build_continue_context(state, Locale.PT_BR)
    assert "Contexto acumulado" in result
    assert "Lacunas:" in result


# ---------------------------------------------------------------------------
# Crystallize context (BUILD -> CRYSTALLIZE)
# ---------------------------------------------------------------------------

def test_crystallize_includes_all_sections():
    """All 10 section groups present in crystallize digest."""
    state = ForgeState()
    state.reframings = [{"text": "R1", "selected": True}]
    state.assumptions = [{"text": "A1", "confirmed": True}]
    state.morphological_box = {"parameters": [{"name": "P1", "values": []}]}
    state.cross_domain_analogies = [{"domain": "Bio"}]
    state.contradictions = [{"property_a": "X", "property_b": "Y"}]
    state.knowledge_graph_nodes = [
        {"claim_text": "Claim1", "status": "validated"},
    ]
    state.knowledge_graph_edges = [
        {"source": "n1", "target": "n2", "type": "supports"},
    ]
    state.negative_knowledge = [
        {"claim_text": "Rejected1", "rejection_reason": "Weak"},
    ]
    state.gaps = ["Gap1"]

    result = build_crystallize_context(state, Locale.EN)
    assert "[S1-2]" in result
    assert "[S3]" in result
    assert "[S4-5]" in result
    assert "[S6]" in result
    assert "[S7]" in result
    assert "[S8-9]" in result
    assert "[S10]" in result
    assert "Knowledge Document Sources" in result


def test_crystallize_includes_all_graph_nodes():
    """No truncation on knowledge graph nodes (all needed for document)."""
    state = ForgeState()
    state.knowledge_graph_nodes = [
        {"claim_text": f"Claim {i}", "status": "validated"} for i in range(10)
    ]
    result = build_crystallize_context(state, Locale.EN)
    assert "Claim 0" in result
    assert "Claim 9" in result


def test_crystallize_includes_all_negative_knowledge():
    state = ForgeState()
    state.negative_knowledge = [
        {"claim_text": f"Neg {i}", "rejection_reason": f"Reason {i}"}
        for i in range(5)
    ]
    result = build_crystallize_context(state, Locale.EN)
    assert "Neg 0" in result
    assert "Neg 4" in result


def test_crystallize_includes_edge_type_summary():
    state = ForgeState()
    state.knowledge_graph_edges = [
        {"source": "a", "target": "b", "type": "supports"},
        {"source": "b", "target": "c", "type": "supports"},
        {"source": "c", "target": "d", "type": "contradicts"},
    ]
    result = build_crystallize_context(state, Locale.EN)
    assert "supports=2" in result
    assert "contradicts=1" in result


def test_crystallize_pt_br():
    state = ForgeState()
    state.knowledge_graph_nodes = [
        {"claim_text": "X", "status": "validated"},
    ]
    result = build_crystallize_context(state, Locale.PT_BR)
    assert "Fontes do Documento de Conhecimento" in result
    assert "Afirmações validadas" in result


def test_crystallize_shows_round_count():
    state = ForgeState()
    state.current_round = 3
    result = build_crystallize_context(state, Locale.EN)
    assert "4" in result  # current_round + 1
