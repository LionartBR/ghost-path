"""Round Presentation & Obviousness Enforcement — validates buffer state before user delivery.

Invariants:
    - evaluate_obviousness is PURE: returns action descriptor, does NOT mutate state
    - Shell applies the mutation (remove from buffer or mark tested)
    - OBVIOUSNESS_THRESHOLD (0.6) is single source of truth for the cutoff

Design Decisions:
    - Separated from enforce_gates: different lifecycle — gates checked at generation time,
      round/obviousness checked at presentation time (ADR: responsibility separation)
"""

from app.core.session_state import SessionState


OBVIOUSNESS_THRESHOLD: float = 0.6
MAX_BUFFER_SIZE: int = 3


def evaluate_obviousness(
    state: SessionState, premise_index: int, score: float,
) -> dict:
    """Rule 3: Evaluate obviousness test result. Pure — no state mutation."""
    if premise_index >= state.premises_in_buffer:
        return {
            "status": "error",
            "error_code": "INVALID_INDEX",
            "message": (
                f"ERROR: Invalid premise_buffer_index={premise_index}. "
                f"Buffer has {state.premises_in_buffer} premise(s)."
            ),
        }

    if score > OBVIOUSNESS_THRESHOLD:
        return {
            "status": "rejected",
            "error_code": "TOO_OBVIOUS",
            "premise_index": premise_index,
            "score": score,
            "message": (
                f"REJECTED: Premise #{premise_index + 1} scored {score} "
                f"(> {OBVIOUSNESS_THRESHOLD} threshold). Generate a replacement."
            ),
        }

    return {"status": "ok", "premise_index": premise_index, "score": score}


def validate_round_presentation(state: SessionState) -> dict | None:
    """Rule 6: present_round requires buffer == 3 and all tested."""
    if state.premises_in_buffer != MAX_BUFFER_SIZE:
        return {
            "status": "error",
            "error_code": "INCOMPLETE_ROUND",
            "message": (
                f"ERROR: Round requires exactly 3 premises. "
                f"Current buffer: {state.premises_in_buffer}/3."
            ),
        }

    if not state.all_premises_tested:
        untested = state.premises_in_buffer - len(state.obviousness_tested)
        return {
            "status": "error",
            "error_code": "UNTESTED_PREMISES",
            "message": (
                f"ERROR: {untested} premise(s) have not passed obviousness_test."
            ),
        }

    return None
