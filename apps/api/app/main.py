"""FastAPI application entry point.

Run locally with::

    uv run uvicorn app.main:app --reload

The app wires structured logging, CORS, consistent JSON error handling, a
request-id correlation middleware and the versioned API under ``/api/v1``.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.core.config import Settings, get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.db.session import dispose_engine

log = get_logger(__name__)


def _init_sentry(settings: Settings) -> None:
    if not settings.sentry_dsn:
        return
    try:
        import sentry_sdk

        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.app_env,
            release=settings.app_version,
            traces_sample_rate=0.1 if settings.is_production else 0.0,
            send_default_pii=False,
        )
        log.info("sentry_initialised")
    except Exception as exc:  # noqa: BLE001 - never block startup on telemetry
        log.warning("sentry_init_failed", error=str(exc))


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    log.info(
        "app_starting",
        env=settings.app_env,
        version=settings.app_version,
        llm_provider=settings.llm_provider,
        storage_backend=settings.storage_backend,
        job_execution_mode=settings.job_execution_mode,
    )
    # Automatically ensure special VIP testing accounts exist in non-production
    if not settings.is_production:
        try:
            from app.scripts.create_special_account import ensure_schema
            from app.scripts.create_special_account import main as ensure_vip

            await ensure_schema()
            await ensure_vip()
        except Exception as exc:  # noqa: BLE001 - best-effort dev-only seeding
            log.warning("special_account_autoseed_deferred", error=str(exc))
    yield
    await dispose_engine()
    log.info("app_stopped")


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()
    _init_sentry(settings)

    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description=(
            "Turn a topic into a complete, exportable eBook with an eight-agent "
            "pipeline: research, plan, write, edit, fact-check, design, publish "
            "and market."
        ),
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    if settings.cors_origin_list:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origin_list,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
            expose_headers=["X-Access-Token", "X-Request-ID"],
        )

    @app.middleware("http")
    async def _correlation_id(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id, path=request.url.path, method=request.method
        )
        started = time.perf_counter()
        try:
            response = await call_next(request)
        finally:
            structlog.contextvars.clear_contextvars()
        response.headers["X-Request-ID"] = request_id
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        if request.url.path not in ("/api/v1/health", "/api/v1/ready"):
            log.info(
                "request",
                status=response.status_code,
                duration_ms=elapsed_ms,
            )
        return response

    register_exception_handlers(app)
    app.include_router(api_router, prefix="/api/v1")

    @app.get("/", include_in_schema=False)
    async def root() -> dict[str, str]:
        return {
            "name": settings.app_name,
            "version": settings.app_version,
            "docs": "/docs",
            "health": "/api/v1/health",
        }

    return app


app = create_app()
