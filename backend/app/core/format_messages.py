"""Phase Message Formatting — pure functions for locale-aware agent messages.

Invariants:
    - All functions are pure (no IO, no async, no DB)
    - Every phase transition message includes locale prefix with problem excerpt
    - Message format follows: [locale prefix] + [user feedback summary] + [phase instruction]

Design Decisions:
    - Extracted from session_agent_stream.py (shell) to core (pure) for testability
      without shell dependencies (SQLAlchemy, FastAPI). ADR: ExMA pure/impure separation.
    - Prefix includes problem excerpt because message_history is cleared on phase transitions,
      and the model needs language context re-anchoring at each phase start.
"""

from app.core.forge_state import ForgeState
from app.core.language_strings import get_phase_prefix


def format_user_input(
    input_type: str,
    locale_prefix: str,
    *,
    confirmed_assumptions: list[int] | None = None,
    rejected_assumptions: list[int] | None = None,
    added_assumptions: list[str] | None = None,
    selected_reframings: list[int] | None = None,
    added_reframings: list[str] | None = None,
    starred_analogies: list[int] | None = None,
    suggested_domains: list[str] | None = None,
    added_contradictions: list[str] | None = None,
    claim_feedback: list | None = None,
    verdicts: list | None = None,
    decision: str | None = None,
    deep_dive_claim_id: str | None = None,
    user_insight: str | None = None,
    user_evidence_urls: list[str] | None = None,
) -> str:
    """Format user input into a message string for the agent.

    Pure function — takes structured data, returns formatted string.
    The locale_prefix is pre-built by the caller via get_phase_prefix().
    """
    match input_type:
        case "decompose_review":
            parts = [locale_prefix, "\nThe user reviewed the decomposition:"]
            if confirmed_assumptions:
                parts.append(f"Confirmed assumptions: indices {confirmed_assumptions}")
            if rejected_assumptions:
                parts.append(f"Rejected assumptions: indices {rejected_assumptions}")
            if added_assumptions:
                parts.append(f"Added assumptions: {added_assumptions}")
            if selected_reframings:
                parts.append(f"Selected reframings: indices {selected_reframings}")
            if added_reframings:
                parts.append(f"Added reframings: {added_reframings}")
            parts.append(
                "Proceed to Phase 2 (EXPLORE). Build a morphological box, "
                "search >= 2 distant domains for analogies (use web_search first), "
                "identify contradictions, and map the adjacent possible."
            )
            return "\n".join(parts)

        case "explore_review":
            parts = [locale_prefix, "\nThe user reviewed the exploration:"]
            if starred_analogies:
                parts.append(f"Starred analogies: indices {starred_analogies}")
            if suggested_domains:
                parts.append(f"Suggested domains to search: {suggested_domains}")
            if added_contradictions:
                parts.append(f"Added contradictions: {added_contradictions}")
            parts.append(
                "Proceed to Phase 3 (SYNTHESIZE). For each promising direction, "
                "state a thesis (with evidence), find antithesis (use web_search), "
                "then create a synthesis claim. Generate up to 3 claims this round."
            )
            return "\n".join(parts)

        case "claims_review":
            parts = [locale_prefix, "\nThe user reviewed the claims:"]
            if claim_feedback:
                for fb in claim_feedback:
                    idx = fb.claim_index if hasattr(fb, "claim_index") else fb.get("claim_index", 0)
                    valid = fb.evidence_valid if hasattr(fb, "evidence_valid") else fb.get("evidence_valid", True)
                    parts.append(f"Claim #{idx}:")
                    parts.append(f"  Evidence valid: {valid}")
                    counter = getattr(fb, "counter_example", None) or (fb.get("counter_example") if isinstance(fb, dict) else None)
                    if counter:
                        parts.append(f"  Counter-example: {counter}")
                    ignores = getattr(fb, "synthesis_ignores", None) or (fb.get("synthesis_ignores") if isinstance(fb, dict) else None)
                    if ignores:
                        parts.append(f"  Missing factor: {ignores}")
                    additional = getattr(fb, "additional_evidence", None) or (fb.get("additional_evidence") if isinstance(fb, dict) else None)
                    if additional:
                        parts.append(f"  Additional evidence: {additional}")
            parts.append(
                "Proceed to Phase 4 (VALIDATE). For each claim, attempt falsification "
                "(use web_search to disprove), check novelty (use web_search), "
                "then score each claim."
            )
            return "\n".join(parts)

        case "verdicts":
            parts = [locale_prefix, "\nThe user rendered verdicts on the claims:"]
            if verdicts:
                for v in verdicts:
                    idx = v.claim_index if hasattr(v, "claim_index") else v.get("claim_index", 0)
                    vrd = v.verdict if hasattr(v, "verdict") else v.get("verdict", "")
                    parts.append(f"Claim #{idx}: {vrd}")
                    reason = getattr(v, "rejection_reason", None) or (v.get("rejection_reason") if isinstance(v, dict) else None)
                    if reason:
                        parts.append(f"  Reason: {reason}")
                    qual = getattr(v, "qualification", None) or (v.get("qualification") if isinstance(v, dict) else None)
                    if qual:
                        parts.append(f"  Qualification: {qual}")
                    merge = getattr(v, "merge_with_claim_id", None) or (v.get("merge_with_claim_id") if isinstance(v, dict) else None)
                    if merge:
                        parts.append(f"  Merge with: {merge}")
            parts.append(
                "Proceed to Phase 5 (BUILD). Add accepted/qualified claims to "
                "the knowledge graph, analyze gaps, and present the build review."
            )
            return "\n".join(parts)

        case "build_decision":
            if decision == "continue":
                return (
                    f"{locale_prefix}\n\n"
                    f"The user wants to continue with another round. "
                    f"Go back to Phase 3 (SYNTHESIZE). Remember: call "
                    f"get_negative_knowledge first (Rule #10), and reference "
                    f"at least one previous claim (Rule #9)."
                )
            elif decision == "deep_dive":
                return (
                    f"{locale_prefix}\n\n"
                    f"The user wants to deep-dive into claim {deep_dive_claim_id}. "
                    f"Do a focused EXPLORE -> SYNTHESIZE -> VALIDATE cycle "
                    f"scoped to this claim only."
                )
            elif decision == "resolve":
                return (
                    f"{locale_prefix}\n\n"
                    f"The user is satisfied with the knowledge graph. "
                    f"Proceed to Phase 6 (CRYSTALLIZE). Generate the final "
                    f"Knowledge Document with all 10 sections using "
                    f"generate_knowledge_document."
                )
            elif decision == "add_insight":
                return (
                    f'{locale_prefix}\n\n'
                    f'The user wants to add their own insight:\n'
                    f'"{user_insight}"\n'
                    f'Evidence URLs: {user_evidence_urls or []}\n'
                    f'Call submit_user_insight to add this to the knowledge graph, '
                    f'then present the updated build review.'
                )
            return f"{locale_prefix}\n\nUnknown build decision."

    return f"{locale_prefix}\n\nUnknown user input type."


def build_initial_stream_message(locale_prefix: str, problem: str) -> str:
    """Build the initial message for Phase 1 (DECOMPOSE) stream.

    Includes locale prefix to anchor language from the first message.
    """
    return (
        f'{locale_prefix}\n\n'
        f'The user has submitted the following problem:\n\n'
        f'"{problem}"\n\n'
        f'Begin Phase 1 (DECOMPOSE). Use web_search to research the domain, '
        f'then call decompose_to_fundamentals, map_state_of_art, '
        f'extract_assumptions, and reframe_problem (>= 3 reframings). '
        f'When you are done with all decompose tools, output a summary '
        f'of your findings for the user to review.'
    )
