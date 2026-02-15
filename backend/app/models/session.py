"""Session ORM — persists the aggregate root for knowledge-creation interactions.

Invariants:
    - id is UUID primary key (server-default)
    - problem is non-nullable text
    - message_history stores full Anthropic conversation for resumption
    - status transitions: decomposing -> exploring -> ... -> crystallized | cancelled

Design Decisions:
    - JSON column for message_history: stores Anthropic message array as-is (ADR: hackathon simplicity)
    - current_phase/current_round denormalized: avoids JOIN to determine agent state
    - cascade delete for claims, evidence, edges, reframings, analogies, contradictions
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, Integer, Float, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class Session(Base):
    """Session aggregate root — owns all TRIZ entities."""
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    problem: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="decomposing",
    )
    current_phase: Mapped[int] = mapped_column(
        Integer, nullable=False, default=1,
    )
    current_round: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
    )
    message_history: Mapped[list] = mapped_column(
        JSON, nullable=False, default=list,
    )
    locale: Mapped[str] = mapped_column(
        String(10), nullable=False, default="en",
    )
    locale_confidence: Mapped[float] = mapped_column(
        Float, nullable=False, default=0.0,
    )
    total_tokens_used: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
    )
    total_input_tokens: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
    )
    total_output_tokens: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
    )
    total_cache_creation_tokens: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
    )
    total_cache_read_tokens: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
    )
    forge_state_snapshot: Mapped[dict | None] = mapped_column(
        JSON, nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    # Relationships
    claims: Mapped[list["KnowledgeClaim"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "KnowledgeClaim", back_populates="session",
        cascade="all, delete-orphan", lazy="selectin",
    )
    reframings: Mapped[list["ProblemReframing"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "ProblemReframing", back_populates="session",
        cascade="all, delete-orphan", lazy="selectin",
    )
    analogies: Mapped[list["CrossDomainAnalogy"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "CrossDomainAnalogy", back_populates="session",
        cascade="all, delete-orphan", lazy="selectin",
    )
    contradictions: Mapped[list["Contradiction"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Contradiction", back_populates="session",
        cascade="all, delete-orphan", lazy="selectin",
    )
