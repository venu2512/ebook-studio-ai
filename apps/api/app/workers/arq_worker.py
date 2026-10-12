"""Arq worker: runs generation jobs outside the request cycle.

Start with::

    arq app.workers.arq_worker.WorkerSettings

Also schedules two maintenance crons: reaping stale jobs and applying the
``AgentRun`` retention policy.
"""

from __future__ import annotations

import uuid
from typing import Any, ClassVar

from arq.connections import RedisSettings

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger

log = get_logger(__name__)


async def startup(ctx: dict[str, Any]) -> None:
    configure_logging()
    log.info("worker_started")


async def shutdown(ctx: dict[str, Any]) -> None:
    log.info("worker_stopped")


async def run_job(ctx: dict[str, Any], job_id: str) -> str:
    """Execute a generation job. Delegates to the shared job runner."""
    from app.services.jobs import run_job as _run_job

    return await _run_job(uuid.UUID(job_id))


async def reap_stale_jobs(ctx: dict[str, Any]) -> int:
    """Fail jobs stuck in ``running`` (e.g. after a worker crash)."""
    from app.db.session import session_scope
    from app.services.jobs import mark_stale_jobs_failed

    async with session_scope() as db:
        count = await mark_stale_jobs_failed(db)
    if count:
        log.info("reaped_stale_jobs", count=count)
    return count


async def purge_old_agent_runs(ctx: dict[str, Any]) -> int:
    """Apply the AgentRun prompt/output retention policy."""
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import delete

    from app.db.models import AgentRun
    from app.db.session import session_scope

    settings = get_settings()
    if settings.agent_run_retention_days <= 0:
        return 0
    cutoff = datetime.now(UTC) - timedelta(days=settings.agent_run_retention_days)
    async with session_scope() as db:
        result = await db.execute(delete(AgentRun).where(AgentRun.created_at < cutoff))
        deleted = result.rowcount or 0  # type: ignore[attr-defined]
    log.info("purged_agent_runs", deleted=deleted)
    return deleted


def _redis_settings() -> RedisSettings:
    return RedisSettings.from_dsn(get_settings().redis_url)


class WorkerSettings:
    """Arq worker configuration."""

    functions: ClassVar[list[Any]] = [run_job]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = _redis_settings()
    max_tries = 3
    job_timeout = 60 * 30  # 30 minutes for very long books
    keep_result = 3600
    cron_jobs: ClassVar[list[Any]] = []


def _build_crons() -> list[Any]:
    from arq import cron

    return [
        cron(reap_stale_jobs, minute={0, 15, 30, 45}, run_at_startup=True),
        cron(purge_old_agent_runs, hour={3}, minute={0}),
    ]


WorkerSettings.cron_jobs = _build_crons()
