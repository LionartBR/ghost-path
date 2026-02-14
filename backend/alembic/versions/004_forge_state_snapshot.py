"""Add forge_state_snapshot JSON column to sessions table.

Revision ID: 004_forge_state_snapshot
Revises: 003_add_locale
Create Date: 2026-02-14

Persists entire ForgeState as JSON snapshot for session resumption after
server restart or client disconnect. Complements in-memory ForgeState
(ADR: hackathon single-process, but snapshot enables crash recovery).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '004_forge_state_snapshot'
down_revision: Union[str, None] = '003_add_locale'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'sessions',
        sa.Column('forge_state_snapshot', sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('sessions', 'forge_state_snapshot')
