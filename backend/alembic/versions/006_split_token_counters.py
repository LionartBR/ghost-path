"""Add total_input_tokens and total_output_tokens to sessions.

Revision ID: 006_split_token_counters
Revises: 005_cascade_delete_fks
Create Date: 2026-02-15

Splits the single total_tokens_used counter into input/output so the frontend
can display directional token usage (tokens sent vs received).
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "006_split_token_counters"
down_revision: Union[str, None] = "005_cascade_delete_fks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "sessions",
        sa.Column(
            "total_input_tokens", sa.Integer(),
            nullable=False, server_default="0",
        ),
    )
    op.add_column(
        "sessions",
        sa.Column(
            "total_output_tokens", sa.Integer(),
            nullable=False, server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("sessions", "total_output_tokens")
    op.drop_column("sessions", "total_input_tokens")
