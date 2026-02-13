"""O-Edger schema — knowledge claims, evidence, edges, reframings, analogies, contradictions.

Revision ID: 002_o_edger
Revises: 001_initial
Create Date: 2026-02-13

Drops v1 tables (rounds, premises) and creates O-Edger domain tables.
Modifies sessions table to add current_phase and current_round columns.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "002_o_edger"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # WARNING: Destructive — drops all v1 data (rounds, premises).
    # Acceptable for hackathon (O-Edger replaces GhostPath v1 schema entirely).
    # In production, migrate data before dropping.
    op.drop_table("premises")
    op.drop_table("rounds")

    # Modify sessions: add O-Edger columns, change default status
    op.add_column("sessions", sa.Column("current_phase", sa.Integer, nullable=False, server_default="1"))
    op.add_column("sessions", sa.Column("current_round", sa.Integer, nullable=False, server_default="0"))
    op.alter_column("sessions", "status", server_default="decomposing")

    # Knowledge Claims (Phase 3-5)
    op.create_table(
        "knowledge_claims",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", UUID(as_uuid=True), sa.ForeignKey("sessions.id"), nullable=False),
        sa.Column("claim_text", sa.Text, nullable=False),
        sa.Column("claim_type", sa.String(20), nullable=False),
        sa.Column("thesis_text", sa.Text, nullable=True),
        sa.Column("antithesis_text", sa.Text, nullable=True),
        sa.Column("phase_created", sa.Integer, nullable=False),
        sa.Column("round_created", sa.Integer, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="proposed"),
        sa.Column("confidence", sa.String(20), nullable=True),
        sa.Column("falsifiability_condition", sa.Text, nullable=True),
        sa.Column("qualification", sa.Text, nullable=True),
        sa.Column("novelty_score", sa.Float, nullable=True),
        sa.Column("groundedness_score", sa.Float, nullable=True),
        sa.Column("falsifiability_score", sa.Float, nullable=True),
        sa.Column("significance_score", sa.Float, nullable=True),
        sa.Column("rejection_reason", sa.Text, nullable=True),
        sa.Column("user_feedback", sa.Text, nullable=True),
        sa.Column("cross_domain_source", sa.String(500), nullable=True),
        sa.Column("morphological_params", sa.JSON, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # Evidence
    op.create_table(
        "evidence",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("claim_id", UUID(as_uuid=True), sa.ForeignKey("knowledge_claims.id"), nullable=False),
        sa.Column("session_id", UUID(as_uuid=True), sa.ForeignKey("sessions.id"), nullable=False),
        sa.Column("source_url", sa.String(2000), nullable=False),
        sa.Column("source_title", sa.String(500), nullable=True),
        sa.Column("content_summary", sa.Text, nullable=True),
        sa.Column("evidence_type", sa.String(20), nullable=False),
        sa.Column("contributed_by", sa.String(10), nullable=False, server_default="agent"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # Claim Edges (Knowledge Graph)
    op.create_table(
        "claim_edges",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", UUID(as_uuid=True), sa.ForeignKey("sessions.id"), nullable=False),
        sa.Column("source_claim_id", UUID(as_uuid=True), sa.ForeignKey("knowledge_claims.id"), nullable=False),
        sa.Column("target_claim_id", UUID(as_uuid=True), sa.ForeignKey("knowledge_claims.id"), nullable=False),
        sa.Column("edge_type", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # Problem Reframings (Phase 1)
    op.create_table(
        "problem_reframings",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", UUID(as_uuid=True), sa.ForeignKey("sessions.id"), nullable=False),
        sa.Column("original_problem", sa.Text, nullable=False),
        sa.Column("reframing_text", sa.Text, nullable=False),
        sa.Column("reframing_type", sa.String(20), nullable=False),
        sa.Column("selected", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # Cross-Domain Analogies (Phase 2)
    op.create_table(
        "cross_domain_analogies",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", UUID(as_uuid=True), sa.ForeignKey("sessions.id"), nullable=False),
        sa.Column("source_domain", sa.String(200), nullable=False),
        sa.Column("target_application", sa.Text, nullable=False),
        sa.Column("analogy_description", sa.Text, nullable=False),
        sa.Column("semantic_distance", sa.String(10), nullable=False, server_default="medium"),
        sa.Column("starred", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # Contradictions (Phase 2 — TRIZ)
    op.create_table(
        "contradictions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", UUID(as_uuid=True), sa.ForeignKey("sessions.id"), nullable=False),
        sa.Column("property_a", sa.String(500), nullable=False),
        sa.Column("property_b", sa.String(500), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("resolution_direction", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("contradictions")
    op.drop_table("cross_domain_analogies")
    op.drop_table("problem_reframings")
    op.drop_table("claim_edges")
    op.drop_table("evidence")
    op.drop_table("knowledge_claims")
    op.drop_column("sessions", "current_round")
    op.drop_column("sessions", "current_phase")
    op.alter_column("sessions", "status", server_default="created")

    # Recreate v1 tables
    op.create_table(
        "rounds",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("session_id", UUID(as_uuid=True), sa.ForeignKey("sessions.id"), nullable=False),
        sa.Column("round_number", sa.Integer, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "premises",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("round_id", UUID(as_uuid=True), sa.ForeignKey("rounds.id"), nullable=False),
        sa.Column("session_id", UUID(as_uuid=True), sa.ForeignKey("sessions.id"), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("body", sa.Text, nullable=True),
        sa.Column("premise_type", sa.String(20), nullable=False, server_default="initial"),
        sa.Column("score", sa.Float, nullable=True),
        sa.Column("user_comment", sa.Text, nullable=True),
        sa.Column("is_winner", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("violated_axiom", sa.String(500), nullable=True),
        sa.Column("cross_domain_source", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
