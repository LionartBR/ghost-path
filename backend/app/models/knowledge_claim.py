"""KnowledgeClaim ORM — persists a falsifiable knowledge statement.

Invariants:
    - Always belongs to a Session (session_id FK)
    - claim_text is non-nullable
    - Scores (novelty, groundedness, falsifiability, significance) are agent-computed, 0-1
    - status transitions: proposed -> validated/rejected/qualified/superseded

Design Decisions:
    - session_id denormalized: allows querying claims by session without joins (ADR: query performance)
    - thesis_text/antithesis_text stored: preserves the dialectical trail for Knowledge Document
    - JSON for morphological_params: flexible schema for varied parameter combinations
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, Float, Integer, DateTime, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class KnowledgeClaim(Base):
    """Knowledge claim entity — a falsifiable knowledge statement."""
    __tablename__ = "knowledge_claims"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False,
    )
    claim_text: Mapped[str] = mapped_column(Text, nullable=False)
    claim_type: Mapped[str] = mapped_column(
        String(20), nullable=False,
    )
    thesis_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    antithesis_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    phase_created: Mapped[int] = mapped_column(Integer, nullable=False)
    round_created: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="proposed",
    )
    confidence: Mapped[str | None] = mapped_column(String(20), nullable=True)
    falsifiability_condition: Mapped[str | None] = mapped_column(
        Text, nullable=True,
    )
    qualification: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Agent-computed scores (0-1)
    novelty_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    groundedness_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    falsifiability_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    significance_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # User feedback
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Origin tracking
    cross_domain_source: Mapped[str | None] = mapped_column(
        String(500), nullable=True,
    )
    morphological_params: Mapped[dict | None] = mapped_column(
        JSON, nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    session: Mapped["Session"] = relationship(
        "Session", back_populates="claims",
    )
    evidence: Mapped[list["Evidence"]] = relationship(
        "Evidence", back_populates="claim",
        cascade="all, delete-orphan", lazy="selectin",
    )
