"""Decompose Handlers — Phase 1 tool implementations (4 methods).

Invariants:
    - All methods follow impureim sandwich: validate (pure) -> execute -> persist (impure)
    - map_state_of_art enforces web_search gate (Rule #12)
    - Results stored in ForgeState AND persisted to DB when needed

Design Decisions:
    - Handler class with db_session + state: explicit dependencies, no globals (ADR: ExMA)
    - Returns dict (not raises): agent_runner consumes tool results as JSON dicts
    - Handlers do NOT call db.commit(): the route layer owns the transaction boundary
      (impureim sandwich — agent_runner commits after token updates)
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.forge_state import ForgeState
from app.core.enforce_phases import check_web_search
from app.core.repository_protocols import SessionLike
from app.models.problem_reframing import ProblemReframing


class DecomposeHandlers:
    """Phase 1: DECOMPOSE — break problem into fundamentals, research, extract assumptions."""

    def __init__(self, db: AsyncSession, state: ForgeState):
        self.db = db
        self.state = state

    async def decompose_to_fundamentals(
        self, session: SessionLike, input_data: dict,
    ) -> dict:
        """Break problem into irreducible elements (First Principles)."""
        fundamentals = input_data.get("fundamentals", [])
        approach = input_data.get("approach", "")

        self.state.fundamentals = fundamentals

        return {
            "status": "ok",
            "fundamentals": fundamentals,
            "approach": approach,
            "count": len(fundamentals),
        }

    async def map_state_of_art(
        self, session: SessionLike, input_data: dict,
    ) -> dict:
        """Research current knowledge. Gate: requires web_search first (Rule #12)."""
        # Pure gate check
        error = check_web_search(self.state, "state_of_art")
        if error:
            return error

        domain = input_data.get("domain", "")
        key_findings = input_data.get("key_findings", [])

        self.state.state_of_art_researched = True

        return {
            "status": "ok",
            "domain": domain,
            "key_findings": key_findings,
            "message": f"State of art mapped for '{domain}' with {len(key_findings)} findings.",
        }

    async def extract_assumptions(
        self, session: SessionLike, input_data: dict,
    ) -> dict:
        """Identify hidden assumptions in the problem domain."""
        assumptions = input_data.get("assumptions", [])

        for assumption in assumptions:
            self.state.assumptions.append({
                "text": assumption.get("text", ""),
                "source": assumption.get("source", ""),
                "confirmed": None,  # awaiting user review
            })

        return {
            "status": "ok",
            "assumptions": self.state.assumptions,
            "count": len(self.state.assumptions),
        }

    async def reframe_problem(
        self, session: SessionLike, input_data: dict,
    ) -> dict:
        """Generate alternative problem formulation."""
        reframing_text = input_data.get("reframing_text", "")
        reframing_type = input_data.get("reframing_type", "scope_change")
        reasoning = input_data.get("reasoning", "")

        self.state.reframings.append({
            "text": reframing_text,
            "type": reframing_type,
            "reasoning": reasoning,
            "selected": False,  # awaiting user review
        })

        # Persist to DB
        reframing = ProblemReframing(
            session_id=session.id,
            original_problem=session.problem,
            reframing_text=reframing_text,
            reframing_type=reframing_type,
        )
        self.db.add(reframing)

        return {
            "status": "ok",
            "reframing_text": reframing_text,
            "reframing_type": reframing_type,
            "total_reframings": len(self.state.reframings),
        }
