"""TRIZ API — FastAPI application entry point.

Invariants:
    - Routes registered explicitly (no auto-discovery — ExMA anti-pattern)
    - Global error handlers map TrizError -> structured JSON responses
    - CORS configured from settings (not hardcoded)
    - Database initialized on startup via lifespan context manager

Design Decisions:
    - Lifespan over @app.on_event: FastAPI recommended pattern, cleaner cleanup
      (ADR: FastAPI 0.128)
    - Error handlers extracted to api/error_handlers.py (ADR: ExMA fan-out < 10)
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.infrastructure.database import init_db
from app.infrastructure.observability import setup_logging
from app.api.error_handlers import register_error_handlers
from app.api.routes import (
    health, session_lifecycle, session_agent_stream, knowledge_graph,
    research_directive,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup/shutdown lifecycle."""
    settings = get_settings()
    setup_logging(settings.log_level, settings.log_format)
    init_db(
        settings.database_url,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
    )
    logger.info("TRIZ API started")
    yield
    logger.info("TRIZ API shutting down")


app = FastAPI(
    title="TRIZ API",
    version="5.0.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# CORS — configured from settings, not hardcoded
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes — explicit registration (ExMA: no convention-over-config)
app.include_router(health.router)
app.include_router(session_lifecycle.router)
app.include_router(session_agent_stream.router)
app.include_router(knowledge_graph.router)
app.include_router(research_directive.router)

# Error handlers — domain, validation, catch-all (extracted for ExMA fan-out)
register_error_handlers(app)

# Static files — serves React build in production (Railway/Docker)
# ADR: mounted AFTER API routes so /api/v1/* takes precedence
# html=True enables SPA fallback (serves index.html for unknown routes)
if os.path.isdir("static"):
    app.mount("/", StaticFiles(directory="static", html=True), name="static")
