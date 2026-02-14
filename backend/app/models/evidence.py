"""Evidence ORM — persists web-sourced facts supporting or contradicting claims.

Invariants:
    - Always belongs to a KnowledgeClaim (claim_id FK)
    - source_url is non-nullable
    - evidence_type is one of: supporting, contradicting, contextual
    - contributed_by is one of: agent, user

Design Decisions:
    - session_id denormalized: scoped queries without joining through claim (ADR: query performance)
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class Evidence(Base):
    """Evidence entity — a web-sourced fact linked to a claim."""
    __tablename__ = "evidence"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    claim_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_claims.id", ondelete="CASCADE"),
        nullable=False,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_url: Mapped[str] = mapped_column(String(2000), nullable=False)
    source_title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    content_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_type: Mapped[str] = mapped_column(
        String(20), nullable=False,
    )
    contributed_by: Mapped[str] = mapped_column(
        String(10), nullable=False, default="agent",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    claim: Mapped["KnowledgeClaim"] = relationship(
        "KnowledgeClaim", back_populates="evidence",
    )
