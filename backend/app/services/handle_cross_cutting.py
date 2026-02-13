"""Cross-Cutting Handlers — tools available across all phases (2 methods).

Invariants:
    - get_session_status is always available, never gated
    - submit_user_insight creates a user_contributed claim node in the graph

Design Decisions:
    - These tools don't belong to any specific phase — they're utility tools
    - submit_user_insight is called by the agent when processing build_decision.add_insight
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.forge_state import ForgeState
from app.models.knowledge_claim import KnowledgeClaim
from app.models.evidence import Evidence


class CrossCuttingHandlers:
    """Cross-cutting tools — session status and user insight submission."""

    def __init__(self, db: AsyncSession, state: ForgeState):
        self.db = db
        self.state = state

    async def get_session_status(
        self, session: object, input_data: dict,
    ) -> dict:
        """Current phase, round, claims count, gaps count, context usage."""
        return {
            "status": "ok",
            "current_phase": self.state.current_phase.value,
            "current_round": self.state.current_round,
            "claims_this_round": self.state.claims_in_round,
            "total_graph_nodes": len(self.state.knowledge_graph_nodes),
            "total_graph_edges": len(self.state.knowledge_graph_edges),
            "negative_knowledge_count": len(self.state.negative_knowledge),
            "gaps_count": len(self.state.gaps),
            "max_rounds_reached": self.state.max_rounds_reached,
            "deep_dive_active": self.state.deep_dive_active,
            "tokens_used": session.total_tokens_used,
            "tokens_limit": 1_000_000,
        }

    async def submit_user_insight(
        self, session: object, input_data: dict,
    ) -> dict:
        """Create a user-contributed claim node in the knowledge graph."""
        insight_text = input_data.get("insight_text", "")
        evidence_urls = input_data.get("evidence_urls", [])
        relates_to_claim_id = input_data.get("relates_to_claim_id")

        # Persist claim to DB
        db_claim = KnowledgeClaim(
            session_id=session.id,
            claim_text=insight_text,
            claim_type="user_contributed",
            phase_created=5,
            round_created=self.state.current_round,
            status="validated",
            confidence="grounded",
        )
        self.db.add(db_claim)
        await self.db.flush()

        # Persist evidence URLs
        for url in evidence_urls:
            db_evidence = Evidence(
                claim_id=db_claim.id,
                session_id=session.id,
                source_url=url,
                evidence_type="supporting",
                contributed_by="user",
            )
            self.db.add(db_evidence)

        # Add to knowledge graph
        node = {
            "id": str(db_claim.id),
            "claim_text": insight_text,
            "confidence": "grounded",
            "status": "user_contributed",
            "round_created": self.state.current_round,
            "evidence_count": len(evidence_urls),
        }
        self.state.knowledge_graph_nodes.append(node)

        # Add edge if relates to existing claim
        if relates_to_claim_id:
            self.state.knowledge_graph_edges.append({
                "source": str(db_claim.id),
                "target": relates_to_claim_id,
                "type": "extends",
            })

        return {
            "status": "ok",
            "claim_id": str(db_claim.id),
            "insight_text": insight_text,
            "evidence_count": len(evidence_urls),
            "total_graph_nodes": len(self.state.knowledge_graph_nodes),
        }
