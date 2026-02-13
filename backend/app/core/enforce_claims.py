"""Claim Validation Enforcement — validates knowledge claim invariants.

Invariants:
    - All functions are PURE: no IO, no async, no DB, no side effects
    - Return error dict on violation, None on success
    - Claims must go through thesis -> antithesis -> synthesis (dialectical)
    - Every claim must be falsification-tested and novelty-checked before scoring

Design Decisions:
    - Separated from enforce_phases: phase checks guard transitions,
      claim checks guard individual tool calls within a phase (ADR: responsibility separation)
"""

from app.core.forge_state import ForgeState
from app.core.domain_types import MAX_CLAIMS_PER_ROUND


# --- Phase 3: Synthesis validation --------------------------------------------

def check_antithesis_exists(state: ForgeState, claim_index: int) -> dict | None:
    """Rule #3: Every synthesis must have antithesis searched."""
    if claim_index not in state.antitheses_searched:
        return _error(
            "ANTITHESIS_MISSING",
            f"Claim #{claim_index} has no antithesis. Call find_antithesis first.",
        )
    return None


def check_claim_limit(state: ForgeState) -> dict | None:
    """Rule #8: Max 3 claims per synthesis round."""
    if state.claims_in_round >= MAX_CLAIMS_PER_ROUND:
        return _error(
            "CLAIM_LIMIT_EXCEEDED",
            f"Round claim limit reached ({MAX_CLAIMS_PER_ROUND}/{MAX_CLAIMS_PER_ROUND}).",
        )
    return None


# --- Phase 4: Validation checks -----------------------------------------------

def check_falsification(state: ForgeState, claim_index: int) -> dict | None:
    """Rule #5: Every claim must have falsification attempt."""
    if claim_index not in state.falsification_attempted:
        return _error(
            "FALSIFICATION_MISSING",
            f"Claim #{claim_index} has not been falsification-tested.",
        )
    return None


def check_novelty_done(state: ForgeState, claim_index: int) -> dict | None:
    """Rule #6: Every claim must have novelty check."""
    if claim_index not in state.novelty_checked:
        return _error(
            "NOVELTY_UNCHECKED",
            f"Claim #{claim_index} has not been novelty-checked.",
        )
    return None


def check_evidence_grounding(claim: dict) -> dict | None:
    """Rule #7: Claims without external evidence are flagged."""
    evidence = claim.get("evidence", [])
    if not evidence:
        return _error(
            "UNGROUNDED_CLAIM",
            "Claim has no external evidence. Provide web-sourced evidence.",
        )
    return None


def check_claim_index_valid(state: ForgeState, claim_index: int) -> dict | None:
    """Validate that claim_index is within bounds."""
    if claim_index < 0 or claim_index >= state.claims_in_round:
        return _error(
            "INVALID_CLAIM_INDEX",
            f"Invalid claim index {claim_index}. "
            f"Round has {state.claims_in_round} claim(s).",
        )
    return None


# --- Composite validators -----------------------------------------------------

def validate_synthesis_prerequisites(state: ForgeState, claim_index: int) -> dict | None:
    """Validate all prerequisites for creating a synthesis claim."""
    return (
        check_claim_index_valid(state, claim_index)
        or check_claim_limit(state)
        or check_antithesis_exists(state, claim_index)
    )


def validate_scoring_prerequisites(state: ForgeState, claim_index: int) -> dict | None:
    """Validate all prerequisites for scoring a claim (Rule #5 + #6)."""
    return (
        check_claim_index_valid(state, claim_index)
        or check_falsification(state, claim_index)
        or check_novelty_done(state, claim_index)
    )


def validate_graph_addition(state: ForgeState, claim_index: int, verdict: str) -> dict | None:
    """Validate a claim can be added to the knowledge graph."""
    error = check_claim_index_valid(state, claim_index)
    if error:
        return error

    if verdict not in ("accept", "qualify"):
        return _error(
            "INVALID_VERDICT",
            f"Only accepted or qualified claims can be added to graph. Got: {verdict}.",
        )

    return None


# --- Helper -------------------------------------------------------------------

def _error(code: str, message: str) -> dict:
    """Construct a standard error dict."""
    return {
        "status": "error",
        "error_code": code,
        "message": f"ERROR: {message}",
    }
