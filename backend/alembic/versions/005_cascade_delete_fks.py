"""Add ON DELETE CASCADE to all session-scoped foreign keys.

Revision ID: 005_cascade_delete_fks
Revises: 004_forge_state_snapshot
Create Date: 2026-02-14

Without DB-level cascade, deleting a session fails with IntegrityError because
tool_calls, claim_edges, and evidence have FKs to sessions/knowledge_claims
that block deletion. ORM-level cascade (Session.claims etc.) is insufficient
when child tables lack ORM relationships to Session (ADR: fix missing cascades).
"""
from typing import Sequence, Union

from alembic import op

revision: str = "005_cascade_delete_fks"
down_revision: Union[str, None] = "004_forge_state_snapshot"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (table, constraint_name, column, referenced_table)
_SESSION_FKS = [
    ("tool_calls", "tool_calls_session_id_fkey", "session_id", "sessions.id"),
    ("knowledge_claims", "knowledge_claims_session_id_fkey", "session_id", "sessions.id"),
    ("evidence", "evidence_session_id_fkey", "session_id", "sessions.id"),
    ("evidence", "evidence_claim_id_fkey", "claim_id", "knowledge_claims.id"),
    ("claim_edges", "claim_edges_session_id_fkey", "session_id", "sessions.id"),
    ("claim_edges", "claim_edges_source_claim_id_fkey", "source_claim_id", "knowledge_claims.id"),
    ("claim_edges", "claim_edges_target_claim_id_fkey", "target_claim_id", "knowledge_claims.id"),
    ("problem_reframings", "problem_reframings_session_id_fkey", "session_id", "sessions.id"),
    ("cross_domain_analogies", "cross_domain_analogies_session_id_fkey", "session_id", "sessions.id"),
    ("contradictions", "contradictions_session_id_fkey", "session_id", "sessions.id"),
]


def upgrade() -> None:
    for table, constraint, column, ref in _SESSION_FKS:
        op.drop_constraint(constraint, table, type_="foreignkey")
        op.create_foreign_key(
            constraint, table, ref.split(".")[0],
            [column], [ref.split(".")[1]],
            ondelete="CASCADE",
        )


def downgrade() -> None:
    for table, constraint, column, ref in _SESSION_FKS:
        op.drop_constraint(constraint, table, type_="foreignkey")
        op.create_foreign_key(
            constraint, table, ref.split(".")[0],
            [column], [ref.split(".")[1]],
        )
