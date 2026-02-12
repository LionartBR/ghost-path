"""Round Enforcement — tests for pure round and obviousness validation.

Tests cover:
    - evaluate_obviousness rejects above threshold
    - evaluate_obviousness passes below threshold
    - evaluate_obviousness rejects invalid index
    - validate_round_presentation requires exactly 3 premises
    - validate_round_presentation requires all premises tested
"""

from app.core.session_state import SessionState
from app.core.enforce_round import (
    evaluate_obviousness,
    validate_round_presentation,
    OBVIOUSNESS_THRESHOLD,
    MAX_BUFFER_SIZE,
)


# ─── evaluate_obviousness ────────────────────────────────────────

def test_evaluate_obviousness_rejects_above_threshold():
    state = SessionState()
    state.current_round_buffer.append({"title": "P1"})
    result = evaluate_obviousness(state, 0, 0.7)
    assert result["status"] == "rejected"
    assert result["error_code"] == "TOO_OBVIOUS"
    assert result["score"] == 0.7


def test_evaluate_obviousness_passes_below_threshold():
    state = SessionState()
    state.current_round_buffer.append({"title": "P1"})
    result = evaluate_obviousness(state, 0, 0.4)
    assert result["status"] == "ok"
    assert result["premise_index"] == 0
    assert result["score"] == 0.4


def test_evaluate_obviousness_passes_at_threshold():
    state = SessionState()
    state.current_round_buffer.append({"title": "P1"})
    result = evaluate_obviousness(state, 0, OBVIOUSNESS_THRESHOLD)
    assert result["status"] == "ok"


def test_evaluate_obviousness_rejects_just_above_threshold():
    state = SessionState()
    state.current_round_buffer.append({"title": "P1"})
    result = evaluate_obviousness(state, 0, 0.61)
    assert result["status"] == "rejected"
    assert result["error_code"] == "TOO_OBVIOUS"


def test_evaluate_obviousness_rejects_invalid_index():
    state = SessionState()
    state.current_round_buffer.append({"title": "P1"})
    result = evaluate_obviousness(state, 5, 0.3)
    assert result["status"] == "error"
    assert result["error_code"] == "INVALID_INDEX"


def test_evaluate_obviousness_rejects_index_on_empty_buffer():
    state = SessionState()
    result = evaluate_obviousness(state, 0, 0.3)
    assert result["status"] == "error"
    assert result["error_code"] == "INVALID_INDEX"


def test_evaluate_obviousness_with_zero_score():
    state = SessionState()
    state.current_round_buffer.append({"title": "Novel"})
    result = evaluate_obviousness(state, 0, 0.0)
    assert result["status"] == "ok"


def test_evaluate_obviousness_with_max_score():
    state = SessionState()
    state.current_round_buffer.append({"title": "Obvious"})
    result = evaluate_obviousness(state, 0, 1.0)
    assert result["status"] == "rejected"
    assert result["error_code"] == "TOO_OBVIOUS"


# ─── validate_round_presentation ─────────────────────────────────

def test_validate_round_requires_exactly_3_premises():
    state = SessionState()
    state.current_round_buffer.append({"title": "P1"})
    state.current_round_buffer.append({"title": "P2"})
    error = validate_round_presentation(state)
    assert error is not None
    assert error["error_code"] == "INCOMPLETE_ROUND"


def test_validate_round_rejects_empty_buffer():
    state = SessionState()
    error = validate_round_presentation(state)
    assert error is not None
    assert error["error_code"] == "INCOMPLETE_ROUND"


def test_validate_round_requires_all_premises_tested():
    state = SessionState()
    for i in range(MAX_BUFFER_SIZE):
        state.current_round_buffer.append({"title": f"P{i}"})
    state.obviousness_tested.add(0)
    error = validate_round_presentation(state)
    assert error is not None
    assert error["error_code"] == "UNTESTED_PREMISES"


def test_validate_round_passes_with_3_tested_premises():
    state = SessionState()
    for i in range(MAX_BUFFER_SIZE):
        state.current_round_buffer.append({"title": f"P{i}"})
        state.obviousness_tested.add(i)
    assert validate_round_presentation(state) is None


def test_validate_round_returns_none_on_success():
    state = SessionState()
    for i in range(3):
        state.current_round_buffer.append({"title": f"P{i}"})
        state.obviousness_tested.add(i)
    result = validate_round_presentation(state)
    assert result is None


def test_threshold_constant_is_0_6():
    assert OBVIOUSNESS_THRESHOLD == 0.6


def test_max_buffer_size_is_3():
    assert MAX_BUFFER_SIZE == 3
