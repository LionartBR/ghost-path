"""Contradiction ORM — Phase 2 output: competing requirements (TRIZ).

Invariants:
    - Always belongs to a Session (session_id FK)
    - property_a and property_b are the two competing desirable properties
    - resolution_direction is nullable (filled after synthesis)

Design Decisions:
    - Persisted (not just in ForgeState): TRIZ contradictions feed into synthesis and Knowledge Document
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class Contradiction(Base):
    """Phase 2 output — two desirable properties that seem mutually exclusive."""
    __tablename__ = "contradictions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    property_a: Mapped[str] = mapped_column(String(500), nullable=False)
    property_b: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    resolution_direction: Mapped[str | None] = mapped_column(
        Text, nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    session: Mapped["Session"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Session", back_populates="contradictions",
    )
