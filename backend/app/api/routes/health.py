"""Health & Readiness Probes — liveness and readiness endpoints for container orchestration.

Invariants:
    - GET /health/ always returns 200 if process is up (liveness)
    - GET /health/ready returns 503 if database is unreachable (readiness)

Design Decisions:
    - Separate liveness/readiness: Kubernetes best practice — liveness restarts,
      readiness removes from load balancer (ADR: production readiness)
"""

import logging
from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from app.infrastructure.database import db_manager

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/health", tags=["health"])


@router.get("/", status_code=status.HTTP_200_OK)
async def health_check():
    """Basic liveness probe. Returns 200 if the process is up."""
    return {
        "status": "healthy",
        "service": "o-edger-api",
        "version": "5.0.0",
    }


@router.get("/ready")
async def readiness_check():
    """Readiness probe — includes database connectivity."""
    db_ok = await db_manager.health_check() if db_manager else False
    if not db_ok:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "not_ready",
                "reason": "database_unavailable",
            },
        )
    return {"status": "ready", "checks": {"database": "healthy"}}
