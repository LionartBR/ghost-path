"""Tests for compute_session_stats — pure stats from ForgeState, no IO."""

from app.core.forge_state import ForgeState
from app.core.session_stats import compute_session_stats


def test_empty_state_returns_zero_stats():
    state = ForgeState()
    stats = compute_session_stats(state)
    assert stats["claims_validated"] == 0
    assert stats["claims_rejected"] == 0
    assert stats["claims_qualified"] == 0
    assert stats["total_claims"] == 0
    assert stats["analogies_used"] == 0
    assert stats["contradictions_found"] == 0
    assert stats["evidence_collected"] == 0
    assert stats["graph_nodes"] == 0
    assert stats["graph_edges"] == 0
    assert stats["total_rounds"] == 1  # round 0 + 1


def test_counts_validated_claims_from_graph_nodes():
    state = ForgeState()
    state.knowledge_graph_nodes = [
        {"claim_text": "C1", "status": "validated", "evidence_count": 2},
        {"claim_text": "C2", "status": "validated", "evidence_count": 1},
        {"claim_text": "C3", "status": "qualified", "evidence_count": 0},
    ]
    stats = compute_session_stats(state)
    assert stats["claims_validated"] == 2
    assert stats["claims_qualified"] == 1
    assert stats["graph_nodes"] == 3
    assert stats["evidence_collected"] == 3


def test_counts_rejected_claims_from_negative_knowledge():
    state = ForgeState()
    state.negative_knowledge = [
        {"claim_text": "Bad1", "rejection_reason": "wrong", "round": 0},
        {"claim_text": "Bad2", "rejection_reason": "invalid", "round": 1},
    ]
    state.knowledge_graph_nodes = [
        {"claim_text": "Good1", "status": "validated", "evidence_count": 1},
    ]
    stats = compute_session_stats(state)
    assert stats["claims_rejected"] == 2
    assert stats["total_claims"] == 3  # 1 graph node + 2 rejected


def test_counts_resonated_analogies_only():
    state = ForgeState()
    state.cross_domain_analogies = [
        {"domain": "biology", "resonated": True},
        {"domain": "physics", "resonated": False},
        {"domain": "music", "resonated": True},
        {"domain": "cooking"},  # no resonated key
    ]
    stats = compute_session_stats(state)
    assert stats["analogies_used"] == 2


def test_total_rounds_is_current_plus_one():
    state = ForgeState()
    state.current_round = 3
    stats = compute_session_stats(state)
    assert stats["total_rounds"] == 4


def test_counts_fundamentals_assumptions_reframings():
    state = ForgeState()
    state.fundamentals = ["F1", "F2", "F3"]
    state.assumptions = [{"text": "A1"}, {"text": "A2"}]
    state.reframings = [{"text": "R1"}, {"text": "R2"}, {"text": "R3"}, {"text": "R4"}]
    state.contradictions = [{"description": "C1"}]
    state.knowledge_graph_edges = [{"source": "a", "target": "b"}]
    stats = compute_session_stats(state)
    assert stats["fundamentals_identified"] == 3
    assert stats["assumptions_examined"] == 2
    assert stats["reframings_explored"] == 4
    assert stats["contradictions_found"] == 1
    assert stats["graph_edges"] == 1
