"""Generation Handlers — generate_premise, mutate_premise, cross_pollinate.

Invariants:
    - Every method calls validate_generation_prerequisites (pure) before buffer mutation
    - Follows impureim sandwich: read state → pure validate → mutate buffer
    - No DB writes here — premises stored on present_round

Design Decisions:
    - Validation delegated entirely to core/enforce_gates.py (ADR: Functional Core)
    - Buffer mutation is in-memory only — DB persistence deferred to present_round
      (ADR: atomic round writes)
"""

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.session_state import SessionState
from app.core.enforce_gates import validate_generation_prerequisites


class GenerationHandlers:
    """Premise creation handlers — gate-checked, buffer-managed."""

    def __init__(self, db: AsyncSession, state: SessionState):
        self.db = db
        self.state = state

    async def generate_premise(self, session, input_data: dict) -> dict:
        """Generate ONE premise and add to buffer. Gate-checked."""
        # ── PURE: validate all prerequisites ──
        error = validate_generation_prerequisites(
            self.state, input_data.get("premise_type", "initial"),
        )
        if error:
            return error

        # ── IMPURE: mutate buffer ──
        premise_index = self.state.premises_in_buffer
        self.state.current_round_buffer.append(input_data)
        remaining = self.state.premises_remaining

        return {
            "status": "ok",
            "premise_index": premise_index,
            "premises_in_buffer": self.state.premises_in_buffer,
            "premises_remaining": remaining,
            "message": (
                f"Premise #{premise_index + 1} generated and added to buffer. "
                f"{remaining} premise(s) remaining."
                if remaining > 0
                else (
                    f"Premise #{premise_index + 1} generated. "
                    "Buffer complete! Run obviousness_test then "
                    "call present_round."
                )
            ),
        }

    async def mutate_premise(self, session, input_data: dict) -> dict:
        """Mutate existing premise and add to buffer. Gate-checked."""
        error = validate_generation_prerequisites(
            self.state, input_data.get("premise_type", "conservative"),
        )
        if error:
            return error

        premise_index = self.state.premises_in_buffer
        self.state.current_round_buffer.append(input_data)
        remaining = self.state.premises_remaining

        return {
            "status": "ok",
            "premise_index": premise_index,
            "premises_in_buffer": self.state.premises_in_buffer,
            "premises_remaining": remaining,
            "message": (
                f"Mutation applied. Premise #{premise_index + 1} in buffer. "
                f"{remaining} remaining."
            ),
        }

    async def cross_pollinate(self, session, input_data: dict) -> dict:
        """Combine premises and add to buffer. Gate-checked."""
        error = validate_generation_prerequisites(
            self.state, input_data.get("premise_type", "combination"),
        )
        if error:
            return error

        premise_index = self.state.premises_in_buffer
        self.state.current_round_buffer.append(input_data)
        remaining = self.state.premises_remaining

        return {
            "status": "ok",
            "premise_index": premise_index,
            "premises_in_buffer": self.state.premises_in_buffer,
            "premises_remaining": remaining,
            "message": (
                f"Cross-pollination completed. "
                f"Premise #{premise_index + 1} in buffer. "
                f"{remaining} remaining."
            ),
        }
