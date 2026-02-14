"""Build Handlers — Phase 5 tool implementations (3 methods).

Invariants:
    - add_to_knowledge_graph only accepts claims with verdict accept/qualify
    - get_negative_knowledge sets negative_knowledge_consulted flag (Rule #10)
    - Knowledge graph and negative knowledge persist across rounds

Design Decisions:
    - Graph data stored in ForgeState (in-memory) for fast access during agent loop
    - Also persisted to DB via ClaimEdge model for API retrieval
"""

import uuid as uuid_mod

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.forge_state import ForgeState
from app.core.enforce_claims import validate_graph_addition
from app.core.repository_protocols import SessionLike
from app.models.claim_edge import ClaimEdge


class BuildHandlers:
    """Phase 5: BUILD — knowledge graph construction, gap analysis, negative knowledge."""

    def __init__(self, db: AsyncSession, state: ForgeState):
        self.db = db
        self.state = state

    async def add_to_knowledge_graph(
        self, session: SessionLike, input_data: dict,
    ) -> dict:
        """Add validated claim + edges to knowledge graph."""
        claim_index = input_data.get("claim_index", 0)
        edges = input_data.get("edges", [])

        # Read verdict from claim buffer (set by user in _apply_user_input)
        claim_data = self.state.current_round_claims[claim_index]
        verdict = claim_data.get("verdict", "accept")

        # Pure gate check: claim index valid + verdict is accept/qualify
        error = validate_graph_addition(self.state, claim_index, verdict)
        if error:
            return error

        # Add node to graph
        node = {
            "id": claim_data.get("claim_id", f"claim-{claim_index}-r{self.state.current_round}"),
            "claim_text": claim_data.get("claim_text", ""),
            "confidence": claim_data.get("confidence", "speculative"),
            "status": "qualified" if verdict == "qualify" else "validated",
            "round_created": self.state.current_round,
            "qualification": claim_data.get("qualification") or input_data.get("qualification"),
        }
        self.state.knowledge_graph_nodes.append(node)

        # Add edges to ForgeState + persist to DB
        for edge in edges:
            target_id = edge.get("target_claim_id", "")
            edge_type = edge.get("edge_type", "supports")
            edge_data = {
                "source": node["id"],
                "target": target_id,
                "type": edge_type,
            }
            self.state.knowledge_graph_edges.append(edge_data)

            # Persist ClaimEdge to DB (never crashes)
            source_id = claim_data.get("claim_id")
            if source_id and target_id:
                try:
                    self.db.add(ClaimEdge(
                        session_id=session.id,
                        source_claim_id=uuid_mod.UUID(source_id),
                        target_claim_id=uuid_mod.UUID(target_id),
                        edge_type=edge_type,
                    ))
                except (ValueError, KeyError):
                    pass  # Skip invalid UUIDs

        return {
            "status": "ok",
            "node_id": node["id"],
            "edges_added": len(edges),
            "total_nodes": len(self.state.knowledge_graph_nodes),
            "total_edges": len(self.state.knowledge_graph_edges),
        }

    async def analyze_gaps(
        self, session: SessionLike, input_data: dict,
    ) -> dict:
        """Identify missing prerequisites and disconnected nodes."""
        gaps = input_data.get("gaps", [])
        convergence_locks = input_data.get("convergence_locks", [])

        self.state.gaps = gaps

        return {
            "status": "ok",
            "gaps": gaps,
            "convergence_locks": convergence_locks,
            "total_gaps": len(gaps),
            "graph_nodes": len(self.state.knowledge_graph_nodes),
            "graph_edges": len(self.state.knowledge_graph_edges),
        }

    async def get_negative_knowledge(
        self, session: SessionLike, input_data: dict,
    ) -> dict:
        """Retrieve all rejected claims with rejection reasons (Rule #10 gate)."""
        self.state.negative_knowledge_consulted = True

        return {
            "status": "ok",
            "negative_knowledge": self.state.negative_knowledge,
            "count": len(self.state.negative_knowledge),
            "message": (
                "Negative knowledge consulted. Use these rejected paths "
                "to inform your next round of synthesis."
            ),
        }
