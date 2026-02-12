"""Database Session Manager — async connection pool with automatic rollback and health checks.

Invariants:
    - Every session auto-rolls-back on exception (no partial commits leak)
    - Connection pool uses pool_pre_ping for stale connection detection
    - All SQLAlchemy exceptions mapped to DatabaseError (core/errors.py)

Design Decisions:
    - Singleton db_manager initialized on startup: FastAPI lifespan manages lifecycle
      (ADR: no global import side effects)
    - expire_on_commit=False: prevents lazy-load issues in async context
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession, create_async_engine, async_sessionmaker,
)
from sqlalchemy.exc import (
    IntegrityError, OperationalError, DBAPIError, SQLAlchemyError,
)
from sqlalchemy import text

from app.core.errors import DatabaseError

logger = logging.getLogger(__name__)


class DatabaseSessionManager:
    """Manages async database sessions with pooling, rollback, and health checks."""

    def __init__(
        self, database_url: str, pool_size: int = 20, max_overflow: int = 10,
    ):
        self.engine = create_async_engine(
            database_url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_pre_ping=True,
            pool_recycle=3600,
        )
        self._session_factory = async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """Provide session with auto-rollback on exception."""
        session = self._session_factory()
        try:
            yield session
        except IntegrityError as e:
            await session.rollback()
            logger.error(f"DB integrity error: {e}")
            raise DatabaseError("Integrity constraint violated", "commit")
        except OperationalError as e:
            await session.rollback()
            logger.error(f"DB operational error: {e}")
            raise DatabaseError("Connection or operational error", "execute")
        except DBAPIError as e:
            await session.rollback()
            logger.error(f"DB driver error: {e}")
            raise DatabaseError("Database driver error", "query")
        except SQLAlchemyError as e:
            await session.rollback()
            logger.error(f"SQLAlchemy error: {e}")
            raise DatabaseError("Database operation failed", "unknown")
        finally:
            await session.close()

    async def health_check(self) -> bool:
        """Check database connectivity (for readiness probes)."""
        try:
            async with self.session() as db:
                await db.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logger.error(f"DB health check failed: {e}")
            return False


# Singleton (initialized on startup)
db_manager: DatabaseSessionManager | None = None


def init_db(database_url: str, **kwargs):
    global db_manager
    db_manager = DatabaseSessionManager(database_url, **kwargs)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions."""
    if not db_manager:
        raise RuntimeError("Database not initialized")
    async with db_manager.session() as session:
        yield session
