"""SQLAlchemy Declarative Base — shared base class for all ORM models.

Invariants:
    - All models inherit from Base
    - Base is the single source of truth for table metadata

Design Decisions:
    - Separate file for Base: avoids circular imports between models (ADR: SQLAlchemy best practice)
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all GhostPath ORM models."""
    pass
