"""Phase enforcement tests — pure tests for phase transition gates.

Tests cover all 15 enforcement rules from the plan:
    Rules #1, #2: Phase transition completeness
    Rules #9, #10, #11: Round 2+ cumulative gates
    Rules #12-15: web_search enforcement
    Composite validator: validate_phase_transition
"""

from app.core.enforce_phases import (
    check_decompose_complete,
    check_explore_complete,
    check_all_antitheses,
    check_cumulative,
    check_negative_consulted,
    check_max_rounds,
    check_web_search,
    validate_phase_transition,
)
from app.core.forge_state import ForgeState
from app.core.domain_types import Phase


# --- Helper: build a fully-decomposed state -----------------------------------

def _decomposed_state() -> ForgeState:
    """ForgeState that has completed Phase 1."""
    state = ForgeState()
    state.fundamentals = ["f1", "f2"]
    state.state_of_art_researched = True
    state.assumptions = [
        {"text": "a1", "confirmed": True},
        {"text": "a2", "confirmed": True},
        {"text": "a3", "confirmed": None},
    ]
    state.reframings = [
        {"text": "r1", "type": "scope_change", "selected": True},
        {"text": "r2", "type": "entity_question", "selected": False},
        {"text": "r3", "type": "variable_change", "selected": False},
    ]
    return state


def _explored_state() -> ForgeState:
    """ForgeState that has completed Phase 2."""
    state = _decomposed_state()
    state.morphological_box = {"parameters": [{"name": "p1", "values": ["a", "b", "c"]}]}
    state.cross_domain_search_count = 2
    state.contradictions = [{"property_a": "fast", "property_b": "cheap", "description": "tradeoff"}]
    state.cross_domain_analogies = [
        {"domain": "music", "description": "harmony patterns", "starred": True},
    ]
    return state


# --- Rule #1: check_decompose_complete ----------------------------------------

def test_decompose_fails_without_fundamentals():
    state = ForgeState()
    error = check_decompose_complete(state)
    assert error is not None
    assert error["error_code"] == "DECOMPOSE_INCOMPLETE"


def test_decompose_fails_without_state_of_art():
    state = ForgeState()
    state.fundamentals = ["f1"]
    error = check_decompose_complete(state)
    assert error is not None
    assert error["error_code"] == "DECOMPOSE_INCOMPLETE"


def test_decompose_fails_with_fewer_than_3_assumptions():
    state = ForgeState()
    state.fundamentals = ["f1"]
    state.state_of_art_researched = True
    state.assumptions = [{"text": "a1", "confirmed": True}]
    error = check_decompose_complete(state)
    assert error is not None
    assert "assumptions" in error["message"].lower()


def test_decompose_fails_with_fewer_than_3_reframings():
    state = ForgeState()
    state.fundamentals = ["f1"]
    state.state_of_art_researched = True
    state.assumptions = [{"text": f"a{i}"} for i in range(3)]
    state.reframings = [{"text": "r1", "selected": True}]
    error = check_decompose_complete(state)
    assert error is not None
    assert "reframings" in error["message"].lower()


def test_decompose_fails_without_selected_reframing():
    state = ForgeState()
    state.fundamentals = ["f1"]
    state.state_of_art_researched = True
    state.assumptions = [{"text": f"a{i}"} for i in range(3)]
    state.reframings = [
        {"text": f"r{i}", "type": "scope_change", "selected": False}
        for i in range(3)
    ]
    error = check_decompose_complete(state)
    assert error is not None
    assert "select" in error["message"].lower()


def test_decompose_passes_with_user_added_reframings():
    state = ForgeState()
    state.fundamentals = ["f1"]
    state.state_of_art_researched = True
    state.assumptions = [{"text": f"a{i}"} for i in range(3)]
    state.reframings = [
        {"text": f"r{i}", "type": "scope_change", "selected": False}
        for i in range(3)
    ]
    state.user_added_reframings = ["my own reframing"]
    error = check_decompose_complete(state)
    assert error is None


def test_decompose_succeeds_with_complete_state():
    state = _decomposed_state()
    error = check_decompose_complete(state)
    assert error is None


def test_decompose_counts_user_added_assumptions():
    state = ForgeState()
    state.fundamentals = ["f1"]
    state.state_of_art_researched = True
    state.assumptions = [{"text": "a1"}]
    state.user_added_assumptions = ["ua1", "ua2"]
    state.reframings = [
        {"text": "r1", "type": "scope_change", "selected": True},
        {"text": "r2", "type": "scope_change", "selected": False},
        {"text": "r3", "type": "scope_change", "selected": False},
    ]
    error = check_decompose_complete(state)
    assert error is None


# --- Rule #2: check_explore_complete ------------------------------------------

def test_explore_fails_without_morphological_box():
    state = ForgeState()
    error = check_explore_complete(state)
    assert error is not None
    assert error["error_code"] == "EXPLORE_INCOMPLETE"


def test_explore_fails_with_fewer_than_2_cross_domain():
    state = ForgeState()
    state.morphological_box = {"parameters": []}
    state.cross_domain_search_count = 1
    error = check_explore_complete(state)
    assert error is not None
    assert "cross-domain" in error["message"].lower()


def test_explore_fails_without_contradictions():
    state = ForgeState()
    state.morphological_box = {"parameters": []}
    state.cross_domain_search_count = 2
    error = check_explore_complete(state)
    assert error is not None
    assert "contradiction" in error["message"].lower()


def test_explore_fails_without_starred_analogies():
    state = ForgeState()
    state.morphological_box = {"parameters": []}
    state.cross_domain_search_count = 2
    state.contradictions = [{"property_a": "a", "property_b": "b", "description": "d"}]
    state.cross_domain_analogies = [
        {"domain": "music", "description": "d", "starred": False},
    ]
    error = check_explore_complete(state)
    assert error is not None
    assert "star" in error["message"].lower()


def test_explore_succeeds_with_complete_state():
    state = _explored_state()
    error = check_explore_complete(state)
    assert error is None


# --- Rule #4: check_all_antitheses -------------------------------------------

def test_antitheses_fails_with_no_claims():
    state = ForgeState()
    error = check_all_antitheses(state)
    assert error is not None
    assert error["error_code"] == "SYNTHESIS_INCOMPLETE"


def test_antitheses_fails_with_partial_coverage():
    state = ForgeState()
    state.current_round_claims = [{"claim_text": "C1"}, {"claim_text": "C2"}]
    state.antitheses_searched = {0}
    error = check_all_antitheses(state)
    assert error is not None
    assert error["error_code"] == "SYNTHESIS_INCOMPLETE"


def test_antitheses_succeeds_with_full_coverage():
    state = ForgeState()
    state.current_round_claims = [{"claim_text": "C1"}, {"claim_text": "C2"}]
    state.antitheses_searched = {0, 1}
    error = check_all_antitheses(state)
    assert error is None


# --- Rule #9: check_cumulative ------------------------------------------------

def test_cumulative_passes_on_round_0():
    state = ForgeState()
    state.current_round = 0
    error = check_cumulative(state)
    assert error is None


def test_cumulative_fails_on_round_1_without_reference():
    state = ForgeState()
    state.current_round = 1
    state.previous_claims_referenced = False
    error = check_cumulative(state)
    assert error is not None
    assert error["error_code"] == "NOT_CUMULATIVE"


def test_cumulative_passes_on_round_1_with_reference():
    state = ForgeState()
    state.current_round = 1
    state.previous_claims_referenced = True
    error = check_cumulative(state)
    assert error is None


# --- Rule #10: check_negative_consulted ---------------------------------------

def test_negative_passes_on_round_0():
    state = ForgeState()
    state.current_round = 0
    error = check_negative_consulted(state)
    assert error is None


def test_negative_fails_on_round_1_without_consult():
    state = ForgeState()
    state.current_round = 1
    state.negative_knowledge_consulted = False
    error = check_negative_consulted(state)
    assert error is not None
    assert error["error_code"] == "NEGATIVE_KNOWLEDGE_MISSING"


def test_negative_passes_on_round_1_with_consult():
    state = ForgeState()
    state.current_round = 1
    state.negative_knowledge_consulted = True
    error = check_negative_consulted(state)
    assert error is None


# --- Rule #11: check_max_rounds -----------------------------------------------

def test_max_rounds_passes_at_3():
    """Round 3 (4th round, 0-indexed) still has one round left."""
    state = ForgeState()
    state.current_round = 3
    error = check_max_rounds(state)
    assert error is None


def test_max_rounds_fails_at_4():
    """Round 4 (5th round, 0-indexed) is the last — MAX_ROUNDS_PER_SESSION=5."""
    state = ForgeState()
    state.current_round = 4
    error = check_max_rounds(state)
    assert error is not None
    assert error["error_code"] == "MAX_ROUNDS_EXCEEDED"


# --- Rules #12-15: check_web_search -------------------------------------------

def test_web_search_fails_without_search_for_state_of_art():
    state = ForgeState()
    error = check_web_search(state, "state_of_art")
    assert error is not None
    assert error["error_code"] == "STATE_OF_ART_NOT_RESEARCHED"


def test_web_search_fails_without_search_for_cross_domain():
    state = ForgeState()
    error = check_web_search(state, "cross_domain")
    assert error is not None
    assert error["error_code"] == "CROSS_DOMAIN_NOT_SEARCHED"


def test_web_search_fails_without_search_for_antithesis():
    state = ForgeState()
    error = check_web_search(state, "antithesis")
    assert error is not None
    assert error["error_code"] == "ANTITHESIS_NOT_SEARCHED"


def test_web_search_fails_without_search_for_falsification():
    state = ForgeState()
    error = check_web_search(state, "falsification")
    assert error is not None
    assert error["error_code"] == "FALSIFICATION_NOT_SEARCHED"


def test_web_search_passes_when_search_recorded():
    state = ForgeState()
    state.record_web_search("TRIZ methods", "results")
    for ctx in ["state_of_art", "cross_domain", "antithesis", "falsification"]:
        error = check_web_search(state, ctx)
        assert error is None, f"Should pass for {ctx}"


def test_web_search_invalid_context():
    state = ForgeState()
    error = check_web_search(state, "nonexistent")
    assert error is not None
    assert error["error_code"] == "INVALID_CONTEXT"


# --- Composite: validate_phase_transition -------------------------------------

def test_transition_to_explore_checks_decompose():
    state = ForgeState()
    error = validate_phase_transition(state, Phase.EXPLORE)
    assert error is not None
    assert error["error_code"] == "DECOMPOSE_INCOMPLETE"


def test_transition_to_explore_passes():
    state = _decomposed_state()
    error = validate_phase_transition(state, Phase.EXPLORE)
    assert error is None


def test_transition_to_synthesize_checks_explore():
    state = _decomposed_state()
    error = validate_phase_transition(state, Phase.SYNTHESIZE)
    assert error is not None
    assert error["error_code"] == "EXPLORE_INCOMPLETE"


def test_transition_to_synthesize_passes():
    state = _explored_state()
    error = validate_phase_transition(state, Phase.SYNTHESIZE)
    assert error is None


def test_transition_to_synthesize_round_2_checks_cumulative():
    state = _explored_state()
    state.current_round = 1
    state.negative_knowledge_consulted = True
    state.previous_claims_referenced = False
    error = validate_phase_transition(state, Phase.SYNTHESIZE)
    assert error is not None
    assert error["error_code"] == "NOT_CUMULATIVE"


def test_transition_to_synthesize_round_2_checks_negative():
    state = _explored_state()
    state.current_round = 1
    state.previous_claims_referenced = True
    state.negative_knowledge_consulted = False
    error = validate_phase_transition(state, Phase.SYNTHESIZE)
    assert error is not None
    assert error["error_code"] == "NEGATIVE_KNOWLEDGE_MISSING"


def test_transition_to_validate_checks_antitheses():
    state = ForgeState()
    error = validate_phase_transition(state, Phase.VALIDATE)
    assert error is not None
    assert error["error_code"] == "SYNTHESIS_INCOMPLETE"


def test_transition_to_build_returns_none():
    state = ForgeState()
    error = validate_phase_transition(state, Phase.BUILD)
    assert error is None


def test_transition_to_crystallize_returns_none():
    state = ForgeState()
    error = validate_phase_transition(state, Phase.CRYSTALLIZE)
    assert error is None
