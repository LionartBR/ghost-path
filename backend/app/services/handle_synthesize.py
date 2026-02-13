"""Synthesize Handlers — Phase 3 tool implementations (3 methods).

Invariants:
    - Dialectical pattern: thesis -> antithesis (web_search) -> synthesis
    - find_antithesis enforces web_search gate (Rule #14)
    - create_synthesis enforces antithesis existence (Rule #3) and claim limit (Rule #8)
    - builds_on_claim_id sets previous_claims_referenced flag (Rule #9)

Design Decisions:
    - Claims stored in ForgeState buffer AND persisted to DB
    - Evidence stored alongside claims for Knowledge Document generation
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.forge_state import ForgeState
from app.core.enforce_phases import check_web_search
from app.core.enforce_claims import check_antithesis_exists, check_claim_limit
from app.models.knowledge_claim import KnowledgeClaim
from app.models.evidence import Evidence


class SynthesizeHandlers:
    """Phase 3: SYNTHESIZE — thesis, antithesis, synthesis (Hegelian dialectics)."""

    def __init__(self, db: AsyncSession, state: ForgeState):
        self.db = db
        self.state = state

    async def state_thesis(
        self, session: object, input_data: dict,
    ) -> dict:
        """Declare current knowledge on a direction."""
        thesis_text = input_data.get("thesis_text", "")
        direction = input_data.get("direction", "")
        supporting_evidence = input_data.get("supporting_evidence", [])

        self.state.theses_stated += 1

        return {
            "status": "ok",
            "thesis_text": thesis_text,
            "direction": direction,
            "supporting_evidence_count": len(supporting_evidence),
            "thesis_number": self.state.theses_stated,
        }

    async def find_antithesis(
        self, session: object, input_data: dict,
    ) -> dict:
        """Search for contradicting evidence. Gate: web_search required (Rule #14)."""
        error = check_web_search(self.state, "antithesis")
        if error:
            return error

        claim_index = input_data.get("claim_index", self.state.theses_stated - 1)
        antithesis_text = input_data.get("antithesis_text", "")
        contradicting_evidence = input_data.get("contradicting_evidence", [])

        self.state.antitheses_searched.add(claim_index)

        return {
            "status": "ok",
            "claim_index": claim_index,
            "antithesis_text": antithesis_text,
            "contradicting_evidence_count": len(contradicting_evidence),
        }

    async def create_synthesis(
        self, session: object, input_data: dict,
    ) -> dict:
        """Generate knowledge claim from thesis + antithesis (dialectical synthesis).

        Gates: Rule #3 (antithesis must exist), Rule #8 (max 3 claims per round).
        """
        claim_index = input_data.get("claim_index", self.state.theses_stated - 1)

        # Pure gate checks
        limit_error = check_claim_limit(self.state)
        if limit_error:
            return limit_error

        antithesis_error = check_antithesis_exists(self.state, claim_index)
        if antithesis_error:
            return antithesis_error

        claim_text = input_data.get("claim_text", "")
        reasoning = input_data.get("reasoning", "")
        falsifiability_condition = input_data.get("falsifiability_condition", "")
        confidence = input_data.get("confidence", "speculative")
        evidence_list = input_data.get("evidence", [])
        builds_on_claim_id = input_data.get("builds_on_claim_id")

        # Rule #9: track cumulative reference
        if builds_on_claim_id:
            # Validate the referenced claim exists in knowledge graph
            found = any(
                n.get("id") == builds_on_claim_id
                for n in self.state.knowledge_graph_nodes
            )
            if found:
                self.state.previous_claims_referenced = True

        # Add to round buffer
        claim_data = {
            "claim_text": claim_text,
            "reasoning": reasoning,
            "falsifiability_condition": falsifiability_condition,
            "confidence": confidence,
            "evidence": evidence_list,
            "builds_on_claim_id": builds_on_claim_id,
        }
        self.state.current_round_claims.append(claim_data)

        # Persist claim to DB
        thesis_text = input_data.get("thesis_text", "")
        antithesis_text = input_data.get("antithesis_text", "")
        db_claim = KnowledgeClaim(
            session_id=session.id,
            claim_text=claim_text,
            claim_type="synthesis",
            thesis_text=thesis_text,
            antithesis_text=antithesis_text,
            phase_created=3,
            round_created=self.state.current_round,
            status="proposed",
            confidence=confidence,
            falsifiability_condition=falsifiability_condition,
        )
        self.db.add(db_claim)
        await self.db.flush()

        # Store claim_id back in buffer for BUILD phase graph construction
        claim_data["claim_id"] = str(db_claim.id)

        # Persist evidence
        for ev in evidence_list:
            db_evidence = Evidence(
                claim_id=db_claim.id,
                session_id=session.id,
                source_url=ev.get("url", ""),
                source_title=ev.get("title", ""),
                content_summary=ev.get("summary", ""),
                evidence_type=ev.get("type", "supporting"),
                contributed_by="agent",
            )
            self.db.add(db_evidence)

        return {
            "status": "ok",
            "claim_text": claim_text,
            "claim_index": self.state.claims_in_round - 1,
            "confidence": confidence,
            "claims_this_round": self.state.claims_in_round,
            "claims_remaining": self.state.claims_remaining,
            "claim_id": str(db_claim.id),
        }
