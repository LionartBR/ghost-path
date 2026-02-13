"""Validate Handlers — Phase 4 tool implementations (3 methods).

Invariants:
    - attempt_falsification enforces web_search gate (Rule #15)
    - check_novelty enforces web_search gate
    - score_claim enforces falsification AND novelty done first (Rules #5, #6)
    - All scores are agent-computed, 0-1 range

Design Decisions:
    - Falsification follows Popperian methodology: knowledge advances through disproof attempts
    - Scores update both ForgeState and DB claim records
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.forge_state import ForgeState
from app.core.enforce_phases import check_web_search
from app.core.enforce_claims import (
    check_claim_index_valid,
    validate_scoring_prerequisites,
)


class ValidateHandlers:
    """Phase 4: VALIDATE — falsification, novelty check, scoring."""

    def __init__(self, db: AsyncSession, state: ForgeState):
        self.db = db
        self.state = state

    async def attempt_falsification(
        self, session: object, input_data: dict,
    ) -> dict:
        """Try to disprove a claim. Gate: web_search required (Rule #15)."""
        error = check_web_search(self.state, "falsification")
        if error:
            return error

        claim_index = input_data.get("claim_index", 0)

        index_error = check_claim_index_valid(self.state, claim_index)
        if index_error:
            return index_error

        falsification_approach = input_data.get("falsification_approach", "")
        result = input_data.get("result", "")
        falsified = input_data.get("falsified", False)
        evidence = input_data.get("evidence", [])

        self.state.falsification_attempted.add(claim_index)

        return {
            "status": "ok",
            "claim_index": claim_index,
            "falsification_approach": falsification_approach,
            "result": result,
            "falsified": falsified,
            "evidence_count": len(evidence),
        }

    async def check_novelty(
        self, session: object, input_data: dict,
    ) -> dict:
        """Verify claim isn't already known. Gate: web_search required."""
        error = check_web_search(self.state, "novelty")
        if error:
            return error

        claim_index = input_data.get("claim_index", 0)

        index_error = check_claim_index_valid(self.state, claim_index)
        if index_error:
            return index_error

        existing_knowledge = input_data.get("existing_knowledge", [])
        is_novel = input_data.get("is_novel", True)
        novelty_explanation = input_data.get("novelty_explanation", "")

        self.state.novelty_checked.add(claim_index)

        return {
            "status": "ok",
            "claim_index": claim_index,
            "is_novel": is_novel,
            "novelty_explanation": novelty_explanation,
            "existing_knowledge_count": len(existing_knowledge),
        }

    async def score_claim(
        self, session: object, input_data: dict,
    ) -> dict:
        """Compute scores. Gate: falsification AND novelty must be done (Rules #5, #6)."""
        claim_index = input_data.get("claim_index", 0)

        # Pure gate check: validates index + falsification + novelty
        error = validate_scoring_prerequisites(self.state, claim_index)
        if error:
            return error

        novelty_score = input_data.get("novelty_score", 0.0)
        groundedness_score = input_data.get("groundedness_score", 0.0)
        falsifiability_score = input_data.get("falsifiability_score", 0.0)
        significance_score = input_data.get("significance_score", 0.0)
        reasoning = input_data.get("reasoning", "")

        # Update claim in buffer
        if claim_index < len(self.state.current_round_claims):
            claim = self.state.current_round_claims[claim_index]
            claim["scores"] = {
                "novelty": novelty_score,
                "groundedness": groundedness_score,
                "falsifiability": falsifiability_score,
                "significance": significance_score,
            }
            claim["score_reasoning"] = reasoning

        return {
            "status": "ok",
            "claim_index": claim_index,
            "scores": {
                "novelty": novelty_score,
                "groundedness": groundedness_score,
                "falsifiability": falsifiability_score,
                "significance": significance_score,
            },
            "reasoning": reasoning,
        }
