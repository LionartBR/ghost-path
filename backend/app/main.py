"""GhostPath API — FastAPI application entry point.

Invariants:
    - Routes registered explicitly (no auto-discovery — ExMA anti-pattern)
    - Global error handlers map GhostPathError → structured JSON responses
    - CORS configured from settings (not hardcoded)
    - Database initialized on startup via lifespan context manager

Design Decisions:
    - Lifespan over @app.on_event: FastAPI recommended pattern, cleaner cleanup
      (ADR: FastAPI 0.128)
    - Three error handler layers: GhostPathError (domain), RequestValidationError
      (Pydantic), Exception (catch-all) — never leaks internal details
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.errors import GhostPathError, ErrorSeverity
from app.infrastructure.database import init_db
from app.infrastructure.observability import setup_logging
from app.config import get_settings
from app.api.routes import health, session_lifecycle, session_agent_stream

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
    logger.info("GhostPath API started")
    yield
    logger.info("GhostPath API shutting down")


app = FastAPI(
    title="GhostPath API", version="4.0.0", lifespan=lifespan,
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

# Static files — serves React build in production (Railway/Docker)
# ADR: mounted AFTER API routes so /api/v1/* takes precedence
# html=True enables SPA fallback (serves index.html for unknown routes)
if os.path.isdir("static"):
    app.mount("/", StaticFiles(directory="static", html=True), name="static")


# ─── GLOBAL ERROR HANDLERS ──────────────────────────────────────

@app.exception_handler(GhostPathError)
async def ghostpath_error_handler(request: Request, exc: GhostPathError):
    """Handle all GhostPath domain/infrastructure errors."""
    logger.error(
        f"GhostPathError: {exc.message}",
        extra={"error_code": exc.code, "path": request.url.path},
    )
    return JSONResponse(
        status_code=exc.http_status, content=exc.to_response(),
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(
    request: Request, exc: RequestValidationError,
):
    """Handle Pydantic validation errors with structured response."""
    logger.warning(
        f"Validation error on {request.url.path}: {exc.errors()}",
    )
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "Invalid request data",
                "category": "validation",
                "severity": ErrorSeverity.ERROR.value,
                "details": [
                    {
                        "field": ".".join(str(loc) for loc in e["loc"]),
                        "message": e["msg"],
                        "type": e["type"],
                    }
                    for e in exc.errors()
                ],
            },
        },
    )


@app.exception_handler(Exception)
async def generic_error_handler(request: Request, exc: Exception):
    """Catch-all — never leaks internal details."""
    logger.error(
        f"Unhandled exception on {request.url.path}: {exc}",
        exc_info=True,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred",
                "category": "internal",
                "severity": ErrorSeverity.CRITICAL.value,
            },
        },
    )
