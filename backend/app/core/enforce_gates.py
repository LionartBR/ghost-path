"""Gate Prerequisite Enforcement — validates all conditions before premise generation.

Invariants:
    - All functions are PURE: no IO, no async, no DB, no side effects
    - Return error dict on violation, None on success
    - validate_generation_prerequisites chains all checks — first error wins

Design Decisions:
    - Pure functions over method dispatch: testable without mocks (ADR: ExMA Functional Core)
    - Return dicts (not exceptions): agent_runner consumes tool results as JSON dicts,
      keeping error path identical to success path (ADR: uniform tool response shape)
"""

from app.core.session_state import SessionState
from app.core.domain_types import PremiseType


def check_gates(state: SessionState) -> dict | None:
    """Rule 1: All 3 analysis gates must complete before generation."""
    if not state.all_gates_satisfied:
        return {
            "status": "error",
            "error_code": "GATES_NOT_SATISFIED",
            "message": (
                f"ERROR: Cannot generate premises. "
                f"Missing mandatory tools: {state.missing_gates}. "
                f"Call these tools first."
            ),
            "missing_gates": state.missing_gates,
        }
    return None


def check_radical_prerequisite(state: SessionState, premise_type: str) -> dict | None:
    """Rule 4: Radical premises require challenge_axiom first."""
    if premise_type == PremiseType.RADICAL and not state.axiom_challenged:
        return {
            "status": "error",
            "error_code": "AXIOM_NOT_CHALLENGED",
            "message": (
                "ERROR: Radical premises require calling challenge_axiom first. "
                "Challenge an axiom from extract_hidden_axioms."
            ),
        }
    return None


def check_negative_context(state: SessionState) -> dict | None:
    """Rule 5: Rounds 2+ require get_negative_context before generation."""
    if state.current_round_number >= 1 and not state.negative_context_fetched:
        return {
            "status": "error",
            "error_code": "NEGATIVE_CONTEXT_MISSING",
            "message": (
                "ERROR: Rounds 2+ require calling get_negative_context "
                "before generating premises."
            ),
        }
    return None


def check_buffer_capacity(state: SessionState) -> dict | None:
    """Rule 2: Round buffer accepts exactly 3 premises, no more."""
    if state.premises_in_buffer >= 3:
        return {
            "status": "error",
            "error_code": "ROUND_BUFFER_FULL",
            "message": (
                "ERROR: Round buffer is full (3/3). "
                "Call present_round or discard a premise."
            ),
        }
    return None


def validate_generation_prerequisites(
    state: SessionState, premise_type: str,
) -> dict | None:
    """Chain all generation prerequisite checks. Returns first error or None."""
    return (
        check_gates(state)
        or check_radical_prerequisite(state, premise_type)
        or check_negative_context(state)
        or check_buffer_capacity(state)
    )
