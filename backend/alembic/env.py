"""Alembic environment — async migration runner for TRIZ.

Uses async engine for PostgreSQL migrations. Imports all models
to ensure metadata is populated before autogenerate.

Design Decisions:
    - Reads DATABASE_URL from env (Railway sets it automatically)
    - Converts postgresql:// → postgresql+asyncpg:// (same as config.py)
    - Falls back to alembic.ini value for local docker-compose
"""

import asyncio
import os
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

from app.db.base import Base
# Import all models so Base.metadata has them
from app.models.session import Session  # noqa: F401
from app.models.knowledge_claim import KnowledgeClaim  # noqa: F401
from app.models.evidence import Evidence  # noqa: F401
from app.models.claim_edge import ClaimEdge  # noqa: F401
from app.models.problem_reframing import ProblemReframing  # noqa: F401
from app.models.cross_domain_analogy import CrossDomainAnalogy  # noqa: F401
from app.models.contradiction import Contradiction  # noqa: F401
from app.models.tool_call import ToolCall  # noqa: F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _get_database_url() -> str:
    """Get DB URL from env (Railway) or alembic.ini (local docker-compose)."""
    url = os.environ.get("DATABASE_URL", "")
    if url:
        # Railway provides postgresql:// but asyncpg needs postgresql+asyncpg://
        if url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url
    return config.get_main_option("sqlalchemy.url")


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = _get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode with async engine."""
    configuration = config.get_section(config.config_ini_section, {})
    # Override with env var if present (Railway sets DATABASE_URL)
    db_url = _get_database_url()
    if db_url:
        configuration["sqlalchemy.url"] = db_url
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
