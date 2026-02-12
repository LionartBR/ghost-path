"""Interaction Handlers — ask_user, present_round, generate_final_spec.

Invariants:
    - All 3 tools pause the agent loop (set awaiting_user_input = True)
    - present_round validates via core/enforce_round.validate_round_presentation
    - present_round creates DB Round + Premises, then resets SessionState for next round
    - generate_final_spec marks session as resolved

Design Decisions:
    - present_round is the atomic persistence point: buffer → DB happens here,
      not during generate_premise (ADR: atomic round writes)
    - Spec saved to filesystem, not DB: simple download via FileResponse (ADR: hackathon)
"""

import logging
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.session_state import SessionState
from app.core.enforce_round import validate_round_presentation
from app.models.round import Round
from app.models.premise import Premise

logger = logging.getLogger(__name__)


class InteractionHandlers:
    """User-facing tool handlers — all pause the agent loop."""

    def __init__(self, db: AsyncSession, state: SessionState):
        self.db = db
        self.state = state

    async def ask_user(self, session, input_data: dict) -> dict:
        """Ask the user a question — pauses agent loop."""
        self.state.awaiting_user_input = True
        self.state.awaiting_input_type = "ask_user"
        return {
            "status": "ok",
            "message": "Question sent to user. Awaiting response.",
        }

    async def present_round(self, session, input_data: dict) -> dict:
        """Present 3 premises — validates, persists, resets, pauses."""
        # ── PURE: validate round state ──
        error = validate_round_presentation(self.state)
        if error:
            return error

        # ── IMPURE: persist round and premises to DB ──
        round_number = self.state.current_round_number + 1
        db_round = Round(
            session_id=session.id,
            round_number=round_number,
        )
        self.db.add(db_round)
        await self.db.flush()

        premises_data = []
        for premise_dict in self.state.current_round_buffer:
            db_premise = Premise(
                round_id=db_round.id,
                session_id=session.id,
                title=premise_dict.get("title", "Untitled"),
                body=premise_dict.get("body", ""),
                premise_type=premise_dict.get("premise_type", "initial"),
                violated_axiom=premise_dict.get("violated_axiom"),
                cross_domain_source=premise_dict.get("cross_domain_source"),
            )
            self.db.add(db_premise)
            premises_data.append({
                "title": db_premise.title,
                "body": db_premise.body,
                "premise_type": db_premise.premise_type,
                "violated_axiom": db_premise.violated_axiom,
                "cross_domain_source": db_premise.cross_domain_source,
            })

        session.status = "active"
        await self.db.commit()

        # ── PURE: reset state for next round ──
        self.state.reset_for_next_round()
        self.state.current_round_number = round_number
        self.state.awaiting_user_input = True
        self.state.awaiting_input_type = "scores"

        return {
            "status": "awaiting_user_scores",
            "round_number": round_number,
            "premises": premises_data,
            "message": (
                f"Round {round_number} presented with 3 premises. "
                "Awaiting user scores."
            ),
        }

    async def generate_final_spec(
        self, session, input_data: dict,
    ) -> dict:
        """Generate final spec — marks session resolved, pauses loop."""
        session.status = "resolved"
        session.resolved_at = datetime.now(timezone.utc)
        await self.db.commit()

        self.state.awaiting_user_input = True
        self.state.awaiting_input_type = "resolved"

        return {
            "status": "ok",
            "message": "Final spec generated. Session resolved.",
            "spec_content": input_data.get("spec_content", ""),
        }
