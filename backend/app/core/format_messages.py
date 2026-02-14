"""Phase Message Formatting — pure functions for locale-aware agent messages.

Invariants:
    - All functions are pure (no IO, no async, no DB)
    - Every phase transition message includes locale prefix with problem excerpt
    - Message format follows: [locale prefix] + [user feedback summary] + [phase instruction]
    - PT_BR messages are fully translated (not just prefixed) to prevent English context drift

Design Decisions:
    - Extracted from session_agent_stream.py (shell) to core (pure) for testability
      without shell dependencies (SQLAlchemy, FastAPI). ADR: ExMA pure/impure separation.
    - Prefix includes problem excerpt because message_history is cleared on phase transitions,
      and the model needs language context re-anchoring at each phase start.
    - Full PT_BR translation of message bodies (ADR: the model drifted to English because
      user-role messages had English instructions after a Portuguese prefix; recency bias
      caused the English body to override the Portuguese system prompt).
"""

from app.core.domain_types import Locale
from app.core.forge_state import ForgeState
from app.core.language_strings import get_phase_prefix
from app.core import format_messages_pt_br as _pt_br


def _labels(locale: Locale) -> dict[str, str]:
    """Return feedback labels for the given locale."""
    if locale == Locale.PT_BR:
        return _pt_br.LABELS_PT_BR
    return {
        "reviewed_decomposition": "The user reviewed the decomposition:",
        "confirmed": "Confirmed assumptions: indices",
        "rejected": "Rejected assumptions: indices",
        "added_assumptions": "Added assumptions:",
        "selected_reframings": "Selected reframings: indices",
        "added_reframings": "Added reframings:",
        "reviewed_exploration": "The user reviewed the exploration:",
        "starred_analogies": "Starred analogies: indices",
        "suggested_domains": "Suggested domains to search:",
        "added_contradictions": "Added contradictions:",
        "reviewed_claims": "The user reviewed the claims:",
        "claim_n": "Claim #{idx}:",
        "evidence_valid": "  Evidence valid:",
        "counter_example": "  Counter-example:",
        "missing_factor": "  Missing factor:",
        "additional_evidence": "  Additional evidence:",
        "rendered_verdicts": "The user rendered verdicts on the claims:",
        "reason": "  Reason:",
        "qualification": "  Qualification:",
        "merge_with": "  Merge with:",
    }


def format_user_input(
    input_type: str,
    locale_prefix: str,
    *,
    locale: Locale = Locale.EN,
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
    For PT_BR, message bodies are fully translated to prevent English drift.
    """
    pt = locale == Locale.PT_BR
    lbl = _labels(locale)

    match input_type:
        case "decompose_review":
            parts = [locale_prefix, f"\n{lbl['reviewed_decomposition']}"]
            if confirmed_assumptions:
                parts.append(f"{lbl['confirmed']} {confirmed_assumptions}")
            if rejected_assumptions:
                parts.append(f"{lbl['rejected']} {rejected_assumptions}")
            if added_assumptions:
                parts.append(f"{lbl['added_assumptions']} {added_assumptions}")
            if selected_reframings:
                parts.append(f"{lbl['selected_reframings']} {selected_reframings}")
            if added_reframings:
                parts.append(f"{lbl['added_reframings']} {added_reframings}")
            instr = _pt_br.DECOMPOSE_INSTRUCTION if pt else (
                "Proceed to Phase 2 (EXPLORE). Build a morphological box, "
                "search >= 2 distant domains for analogies (use web_search first), "
                "identify contradictions, and map the adjacent possible."
            )
            parts.append(instr)
            return "\n".join(parts)

        case "explore_review":
            parts = [locale_prefix, f"\n{lbl['reviewed_exploration']}"]
            if starred_analogies:
                parts.append(f"{lbl['starred_analogies']} {starred_analogies}")
            if suggested_domains:
                parts.append(f"{lbl['suggested_domains']} {suggested_domains}")
            if added_contradictions:
                parts.append(f"{lbl['added_contradictions']} {added_contradictions}")
            instr = _pt_br.EXPLORE_INSTRUCTION if pt else (
                "Proceed to Phase 3 (SYNTHESIZE). For each promising direction, "
                "state a thesis (with evidence), find antithesis (use web_search), "
                "then create a synthesis claim. Generate up to 3 claims this round."
            )
            parts.append(instr)
            return "\n".join(parts)

        case "claims_review":
            parts = [locale_prefix, f"\n{lbl['reviewed_claims']}"]
            if claim_feedback:
                for fb in claim_feedback:
                    idx = fb.claim_index if hasattr(fb, "claim_index") else fb.get("claim_index", 0)
                    valid = fb.evidence_valid if hasattr(fb, "evidence_valid") else fb.get("evidence_valid", True)
                    parts.append(lbl['claim_n'].format(idx=idx))
                    parts.append(f"{lbl['evidence_valid']} {valid}")
                    counter = getattr(fb, "counter_example", None) or (fb.get("counter_example") if isinstance(fb, dict) else None)
                    if counter:
                        parts.append(f"{lbl['counter_example']} {counter}")
                    ignores = getattr(fb, "synthesis_ignores", None) or (fb.get("synthesis_ignores") if isinstance(fb, dict) else None)
                    if ignores:
                        parts.append(f"{lbl['missing_factor']} {ignores}")
                    additional = getattr(fb, "additional_evidence", None) or (fb.get("additional_evidence") if isinstance(fb, dict) else None)
                    if additional:
                        parts.append(f"{lbl['additional_evidence']} {additional}")
            instr = _pt_br.CLAIMS_INSTRUCTION if pt else (
                "Proceed to Phase 4 (VALIDATE). For each claim, attempt falsification "
                "(use web_search to disprove), check novelty (use web_search), "
                "then score each claim."
            )
            parts.append(instr)
            return "\n".join(parts)

        case "verdicts":
            parts = [locale_prefix, f"\n{lbl['rendered_verdicts']}"]
            if verdicts:
                for v in verdicts:
                    idx = v.claim_index if hasattr(v, "claim_index") else v.get("claim_index", 0)
                    vrd = v.verdict if hasattr(v, "verdict") else v.get("verdict", "")
                    parts.append(lbl['claim_n'].format(idx=idx))
                    parts.append(f"  {vrd}")
                    reason = getattr(v, "rejection_reason", None) or (v.get("rejection_reason") if isinstance(v, dict) else None)
                    if reason:
                        parts.append(f"{lbl['reason']} {reason}")
                    qual = getattr(v, "qualification", None) or (v.get("qualification") if isinstance(v, dict) else None)
                    if qual:
                        parts.append(f"{lbl['qualification']} {qual}")
                    merge = getattr(v, "merge_with_claim_id", None) or (v.get("merge_with_claim_id") if isinstance(v, dict) else None)
                    if merge:
                        parts.append(f"{lbl['merge_with']} {merge}")
            instr = _pt_br.VERDICTS_INSTRUCTION if pt else (
                "Proceed to Phase 5 (BUILD). Add accepted/qualified claims to "
                "the knowledge graph, analyze gaps, and present the build review."
            )
            parts.append(instr)
            return "\n".join(parts)

        case "build_decision":
            return _format_build_decision(
                locale_prefix, locale, decision,
                deep_dive_claim_id, user_insight, user_evidence_urls,
            )

    fallback = _pt_br.UNKNOWN_INPUT if pt else "Unknown user input type."
    return f"{locale_prefix}\n\n{fallback}"


def _format_build_decision(
    prefix: str, locale: Locale, decision: str | None,
    claim_id: str | None, insight: str | None, urls: list[str] | None,
) -> str:
    """Format build_decision variant. Extracted to keep format_user_input under 50 lines."""
    pt = locale == Locale.PT_BR
    if decision == "continue":
        body = _pt_br.BUILD_CONTINUE if pt else (
            "The user wants to continue with another round. "
            "Go back to Phase 3 (SYNTHESIZE). Remember: call "
            "get_negative_knowledge first (Rule #10), and reference "
            "at least one previous claim (Rule #9)."
        )
        return f"{prefix}\n\n{body}"
    elif decision == "deep_dive":
        tmpl = _pt_br.BUILD_DEEP_DIVE if pt else (
            "The user wants to deep-dive into claim {claim_id}. "
            "Do a focused EXPLORE -> SYNTHESIZE -> VALIDATE cycle "
            "scoped to this claim only."
        )
        return f"{prefix}\n\n{tmpl.format(claim_id=claim_id)}"
    elif decision == "resolve":
        body = _pt_br.BUILD_RESOLVE if pt else (
            "The user is satisfied with the knowledge graph. "
            "Proceed to Phase 6 (CRYSTALLIZE). Generate the final "
            "Knowledge Document with all 10 sections using "
            "generate_knowledge_document."
        )
        return f"{prefix}\n\n{body}"
    elif decision == "add_insight":
        tmpl = _pt_br.BUILD_INSIGHT if pt else (
            'The user wants to add their own insight:\n'
            '"{insight}"\n'
            'Evidence URLs: {urls}\n'
            'Call submit_user_insight to add this to the knowledge graph, '
            'then present the updated build review.'
        )
        return f"{prefix}\n\n{tmpl.format(insight=insight, urls=urls or [])}"
    fallback = _pt_br.UNKNOWN_BUILD if pt else "Unknown build decision."
    return f"{prefix}\n\n{fallback}"


def build_initial_stream_message(
    locale_prefix: str, problem: str, locale: Locale = Locale.EN,
) -> str:
    """Build the initial message for Phase 1 (DECOMPOSE) stream.

    Includes locale prefix to anchor language from the first message.
    For PT_BR, the entire body is in Portuguese to prevent English drift.
    """
    if locale == Locale.PT_BR:
        body = _pt_br.INITIAL_BODY.format(problem=problem)
    else:
        body = (
            f'The user has submitted the following problem:\n\n'
            f'"{problem}"\n\n'
            f'Begin Phase 1 (DECOMPOSE). Use web_search to research the domain, '
            f'then call decompose_to_fundamentals, map_state_of_art, '
            f'extract_assumptions, and reframe_problem (>= 3 reframings). '
            f'When you are done with all decompose tools, output a summary '
            f'of your findings for the user to review.'
        )
    return f'{locale_prefix}\n\n{body}'
