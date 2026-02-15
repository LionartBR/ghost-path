"""Phase Digest Builders — compact context injection for phase transitions.

Invariants:
    - All functions are pure (no IO, no async, no DB)
    - User selection indices used where state flags not yet set (timing rule)
    - Token budgets: Phase 1 ~50 tokens, Phase 2-5 ~100-300 tokens, Phase 6 ~1200 tokens
    - Empty state -> empty string (except crystallize, which always emits template)
    - No research digest injection (ADR: agent has recall_phase_context + search_research_archive)
    - No duplication with user feedback section in same message (ADR: format_messages already
      includes assumption/reframing/analogy responses — digest adds only NON-DUPLICATED data)

Design Decisions:
    - Extracted from format_messages.py (ADR: ExMA 400-line limit)
    - Progressive compression: earlier phase data shrinks in later digests
    - Sub-functions keep each builder under 50 lines (ADR: ExMA)
    - Research digests REMOVED — recall tools available from Phase 2 onward,
      system prompt RESEARCH_ARCHIVE section instructs agent to use them
"""

from typing import Any

from app.core.domain_types import Locale
from app.core.forge_state import ForgeState
from app.core import format_messages_pt_br as _pt_br

# Re-export crystallize context builder (used by format_messages.py)
from app.core.phase_digest_crystallize import build_crystallize_context  # noqa: F401


def _resp_attr(obj: object, name: str, default: Any = None) -> Any:
    """Get attribute or dict key — handles Pydantic models and dicts."""
    if hasattr(obj, name):
        return getattr(obj, name)
    if isinstance(obj, dict):
        return obj.get(name, default)
    return default


# ---------------------------------------------------------------------------
# Phase 1 context (DECOMPOSE -> EXPLORE)
# ADR: only fundamentals here — reframings/assumptions already in user feedback
# section of the same message (format_messages._format_decompose_review)
# ---------------------------------------------------------------------------

def build_phase1_context(
    state: ForgeState, locale: Locale,
    selected_reframings: list[int] | None = None,
    assumption_responses: list | None = None,
    *, reframing_responses: list | None = None,
) -> str:
    """Compact Phase 1 summary for Phase 2 context injection.

    Only includes fundamentals — reframings and assumptions are already
    in the user feedback section of the same transition message.
    """
    if not state.fundamentals:
        return ""
    pt = locale == Locale.PT_BR
    label = "Fundamentos:" if pt else "Fundamentals:"
    header = (
        _pt_br.DIGEST_PHASE1_HEADER if pt else
        "Phase 1 findings (use these to derive cross-domain analogy sources):"
    )
    return f"\n{header}\n{label} {', '.join(state.fundamentals[:5])}\n"


# ---------------------------------------------------------------------------
# Phase 2 context (EXPLORE -> SYNTHESIZE)
# ADR: selected reframings removed — available via recall_phase_context("decompose", "reframings")
# ADR: research digest removed — agent has search_research_archive tool
# ---------------------------------------------------------------------------

def build_phase2_context(
    state: ForgeState, locale: Locale,
    starred_analogies: list[int] | None = None,
    *, analogy_responses: list | None = None,
) -> str:
    """Phase 2 summary for Phase 3 context.

    ADR: analogy_responses (new) preferred over starred_analogies (legacy).
    """
    pt = locale == Locale.PT_BR
    parts: list[str] = []
    _append_analogy_digest(parts, state, pt, analogy_responses, starred_analogies)
    _append_contradictions_digest(parts, state, pt)
    _append_morphological_digest(parts, state, pt)
    if not parts:
        return ""
    header = (
        _pt_br.DIGEST_PHASE2_HEADER if pt else
        "Phase 2 findings (use these to derive synthesis directions):"
    )
    return f"\n{header}\n" + "\n".join(parts) + "\n"


def _append_analogy_digest(
    parts: list, state: ForgeState, pt: bool,
    responses: list | None, starred: list[int] | None,
) -> None:
    """Append analogy digest — new resonance path or legacy starred path."""
    if responses and state.cross_domain_analogies:
        label = "Respostas às analogias:" if pt else "Analogy responses:"
        parts.append(label)
        for resp in responses:
            idx = _resp_attr(resp, "analogy_index", 0)
            opt_idx = _resp_attr(resp, "selected_option", 0)
            if opt_idx == 0:
                continue
            if 0 <= idx < len(state.cross_domain_analogies):
                a = state.cross_domain_analogies[idx]
                domain = a.get("domain", "")
                desc = a.get("description", "")[:80]
                options = a.get("resonance_options", [])
                opt = options[opt_idx] if opt_idx < len(options) else f"option {opt_idx}"
                parts.append(f"  - [{domain}] {desc}")
                parts.append(f"    User resonance: '{opt}'")
    elif starred and state.cross_domain_analogies:
        label = "Analogias marcadas:" if pt else "Starred analogies:"
        parts.append(label)
        for idx in starred:
            if 0 <= idx < len(state.cross_domain_analogies):
                a = state.cross_domain_analogies[idx]
                domain = a.get("domain", "")
                desc = a.get("description", "")[:80]
                parts.append(f"  - [{domain}] {desc}")


def _append_contradictions_digest(
    parts: list, state: ForgeState, pt: bool,
) -> None:
    """Append contradictions to parts."""
    if not state.contradictions:
        return
    label = "Contradições:" if pt else "Contradictions:"
    parts.append(label)
    for c in state.contradictions[:3]:
        parts.append(f"  - {c.get('property_a', '')} vs {c.get('property_b', '')}")


def _append_morphological_digest(
    parts: list, state: ForgeState, pt: bool,
) -> None:
    """Append morphological box parameter names."""
    if not state.morphological_box:
        return
    params = state.morphological_box.get("parameters", [])
    if params:
        label = "Parâmetros morfológicos:" if pt else "Morphological parameters:"
        names = [p.get("name", "") for p in params[:5] if p.get("name")]
        parts.append(f"{label} {', '.join(names)}")


# ---------------------------------------------------------------------------
# Phase 3 context (SYNTHESIZE -> VALIDATE)
# ---------------------------------------------------------------------------

def build_phase3_context(state: ForgeState, locale: Locale) -> str:
    """Phase 3 summary for Phase 4 context.

    ADR: research digest removed — agent has search_research_archive tool.
    """
    if not state.current_round_claims:
        return ""
    pt = locale == Locale.PT_BR
    header = _pt_br.DIGEST_PHASE3_HEADER if pt else "Claims to validate:"
    parts: list[str] = [header]
    for i, claim in enumerate(state.current_round_claims):
        text = claim.get("claim_text", "")[:120]
        fc = claim.get("falsifiability_condition", "")[:80]
        ev_count = len(claim.get("evidence", []))
        lfc = "Condição de falsificabilidade" if pt else "Falsifiability"
        lev = "evidências" if pt else "evidence items"
        parts.append(f"  [{i}] {text}\n      {lfc}: {fc}\n      {ev_count} {lev}")
    return "\n" + "\n".join(parts) + "\n"


# ---------------------------------------------------------------------------
# Phase 4 context (VALIDATE -> BUILD)
# ---------------------------------------------------------------------------

def _build_verdict_map(verdicts: list | None) -> dict[int, str]:
    """Build verdict lookup from raw UserInput verdicts."""
    if not verdicts:
        return {}
    result: dict[int, str] = {}
    for v in verdicts:
        idx = _resp_attr(v, "claim_index", 0)
        result[idx] = _resp_attr(v, "verdict", "")
    return result


def build_phase4_context(
    state: ForgeState, locale: Locale, verdicts: list | None = None,
) -> str:
    """Phase 4 summary for Phase 5 context.

    ADR: research digest removed — agent has search_research_archive tool.
    Verdicts kept here (not duplicated: user feedback only has verdict type,
    digest adds scores which are unique).
    """
    if not state.current_round_claims:
        return ""
    pt = locale == Locale.PT_BR
    verdict_map = _build_verdict_map(verdicts)
    header = _pt_br.DIGEST_PHASE4_HEADER if pt else "Validation complete:"
    parts: list[str] = [header]
    for i, claim in enumerate(state.current_round_claims):
        text = claim.get("claim_text", "")[:100]
        vrd = verdict_map.get(i, "?")
        scores = claim.get("scores", {})
        lv = "Veredicto" if pt else "Verdict"
        parts.append(
            f"  [{i}] {text}\n      {lv}: {vrd} | "
            f"novelty={scores.get('novelty', '?')}, "
            f"groundedness={scores.get('groundedness', '?')}"
        )
    if state.current_round > 0:
        n = len(state.knowledge_graph_nodes)
        e = len(state.knowledge_graph_edges)
        lg = "Grafo" if pt else "Graph"
        parts.append(f"  {lg}: {n} nodes, {e} edges")
    return "\n" + "\n".join(parts) + "\n"


# ---------------------------------------------------------------------------
# Continue context (BUILD -> SYNTHESIZE, round 2+)
# ---------------------------------------------------------------------------

def build_continue_context(state: ForgeState, locale: Locale) -> str:
    """Cumulative context for round 2+ synthesis.

    ADR: research digest removed — agent has search_research_archive tool.
    """
    pt = locale == Locale.PT_BR
    parts: list[str] = []
    if state.knowledge_graph_nodes:
        label = "Nós recentes do grafo:" if pt else "Recent graph nodes:"
        parts.append(label)
        for node in state.knowledge_graph_nodes[-5:]:
            parts.append(f"  - [{node.get('status', '')}] {node.get('claim_text', '')[:80]}")
    if state.negative_knowledge:
        label = "Conhecimento negativo:" if pt else "Negative knowledge:"
        parts.append(label)
        for nk in state.negative_knowledge[-3:]:
            parts.append(f"  - {nk.get('claim_text', '')[:80]} (reason: {nk.get('rejection_reason', '')[:60]})")
    if state.gaps:
        label = "Lacunas:" if pt else "Gaps:"
        parts.append(label)
        for gap in state.gaps[:3]:
            parts.append(f"  - {gap[:120]}")
    if not parts:
        return ""
    rnd = state.current_round + 1
    header = (
        _pt_br.DIGEST_CONTINUE_HEADER.format(round=rnd) if pt else
        f"Cumulative context (round {rnd}):"
    )
    return f"{header}\n" + "\n".join(parts) + "\n\n"
