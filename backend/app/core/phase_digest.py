"""Phase Digest Builders — compact context injection for phase transitions.

Invariants:
    - All functions are pure (no IO, no async, no DB)
    - User selection indices used where state flags not yet set (timing rule)
    - Token budgets: Phase 1-5 ~150-400 tokens, Phase 6 ~1200-1500 tokens
    - Empty state -> empty string (except crystallize, which always emits template)

Design Decisions:
    - Extracted from format_messages.py (ADR: ExMA 400-line limit, single responsibility)
    - Progressive compression: earlier phase data shrinks in later digests
    - Crystallize digest maps to Knowledge Document sections (reduces model guesswork)
"""

from app.core.domain_types import Locale
from app.core.forge_state import ForgeState
from app.core import format_messages_pt_br as _pt_br


def _resp_attr(obj, name: str, default=None):
    """Get attribute or dict key — handles both Pydantic models and dicts."""
    if hasattr(obj, name):
        return getattr(obj, name)
    if isinstance(obj, dict):
        return obj.get(name, default)
    return default


# ---------------------------------------------------------------------------
# Phase 1 context (DECOMPOSE -> EXPLORE)
# ---------------------------------------------------------------------------

def build_phase1_context(
    state: ForgeState,
    locale: Locale,
    selected_reframings: list[int] | None = None,
    assumption_responses: list | None = None,
    *,
    reframing_responses: list | None = None,
) -> str:
    """Compact Phase 1 summary for Phase 2 context injection.

    Pure function -- no IO. Uses selection indices (not state flags) because
    this runs BEFORE _apply_user_input sets selected/confirmed flags.
    Limits output to ~150 tokens to prevent context explosion.

    ADR: reframing_responses (new) preferred over selected_reframings (legacy).
    When present, includes user's resonance articulation for richer Phase 2 context.
    """
    pt = locale == Locale.PT_BR
    parts: list[str] = []

    if state.fundamentals:
        label = "Fundamentos:" if pt else "Fundamentals:"
        items = ", ".join(state.fundamentals[:5])
        parts.append(f"{label} {items}")

    # Reframing responses with resonance text (new path)
    if reframing_responses and state.reframings:
        label = (
            "Respostas às reformulações:" if pt
            else "Reframing responses:"
        )
        parts.append(label)
        for resp in reframing_responses:
            idx = _resp_attr(resp, "reframing_index", 0)
            opt_idx = _resp_attr(resp, "selected_option", 0)
            if opt_idx == 0:
                continue  # no perspective shift — skip
            if 0 <= idx < len(state.reframings):
                r = state.reframings[idx]
                text = r.get("text", "")[:120]
                options = r.get("resonance_options", [])
                opt_text = (
                    options[opt_idx] if opt_idx < len(options)
                    else f"option {opt_idx}"
                )
                parts.append(f"  - {text}")
                parts.append(f"    User resonance: '{opt_text}'")

    # Selected reframings by index — backward compat
    elif selected_reframings and state.reframings:
        label = "Reformulações selecionadas:" if pt else "Selected reframings:"
        parts.append(label)
        for idx in selected_reframings:
            if 0 <= idx < len(state.reframings):
                text = state.reframings[idx].get("text", "")[:120]
                if text:
                    parts.append(f"  - {text}")

    if assumption_responses and state.assumptions:
        label = "Respostas aos pressupostos:" if pt else "Assumption responses:"
        parts.append(label)
        for resp in assumption_responses[:5]:
            idx = _resp_attr(resp, "assumption_index", 0)
            opt_idx = _resp_attr(resp, "selected_option", 0)
            if 0 <= idx < len(state.assumptions):
                a = state.assumptions[idx]
                text = a.get("text", "")
                options = a.get("options", [])
                opt_text = options[opt_idx] if opt_idx < len(options) else f"option {opt_idx}"
                parts.append(f"  - {text} → {opt_text}")

    if not parts:
        return ""

    header = (
        _pt_br.DIGEST_PHASE1_HEADER if pt else
        "Phase 1 findings (use these to derive cross-domain analogy sources):"
    )
    return f"\n{header}\n" + "\n".join(parts) + "\n"


# ---------------------------------------------------------------------------
# Phase 2 context (EXPLORE -> SYNTHESIZE)
# ---------------------------------------------------------------------------

def build_phase2_context(
    state: ForgeState,
    locale: Locale,
    starred_analogies: list[int] | None = None,
    *,
    analogy_responses: list | None = None,
) -> str:
    """Phase 2 summary for Phase 3 context. Uses indices for starred analogies
    (not yet set in state at format time). Reads selected_reframings from state
    (already set by prior _apply_user_input).

    ADR: analogy_responses (new) preferred over starred_analogies (legacy).
    When present, includes user's resonance articulation for richer Phase 3 context.
    """
    pt = locale == Locale.PT_BR
    parts: list[str] = []

    # Selected reframings (already set in state from decompose_review)
    sel_reframings = state.selected_reframings
    if sel_reframings:
        label = "Reformulações selecionadas:" if pt else "Selected reframings:"
        parts.append(label)
        for r in sel_reframings[:3]:
            parts.append(f"  - {r.get('text', '')[:120]}")

    # Analogy responses with resonance text (new path)
    if analogy_responses and state.cross_domain_analogies:
        label = (
            "Respostas às analogias:" if pt
            else "Analogy responses:"
        )
        parts.append(label)
        for resp in analogy_responses:
            idx = _resp_attr(resp, "analogy_index", 0)
            opt_idx = _resp_attr(resp, "selected_option", 0)
            if opt_idx == 0:
                continue  # no structural connection — skip
            if 0 <= idx < len(state.cross_domain_analogies):
                a = state.cross_domain_analogies[idx]
                domain = a.get("domain", "")
                desc = a.get("description", "")[:80]
                options = a.get("resonance_options", [])
                opt_text = (
                    options[opt_idx] if opt_idx < len(options)
                    else f"option {opt_idx}"
                )
                parts.append(f"  - [{domain}] {desc}")
                parts.append(f"    User resonance: '{opt_text}'")

    # Starred analogies by index — backward compat (NOT yet set in state)
    elif starred_analogies and state.cross_domain_analogies:
        label = "Analogias marcadas:" if pt else "Starred analogies:"
        parts.append(label)
        for idx in starred_analogies:
            if 0 <= idx < len(state.cross_domain_analogies):
                a = state.cross_domain_analogies[idx]
                domain = a.get("domain", "")
                desc = a.get("description", "")[:80]
                parts.append(f"  - [{domain}] {desc}")

    # Contradictions (already populated by handlers)
    if state.contradictions:
        label = "Contradições:" if pt else "Contradictions:"
        parts.append(label)
        for c in state.contradictions[:3]:
            pa = c.get("property_a", "")
            pb = c.get("property_b", "")
            parts.append(f"  - {pa} vs {pb}")

    # Morphological box parameter names
    if state.morphological_box:
        params = state.morphological_box.get("parameters", [])
        if params:
            label = "Parâmetros morfológicos:" if pt else "Morphological parameters:"
            names = [p.get("name", "") for p in params[:5] if p.get("name")]
            parts.append(f"{label} {', '.join(names)}")

    if not parts:
        return ""

    header = (
        _pt_br.DIGEST_PHASE2_HEADER if pt else
        "Phase 2 findings (use these to derive synthesis directions):"
    )
    return f"\n{header}\n" + "\n".join(parts) + "\n"


# ---------------------------------------------------------------------------
# Phase 3 context (SYNTHESIZE -> VALIDATE)
# ---------------------------------------------------------------------------

def build_phase3_context(
    state: ForgeState,
    locale: Locale,
) -> str:
    """Phase 3 summary for Phase 4 context. No timing issue: claims are set by
    handlers during Phase 3, not by _apply_user_input.
    """
    if not state.current_round_claims:
        return ""

    pt = locale == Locale.PT_BR
    header = (
        _pt_br.DIGEST_PHASE3_HEADER if pt else "Claims to validate:"
    )
    parts: list[str] = [header]

    for i, claim in enumerate(state.current_round_claims):
        text = claim.get("claim_text", "")[:120]
        fc = claim.get("falsifiability_condition", "")[:80]
        ev_count = len(claim.get("evidence", []))
        label_fc = "Condição de falsificabilidade" if pt else "Falsifiability"
        label_ev = "evidências" if pt else "evidence items"
        parts.append(
            f"  [{i}] {text}\n"
            f"      {label_fc}: {fc}\n"
            f"      {ev_count} {label_ev}"
        )

    return "\n" + "\n".join(parts) + "\n"


# ---------------------------------------------------------------------------
# Phase 4 context (VALIDATE -> BUILD)
# ---------------------------------------------------------------------------

def build_phase4_context(
    state: ForgeState,
    locale: Locale,
    verdicts: list | None = None,
) -> str:
    """Phase 4 summary for Phase 5 context. Verdicts come from raw UserInput
    (NOT yet set in state at format time).
    """
    if not state.current_round_claims:
        return ""

    pt = locale == Locale.PT_BR

    # Build verdict lookup from raw input
    verdict_map: dict[int, str] = {}
    if verdicts:
        for v in verdicts:
            idx = (
                v.claim_index if hasattr(v, "claim_index")
                else v.get("claim_index", 0)
            )
            vrd = (
                v.verdict if hasattr(v, "verdict")
                else v.get("verdict", "")
            )
            verdict_map[idx] = vrd

    header = (
        _pt_br.DIGEST_PHASE4_HEADER if pt else "Validation complete:"
    )
    parts: list[str] = [header]

    for i, claim in enumerate(state.current_round_claims):
        text = claim.get("claim_text", "")[:100]
        verdict_str = verdict_map.get(i, "?")
        scores = claim.get("scores", {})
        nov = scores.get("novelty", "?")
        grd = scores.get("groundedness", "?")
        label_v = "Veredicto" if pt else "Verdict"
        parts.append(
            f"  [{i}] {text}\n"
            f"      {label_v}: {verdict_str} | "
            f"novelty={nov}, groundedness={grd}"
        )

    if state.current_round > 0:
        n_nodes = len(state.knowledge_graph_nodes)
        n_edges = len(state.knowledge_graph_edges)
        label_g = "Grafo" if pt else "Graph"
        parts.append(f"  {label_g}: {n_nodes} nodes, {n_edges} edges")

    return "\n" + "\n".join(parts) + "\n"


# ---------------------------------------------------------------------------
# Continue context (BUILD -> SYNTHESIZE, round 2+)
# ---------------------------------------------------------------------------

def build_continue_context(
    state: ForgeState,
    locale: Locale,
) -> str:
    """Cumulative context for round 2+ synthesis. All data already in state."""
    pt = locale == Locale.PT_BR
    parts: list[str] = []

    # Recent graph nodes (last 5)
    if state.knowledge_graph_nodes:
        label = "Nós recentes do grafo:" if pt else "Recent graph nodes:"
        parts.append(label)
        for node in state.knowledge_graph_nodes[-5:]:
            text = node.get("claim_text", "")[:80]
            status = node.get("status", "")
            parts.append(f"  - [{status}] {text}")

    # Negative knowledge (last 3)
    if state.negative_knowledge:
        label = "Conhecimento negativo:" if pt else "Negative knowledge:"
        parts.append(label)
        for nk in state.negative_knowledge[-3:]:
            text = nk.get("claim_text", "")[:80]
            reason = nk.get("rejection_reason", "")[:60]
            parts.append(f"  - {text} (reason: {reason})")

    # Gaps (top 3)
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


# ---------------------------------------------------------------------------
# Crystallize context (BUILD -> CRYSTALLIZE)
# ---------------------------------------------------------------------------

def build_crystallize_context(
    state: ForgeState,
    locale: Locale,
) -> str:
    """Rich digest for Phase 6 -- primary context source for Knowledge Document.

    Section-mapped template organizes data by document sections.
    Budget: ~1200-1500 tokens. Delegates to per-section builders.
    """
    pt = locale == Locale.PT_BR
    header = (
        _pt_br.DIGEST_CRYSTALLIZE_HEADER if pt else
        "== Knowledge Document Sources =="
    )
    parts = [header]
    parts.append(_cryst_problem_framing(state, pt))
    parts.append(_cryst_exploration(state, pt))
    parts.append(_cryst_claims(state, pt))
    parts.append(_cryst_graph_structure(state, pt))
    parts.append(_cryst_negative_knowledge(state, pt))
    parts.append(_cryst_gaps(state, pt))
    s10 = "Rodadas" if pt else "Rounds"
    parts.append(f"\n[S10] {s10}: {state.current_round + 1}")
    return "\n".join(p for p in parts if p) + "\n\n"


def _cryst_problem_framing(state: ForgeState, pt: bool) -> str:
    """Sections 1-2: Reframings + assumptions."""
    sel_ref = state.selected_reframings
    rev_assum = state.reviewed_assumptions
    if not (sel_ref or rev_assum):
        return ""
    lines = ["\n[S1-2]"]
    if sel_ref:
        s = "Reformulações" if pt else "Reframings"
        lines.append(f"  {s}:")
        for r in sel_ref:
            lines.append(f"  - {r.get('text', '')[:120]}")
    if rev_assum:
        s = "Pressupostos" if pt else "Assumptions"
        lines.append(f"  {s}:")
        for a in rev_assum:
            text = a.get("text", "")[:120]
            opt_idx = a.get("selected_option", 0)
            options = a.get("options", [])
            opt_text = options[opt_idx] if opt_idx < len(options) else ""
            if opt_text:
                lines.append(f"  - {text} → {opt_text}")
            else:
                lines.append(f"  - {text}")
    return "\n".join(lines)


def _cryst_exploration(state: ForgeState, pt: bool) -> str:
    """Section 3: Morphological box, analogies, contradictions."""
    morph_count = 0
    if state.morphological_box:
        morph_count = len(state.morphological_box.get("parameters", []))
    analogy_count = len(state.cross_domain_analogies)
    s3 = "Exploração" if pt else "Exploration"
    lines = [
        f"\n[S3] {s3}: {morph_count} morph params, "
        f"{analogy_count} analogies",
    ]
    if state.contradictions:
        s = "Contradições" if pt else "Contradictions"
        lines.append(f"  {s}:")
        for c in state.contradictions:
            pa = c.get("property_a", "")
            pb = c.get("property_b", "")
            lines.append(f"  - {pa} vs {pb}")
    return "\n".join(lines)


def _cryst_claims(state: ForgeState, pt: bool) -> str:
    """Sections 4-5: Validated claims."""
    if not state.knowledge_graph_nodes:
        return ""
    s = "Afirmações validadas" if pt else "Validated claims"
    lines = [f"\n[S4-5] {s}:"]
    for node in state.knowledge_graph_nodes:
        text = node.get("claim_text", "")[:120]
        st = node.get("status", "")
        qual = node.get("qualification", "")
        line = f"  - [{st}] {text}"
        if qual:
            line += f" ({qual})"
        lines.append(line)
    return "\n".join(lines)


def _cryst_graph_structure(state: ForgeState, pt: bool) -> str:
    """Section 6: Graph node/edge counts and edge type summary."""
    n_nodes = len(state.knowledge_graph_nodes)
    n_edges = len(state.knowledge_graph_edges)
    s6 = "Estrutura do grafo" if pt else "Graph structure"
    lines = [f"\n[S6] {s6}: {n_nodes} nodes, {n_edges} edges"]
    if state.knowledge_graph_edges:
        edge_types: dict[str, int] = {}
        for e in state.knowledge_graph_edges:
            et = e.get("type", "unknown")
            edge_types[et] = edge_types.get(et, 0) + 1
        summary = ", ".join(f"{k}={v}" for k, v in edge_types.items())
        lines.append(f"  Edge types: {summary}")
    return "\n".join(lines)


def _cryst_negative_knowledge(state: ForgeState, pt: bool) -> str:
    """Section 7: Rejected claims and reasons."""
    if not state.negative_knowledge:
        return ""
    s7 = "Conhecimento negativo" if pt else "Negative knowledge"
    lines = [f"\n[S7] {s7}:"]
    for nk in state.negative_knowledge:
        text = nk.get("claim_text", "")[:120]
        reason = nk.get("rejection_reason", "")[:80]
        lines.append(f"  - {text} (reason: {reason})")
    return "\n".join(lines)


def _cryst_gaps(state: ForgeState, pt: bool) -> str:
    """Sections 8-9: Knowledge gaps."""
    if not state.gaps:
        return ""
    s89 = "Lacunas" if pt else "Gaps"
    lines = [f"\n[S8-9] {s89}:"]
    for gap in state.gaps:
        lines.append(f"  - {gap[:120]}")
    return "\n".join(lines)
