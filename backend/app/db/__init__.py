"""Database Infrastructure — async session factory and SQLAlchemy Base.

Invariants:
    - Single async engine per process (initialized via init_db)
    - All sessions are async (AsyncSession)

Design Decisions:
    - asyncpg driver for PostgreSQL (ADR: native async, no thread pool overhead)
"""
