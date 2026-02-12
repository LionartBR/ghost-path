"""Session State — tests for in-memory enforcement engine.

Tests cover:
    - Gate satisfaction logic (all_gates_satisfied, missing_gates)
    - Buffer management (premises_in_buffer, premises_remaining)
    - Obviousness tracking (all_premises_tested)
    - Per-round reset behavior
"""

from app.core.session_state import SessionState
from app.core.domain_types import AnalysisGate


def test_new_state_has_no_gates_satisfied():
    state = SessionState()
    assert not state.all_gates_satisfied
    assert len(state.missing_gates) == 3


def test_one_gate_does_not_satisfy_all():
    state = SessionState()
    state.completed_gates.add(AnalysisGate.DECOMPOSE)
    assert not state.all_gates_satisfied
    assert "map_conventional_approaches" in state.missing_gates
    assert "extract_hidden_axioms" in state.missing_gates


def test_two_gates_do_not_satisfy_all():
    state = SessionState()
    state.completed_gates.add(AnalysisGate.DECOMPOSE)
    state.completed_gates.add(AnalysisGate.CONVENTIONAL)
    assert not state.all_gates_satisfied
    assert "extract_hidden_axioms" in state.missing_gates


def test_all_three_gates_satisfy():
    state = SessionState()
    state.completed_gates.add(AnalysisGate.DECOMPOSE)
    state.completed_gates.add(AnalysisGate.CONVENTIONAL)
    state.completed_gates.add(AnalysisGate.AXIOMS)
    assert state.all_gates_satisfied
    assert state.missing_gates == []


def test_buffer_starts_empty():
    state = SessionState()
    assert state.premises_in_buffer == 0
    assert state.premises_remaining == 3


def test_buffer_holds_exactly_3_premises_per_round():
    state = SessionState()
    for i in range(3):
        state.current_round_buffer.append({"title": f"P{i}"})
    assert state.premises_in_buffer == 3
    assert state.premises_remaining == 0


def test_buffer_tracks_count_incrementally():
    state = SessionState()
    state.current_round_buffer.append({"title": "P0"})
    assert state.premises_in_buffer == 1
    assert state.premises_remaining == 2


def test_all_premises_tested_when_empty():
    state = SessionState()
    assert state.all_premises_tested


def test_all_premises_tested_with_full_buffer():
    state = SessionState()
    for i in range(3):
        state.current_round_buffer.append({"title": f"P{i}"})
        state.obviousness_tested.add(i)
    assert state.all_premises_tested


def test_not_all_premises_tested_when_partial():
    state = SessionState()
    for i in range(3):
        state.current_round_buffer.append({"title": f"P{i}"})
    state.obviousness_tested.add(0)
    assert not state.all_premises_tested


def test_round_reset_clears_buffer_and_flags():
    state = SessionState()
    state.axiom_challenged = True
    state.negative_context_fetched = True
    state.current_round_buffer.append({"title": "P1"})
    state.obviousness_tested.add(0)
    state.reset_for_next_round()
    assert state.current_round_buffer == []
    assert state.axiom_challenged is False
    assert state.negative_context_fetched is False
    assert len(state.obviousness_tested) == 0


def test_round_reset_preserves_gates_and_axioms():
    state = SessionState()
    state.completed_gates.add(AnalysisGate.DECOMPOSE)
    state.extracted_axioms.append("axiom1")
    state.current_round_number = 1
    state.reset_for_next_round()
    assert AnalysisGate.DECOMPOSE in state.completed_gates
    assert "axiom1" in state.extracted_axioms
    assert state.current_round_number == 1


def test_initial_round_number_is_zero():
    state = SessionState()
    assert state.current_round_number == 0


def test_awaiting_user_input_defaults_false():
    state = SessionState()
    assert state.awaiting_user_input is False
    assert state.awaiting_input_type is None
