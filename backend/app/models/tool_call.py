"""ToolCall ORM — logging table for tool invocations within agent runs.

Invariants:
    - Every tool call (success or error) is logged
    - session_id links to the owning session

Design Decisions:
    - Logging table, not enforcement: observability only, no business logic depends on it
    - JSON columns for input/output: flexible schema for varied tool signatures
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import String, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.db.base import Base


class ToolCall(Base):
    """ToolCall log entry — observability for agent tool usage."""
    __tablename__ = "tool_calls"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False,
    )
    tool_name: Mapped[str] = mapped_column(String(50), nullable=False)
    tool_input: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    tool_output: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_code: Mapped[str | None] = mapped_column(
        String(50), nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
