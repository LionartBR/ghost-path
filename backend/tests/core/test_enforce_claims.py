"""Claim enforcement tests — pure tests for knowledge claim validation rules.

Tests cover:
    Rule #3: check_antithesis_exists
    Rule #5: check_falsification
    Rule #6: check_novelty_done
    Rule #7: check_evidence_grounding
    Rule #8: check_claim_limit
    Composite validators: validate_synthesis_prerequisites, validate_scoring_prerequisites
"""

from app.core.enforce_claims import (
    check_antithesis_exists,
    check_claim_limit,
    check_falsification,
    check_novelty_done,
    check_evidence_grounding,
    check_claim_index_valid,
    validate_synthesis_prerequisites,
    validate_scoring_prerequisites,
    validate_graph_addition,
)
from app.core.forge_state import ForgeState


# --- Rule #3: check_antithesis_exists -----------------------------------------

def test_antithesis_fails_when_not_searched():
    state = ForgeState()
    error = check_antithesis_exists(state, 0)
    assert error is not None
    assert error["error_code"] == "ANTITHESIS_MISSING"


def test_antithesis_passes_when_searched():
    state = ForgeState()
    state.antitheses_searched = {0, 1}
    error = check_antithesis_exists(state, 0)
    assert error is None


def test_antithesis_fails_for_wrong_index():
    state = ForgeState()
    state.antitheses_searched = {0}
    error = check_antithesis_exists(state, 1)
    assert error is not None
    assert error["error_code"] == "ANTITHESIS_MISSING"


# --- Rule #5: check_falsification --------------------------------------------

def test_falsification_fails_when_not_attempted():
    state = ForgeState()
    error = check_falsification(state, 0)
    assert error is not None
    assert error["error_code"] == "FALSIFICATION_MISSING"


def test_falsification_passes_when_attempted():
    state = ForgeState()
    state.falsification_attempted = {0}
    error = check_falsification(state, 0)
    assert error is None


# --- Rule #6: check_novelty_done ---------------------------------------------

def test_novelty_fails_when_not_checked():
    state = ForgeState()
    error = check_novelty_done(state, 0)
    assert error is not None
    assert error["error_code"] == "NOVELTY_UNCHECKED"


def test_novelty_passes_when_checked():
    state = ForgeState()
    state.novelty_checked = {0}
    error = check_novelty_done(state, 0)
    assert error is None


# --- Rule #7: check_evidence_grounding ----------------------------------------

def test_evidence_fails_with_no_evidence():
    claim = {"claim_text": "Some claim"}
    error = check_evidence_grounding(claim)
    assert error is not None
    assert error["error_code"] == "UNGROUNDED_CLAIM"


def test_evidence_fails_with_empty_list():
    claim = {"claim_text": "Some claim", "evidence": []}
    error = check_evidence_grounding(claim)
    assert error is not None
    assert error["error_code"] == "UNGROUNDED_CLAIM"


def test_evidence_passes_with_evidence():
    claim = {
        "claim_text": "Some claim",
        "evidence": [{"url": "https://example.com", "type": "supporting"}],
    }
    error = check_evidence_grounding(claim)
    assert error is None


# --- Rule #8: check_claim_limit ----------------------------------------------

def test_claim_limit_passes_with_fewer_than_3():
    state = ForgeState()
    state.current_round_claims = [{"claim_text": "C1"}, {"claim_text": "C2"}]
    error = check_claim_limit(state)
    assert error is None


def test_claim_limit_fails_at_3():
    state = ForgeState()
    state.current_round_claims = [
        {"claim_text": f"C{i}"} for i in range(3)
    ]
    error = check_claim_limit(state)
    assert error is not None
    assert error["error_code"] == "CLAIM_LIMIT_EXCEEDED"


def test_claim_limit_passes_with_empty_buffer():
    state = ForgeState()
    error = check_claim_limit(state)
    assert error is None


# --- check_claim_index_valid --------------------------------------------------

def test_claim_index_valid_passes():
    state = ForgeState()
    state.current_round_claims = [{"claim_text": "C1"}, {"claim_text": "C2"}]
    error = check_claim_index_valid(state, 0)
    assert error is None
    error = check_claim_index_valid(state, 1)
    assert error is None


def test_claim_index_valid_fails_negative():
    state = ForgeState()
    state.current_round_claims = [{"claim_text": "C1"}]
    error = check_claim_index_valid(state, -1)
    assert error is not None
    assert error["error_code"] == "INVALID_CLAIM_INDEX"


def test_claim_index_valid_fails_out_of_bounds():
    state = ForgeState()
    state.current_round_claims = [{"claim_text": "C1"}]
    error = check_claim_index_valid(state, 1)
    assert error is not None
    assert error["error_code"] == "INVALID_CLAIM_INDEX"


# --- Composite: validate_synthesis_prerequisites ------------------------------

def test_synthesis_prerequisites_fails_at_limit():
    state = ForgeState()
    state.current_round_claims = [{"claim_text": f"C{i}"} for i in range(3)]
    state.antitheses_searched = {0}
    error = validate_synthesis_prerequisites(state, 0)
    assert error is not None
    assert error["error_code"] == "CLAIM_LIMIT_EXCEEDED"


def test_synthesis_prerequisites_fails_without_antithesis():
    state = ForgeState()
    state.current_round_claims = [{"claim_text": "C1"}]
    error = validate_synthesis_prerequisites(state, 0)
    assert error is not None
    assert error["error_code"] == "ANTITHESIS_MISSING"


def test_synthesis_prerequisites_passes():
    state = ForgeState()
    state.current_round_claims = [{"claim_text": "C1"}]
    state.antitheses_searched = {0}
    error = validate_synthesis_prerequisites(state, 0)
    assert error is None


# --- Composite: validate_scoring_prerequisites --------------------------------

def test_scoring_prerequisites_fails_invalid_index():
    state = ForgeState()
    error = validate_scoring_prerequisites(state, 0)
    assert error is not None
    assert error["error_code"] == "INVALID_CLAIM_INDEX"


def test_scoring_prerequisites_fails_without_falsification():
    state = ForgeState()
    state.current_round_claims = [{"claim_text": "C1"}]
    state.novelty_checked = {0}
    error = validate_scoring_prerequisites(state, 0)
    assert error is not None
    assert error["error_code"] == "FALSIFICATION_MISSING"


def test_scoring_prerequisites_fails_without_novelty():
    state = ForgeState()
    state.current_round_claims = [{"claim_text": "C1"}]
    state.falsification_attempted = {0}
    error = validate_scoring_prerequisites(state, 0)
    assert error is not None
    assert error["error_code"] == "NOVELTY_UNCHECKED"


def test_scoring_prerequisites_passes():
    state = ForgeState()
    state.current_round_claims = [{"claim_text": "C1"}]
    state.falsification_attempted = {0}
    state.novelty_checked = {0}
    error = validate_scoring_prerequisites(state, 0)
    assert error is None


# --- Composite: validate_graph_addition ---------------------------------------

def test_graph_addition_fails_invalid_index():
    state = ForgeState()
    error = validate_graph_addition(state, 0, "accept")
    assert error is not None
    assert error["error_code"] == "INVALID_CLAIM_INDEX"


def test_graph_addition_fails_with_reject_verdict():
    state = ForgeState()
    state.current_round_claims = [{"claim_text": "C1"}]
    error = validate_graph_addition(state, 0, "reject")
    assert error is not None
    assert error["error_code"] == "INVALID_VERDICT"


def test_graph_addition_passes_with_accept():
    state = ForgeState()
    state.current_round_claims = [{"claim_text": "C1"}]
    error = validate_graph_addition(state, 0, "accept")
    assert error is None


def test_graph_addition_passes_with_qualify():
    state = ForgeState()
    state.current_round_claims = [{"claim_text": "C1"}]
    error = validate_graph_addition(state, 0, "qualify")
    assert error is None


def test_graph_addition_passes_with_merge():
    state = ForgeState()
    state.current_round_claims = [{"claim_text": "C1"}]
    error = validate_graph_addition(state, 0, "merge")
    assert error is None
