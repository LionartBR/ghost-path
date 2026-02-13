"""CrossDomainAnalogy ORM — Phase 2 output: analogies from distant domains.

Invariants:
    - Always belongs to a Session (session_id FK)
    - semantic_distance is one of: near, medium, far
    - starred defaults to False (set when user stars during explore review)

Design Decisions:
    - Persisted (not just in ForgeState): needed for Knowledge Document generation (ADR: data completeness)
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class CrossDomainAnalogy(Base):
    """Phase 2 output — a cross-domain structural similarity."""
    __tablename__ = "cross_domain_analogies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False,
    )
    source_domain: Mapped[str] = mapped_column(String(200), nullable=False)
    target_application: Mapped[str] = mapped_column(Text, nullable=False)
    analogy_description: Mapped[str] = mapped_column(Text, nullable=False)
    semantic_distance: Mapped[str] = mapped_column(
        String(10), nullable=False, default="medium",
    )
    starred: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    session: Mapped["Session"] = relationship(
        "Session", back_populates="analogies",
    )
