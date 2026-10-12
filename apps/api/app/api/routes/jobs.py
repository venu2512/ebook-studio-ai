"""Job routes: start generation, poll status, stream progress (SSE), cancel, retry."""

from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Query, Request, status
from fastapi.responses import StreamingResponse

from app.api.deps import CurrentUser, SessionDep
from app.core.logging import get_logger
from app.core.ratelimit import rate_limit
from app.db.models import Job
from app.db.session import session_scope
from app.schemas.common import Page
from app.schemas.job import (
    AgentRunDetail,
    AgentRunRead,
    GenerateRequest,
    JobRead,
    PipelineState,
    PipelineStep,
)
from app.services import books as books_service
from app.services import jobs as jobs_service

log = get_logger(__name__)
router = APIRouter(tags=["jobs"])

# Display metadata for the live generation cards.
AGENT_LABELS = {
    "researcher": "Researcher",
    "planner": "Book Planner",
    "writer": "Writer",
    "editor": "Editor",
    "fact_checker": "Fact Checker",
    "designer": "Designer",
    "publisher": "Publisher",
    "marketer": "Marketing Specialist",
}
PIPELINE_AGENTS = list(AGENT_LABELS)
HEARTBEAT_SECONDS = 15
POLL_SECONDS = 0.75


@router.post(
    "/books/{book_id}/generate",
    response_model=JobRead,
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(rate_limit("generate", 30, 3600))],
)
async def generate_book(
    book_id: uuid.UUID, payload: GenerateRequest, user: CurrentUser, db: SessionDep
) -> JobRead:
    """Start a full-book generation run (chapters must be approved)."""
    book = await books_service.get_owned_book(db, book_id, user)
    await jobs_service.assert_book_generatable(book)
    job = await jobs_service.create_job(
        db,
        user,
        book,
        job_type=payload.type,
        target_chapter_id=payload.chapter_id,
        input_params={
            "format": payload.format,
            "template": payload.template,
            "force": payload.force,
        },
    )
    # Commit before spawning the inline worker so it can observe the job row.
    await db.commit()
    await jobs_service.enqueue(job)
    return JobRead.model_validate(job)


@router.get("/books/{book_id}/jobs", response_model=Page[JobRead])
async def list_book_jobs(
    book_id: uuid.UUID,
    user: CurrentUser,
    db: SessionDep,
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> Page[JobRead]:
    await books_service.get_owned_book(db, book_id, user)
    items, total = await jobs_service.list_jobs(
        db, user, book_id=book_id, limit=limit, offset=offset
    )
    return Page.build([JobRead.model_validate(j) for j in items], total, limit, offset)


@router.get("/jobs/{job_id}", response_model=JobRead)
async def get_job(job_id: uuid.UUID, user: CurrentUser, db: SessionDep) -> JobRead:
    job = await jobs_service.get_job(db, job_id, user)
    return JobRead.model_validate(job)


@router.get("/jobs/{job_id}/runs", response_model=Page[AgentRunRead])
async def list_runs(
    job_id: uuid.UUID,
    user: CurrentUser,
    db: SessionDep,
    include_output: bool = Query(default=False),
) -> Page[AgentRunRead]:
    await jobs_service.get_job(db, job_id, user)
    runs = await jobs_service.list_agent_runs(db, job_id)
    items: list[Any]
    if include_output:
        items = [AgentRunDetail.model_validate(r) for r in runs]
    else:
        items = [AgentRunRead.model_validate(r) for r in runs]
    return Page.build(items, len(items), len(items), 0)


@router.post("/jobs/{job_id}/cancel", response_model=JobRead)
async def cancel_job(job_id: uuid.UUID, user: CurrentUser, db: SessionDep) -> JobRead:
    job = await jobs_service.get_job(db, job_id, user)
    job = await jobs_service.request_cancel(db, job)
    return JobRead.model_validate(job)


@router.post("/jobs/{job_id}/retry", response_model=JobRead)
async def retry_job(job_id: uuid.UUID, user: CurrentUser, db: SessionDep) -> JobRead:
    job = await jobs_service.get_job(db, job_id, user)
    job = await jobs_service.retry_job(db, user, job)
    return JobRead.model_validate(job)


# ---------------------------------------------------------------------------
# SSE progress stream
# ---------------------------------------------------------------------------
def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, default=str)}\n\n"


async def _build_pipeline_state(db, job: Job) -> PipelineState:
    runs = await jobs_service.list_agent_runs(db, job.id)
    by_agent: dict[str, list] = {}
    for run in runs:
        by_agent.setdefault(run.agent_name, []).append(run)

    steps: list[PipelineStep] = []
    for agent in PIPELINE_AGENTS:
        agent_runs = by_agent.get(agent, [])
        status_value = "pending"
        tokens = 0
        cost = 0.0
        elapsed: int | None = None
        detail: str | None = None

        if agent_runs:
            tokens = sum(r.total_tokens for r in agent_runs)
            cost = round(sum(r.cost_usd for r in agent_runs), 6)
            elapsed = sum(r.duration_ms for r in agent_runs) or None
            last = agent_runs[-1]
            if last.status == "failed":
                status_value = "failed"
                detail = last.error
            elif any(r.status == "started" for r in agent_runs):
                status_value = "running"
            else:
                status_value = "succeeded"
            detail = detail or f"{len(agent_runs)} step(s)"

        if job.current_step and job.current_step.startswith(agent) and job.status == "running":
            status_value = "running"

        steps.append(
            PipelineStep(
                key=agent,
                agent=agent,
                label=AGENT_LABELS[agent],
                status=status_value,
                detail=detail,
                progress_pct=job.progress_pct if status_value == "running" else 0,
                elapsed_ms=elapsed,
                tokens=tokens,
                cost_usd=cost,
            )
        )

    return PipelineState(
        job_id=job.id,
        status=job.status,
        progress_pct=job.progress_pct,
        steps=steps,
        message=job.error,
    )


@router.get("/jobs/{job_id}/events")
async def job_events(
    job_id: uuid.UUID,
    request: Request,
    user: CurrentUser,
) -> StreamingResponse:
    """Stream live pipeline progress as Server-Sent Events."""

    async def event_stream() -> AsyncIterator[str]:
        last_signature: str | None = None
        last_heartbeat = datetime.now(UTC)
        # Emit an immediate snapshot so the UI paints without waiting.
        async with session_scope() as db:
            job = await db.get(Job, job_id)
            if job is None or job.user_id != user.id:
                yield _sse("error", {"message": "Job not found."})
                return
            state = await _build_pipeline_state(db, job)
            yield _sse("snapshot", state.model_dump(mode="json"))
            last_signature = state.model_dump_json()

        while True:
            if await request.is_disconnected():
                break
            await asyncio.sleep(POLL_SECONDS)

            async with session_scope() as db:
                job = await db.get(Job, job_id)
                if job is None or job.user_id != user.id:
                    yield _sse("error", {"message": "Job not found."})
                    break
                state = await _build_pipeline_state(db, job)
                signature = state.model_dump_json()
                if signature != last_signature:
                    yield _sse("progress", state.model_dump(mode="json"))
                    last_signature = signature

                now = datetime.now(UTC)
                if (now - last_heartbeat).total_seconds() >= HEARTBEAT_SECONDS:
                    yield ": heartbeat\n\n"
                    last_heartbeat = now

                if job.is_terminal:
                    yield _sse(
                        "done",
                        {
                            "job_id": str(job.id),
                            "status": job.status,
                            "error": job.error,
                            "progress_pct": job.progress_pct,
                        },
                    )
                    break

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/jobs/{job_id}/pipeline", response_model=PipelineState)
async def job_pipeline(job_id: uuid.UUID, user: CurrentUser, db: SessionDep) -> PipelineState:
    """One-shot snapshot of the pipeline (used by polling clients)."""
    job = await jobs_service.get_job(db, job_id, user)
    return await _build_pipeline_state(db, job)
