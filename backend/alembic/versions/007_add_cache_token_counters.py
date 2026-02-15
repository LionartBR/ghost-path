"""Add cache token counters to sessions.

Revision ID: 007_add_cache_token_counters
Revises: 006_split_token_counters
Create Date: 2026-02-15

Prompt caching splits input tokens into three buckets (regular, cache_creation,
cache_read). Without tracking cache tokens, the ↑ input counter under-reports
by ~15K+ tokens per API call (system prompt + tool definitions).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "007_add_cache_token_counters"
down_revision: Union[str, None] = "006_split_token_counters"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "sessions",
        sa.Column(
            "total_cache_creation_tokens", sa.Integer(),
            nullable=False, server_default="0",
        ),
    )
    op.add_column(
        "sessions",
        sa.Column(
            "total_cache_read_tokens", sa.Integer(),
            nullable=False, server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("sessions", "total_cache_read_tokens")
    op.drop_column("sessions", "total_cache_creation_tokens")
