"""ORM Models — SQLAlchemy declarative models for all domain entities.

Invariants:
    - All models inherit from Base (db/base.py)
    - Session is the aggregate root; all entities scoped by session_id

Design Decisions:
    - One file per entity for locality (ADR: ExMA max 3-4 files to understand a feature)
"""
