"""Operational endpoints: liveness and readiness probes.

These are intentionally unauthenticated so container orchestrators and load
balancers can probe them. They expose no user data.
"""

from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.deps import SessionDep
from app.core.config import get_settings
from app.core.logging import get_logger

router = APIRouter(tags=["ops"])
log = get_logger(__name__)


@router.get("/health")
async def health() -> dict[str, str]:
    """Liveness: the process is up and serving."""
    settings = get_settings()
    return {
        "status": "ok",
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.app_env,
    }


@router.get("/ready")
async def ready(db: SessionDep) -> JSONResponse:
    """Readiness: dependencies required to serve traffic are reachable."""
    settings = get_settings()
    checks: dict[str, str] = {"database": "ok"}
    healthy = True
    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001 - report, do not raise
        checks["database"] = "error"
        healthy = False
        log.warning("readiness_db_failed", error=str(exc))

    checks["storage"] = settings.storage_backend
    checks["llm"] = settings.llm_provider

    return JSONResponse(
        status_code=200 if healthy else 503,
        content={"status": "ready" if healthy else "degraded", "checks": checks},
    )
