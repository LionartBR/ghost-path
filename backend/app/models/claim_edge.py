"""ClaimEdge ORM — typed edges in the knowledge graph DAG.

Invariants:
    - Connects two KnowledgeClaims (source_claim_id -> target_claim_id)
    - edge_type is one of: supports, contradicts, extends, supersedes, depends_on, merged_from
    - Always scoped by session_id

Design Decisions:
    - session_id denormalized: graph queries scoped by session without joining (ADR: query performance)
    - No unique constraint on (source, target, type): allows multiple relationship types between same claims
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class ClaimEdge(Base):
    """Typed edge in the knowledge graph DAG."""
    __tablename__ = "claim_edges"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_claim_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_claims.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_claim_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("knowledge_claims.id", ondelete="CASCADE"),
        nullable=False,
    )
    edge_type: Mapped[str] = mapped_column(
        String(20), nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
