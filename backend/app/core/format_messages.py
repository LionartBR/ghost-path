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
    - Per-type formatters extracted from format_user_input to stay under ExMA 50-line limit.
"""

from app.core.domain_types import Locale, Phase
from app.core.forge_state import ForgeState
from app.core.language_strings import get_phase_prefix
from app.core import format_messages_pt_br as _pt_br
from app.core import phase_digest as _digest


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


# Re-export for backward compat (tests import from this module)
_build_phase1_context = _digest.build_phase1_context


def format_user_input(
    input_type: str,
    locale_prefix: str,
    *,
    locale: Locale = Locale.EN,
    forge_state: ForgeState | None = None,
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

    Pure function — dispatches to per-type formatters.
    """
    lbl = _labels(locale)
    pt = locale == Locale.PT_BR

    match input_type:
        case "decompose_review":
            return _format_decompose_review(
                locale_prefix, pt, lbl, forge_state,
                confirmed_assumptions, rejected_assumptions,
                added_assumptions, selected_reframings,
                added_reframings, locale,
            )
        case "explore_review":
            return _format_explore_review(
                locale_prefix, pt, lbl, forge_state,
                starred_analogies, suggested_domains,
                added_contradictions, locale,
            )
        case "claims_review":
            return _format_claims_review(
                locale_prefix, pt, lbl, forge_state,
                claim_feedback, locale,
            )
        case "verdicts":
            return _format_verdicts(
                locale_prefix, pt, lbl, forge_state,
                verdicts, locale,
            )
        case "build_decision":
            return _format_build_decision(
                locale_prefix, locale, decision,
                deep_dive_claim_id, user_insight,
                user_evidence_urls, forge_state,
            )

    fallback = _pt_br.UNKNOWN_INPUT if pt else "Unknown user input type."
    return f"{locale_prefix}\n\n{fallback}"


# -- Per-type formatters -------------------------------------------------------

def _format_decompose_review(
    prefix, pt, lbl, forge_state,
    confirmed, rejected, added, selected, added_ref, locale,
):
    """Format decompose_review input."""
    parts = [prefix, f"\n{lbl['reviewed_decomposition']}"]
    if confirmed:
        parts.append(f"{lbl['confirmed']} {confirmed}")
    if rejected:
        parts.append(f"{lbl['rejected']} {rejected}")
    if added:
        parts.append(f"{lbl['added_assumptions']} {added}")
    if selected:
        parts.append(f"{lbl['selected_reframings']} {selected}")
    if added_ref:
        parts.append(f"{lbl['added_reframings']} {added_ref}")
    if forge_state:
        ctx = _build_phase1_context(
            forge_state, locale, selected, confirmed,
        )
        if ctx:
            parts.append(ctx)
    instr = _pt_br.DECOMPOSE_INSTRUCTION if pt else (
        "Proceed to Phase 2 (EXPLORE). Build a morphological box, "
        "search >= 2 distant domains for analogies (use web_search first), "
        "identify contradictions, and map the adjacent possible."
    )
    parts.append(instr)
    return "\n".join(parts)


def _format_explore_review(
    prefix, pt, lbl, forge_state,
    starred, suggested, added_contradictions, locale,
):
    """Format explore_review input."""
    parts = [prefix, f"\n{lbl['reviewed_exploration']}"]
    if forge_state:
        ctx = _digest.build_phase2_context(
            forge_state, locale, starred,
        )
        if ctx:
            parts.append(ctx)
    elif starred:
        parts.append(f"{lbl['starred_analogies']} {starred}")
    if suggested:
        parts.append(f"{lbl['suggested_domains']} {suggested}")
    if added_contradictions:
        parts.append(
            f"{lbl['added_contradictions']} {added_contradictions}",
        )
    instr = _pt_br.EXPLORE_INSTRUCTION if pt else (
        "Proceed to Phase 3 (SYNTHESIZE). For each promising direction, "
        "state a thesis (with evidence), find antithesis (use web_search), "
        "then create a synthesis claim. Generate up to 3 claims this round."
    )
    parts.append(instr)
    return "\n".join(parts)


def _format_claims_review(prefix, pt, lbl, forge_state, feedback, locale):
    """Format claims_review input."""
    parts = [prefix, f"\n{lbl['reviewed_claims']}"]
    if forge_state:
        ctx = _digest.build_phase3_context(forge_state, locale)
        if ctx:
            parts.append(ctx)
    if feedback:
        for fb in feedback:
            _append_claim_feedback(parts, fb, lbl)
    instr = _pt_br.CLAIMS_INSTRUCTION if pt else (
        "Proceed to Phase 4 (VALIDATE). For each claim, attempt "
        "falsification (use web_search to disprove), check novelty "
        "(use web_search), then score each claim."
    )
    parts.append(instr)
    return "\n".join(parts)


def _append_claim_feedback(parts: list, fb, lbl: dict) -> None:
    """Append a single claim's feedback lines to parts."""
    idx = _attr_or_key(fb, "claim_index", 0)
    valid = _attr_or_key(fb, "evidence_valid", True)
    parts.append(lbl['claim_n'].format(idx=idx))
    parts.append(f"{lbl['evidence_valid']} {valid}")
    counter = _attr_or_key(fb, "counter_example", None)
    if counter:
        parts.append(f"{lbl['counter_example']} {counter}")
    ignores = _attr_or_key(fb, "synthesis_ignores", None)
    if ignores:
        parts.append(f"{lbl['missing_factor']} {ignores}")
    additional = _attr_or_key(fb, "additional_evidence", None)
    if additional:
        parts.append(f"{lbl['additional_evidence']} {additional}")


def _format_verdicts(prefix, pt, lbl, forge_state, verdicts, locale):
    """Format verdicts input."""
    parts = [prefix, f"\n{lbl['rendered_verdicts']}"]
    if forge_state:
        ctx = _digest.build_phase4_context(
            forge_state, locale, verdicts,
        )
        if ctx:
            parts.append(ctx)
    if verdicts:
        for v in verdicts:
            _append_verdict_detail(parts, v, lbl)
    instr = _pt_br.VERDICTS_INSTRUCTION if pt else (
        "Proceed to Phase 5 (BUILD). Add accepted/qualified claims to "
        "the knowledge graph, analyze gaps, and present the build review."
    )
    parts.append(instr)
    return "\n".join(parts)


def _append_verdict_detail(parts: list, v, lbl: dict) -> None:
    """Append verdict detail lines (reason/qualification/merge) if present."""
    reason = _attr_or_key(v, "rejection_reason", None)
    qual = _attr_or_key(v, "qualification", None)
    merge = _attr_or_key(v, "merge_with_claim_id", None)
    if not (reason or qual or merge):
        return
    idx = _attr_or_key(v, "claim_index", 0)
    parts.append(lbl['claim_n'].format(idx=idx))
    if reason:
        parts.append(f"{lbl['reason']} {reason}")
    if qual:
        parts.append(f"{lbl['qualification']} {qual}")
    if merge:
        parts.append(f"{lbl['merge_with']} {merge}")


def _attr_or_key(obj, name: str, default=None):
    """Get attribute or dict key — handles both Pydantic models and dicts."""
    if hasattr(obj, name):
        return getattr(obj, name)
    if isinstance(obj, dict):
        return obj.get(name, default)
    return default


def _format_build_decision(
    prefix: str, locale: Locale, decision: str | None,
    claim_id: str | None, insight: str | None,
    urls: list[str] | None, forge_state: ForgeState | None = None,
) -> str:
    """Format build_decision variant."""
    pt = locale == Locale.PT_BR
    if decision == "continue":
        body = _pt_br.BUILD_CONTINUE if pt else (
            "The user wants to continue with another round. "
            "Go back to Phase 3 (SYNTHESIZE). Remember: call "
            "get_negative_knowledge first (Rule #10), and reference "
            "at least one previous claim (Rule #9)."
        )
        ctx = ""
        if forge_state:
            ctx = _digest.build_continue_context(forge_state, locale)
        return f"{prefix}\n\n{ctx}{body}"
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
        ctx = ""
        if forge_state:
            ctx = _digest.build_crystallize_context(forge_state, locale)
        return f"{prefix}\n\n{ctx}{body}"
    elif decision == "add_insight":
        tmpl = _pt_br.BUILD_INSIGHT if pt else (
            'The user wants to add their own insight:\n'
            '"{insight}"\n'
            'Evidence URLs: {urls}\n'
            'Call submit_user_insight to add this to the knowledge '
            'graph, then present the updated build review.'
        )
        return f"{prefix}\n\n{tmpl.format(insight=insight, urls=urls or [])}"
    fallback = _pt_br.UNKNOWN_BUILD if pt else "Unknown build decision."
    return f"{prefix}\n\n{fallback}"


def build_initial_stream_message(
    locale_prefix: str, problem: str, locale: Locale = Locale.EN,
) -> str:
    """Build the initial message for Phase 1 (DECOMPOSE) stream."""
    if locale == Locale.PT_BR:
        body = _pt_br.INITIAL_BODY.format(problem=problem)
    else:
        body = (
            f'The user has submitted the following problem:\n\n'
            f'"{problem}"\n\n'
            f'Begin Phase 1 (DECOMPOSE). Use web_search to research '
            f'the domain, then call decompose_to_fundamentals, '
            f'map_state_of_art, extract_assumptions, and '
            f'reframe_problem (>= 3 reframings). When you are done '
            f'with all decompose tools, output a summary of your '
            f'findings for the user to review.'
        )
    return f'{locale_prefix}\n\n{body}'


def build_resume_message(
    locale_prefix: str, phase: Phase, problem: str,
    locale: Locale = Locale.EN,
) -> str:
    """Build a phase-appropriate message for resuming a session."""
    if phase == Phase.DECOMPOSE:
        return build_initial_stream_message(locale_prefix, problem, locale)

    pt = locale == Locale.PT_BR
    _RESUME = {
        Phase.EXPLORE: (
            _pt_br.RESUME_EXPLORE if pt else
            "Continue Phase 2 (EXPLORE). Build a morphological box, "
            "search >= 2 distant domains for analogies (use "
            "web_search first), identify contradictions, and map "
            "the adjacent possible."
        ),
        Phase.SYNTHESIZE: (
            _pt_br.RESUME_SYNTHESIZE if pt else
            "Continue Phase 3 (SYNTHESIZE). For each promising "
            "direction, state a thesis (with evidence), find "
            "antithesis (use web_search), then create a synthesis "
            "claim. Generate up to 3 claims this round."
        ),
        Phase.VALIDATE: (
            _pt_br.RESUME_VALIDATE if pt else
            "Continue Phase 4 (VALIDATE). For each claim, attempt "
            "falsification (use web_search to disprove), check "
            "novelty (use web_search), then score each claim."
        ),
        Phase.BUILD: (
            _pt_br.RESUME_BUILD if pt else
            "Continue Phase 5 (BUILD). Add accepted/qualified "
            "claims to the knowledge graph, analyze gaps, and "
            "present the build review."
        ),
        Phase.CRYSTALLIZE: (
            _pt_br.RESUME_CRYSTALLIZE if pt else
            "Continue Phase 6 (CRYSTALLIZE). Generate the final "
            "Knowledge Document with all 10 sections using "
            "generate_knowledge_document."
        ),
    }
    body = _RESUME[phase]
    return f"{locale_prefix}\n\n{body}"
