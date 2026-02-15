"""Phase Transition Enforcement — validates conditions for advancing between phases.

Invariants:
    - All functions are PURE: no IO, no async, no DB, no side effects
    - Return error dict on violation, None on success
    - Phase transitions are user-initiated, not automatic
    - web_search enforcement is heuristic: verifies action, not quality

Design Decisions:
    - Pure functions over method dispatch: testable without mocks (ADR: ExMA Functional Core)
    - Return dicts (not exceptions): agent_runner consumes tool results as JSON dicts,
      keeping error path identical to success path (ADR: uniform tool response shape)
"""

from app.core.forge_state import ForgeState
from app.core.domain_types import Phase


# --- Phase 1 -> 2: Decompose -> Explore --------------------------------------

def check_decompose_complete(state: ForgeState) -> dict | None:
    """Rule #1: Cannot explore without decompose complete.

    Requires: web research done + >=3 assumptions + >=3 reframings + user selected >=1.
    """
    if not state.fundamentals:
        return _error("DECOMPOSE_INCOMPLETE", "Decompose fundamentals not yet identified.")

    if not state.state_of_art_researched:
        return _error("DECOMPOSE_INCOMPLETE", "State of art has not been researched.")

    total_assumptions = len(state.assumptions)
    if total_assumptions < 3:
        return _error(
            "DECOMPOSE_INCOMPLETE",
            f"Need >= 3 assumptions, have {total_assumptions}.",
        )

    total_reframings = len(state.reframings)
    if total_reframings < 3:
        return _error(
            "DECOMPOSE_INCOMPLETE",
            f"Need >= 3 reframings, have {total_reframings}.",
        )

    if not state.selected_reframings:
        return _error(
            "DECOMPOSE_INCOMPLETE",
            "User must select >= 1 reframing or add their own.",
        )

    return None


# --- Phase 2 -> 3: Explore -> Synthesize -------------------------------------

def check_explore_complete(state: ForgeState) -> dict | None:
    """Rule #2: Cannot synthesize without explore complete.

    Requires: morphological box + >=2 cross-domain searches + >=1 contradiction
              + user starred >=1 analogy.
    """
    if state.morphological_box is None:
        return _error("EXPLORE_INCOMPLETE", "Morphological box not built.")

    if state.cross_domain_search_count < 2:
        return _error(
            "EXPLORE_INCOMPLETE",
            f"Need >= 2 cross-domain searches, have {state.cross_domain_search_count}.",
        )

    if not state.contradictions:
        return _error("EXPLORE_INCOMPLETE", "No contradictions identified.")

    if not state.starred_analogies:
        return _error(
            "EXPLORE_INCOMPLETE",
            "User must star >= 1 analogy.",
        )

    return None


# --- Phase 3 -> 4: Synthesize -> Validate ------------------------------------

def check_all_antitheses(state: ForgeState) -> dict | None:
    """Rule #4: Cannot validate without all claims having antithesis."""
    if not state.current_round_claims:
        return _error("SYNTHESIS_INCOMPLETE", "No claims generated this round.")

    if not state.all_claims_have_antithesis:
        missing = len(state.current_round_claims) - len(state.antitheses_searched)
        return _error(
            "SYNTHESIS_INCOMPLETE",
            f"{missing} claim(s) missing antithesis search.",
        )

    return None


# --- Phase 5 -> Phase 3 (new round): Build -> Synthesize ---------------------

def check_cumulative(state: ForgeState) -> dict | None:
    """Rule #9: Round 2+ must reference previous claims."""
    if state.current_round >= 1 and not state.previous_claims_referenced:
        return _error(
            "NOT_CUMULATIVE",
            "Round 2+ must reference >= 1 previous claim via builds_on_claim_id.",
        )
    return None


def check_negative_consulted(state: ForgeState) -> dict | None:
    """Rule #10: Round 2+ must consult negative knowledge."""
    if state.current_round >= 1 and not state.negative_knowledge_consulted:
        return _error(
            "NEGATIVE_KNOWLEDGE_MISSING",
            "Round 2+ must call get_negative_knowledge before synthesis.",
        )
    return None


def check_max_rounds(state: ForgeState) -> dict | None:
    """Rule #11: Max 5 rounds per session."""
    if state.max_rounds_reached:
        return _error(
            "MAX_ROUNDS_EXCEEDED",
            "Maximum 5 rounds reached. Must resolve session.",
        )
    return None


# --- web_search enforcement ---------------------------------------------------

def check_web_search(state: ForgeState, context: str) -> dict | None:
    """Rules #12-15: Verify web_search was called before gated tools.

    Args:
        state: Current forge state.
        context: One of "state_of_art", "cross_domain", "antithesis", "falsification".
    """
    error_map = {
        "state_of_art": (
            "STATE_OF_ART_NOT_RESEARCHED",
            "map_state_of_art requires web_search first.",
        ),
        "cross_domain": (
            "CROSS_DOMAIN_NOT_SEARCHED",
            "search_cross_domain requires web_search for the target domain first.",
        ),
        "antithesis": (
            "ANTITHESIS_NOT_SEARCHED",
            "find_antithesis requires web_search for counter-evidence first.",
        ),
        "falsification": (
            "FALSIFICATION_NOT_SEARCHED",
            "attempt_falsification requires web_search to disprove first.",
        ),
    }

    if context not in error_map:
        return _error("INVALID_CONTEXT", f"Unknown web_search context: {context}")

    if not state.has_web_search_this_phase:
        code, message = error_map[context]
        return _error(code, message)

    return None


# --- Composite validators -----------------------------------------------------

def validate_phase_transition(state: ForgeState, target: Phase) -> dict | None:
    """Validate all gates for transitioning to target phase."""
    if target == Phase.EXPLORE:
        return check_decompose_complete(state)

    if target == Phase.SYNTHESIZE:
        error = check_explore_complete(state)
        if error:
            return error
        if state.current_round >= 1:
            return (
                check_max_rounds(state)
                or check_cumulative(state)
                or check_negative_consulted(state)
            )
        return None

    if target == Phase.VALIDATE:
        return check_all_antitheses(state)

    # BUILD and CRYSTALLIZE transitions validated by tool handlers
    return None


# --- Helper -------------------------------------------------------------------

def _error(code: str, message: str) -> dict:
    """Construct a standard error dict."""
    return {
        "status": "error",
        "error_code": code,
        "message": f"ERROR: {message}",
    }
