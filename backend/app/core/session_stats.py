"""Session Stats — pure computation of session summary statistics from ForgeState.

Invariants:
    - All inputs come from ForgeState fields (no IO, no DB)
    - Returns a flat dict of integer counts (serializable as JSON)
    - Never raises — missing/empty fields default to 0

Design Decisions:
    - Pure function, not a method on ForgeState (ADR: ForgeState is enforcement, stats are presentation)
    - Counts validated/qualified from knowledge_graph_nodes status field
    - Counts rejected from negative_knowledge (removed from graph on rejection)
"""

from app.core.forge_state import ForgeState


def compute_session_stats(state: ForgeState) -> dict:
    """Compute summary statistics from ForgeState. Pure, no IO."""
    nodes = state.knowledge_graph_nodes
    validated = sum(1 for n in nodes if n.get("status") == "validated")
    qualified = sum(1 for n in nodes if n.get("status") == "qualified")
    rejected = len(state.negative_knowledge)
    evidence = sum(n.get("evidence_count", 0) for n in nodes)
    starred = sum(1 for a in state.cross_domain_analogies if a.get("starred"))

    return {
        "total_rounds": state.current_round + 1,
        "claims_validated": validated,
        "claims_rejected": rejected,
        "claims_qualified": qualified,
        "total_claims": len(nodes) + rejected,
        "analogies_used": starred,
        "contradictions_found": len(state.contradictions),
        "evidence_collected": evidence,
        "fundamentals_identified": len(state.fundamentals),
        "assumptions_examined": len(state.assumptions),
        "reframings_explored": len(state.reframings),
        "graph_nodes": len(nodes),
        "graph_edges": len(state.knowledge_graph_edges),
    }
