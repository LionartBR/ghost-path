"""Review Event Builders — SSE review event construction for each phase.

Invariants:
    - build_review_event returns the correct SSE event for current phase (excludes DECOMPOSE)
    - build_resume_review_event covers all phases including DECOMPOSE (for reconnection)
    - _to_react_flow_graph transforms ForgeState nodes/edges into React Flow format
    - All functions are pure transforms — no DB, no async, no side effects

Design Decisions:
    - Extracted from session_stream_helpers.py to reduce file size (ADR: ExMA 200-400 lines/file)
    - CRYSTALLIZE event includes stats from compute_session_stats (core/session_stats.py)
    - React Flow transform inline (not via Pydantic) — SSE events bypass schema layer
    - build_resume_review_event extends build_review_event with DECOMPOSE case for reconnection
"""

from app.core.domain_types import Phase
from app.core.forge_state import ForgeState


def _to_react_flow_graph(state: ForgeState) -> dict:
    """Transform flat ForgeState nodes/edges into React Flow format.

    ADR: knowledge_graph_nodes are stored as flat dicts in ForgeState,
    but the frontend expects React Flow format with nested 'data' object.
    The /graph endpoint does this via Pydantic schemas; SSE events need
    the same transform inline.
    """
    nodes = []
    for n in state.knowledge_graph_nodes:
        scores = n.get("scores", {})
        nodes.append({
            "id": n.get("id", ""),
            "type": n.get("status", "proposed"),
            "data": {
                "claim_text": n.get("claim_text", ""),
                "confidence": n.get("confidence"),
                "scores": {
                    "novelty": scores.get("novelty"),
                    "groundedness": scores.get("groundedness"),
                    "falsifiability": scores.get("falsifiability"),
                    "significance": scores.get("significance"),
                },
                "qualification": n.get("qualification"),
                "rejection_reason": n.get("rejection_reason"),
                "evidence_count": n.get("evidence_count", 0),
                "round_created": n.get("round_created", 0),
            },
        })
    edges = [
        {
            "id": f"edge-{i}",
            "source": e.get("source", ""),
            "target": e.get("target", ""),
            "type": e.get("type", "supports"),
        }
        for i, e in enumerate(state.knowledge_graph_edges)
    ]
    return {"nodes": nodes, "edges": edges}


def build_resume_review_event(
    state: ForgeState, session=None,
) -> dict | None:
    """Build review event covering ALL phases (including DECOMPOSE).

    Extends build_review_event (which skips DECOMPOSE) so reconnect
    can re-emit the correct review for any phase.
    """
    if state.current_phase == Phase.DECOMPOSE:
        return {
            "type": "review_decompose",
            "data": {
                "fundamentals": state.fundamentals,
                "assumptions": state.assumptions,
                "reframings": state.reframings,
            },
        }
    return build_review_event(state, session)


def build_review_event(state: ForgeState, session=None) -> dict | None:
    """Build the appropriate review SSE event based on current phase."""
    match state.current_phase:
        case Phase.EXPLORE:
            return {
                "type": "review_explore",
                "data": {
                    "morphological_box": state.morphological_box,
                    "analogies": state.cross_domain_analogies,
                    "contradictions": state.contradictions,
                    "adjacent": state.adjacent_possible,
                },
            }
        case Phase.SYNTHESIZE:
            return {"type": "review_claims", "data": {"claims": state.current_round_claims}}
        case Phase.VALIDATE:
            return {"type": "review_verdicts", "data": {"claims": state.current_round_claims}}
        case Phase.BUILD:
            return {
                "type": "review_build",
                "data": {
                    "graph": _to_react_flow_graph(state),
                    "gaps": state.gaps,
                    "negative_knowledge": state.negative_knowledge,
                    "round": state.current_round,
                    "max_rounds_reached": state.max_rounds_reached,
                },
            }
        case Phase.CRYSTALLIZE:
            return _build_crystallize_event(state, session)
    return None


def _build_crystallize_event(state: ForgeState, session) -> dict | None:
    """Build the knowledge_document SSE event for Phase 6."""
    if not state.knowledge_document_markdown:
        return None
    from app.core.session_stats import compute_session_stats
    stats = compute_session_stats(state)
    if session:
        stats["total_tokens_used"] = getattr(session, "total_tokens_used", 0)
        created = getattr(session, "created_at", None)
        resolved = getattr(session, "resolved_at", None)
        if created and resolved:
            stats["duration_seconds"] = int((resolved - created).total_seconds())
    problem = getattr(session, "problem", "") if session else ""
    return {
        "type": "knowledge_document",
        "data": {
            "markdown": state.knowledge_document_markdown,
            "stats": stats,
            "graph": _to_react_flow_graph(state),
            "problem": problem,
            "problem_summary": _extract_problem_summary(
                state.knowledge_document_markdown, problem,
            ),
        },
    }


def _extract_problem_summary(markdown: str, fallback: str) -> str:
    """Extract first ~250 chars from 'The Discovery' or 'Why This Matters' section.

    ADR: _SECTION_ORDER in handle_crystallize.py maps problem_context → "2. Why This Matters"
    and core_insight → "1. The Discovery". We try The Discovery first (best summary),
    then Why This Matters, then fallback to raw problem text.
    Strips markdown syntax so the result is clean plain text.
    """
    import re
    for heading in (r"The\s+Discovery", r"Why\s+This\s+Matters"):
        match = re.search(
            rf"##\s*\d*\.?\s*{heading}\s*\n+(.*?)(?=\n##|\Z)",
            markdown, re.DOTALL | re.IGNORECASE,
        )
        if match:
            text = match.group(1).strip()
            text = _strip_markdown(text)
            return _truncate_at_word(text, 250)
    return _truncate_at_word(fallback, 250) if fallback else ""


def _strip_markdown(text: str) -> str:
    """Remove markdown syntax, returning clean plain text."""
    import re
    text = re.sub(r"#{1,6}\s+", "", text)           # headings
    text = re.sub(r"\*{1,3}([^*]+)\*{1,3}", r"\1", text)  # bold/italic
    text = re.sub(r"_{1,3}([^_]+)_{1,3}", r"\1", text)    # underscored bold/italic
    text = re.sub(r"`([^`]+)`", r"\1", text)         # inline code
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)  # links [text](url)
    text = re.sub(r"^[-*+]\s+", "", text, flags=re.MULTILINE)  # list bullets
    text = re.sub(r"^\d+\.\s+", "", text, flags=re.MULTILINE)  # numbered lists
    text = re.sub(r"\s+", " ", text)                  # collapse whitespace
    return text.strip()


def _truncate_at_word(text: str, limit: int) -> str:
    """Truncate at word boundary, appending ellipsis."""
    if len(text) <= limit:
        return text
    truncated = text[:limit].rsplit(" ", 1)[0]
    return truncated + "..."
