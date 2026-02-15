"""Phase Digest Builder — Crystallize Context (Phase 6).

Invariants:
    - All functions are pure (no IO, no async, no DB)
    - Section-mapped template organizes data by Knowledge Document sections
    - Token budget: ~1200-1500 tokens
    - Empty sections omitted from output

Design Decisions:
    - Extracted from phase_digest.py (ADR: ExMA 400-line limit per file)
    - build_crystallize_context delegates to 6 per-section builders (_cryst_*)
    - Section markers [S1-2], [S3], etc. guide model's Knowledge Document generation
    - Progressive detail: recent items prioritized, older compressed
"""

from app.core.domain_types import Locale
from app.core.forge_state import ForgeState
from app.core import format_messages_pt_br as _pt_br


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
