"""Innovation Handlers — challenge_axiom, import_foreign_domain, obviousness_test, invert_problem.

Invariants:
    - challenge_axiom sets axiom_challenged flag (unlocks radical premises)
    - obviousness_test delegates to core/enforce_round.evaluate_obviousness (pure)
    - Rejected premises (score > 0.6) are removed from buffer by this handler
    - Passed premises are marked as tested in SessionState

Design Decisions:
    - evaluate_obviousness is pure — it returns the action, this handler applies it
      (ADR: impureim sandwich — pure decides, shell mutates)
    - Warning (not error) if axiom not in extracted list: agent may rephrase axioms
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.session_state import SessionState
from app.core.enforce_round import evaluate_obviousness


class InnovationHandlers:
    """Originality enforcement handlers."""

    def __init__(self, db: AsyncSession, state: SessionState):
        self.db = db
        self.state = state

    async def challenge_axiom(self, session, input_data: dict) -> dict:
        """Challenge an axiom — unlocks radical premise type."""
        axiom = input_data.get("axiom", "")
        known = axiom in self.state.extracted_axioms

        self.state.axiom_challenged = True

        if not known:
            return {
                "status": "ok",
                "warning": (
                    f"Axiom '{axiom[:80]}' was not in the extracted axioms list. "
                    "Proceeding anyway — radical premises are now unlocked."
                ),
                "axiom_challenged": True,
                "message": (
                    "Axiom challenged (with warning). "
                    "Radical premise type is now available."
                ),
            }

        return {
            "status": "ok",
            "axiom_challenged": True,
            "message": (
                f"Axiom '{axiom[:80]}' challenged via "
                f"'{input_data.get('violation_strategy', 'unknown')}'. "
                "Radical premise type is now available."
            ),
        }

    async def import_foreign_domain(
        self, session, input_data: dict,
    ) -> dict:
        """Find analogy from a semantically distant domain."""
        return {
            "status": "ok",
            "source_domain": input_data.get("source_domain", ""),
            "message": (
                f"Foreign domain analogy imported from "
                f"'{input_data.get('source_domain', 'unknown')}'. "
                f"Insight: {input_data.get('translated_insight', '')[:200]}"
            ),
        }

    async def obviousness_test(self, session, input_data: dict) -> dict:
        """Test premise obviousness. Pure evaluation + shell mutation."""
        premise_index = input_data.get("premise_buffer_index", 0)
        score = input_data.get("obviousness_score", 0.0)

        # ── PURE: evaluate ──
        result = evaluate_obviousness(self.state, premise_index, score)

        # ── IMPURE: apply mutation based on pure result ──
        if result["status"] == "rejected":
            if premise_index < len(self.state.current_round_buffer):
                self.state.current_round_buffer.pop(premise_index)
                # Adjust tested indices after removal
                new_tested = set()
                for idx in self.state.obviousness_tested:
                    if idx < premise_index:
                        new_tested.add(idx)
                    elif idx > premise_index:
                        new_tested.add(idx - 1)
                self.state.obviousness_tested = new_tested
            result["premises_in_buffer"] = self.state.premises_in_buffer
            result["premises_remaining"] = self.state.premises_remaining

        elif result["status"] == "ok":
            self.state.obviousness_tested.add(premise_index)
            untested = (
                self.state.premises_in_buffer
                - len(self.state.obviousness_tested)
            )
            result["premises_tested"] = len(self.state.obviousness_tested)
            result["premises_untested"] = untested
            result["message"] = (
                f"Premise #{premise_index + 1} passed obviousness test "
                f"(score: {score}). "
                f"{untested} premise(s) still need testing."
            )

        return result

    async def invert_problem(self, session, input_data: dict) -> dict:
        """Invert the problem using Munger's technique."""
        return {
            "status": "ok",
            "inversion_type": input_data.get("inversion_type", ""),
            "message": (
                f"Problem inverted via "
                f"'{input_data.get('inversion_type', 'unknown')}'. "
                f"Insights: {input_data.get('insights', [])}"
            ),
        }
