"""Round ORM — persists a cycle of 3 premises presented to the user.

Invariants:
    - Always belongs to a Session (session_id FK)
    - round_number starts at 1 and increments
    - Owns exactly 3 Premises per round

Design Decisions:
    - round_number as Integer (not auto-increment): controlled by SessionState.current_round_number
    - cascade delete for premises: round owns all its premises
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Integer, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class Round(Base):
    """Round entity — a cycle of 3 premises."""
    __tablename__ = "rounds"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False,
    )
    round_number: Mapped[int] = mapped_column(
        Integer, nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    session: Mapped["Session"] = relationship(
        "Session", back_populates="rounds",
    )
    premises: Mapped[list["Premise"]] = relationship(
        "Premise", back_populates="round", cascade="all, delete-orphan",
        lazy="selectin",
    )
