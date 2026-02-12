"""Analysis Handlers — decompose_problem, map_conventional_approaches, extract_hidden_axioms.

Invariants:
    - Each method marks its gate as completed in SessionState
    - Gate completion is idempotent (calling twice does not error)
    - extract_hidden_axioms stores axiom strings for challenge_axiom validation

Design Decisions:
    - No DB writes in gate handlers: gate results are stored in Anthropic message history,
      not in a separate table (ADR: hackathon — gates are ephemeral, session is the aggregate)
    - Axioms stored in SessionState.extracted_axioms: enables challenge_axiom to validate
      that the agent is challenging a real axiom (ADR: enforcement fidelity)
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.session_state import SessionState
from app.core.domain_types import AnalysisGate


class AnalysisHandlers:
    """Gate tool handlers — mark analysis gates as completed."""

    def __init__(self, db: AsyncSession, state: SessionState):
        self.db = db
        self.state = state

    async def decompose_problem(self, session, input_data: dict) -> dict:
        """Gate 1: decompose_problem — marks DECOMPOSE gate as completed."""
        self.state.completed_gates.add(AnalysisGate.DECOMPOSE)
        return {
            "status": "ok",
            "gate": "decompose_problem",
            "message": (
                "Problem decomposed. "
                f"Gates completed: {len(self.state.completed_gates)}/3. "
                f"Missing: {self.state.missing_gates or 'none'}."
            ),
        }

    async def map_conventional_approaches(
        self, session, input_data: dict,
    ) -> dict:
        """Gate 2: map_conventional — marks CONVENTIONAL gate as completed."""
        self.state.completed_gates.add(AnalysisGate.CONVENTIONAL)
        return {
            "status": "ok",
            "gate": "map_conventional_approaches",
            "message": (
                "Conventional approaches mapped. "
                f"Gates completed: {len(self.state.completed_gates)}/3. "
                f"Missing: {self.state.missing_gates or 'none'}."
            ),
        }

    async def extract_hidden_axioms(
        self, session, input_data: dict,
    ) -> dict:
        """Gate 3: extract_axioms — marks AXIOMS gate, stores axiom strings."""
        self.state.completed_gates.add(AnalysisGate.AXIOMS)
        axioms = input_data.get("axioms", [])
        for axiom_obj in axioms:
            axiom_text = axiom_obj.get("axiom", "")
            if axiom_text and axiom_text not in self.state.extracted_axioms:
                self.state.extracted_axioms.append(axiom_text)

        return {
            "status": "ok",
            "gate": "extract_hidden_axioms",
            "axioms_stored": len(self.state.extracted_axioms),
            "message": (
                "Hidden axioms extracted. "
                f"Gates completed: {len(self.state.completed_gates)}/3. "
                f"Missing: {self.state.missing_gates or 'none'}. "
                f"Total axioms available: {len(self.state.extracted_axioms)}."
            ),
        }
