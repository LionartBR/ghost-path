"""Error Handlers — global exception handlers for the TRIZ API.

Invariants:
    - TrizError → structured JSON with error code, message, severity
    - RequestValidationError → field-level error details
    - Exception (catch-all) → never leaks internal details

Design Decisions:
    - Three-layer handler: domain (TrizError), validation (Pydantic), catch-all (Exception)
    - Extracted from main.py (ADR: ExMA import fan-out < 10)
"""

import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.core.errors import TrizError, ErrorSeverity

logger = logging.getLogger(__name__)


def register_error_handlers(app: FastAPI) -> None:
    """Register all global error handlers on the FastAPI app."""
    _register_triz_error_handler(app)
    _register_validation_error_handler(app)
    _register_generic_error_handler(app)


def _register_triz_error_handler(app: FastAPI) -> None:
    """Register TRIZ domain/infrastructure error handler."""

    @app.exception_handler(TrizError)
    async def triz_error_handler(request: Request, exc: TrizError):
        """Handle all TRIZ domain/infrastructure errors."""
        logger.error(
            f"TrizError: {exc.message}",
            extra={"error_code": exc.code, "path": request.url.path},
        )
        return JSONResponse(
            status_code=exc.http_status, content=exc.to_response(),
        )


def _register_validation_error_handler(app: FastAPI) -> None:
    """Register Pydantic validation error handler."""

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError,
    ):
        """Handle Pydantic validation errors."""
        logger.warning(
            f"Validation error on {request.url.path}: {exc.errors()}",
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=_build_validation_error_response(exc),
        )


def _register_generic_error_handler(app: FastAPI) -> None:
    """Register catch-all error handler."""

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


def _build_validation_error_response(exc: RequestValidationError) -> dict:
    """Build structured validation error response."""
    return {
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
    }
