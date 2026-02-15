"""ForgeState tests — pure tests for the in-memory enforcement engine.

Tests cover:
    - Initial state defaults
    - Computed properties (claims_in_round, claims_remaining, etc.)
    - Phase transition helpers
    - web_search recording
    - Per-round reset behavior
    - Deep-dive tracking
"""

from app.core.forge_state import ForgeState
from app.core.forge_state_snapshot import forge_state_to_snapshot, forge_state_from_snapshot
from app.core.domain_types import Locale, Phase


# --- Initial state defaults ---------------------------------------------------

def test_initial_phase_is_decompose():
    state = ForgeState()
    assert state.current_phase == Phase.DECOMPOSE


def test_initial_round_is_zero():
    state = ForgeState()
    assert state.current_round == 0


def test_initial_claims_empty():
    state = ForgeState()
    assert state.claims_in_round == 0
    assert state.claims_remaining == 3


def test_initial_web_searches_empty():
    state = ForgeState()
    assert state.web_searches_this_phase == []
    assert not state.has_web_search_this_phase


def test_initial_knowledge_graph_empty():
    state = ForgeState()
    assert state.knowledge_graph_nodes == []
    assert state.knowledge_graph_edges == []


def test_initial_not_awaiting_input():
    state = ForgeState()
    assert not state.awaiting_user_input
    assert state.awaiting_input_type is None


# --- Computed properties: claims ----------------------------------------------

def test_claims_in_round_counts_buffer():
    state = ForgeState()
    state.current_round_claims.append({"claim_text": "C1"})
    state.current_round_claims.append({"claim_text": "C2"})
    assert state.claims_in_round == 2
    assert state.claims_remaining == 1


def test_claims_remaining_zero_when_full():
    state = ForgeState()
    for i in range(3):
        state.current_round_claims.append({"claim_text": f"C{i}"})
    assert state.claims_remaining == 0


# --- Computed properties: antithesis/falsification/novelty --------------------

def test_all_claims_have_antithesis_false_when_empty():
    state = ForgeState()
    assert not state.all_claims_have_antithesis


def test_all_claims_have_antithesis_true_when_all_searched():
    state = ForgeState()
    state.current_round_claims = [{"claim_text": "C1"}, {"claim_text": "C2"}]
    state.antitheses_searched = {0, 1}
    assert state.all_claims_have_antithesis


def test_all_claims_have_antithesis_false_when_partial():
    state = ForgeState()
    state.current_round_claims = [{"claim_text": "C1"}, {"claim_text": "C2"}]
    state.antitheses_searched = {0}
    assert not state.all_claims_have_antithesis


def test_all_claims_falsified_true():
    state = ForgeState()
    state.current_round_claims = [{"claim_text": "C1"}]
    state.falsification_attempted = {0}
    assert state.all_claims_falsified


def test_all_claims_novelty_checked_true():
    state = ForgeState()
    state.current_round_claims = [{"claim_text": "C1"}]
    state.novelty_checked = {0}
    assert state.all_claims_novelty_checked


# --- Computed properties: max rounds ------------------------------------------

def test_max_rounds_not_reached_at_3():
    """Round 3 (4th round, 0-indexed) is not the last — one more round allowed."""
    state = ForgeState()
    state.current_round = 3
    assert not state.max_rounds_reached


def test_max_rounds_reached_at_4():
    """Round 4 (5th round, 0-indexed) IS the last — MAX_ROUNDS_PER_SESSION=5."""
    state = ForgeState()
    state.current_round = 4
    assert state.max_rounds_reached


# --- Computed properties: starred/selected ------------------------------------

def test_starred_analogies_filters_correctly():
    state = ForgeState()
    state.cross_domain_analogies = [
        {"domain": "music", "starred": True},
        {"domain": "biology", "starred": False},
        {"domain": "cooking", "starred": True},
    ]
    assert len(state.starred_analogies) == 2


def test_selected_reframings_filters_correctly():
    state = ForgeState()
    state.reframings = [
        {"text": "R1", "selected": True},
        {"text": "R2", "selected": False},
    ]
    assert len(state.selected_reframings) == 1


def test_reviewed_assumptions_filters_correctly():
    state = ForgeState()
    state.assumptions = [
        {"text": "A1", "options": ["Yes", "No"], "selected_option": 0},
        {"text": "A2", "options": ["Yes", "No"], "selected_option": 1},
        {"text": "A3", "options": ["Yes", "No"], "selected_option": None},
    ]
    assert len(state.reviewed_assumptions) == 2
    # Backward-compat alias
    assert len(state.confirmed_assumptions) == 2


# --- Phase transition helpers -------------------------------------------------

def test_transition_to_changes_phase():
    state = ForgeState()
    state.transition_to(Phase.EXPLORE)
    assert state.current_phase == Phase.EXPLORE


def test_transition_to_resets_web_searches():
    state = ForgeState()
    state.record_web_search("query1", "result1")
    assert state.has_web_search_this_phase

    state.transition_to(Phase.EXPLORE)
    assert not state.has_web_search_this_phase
    assert state.web_searches_this_phase == []


def test_record_web_search_appends():
    state = ForgeState()
    state.record_web_search("TRIZ methods", "40 inventive principles...")
    state.record_web_search("CRISPR history", "2012 discovery...")
    assert len(state.web_searches_this_phase) == 2
    assert state.web_searches_this_phase[0]["query"] == "TRIZ methods"


# --- Per-round reset ----------------------------------------------------------

def test_reset_increments_round():
    state = ForgeState()
    assert state.current_round == 0
    state.reset_for_new_round()
    assert state.current_round == 1


def test_reset_clears_round_claims():
    state = ForgeState()
    state.current_round_claims = [{"claim_text": "C1"}]
    state.reset_for_new_round()
    assert state.current_round_claims == []


def test_reset_clears_synthesis_tracking():
    state = ForgeState()
    state.theses_stated = 3
    state.antitheses_searched = {0, 1, 2}
    state.reset_for_new_round()
    assert state.theses_stated == 0
    assert state.antitheses_searched == set()


def test_reset_clears_validation_tracking():
    state = ForgeState()
    state.falsification_attempted = {0, 1}
    state.novelty_checked = {0, 1}
    state.reset_for_new_round()
    assert state.falsification_attempted == set()
    assert state.novelty_checked == set()


def test_reset_clears_cumulative_gates():
    state = ForgeState()
    state.negative_knowledge_consulted = True
    state.previous_claims_referenced = True
    state.reset_for_new_round()
    assert not state.negative_knowledge_consulted
    assert not state.previous_claims_referenced


def test_reset_clears_web_searches():
    state = ForgeState()
    state.record_web_search("q", "r")
    state.reset_for_new_round()
    assert state.web_searches_this_phase == []


def test_reset_preserves_knowledge_graph():
    state = ForgeState()
    state.knowledge_graph_nodes = [{"id": "1", "claim_text": "C1"}]
    state.knowledge_graph_edges = [{"source": "1", "target": "2"}]
    state.negative_knowledge = [{"claim_text": "rejected"}]
    state.gaps = ["gap1"]

    state.reset_for_new_round()

    assert len(state.knowledge_graph_nodes) == 1
    assert len(state.knowledge_graph_edges) == 1
    assert len(state.negative_knowledge) == 1
    assert len(state.gaps) == 1


# --- Deep-dive tracking ------------------------------------------------------

def test_deep_dive_defaults_inactive():
    state = ForgeState()
    assert not state.deep_dive_active
    assert state.deep_dive_target_claim_id is None


def test_deep_dive_can_be_activated():
    state = ForgeState()
    state.deep_dive_active = True
    state.deep_dive_target_claim_id = "claim-uuid-123"
    assert state.deep_dive_active
    assert state.deep_dive_target_claim_id == "claim-uuid-123"


# --- Locale tracking ----------------------------------------------------------

def test_locale_defaults_to_english():
    state = ForgeState()
    assert state.locale == Locale.EN
    assert state.locale_confidence == 0.0


def test_locale_persists_across_round_reset():
    state = ForgeState(locale=Locale.PT_BR, locale_confidence=0.95)
    state.current_round_claims = [{"claim_text": "C1"}]
    state.reset_for_new_round()
    assert state.locale == Locale.PT_BR
    assert state.locale_confidence == 0.95


# --- Cancellation flag (transient) -------------------------------------------

def test_initial_not_cancelled():
    state = ForgeState()
    assert state.cancelled is False


def test_cancelled_not_in_snapshot():
    """Cancelled flag is transient — not persisted to snapshot."""
    state = ForgeState()
    state.cancelled = True
    snapshot = forge_state_to_snapshot(state)
    assert "cancelled" not in snapshot


def test_cancelled_defaults_false_on_restore():
    """Restored state always has cancelled=False (resumable after restart)."""
    state = ForgeState()
    state.cancelled = True
    snapshot = forge_state_to_snapshot(state)
    restored = forge_state_from_snapshot(snapshot)
    assert restored.cancelled is False


# --- Awaiting flags persistence (session resume) -----------------------------

def test_snapshot_includes_awaiting_user_input():
    """awaiting_user_input must be persisted for session resume."""
    state = ForgeState()
    state.awaiting_user_input = True
    state.awaiting_input_type = "decompose_review"
    snapshot = forge_state_to_snapshot(state)
    assert snapshot["awaiting_user_input"] is True
    assert snapshot["awaiting_input_type"] == "decompose_review"


def test_snapshot_restores_awaiting_user_input():
    """Restored state must have awaiting flags from snapshot."""
    state = ForgeState()
    state.awaiting_user_input = True
    state.awaiting_input_type = "explore_review"
    snapshot = forge_state_to_snapshot(state)
    restored = forge_state_from_snapshot(snapshot)
    assert restored.awaiting_user_input is True
    assert restored.awaiting_input_type == "explore_review"


def test_snapshot_restores_awaiting_defaults_when_missing():
    """Old snapshots without awaiting fields should default gracefully."""
    snapshot = {"current_phase": "decompose", "current_round": 0}
    restored = forge_state_from_snapshot(snapshot)
    assert restored.awaiting_user_input is False
    assert restored.awaiting_input_type is None


# --- Research directives (user steers agent between iterations) ---------------

def test_initial_research_directives_empty():
    state = ForgeState()
    assert state.research_directives == []


def test_add_research_directive_appends():
    state = ForgeState()
    state.add_research_directive("explore_more", "TRIZ biology", "biology")
    state.add_research_directive("skip_domain", "cooking analogies", "cooking")
    assert len(state.research_directives) == 2
    assert state.research_directives[0]["directive_type"] == "explore_more"
    assert state.research_directives[1]["domain"] == "cooking"


def test_consume_research_directives_returns_and_clears():
    state = ForgeState()
    state.add_research_directive("explore_more", "quantum computing", "physics")
    state.add_research_directive("skip_domain", "skip this", "cooking")
    consumed = state.consume_research_directives()
    assert len(consumed) == 2
    assert consumed[0]["query"] == "quantum computing"
    assert state.research_directives == []


def test_consume_research_directives_empty_returns_empty():
    state = ForgeState()
    consumed = state.consume_research_directives()
    assert consumed == []
    assert state.research_directives == []


def test_research_directives_in_snapshot():
    state = ForgeState()
    state.add_research_directive("explore_more", "test query", "domain")
    snapshot = forge_state_to_snapshot(state)
    assert snapshot["research_directives"] == [
        {"directive_type": "explore_more", "query": "test query", "domain": "domain"},
    ]


def test_research_directives_restored_from_snapshot():
    state = ForgeState()
    state.add_research_directive("explore_more", "test query", "domain")
    snapshot = forge_state_to_snapshot(state)
    restored = forge_state_from_snapshot(snapshot)
    assert len(restored.research_directives) == 1
    assert restored.research_directives[0]["query"] == "test query"


def test_research_directives_default_on_old_snapshot():
    """Old snapshots without research_directives field default to empty list."""
    snapshot = {"current_phase": "decompose", "current_round": 0}
    restored = forge_state_from_snapshot(snapshot)
    assert restored.research_directives == []


# --- User-suggested domains --------------------------------------------------

def test_user_suggested_domains_starts_empty():
    state = ForgeState()
    assert state.user_suggested_domains == []


def test_reset_for_new_round_preserves_user_suggested_domains():
    state = ForgeState()
    state.user_suggested_domains = ["biology"]
    state.reset_for_new_round()
    assert state.user_suggested_domains == ["biology"]


# --- Research archive (cumulative — Haiku delegation) -------------------------

def test_initial_research_archive_empty():
    state = ForgeState()
    assert state.research_archive == []


def test_research_archive_accumulates():
    state = ForgeState()
    state.research_archive.append({
        "query": "TRIZ methods", "purpose": "state_of_art",
        "summary": "Found methods", "sources": [],
    })
    state.research_archive.append({
        "query": "biology analogies", "purpose": "cross_domain",
        "summary": "Found analogies", "sources": [{"url": "https://example.com"}],
    })
    assert len(state.research_archive) == 2


def test_research_archive_persists_across_round_reset():
    """research_archive is cumulative — survives round reset."""
    state = ForgeState()
    state.research_archive.append({"query": "test", "summary": "result"})
    state.reset_for_new_round()
    assert len(state.research_archive) == 1


def test_research_archive_persists_across_phase_transition():
    """research_archive is cumulative — survives phase transition."""
    state = ForgeState()
    state.research_archive.append({"query": "test", "summary": "result"})
    state.transition_to(Phase.EXPLORE)
    assert len(state.research_archive) == 1


def test_initial_research_tokens_used_zero():
    state = ForgeState()
    assert state.research_tokens_used == 0
