"""Add locale columns to sessions table for i18n support.

Revision ID: 003_add_locale
Revises: 002_o_edger
Create Date: 2026-02-13

Adds locale (string, default 'en') and locale_confidence (float, default 0.0)
to support auto-detected language from problem text.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '003_add_locale'
down_revision: Union[str, None] = '002_o_edger'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'sessions',
        sa.Column('locale', sa.String(10), nullable=False, server_default='en'),
    )
    op.add_column(
        'sessions',
        sa.Column('locale_confidence', sa.Float(), nullable=False, server_default='0.0'),
    )


def downgrade() -> None:
    op.drop_column('sessions', 'locale_confidence')
    op.drop_column('sessions', 'locale')
