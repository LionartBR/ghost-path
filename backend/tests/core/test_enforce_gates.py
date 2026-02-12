"""Gate Enforcement — tests for pure gate prerequisite validation.

Tests cover:
    - check_gates returns error when gates incomplete
    - check_gates returns None when all gates satisfied
    - check_radical_prerequisite blocks radical without challenge_axiom
    - check_negative_context blocks rounds 2+ without negative context
    - check_buffer_capacity blocks when buffer full
    - validate_generation_prerequisites chains all checks
"""

from app.core.session_state import SessionState
from app.core.domain_types import AnalysisGate
from app.core.enforce_gates import (
    check_gates,
    check_radical_prerequisite,
    check_negative_context,
    check_buffer_capacity,
    validate_generation_prerequisites,
)


def _make_satisfied_state() -> SessionState:
    """Helper: create state with all gates satisfied."""
    state = SessionState()
    state.completed_gates = {
        AnalysisGate.DECOMPOSE,
        AnalysisGate.CONVENTIONAL,
        AnalysisGate.AXIOMS,
    }
    return state


# ─── check_gates ─────────────────────────────────────────────────

def test_check_gates_returns_error_when_gates_incomplete():
    state = SessionState()
    state.completed_gates.add(AnalysisGate.DECOMPOSE)
    error = check_gates(state)
    assert error is not None
    assert error["error_code"] == "GATES_NOT_SATISFIED"
    assert "missing_gates" in error


def test_check_gates_returns_none_when_all_satisfied():
    state = _make_satisfied_state()
    assert check_gates(state) is None


def test_check_gates_returns_error_when_no_gates():
    state = SessionState()
    error = check_gates(state)
    assert error is not None
    assert error["error_code"] == "GATES_NOT_SATISFIED"
    assert len(error["missing_gates"]) == 3


# ─── check_radical_prerequisite ──────────────────────────────────

def test_radical_blocked_without_challenge_axiom():
    state = SessionState()
    error = check_radical_prerequisite(state, "radical")
    assert error is not None
    assert error["error_code"] == "AXIOM_NOT_CHALLENGED"


def test_radical_allowed_after_challenge_axiom():
    state = SessionState()
    state.axiom_challenged = True
    assert check_radical_prerequisite(state, "radical") is None


def test_non_radical_types_bypass_axiom_check():
    state = SessionState()
    assert check_radical_prerequisite(state, "initial") is None
    assert check_radical_prerequisite(state, "conservative") is None
    assert check_radical_prerequisite(state, "combination") is None


# ─── check_negative_context ──────────────────────────────────────

def test_negative_context_not_required_round_0():
    state = SessionState()
    state.current_round_number = 0
    assert check_negative_context(state) is None


def test_negative_context_required_round_1_plus():
    state = SessionState()
    state.current_round_number = 1
    error = check_negative_context(state)
    assert error is not None
    assert error["error_code"] == "NEGATIVE_CONTEXT_MISSING"


def test_negative_context_satisfied_when_fetched():
    state = SessionState()
    state.current_round_number = 2
    state.negative_context_fetched = True
    assert check_negative_context(state) is None


# ─── check_buffer_capacity ───────────────────────────────────────

def test_buffer_capacity_allows_when_empty():
    state = SessionState()
    assert check_buffer_capacity(state) is None


def test_buffer_capacity_allows_when_partial():
    state = SessionState()
    state.current_round_buffer.append({"title": "P0"})
    state.current_round_buffer.append({"title": "P1"})
    assert check_buffer_capacity(state) is None


def test_buffer_capacity_blocks_when_full():
    state = SessionState()
    for i in range(3):
        state.current_round_buffer.append({"title": f"P{i}"})
    error = check_buffer_capacity(state)
    assert error is not None
    assert error["error_code"] == "ROUND_BUFFER_FULL"


# ─── validate_generation_prerequisites (chain) ───────────────────

def test_validate_generation_prerequisites_chains_all_checks():
    state = SessionState()
    error = validate_generation_prerequisites(state, "initial")
    assert error is not None
    assert error["error_code"] == "GATES_NOT_SATISFIED"


def test_validate_generation_prerequisites_returns_none_when_all_ok():
    state = _make_satisfied_state()
    assert validate_generation_prerequisites(state, "initial") is None


def test_validate_generation_prerequisites_catches_radical_after_gates():
    state = _make_satisfied_state()
    error = validate_generation_prerequisites(state, "radical")
    assert error is not None
    assert error["error_code"] == "AXIOM_NOT_CHALLENGED"


def test_validate_generation_prerequisites_catches_negative_context():
    state = _make_satisfied_state()
    state.current_round_number = 1
    error = validate_generation_prerequisites(state, "initial")
    assert error is not None
    assert error["error_code"] == "NEGATIVE_CONTEXT_MISSING"


def test_validate_generation_prerequisites_catches_buffer_full():
    state = _make_satisfied_state()
    for i in range(3):
        state.current_round_buffer.append({"title": f"P{i}"})
    error = validate_generation_prerequisites(state, "initial")
    assert error is not None
    assert error["error_code"] == "ROUND_BUFFER_FULL"
