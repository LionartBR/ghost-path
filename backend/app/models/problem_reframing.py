"""ProblemReframing ORM — Phase 1 output: alternative problem formulations.

Invariants:
    - Always belongs to a Session (session_id FK)
    - reframing_type is one of: scope_change, entity_question, variable_change, domain_change
    - selected defaults to False (set when user selects during decompose review)

Design Decisions:
    - Persisted (not just in ForgeState): needed for Knowledge Document generation (ADR: data completeness)
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class ProblemReframing(Base):
    """Phase 1 output — an alternative formulation of the original problem."""
    __tablename__ = "problem_reframings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False,
    )
    original_problem: Mapped[str] = mapped_column(Text, nullable=False)
    reframing_text: Mapped[str] = mapped_column(Text, nullable=False)
    reframing_type: Mapped[str] = mapped_column(
        String(20), nullable=False,
    )
    selected: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    session: Mapped["Session"] = relationship(
        "Session", back_populates="reframings",
    )
