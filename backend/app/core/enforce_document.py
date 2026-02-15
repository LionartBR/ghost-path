"""Document Gate Enforcement — blocks phase completion without document update.

Invariants:
    - Agent must call update_working_document at least once per phase (1-5)
    - CRYSTALLIZE (Phase 6) is exempt — document is finalized there
    - Returns nudge message (str) if gate fails, None if ok

Design Decisions:
    - Follows same pattern as check_language in agent_runner_helpers.py
    - Pure function: no IO, no async, no DB — testable in core tests
    - Enforcement in agent_runner (not route handler): agent retries, user never sees failure
"""

from app.core.domain_types import Phase
from app.core.forge_state import ForgeState

# Phases that require at least one document update before completion
_GATED_PHASES = frozenset({
    Phase.DECOMPOSE, Phase.EXPLORE, Phase.SYNTHESIZE,
    Phase.VALIDATE, Phase.BUILD,
})

# Suggested section per phase (hint in the nudge message)
_PHASE_SECTION_HINT: dict[Phase, str] = {
    Phase.DECOMPOSE: "problem_context",
    Phase.EXPLORE: "cross_domain_patterns",
    Phase.SYNTHESIZE: "core_insight",
    Phase.VALIDATE: "evidence_base",
    Phase.BUILD: "boundaries",
}


def check_document_gate(state: ForgeState) -> str | None:
    """Check if agent updated the working document in the current phase.

    Returns None if gate passes, or a nudge message for the agent to retry.
    Only enforced for Phases 1-5 (CRYSTALLIZE is exempt).
    """
    if state.current_phase not in _GATED_PHASES:
        return None
    if state.document_updated_this_phase:
        return None
    hint = _PHASE_SECTION_HINT.get(state.current_phase, "")
    return (
        f"Before completing this phase, call update_working_document to "
        f"capture your discoveries while context is fresh. "
        f"Suggested section for {state.current_phase.value}: \"{hint}\". "
        f"Write a complete section based on what you've found — this content "
        f"will form part of the final Knowledge Document."
    )
