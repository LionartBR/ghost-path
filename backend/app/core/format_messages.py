"""Phase Message Formatting — pure functions for locale-aware agent messages.

Invariants:
    - All functions are pure (no IO, no async, no DB)
    - Message format: [locale prefix] + [user feedback summary] + [phase instruction]
    - PT_BR messages fully translated to prevent English context drift

Design Decisions:
    - Extracted from session_agent_stream.py to core for testability (ADR: ExMA)
    - Lifecycle messages (initial/resume) in format_messages_lifecycle.py
"""
from typing import Any  # noqa: F401 — used in _attr_or_key return type

from app.core.domain_types import Locale
from app.core.forge_state import ForgeState
from app.core import format_messages_pt_br as _pt_br
from app.core import phase_digest as _digest


_LABELS_EN: dict[str, str] = {
    "reviewed_decomposition": "The user reviewed the decomposition:",
    "assumption_responses": "Assumption responses:",
    "custom_argument": "User's argument:",
    "reframing_responses": "Reframing responses:",
    "selected_reframings": "Selected reframings: indices",
    "reviewed_exploration": "The user reviewed the exploration:",
    "analogy_responses": "Analogy responses:",
    "starred_analogies": "Starred analogies: indices",
    "suggested_domains": "Suggested domains to search:",
    "added_contradictions": "Added contradictions:",
    "reviewed_claims": "The user reviewed the claims:",
    "claim_n": "Claim #{idx}:",
    "claim_resonance": "  Resonance: {text}",
    "claim_no_resonance": "  No resonance (user rejected)",
    "custom_argument_claim": "User's argument on claim:",
    "evidence_valid": "  Evidence valid:",
    "counter_example": "  Counter-example:",
    "missing_factor": "  Missing factor:",
    "additional_evidence": "  Additional evidence:",
    "rendered_verdicts": "The user rendered verdicts on the claims:",
    "reason": "  Reason:", "qualification": "  Qualification:",
    "merge_with": "  Merge with:",
}


def _labels(locale: Locale) -> dict[str, str]:
    """Return feedback labels for the given locale."""
    return _pt_br.LABELS_PT_BR if locale == Locale.PT_BR else _LABELS_EN


def format_user_input(
    input_type: str,
    locale_prefix: str,
    *,
    locale: Locale = Locale.EN,
    forge_state: ForgeState | None = None,
    assumption_responses: list | None = None,
    reframing_responses: list | None = None,
    selected_reframings: list[int] | None = None,
    analogy_responses: list | None = None,
    starred_analogies: list[int] | None = None,
    suggested_domains: list[str] | None = None,
    added_contradictions: list[str] | None = None,
    claim_responses: list | None = None,
    claim_feedback: list | None = None,
    verdicts: list | None = None,
    decision: str | None = None,
    deep_dive_claim_id: str | None = None,
    user_insight: str | None = None,
    user_evidence_urls: list[str] | None = None,
    selected_gaps: list[int] | None = None,
    continue_direction: str | None = None,
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
                assumption_responses,
                selected_reframings, locale,
                reframing_responses=reframing_responses,
                suggested_domains=suggested_domains,
            )
        case "explore_review":
            return _format_explore_review(
                locale_prefix, pt, lbl, forge_state,
                starred_analogies, suggested_domains,
                added_contradictions, locale,
                analogy_responses=analogy_responses,
            )
        case "claims_review":
            return _format_claims_review(
                locale_prefix, pt, lbl, forge_state,
                claim_feedback, locale,
                claim_responses=claim_responses,
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
                selected_gaps=selected_gaps,
                continue_direction=continue_direction,
            )

    fallback = _pt_br.UNKNOWN_INPUT if pt else "Unknown user input type."
    return f"{locale_prefix}\n\n{fallback}"


# -- Per-type formatters -------------------------------------------------------

def _format_decompose_review(
    prefix, pt, lbl, forge_state,
    assumption_responses, selected, locale,
    *, reframing_responses=None, suggested_domains=None,
):
    """Format decompose_review input."""
    parts = [prefix, f"\n{lbl['reviewed_decomposition']}"]
    if assumption_responses and forge_state:
        parts.append(lbl['assumption_responses'])
        for resp in assumption_responses:
            idx = _attr_or_key(resp, "assumption_index", 0)
            opt_idx = _attr_or_key(resp, "selected_option", 0)
            custom = _attr_or_key(resp, "custom_argument", None)
            if idx < len(forge_state.assumptions):
                a = forge_state.assumptions[idx]
                text = a.get("text", "")
                if custom:
                    parts.append(f"  [{idx}] '{text}' → {lbl['custom_argument']} '{custom}'")
                else:
                    options = a.get("options", [])
                    opt_text = options[opt_idx] if opt_idx < len(options) else f"option {opt_idx}"
                    parts.append(f"  [{idx}] '{text}' → User: '{opt_text}'")
    if reframing_responses and forge_state:
        parts.append(lbl['reframing_responses'])
        for resp in reframing_responses:
            idx = _attr_or_key(resp, "reframing_index", 0)
            opt_idx = _attr_or_key(resp, "selected_option", 0)
            custom = _attr_or_key(resp, "custom_argument", None)
            if idx < len(forge_state.reframings):
                r = forge_state.reframings[idx]
                text = r.get("text", "")
                if custom:
                    parts.append(f"  [{idx}] '{text}' → {lbl['custom_argument']} '{custom}'")
                else:
                    options = r.get("resonance_options", [])
                    opt_text = options[opt_idx] if opt_idx < len(options) else f"option {opt_idx}"
                    parts.append(f"  [{idx}] '{text}' → User: '{opt_text}'")
    elif selected:
        parts.append(f"{lbl['selected_reframings']} {selected}")
    # Suggested domains for Phase 2
    domains = suggested_domains or (forge_state.user_suggested_domains if forge_state else [])
    if domains:
        parts.append(f"{lbl['suggested_domains']} {domains}")
    if forge_state:
        ctx = _digest.build_phase1_context(
            forge_state, locale, selected, assumption_responses,
            reframing_responses=reframing_responses,
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
    *, analogy_responses=None,
):
    """Format explore_review input."""
    parts = [prefix, f"\n{lbl['reviewed_exploration']}"]
    if forge_state:
        ctx = _digest.build_phase2_context(
            forge_state, locale, starred,
            analogy_responses=analogy_responses,
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


def _format_claims_review(
    prefix, pt, lbl, forge_state, feedback, locale,
    *, claim_responses=None,
):
    """Format claims_review input — resonance (new) or feedback (legacy)."""
    parts = [prefix, f"\n{lbl['reviewed_claims']}"]
    if forge_state:
        ctx = _digest.build_phase3_context(forge_state, locale)
        if ctx:
            parts.append(ctx)
    if claim_responses and forge_state:
        _append_claim_responses(parts, claim_responses, forge_state, lbl)
    elif feedback:
        for fb in feedback:
            _append_claim_feedback(parts, fb, lbl)
    instr = _pt_br.CLAIMS_INSTRUCTION if pt else (
        "Proceed to Phase 4 (VALIDATE). For each claim, attempt "
        "falsification (use web_search to disprove), check novelty "
        "(use web_search), then score each claim."
    )
    parts.append(instr)
    return "\n".join(parts)


def _append_claim_responses(
    parts: list, responses, forge_state, lbl: dict,
) -> None:
    """Append resonance responses — resolves option text from ForgeState claims."""
    for resp in responses:
        idx = _attr_or_key(resp, "claim_index", 0)
        opt_idx = _attr_or_key(resp, "selected_option", 0)
        custom = _attr_or_key(resp, "custom_argument", None)
        parts.append(lbl["claim_n"].format(idx=idx))
        if custom:
            ca_label = lbl.get("custom_argument_claim", lbl.get("custom_argument", "User's argument:"))
            parts.append(f"  {ca_label} '{custom}'")
        elif opt_idx == 0:
            parts.append(lbl["claim_no_resonance"])
        elif idx < len(forge_state.current_round_claims):
            claim = forge_state.current_round_claims[idx]
            options = claim.get("resonance_options", [])
            opt_text = (
                options[opt_idx] if opt_idx < len(options)
                else f"option {opt_idx}"
            )
            parts.append(lbl["claim_resonance"].format(text=opt_text))
        else:
            parts.append(lbl["claim_resonance"].format(text=f"option {opt_idx}"))


def _append_claim_feedback(parts: list, fb, lbl: dict) -> None:
    """Append a single claim's feedback lines to parts (legacy format)."""
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


def _format_verdicts(
    prefix: str, pt: bool, lbl: dict, forge_state: ForgeState | None,
    verdicts: list | None, locale: Locale,
) -> str:
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
    # ADR: check from verdicts param (available before state mutation)
    all_rejected = verdicts and all(
        _attr_or_key(v, "verdict", "accept") == "reject" for v in verdicts
    )
    max_rounds = forge_state and forge_state.max_rounds_reached
    if all_rejected and not max_rounds:
        instr = _pt_br.VERDICTS_ALL_REJECTED if pt else (
            "All claims were rejected. Returning to Phase 3 (SYNTHESIZE) "
            "for a new dialectical round. Call get_negative_knowledge "
            "first (Rule #10), review what failed and why, then reference "
            "at least one previous claim (Rule #9). Generate up to 3 new "
            "claims taking a fundamentally different approach."
        )
    else:
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


def _attr_or_key(obj: object, name: str, default: Any = None) -> Any:
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
    *, selected_gaps: list[int] | None = None,
    continue_direction: str | None = None,
) -> str:
    """Format build_decision variant."""
    pt = locale == Locale.PT_BR
    match decision:
        case "continue":
            return _build_continue(
                prefix, pt, forge_state, locale,
                selected_gaps=selected_gaps,
                continue_direction=continue_direction,
            )
        case "deep_dive":
            return _build_deep_dive(prefix, pt, claim_id)
        case "resolve":
            return _build_resolve(prefix, pt, forge_state, locale)
        case "add_insight":
            return _build_insight(prefix, pt, insight, urls)
    fallback = _pt_br.UNKNOWN_BUILD if pt else "Unknown build decision."
    return f"{prefix}\n\n{fallback}"


def _build_continue(
    prefix, pt, forge_state, locale,
    *, selected_gaps=None, continue_direction=None,
):
    body = _pt_br.BUILD_CONTINUE if pt else (
        "The user wants to continue with another round. "
        "Go back to Phase 3 (SYNTHESIZE). Remember: call "
        "get_negative_knowledge first (Rule #10), and reference "
        "at least one previous claim (Rule #9)."
    )
    ctx = _digest.build_continue_context(forge_state, locale) if forge_state else ""
    gap_section = ""
    if selected_gaps and forge_state and forge_state.gaps:
        gap_header = (
            _pt_br.BUILD_GAPS_FOCUS if pt
            else "The user selected these knowledge gaps to investigate:"
        )
        gap_items = [forge_state.gaps[i] for i in selected_gaps if i < len(forge_state.gaps)]
        if gap_items:
            gap_section = f"\n\n{gap_header}\n" + "\n".join(f"- {g}" for g in gap_items)
    elif continue_direction:
        dir_header = (
            _pt_br.BUILD_DIRECTION_FOCUS if pt
            else "The user wants the next round to focus on:"
        )
        gap_section = f"\n\n{dir_header}\n{continue_direction}"
    return f"{prefix}\n\n{ctx}{body}{gap_section}"


def _build_deep_dive(prefix, pt, claim_id):
    tmpl = _pt_br.BUILD_DEEP_DIVE if pt else (
        "The user wants to deep-dive into claim {claim_id}. "
        "Do a focused EXPLORE -> SYNTHESIZE -> VALIDATE cycle "
        "scoped to this claim only."
    )
    return f"{prefix}\n\n{tmpl.format(claim_id=claim_id)}"


def _build_resolve(prefix, pt, forge_state, locale):
    body = _pt_br.BUILD_RESOLVE if pt else (
        "The user is satisfied with the knowledge graph. "
        "Proceed to Phase 6 (CRYSTALLIZE). Generate the final "
        "Knowledge Document with all 10 sections using "
        "generate_knowledge_document."
    )
    ctx = _digest.build_crystallize_context(forge_state, locale) if forge_state else ""
    return f"{prefix}\n\n{ctx}{body}"


def _build_insight(prefix, pt, insight, urls):
    tmpl = _pt_br.BUILD_INSIGHT if pt else (
        'The user wants to add their own insight:\n'
        '"{insight}"\n'
        'Evidence URLs: {urls}\n'
        'Call submit_user_insight to add this to the knowledge '
        'graph, then present the updated build review.'
    )
    return f"{prefix}\n\n{tmpl.format(insight=insight, urls=urls or [])}"

# Re-exports (backward compat — ADR: callers import from this module)
from app.core.format_messages_lifecycle import build_initial_stream_message, build_resume_message  # noqa: F401, E402, E501
