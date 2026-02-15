"""Cross-Cutting Handlers — tools available across all phases (3 methods).

Invariants:
    - get_session_status is always available, never gated
    - submit_user_insight creates a user_contributed claim node in the graph

Design Decisions:
    - These tools don't belong to any specific phase — they're utility tools
    - submit_user_insight is called by the agent when processing build_decision.add_insight
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.domain_types import Phase
from app.core.forge_state import ForgeState
from app.core.repository_protocols import SessionLike
from app.models.knowledge_claim import KnowledgeClaim
from app.models.evidence import Evidence


# ADR: artifact map for recall_phase_context — module-level constant, not per-call.
_ARTIFACT_MAP = {
    ("decompose", "fundamentals"): lambda s: s.fundamentals,
    ("decompose", "assumptions"): lambda s: s.assumptions,
    ("decompose", "reframings"): lambda s: s.reframings,
    ("explore", "morphological_box"): lambda s: s.morphological_box,
    ("explore", "analogies"): lambda s: s.cross_domain_analogies,
    ("explore", "contradictions"): lambda s: s.contradictions,
    ("explore", "adjacent_possible"): lambda s: s.adjacent_possible,
    ("synthesize", "claims"): lambda s: s.current_round_claims,
    ("validate", "claims"): lambda s: s.current_round_claims,
    ("build", "graph_nodes"): lambda s: s.knowledge_graph_nodes,
    ("build", "graph_edges"): lambda s: s.knowledge_graph_edges,
    ("build", "negative_knowledge"): lambda s: s.negative_knowledge,
    ("build", "gaps"): lambda s: s.gaps,
}


class CrossCuttingHandlers:
    """Cross-cutting tools — session status and user insight submission."""

    def __init__(self, db: AsyncSession, state: ForgeState):
        self.db = db
        self.state = state

    async def get_session_status(
        self, session: SessionLike, input_data: dict,
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

    async def _persist_user_claim(
        self, session: SessionLike, insight_text: str,
    ) -> KnowledgeClaim:
        """Persist user-contributed claim to DB and return the DB object."""
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
        return db_claim

    async def _persist_user_evidence(
        self, session: SessionLike, db_claim: KnowledgeClaim, evidence_urls: list,
    ) -> None:
        """Persist all user-provided evidence URLs."""
        for url in evidence_urls:
            db_evidence = Evidence(
                claim_id=db_claim.id,
                session_id=session.id,
                source_url=url,
                evidence_type="supporting",
                contributed_by="user",
            )
            self.db.add(db_evidence)

    def _add_user_node_to_graph(
        self, claim_id: str, insight_text: str, evidence_count: int, relates_to: str | None,
    ) -> None:
        """Add user insight node and optional edge to knowledge graph."""
        node = {
            "id": claim_id,
            "claim_text": insight_text,
            "confidence": "grounded",
            "status": "user_contributed",
            "round_created": self.state.current_round,
            "evidence_count": evidence_count,
        }
        self.state.knowledge_graph_nodes.append(node)
        if relates_to:
            self.state.knowledge_graph_edges.append({
                "source": claim_id,
                "target": relates_to,
                "type": "extends",
            })

    async def submit_user_insight(
        self, session: SessionLike, input_data: dict,
    ) -> dict:
        """Create a user-contributed claim node in the knowledge graph."""
        insight_text = input_data.get("insight_text", "")
        evidence_urls = input_data.get("evidence_urls", [])
        relates_to_claim_id = input_data.get("relates_to_claim_id")

        # Persist claim to DB
        db_claim = await self._persist_user_claim(session, insight_text)

        # Persist evidence URLs
        await self._persist_user_evidence(session, db_claim, evidence_urls)

        # Add to knowledge graph
        claim_id = str(db_claim.id)
        self._add_user_node_to_graph(claim_id, insight_text, len(evidence_urls), relates_to_claim_id)

        return {
            "status": "ok",
            "claim_id": claim_id,
            "insight_text": insight_text,
            "evidence_count": len(evidence_urls),
            "total_graph_nodes": len(self.state.knowledge_graph_nodes),
        }

    def _validate_phase_request(self, phase_str: str) -> tuple[Phase | None, dict | None]:
        """Validate phase string. Returns (Phase, None) or (None, error_dict)."""
        try:
            requested = Phase(phase_str)
            return requested, None
        except ValueError:
            return None, {
                "status": "error",
                "error_code": "INVALID_PHASE",
                "message": f"Unknown phase: '{phase_str}'",
            }

    def _check_phase_accessibility(self, requested: Phase) -> bool:
        """Check if requested phase has completed and has data available."""
        if self.state.current_round > 0:
            # Round 2+: every phase except CRYSTALLIZE has data
            return requested != Phase.CRYSTALLIZE
        else:
            # Round 0: current phase and all earlier phases have data
            phase_order = list(Phase)
            current_idx = phase_order.index(self.state.current_phase)
            requested_idx = phase_order.index(requested)
            return requested_idx <= current_idx

    async def recall_phase_context(
        self, session: SessionLike, input_data: dict,
    ) -> dict:
        """Retrieve detailed artifacts from a completed phase. Read-only."""
        phase_str = input_data.get("phase", "")
        artifact = input_data.get("artifact", "")

        # Validate phase
        requested, error = self._validate_phase_request(phase_str)
        if error:
            return error

        # Check accessibility (requested is guaranteed non-None after error check above)
        if requested is None:
            return {"status": "error", "error_code": "INVALID_PHASE", "message": "No phase"}
        if not self._check_phase_accessibility(requested):
            return {
                "status": "error",
                "error_code": "PHASE_NOT_COMPLETED",
                "message": (
                    f"Phase '{phase_str}' not yet completed "
                    f"(current: {self.state.current_phase.value})"
                ),
            }

        # Retrieve artifact
        getter = _ARTIFACT_MAP.get((phase_str, artifact))
        if not getter:
            return {
                "status": "error",
                "error_code": "ARTIFACT_NOT_FOUND",
                "message": (
                    f"'{artifact}' not available for phase '{phase_str}'"
                ),
            }

        return {
            "status": "ok",
            "phase": phase_str,
            "artifact": artifact,
            "data": getter(self.state),
        }
