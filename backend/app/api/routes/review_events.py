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
    return {
        "type": "knowledge_document",
        "data": {
            "markdown": state.knowledge_document_markdown,
            "stats": stats,
            "graph": _to_react_flow_graph(state),
            "problem": getattr(session, "problem", "") if session else "",
        },
    }
