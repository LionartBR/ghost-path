"""Session ORM — persists the aggregate root for problem-solving interactions.

Invariants:
    - id is UUID primary key (server-default)
    - problem is non-nullable text
    - message_history stores full Anthropic conversation for resumption
    - status transitions: created → active → resolved | cancelled

Design Decisions:
    - JSON column for message_history: stores Anthropic message array as-is,
      no separate MessageHistory table (ADR: hackathon simplicity)
    - cascade delete for rounds: session owns all rounds and premises
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, Integer, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class Session(Base):
    """Session aggregate root — owns Rounds and Premises."""
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    problem: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="created",
    )
    message_history: Mapped[list | None] = mapped_column(
        JSON, nullable=True, default=None,
    )
    total_tokens_used: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
    )

    rounds: Mapped[list["Round"]] = relationship(
        "Round", back_populates="session", cascade="all, delete-orphan",
        lazy="selectin",
    )
