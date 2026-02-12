"""Memory Handlers — store_premise, query_premises, get_negative_context, get_context_usage.

Invariants:
    - store_premise persists premise to DB (requires existing round for session)
    - get_negative_context sets negative_context_fetched flag (unlocks generation rounds 2+)
    - get_context_usage reads from session.total_tokens_used (no side effects)

Design Decisions:
    - query_premises uses filter enum: prevents arbitrary SQL queries (ADR: security)
    - get_negative_context fetches premises with score < 5.0: aligns with spec definition
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.session_state import SessionState
from app.models.premise import Premise
from app.models.round import Round

logger = logging.getLogger(__name__)


class MemoryHandlers:
    """Persistence and context tool handlers."""

    def __init__(self, db: AsyncSession, state: SessionState):
        self.db = db
        self.state = state

    async def store_premise(self, session, input_data: dict) -> dict:
        """Store premise with score and comment to DB."""
        round_number = input_data.get("round_number", 1)

        # Find or create round
        result = await self.db.execute(
            select(Round)
            .where(Round.session_id == session.id)
            .where(Round.round_number == round_number)
        )
        db_round = result.scalar_one_or_none()
        if not db_round:
            db_round = Round(
                session_id=session.id, round_number=round_number,
            )
            self.db.add(db_round)
            await self.db.flush()

        premise = Premise(
            round_id=db_round.id,
            session_id=session.id,
            title=input_data.get("title", "Untitled"),
            body=input_data.get("body", ""),
            premise_type=input_data.get("premise_type", "initial"),
            score=input_data.get("score"),
            user_comment=input_data.get("user_comment"),
            is_winner=input_data.get("is_winner", False),
        )
        self.db.add(premise)
        await self.db.commit()

        return {
            "status": "ok",
            "premise_id": str(premise.id),
            "message": f"Premise '{premise.title}' stored successfully.",
        }

    async def query_premises(self, session, input_data: dict) -> dict:
        """Query premises by filter."""
        filter_type = input_data.get("filter", "all")
        limit = input_data.get("limit", 10)

        query = (
            select(Premise)
            .where(Premise.session_id == session.id)
        )

        if filter_type == "winners":
            query = query.where(Premise.is_winner.is_(True))
        elif filter_type == "top_scored":
            query = (
                query.where(Premise.score.isnot(None))
                .order_by(Premise.score.desc())
            )
        elif filter_type == "low_scored":
            query = (
                query.where(Premise.score.isnot(None))
                .where(Premise.score < 5.0)
            )
        elif filter_type == "by_type":
            premise_type = input_data.get("premise_type", "initial")
            query = query.where(Premise.premise_type == premise_type)
        elif filter_type == "by_round":
            round_number = input_data.get("round_number", 1)
            query = query.join(Round).where(
                Round.round_number == round_number,
            )

        query = query.limit(limit)
        result = await self.db.execute(query)
        premises = result.scalars().all()

        return {
            "status": "ok",
            "count": len(premises),
            "premises": [
                {
                    "title": p.title,
                    "body": p.body,
                    "premise_type": p.premise_type,
                    "score": p.score,
                    "is_winner": p.is_winner,
                    "user_comment": p.user_comment,
                }
                for p in premises
            ],
        }

    async def get_negative_context(
        self, session, input_data: dict,
    ) -> dict:
        """Get premises scored < 5.0 — sets negative_context_fetched flag."""
        self.state.negative_context_fetched = True

        result = await self.db.execute(
            select(Premise)
            .where(Premise.session_id == session.id)
            .where(Premise.score.isnot(None))
            .where(Premise.score < 5.0)
        )
        low_premises = result.scalars().all()

        return {
            "status": "ok",
            "negative_context_fetched": True,
            "count": len(low_premises),
            "premises": [
                {
                    "title": p.title,
                    "score": p.score,
                    "user_comment": p.user_comment,
                }
                for p in low_premises
            ],
            "message": (
                f"Negative context loaded: {len(low_premises)} premise(s) "
                "scored below 5.0. Generation unlocked for this round."
            ),
        }

    async def get_context_usage(self, session, input_data: dict) -> dict:
        """Return token usage stats for context window monitoring."""
        max_tokens = 1_000_000
        used = session.total_tokens_used
        rounds_count = max(len(session.rounds), 1)
        avg_per_round = used / rounds_count

        return {
            "status": "ok",
            "tokens_used": used,
            "tokens_limit": max_tokens,
            "tokens_remaining": max_tokens - used,
            "usage_percentage": round((used / max_tokens) * 100, 2),
            "estimated_rounds_left": (
                int((max_tokens - used) / avg_per_round)
                if avg_per_round > 0
                else 999
            ),
        }
