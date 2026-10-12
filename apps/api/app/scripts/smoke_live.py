"""End-to-end live smoke test against a *running* API server.

Unlike the pytest suite (which drives the ASGI app in-process), this script talks
to a real ``uvicorn`` server over HTTP. Use it to verify a deployment or a local
SQLite run.

Start the server first, then run this script::

    # Terminal 1 (from apps/api) -- SQLite + mock LLM, no external services
    export DATABASE_URL="sqlite+aiosqlite:///./smoke.db"
    export LLM_PROVIDER="mock"
    export JOB_EXECUTION_MODE="inline"
    export STORAGE_BACKEND="local"
    uv run alembic upgrade head
    uv run python -m app.scripts.seed
    uv run uvicorn app.main:app --port 8000

    # Terminal 2 (from apps/api)
    uv run python -m app.scripts.smoke_live --base-url http://127.0.0.1:8000

It registers a throwaway user and runs the full vertical slice: create book ->
outline job -> approve -> full-book job -> export download -> marketing kit and
cover -> credit accounting. It asserts exactly two generation charges (billing is
idempotent) and exits non-zero on the first failed assertion.
"""

from __future__ import annotations

import argparse
import sys
import time
import uuid
from typing import Any

import httpx

DEFAULT_BASE_URL = "http://127.0.0.1:8000"


def wait_for_job(
    client: httpx.Client, job_id: str, headers: dict[str, str], timeout: float = 300.0
) -> dict[str, Any]:
    """Poll a job endpoint until it reaches a terminal state."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        resp = client.get(f"/jobs/{job_id}", headers=headers)
        resp.raise_for_status()
        job: dict[str, Any] = resp.json()
        if job["status"] in {"succeeded", "failed", "cancelled"}:
            return job
        time.sleep(0.5)
    raise TimeoutError(f"job {job_id} did not finish within {timeout}s")


def run(client: httpx.Client) -> None:
    email = f"smoke+{uuid.uuid4().hex[:10]}@example.com"
    password = "smoke-pass-123"

    health = client.get("/health")
    assert health.status_code == 200, health.text
    print("health:", health.json()["status"])

    reg = client.post("/auth/register", json={"email": email, "password": password})
    assert reg.status_code in (200, 201), reg.text
    print("registered:", email)

    login = client.post("/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200, login.text
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    credits = client.get("/users/me/credits", headers=headers).json()
    print("starting credits:", credits["balance"])

    create = client.post(
        "/books",
        headers=headers,
        json={
            "topic": "Container gardening on a small balcony",
            "audience": "city dwellers",
            "category": "General",
            "language": "en",
            "tone": "conversational",
            "target_pages": 6,
            "chapter_count": 3,
        },
    )
    assert create.status_code == 201, create.text
    book = create.json()
    book_id = book["id"]
    print("book:", book_id, book["status"])

    estimate = client.get(f"/books/{book_id}/cost-estimate", headers=headers).json()
    print("estimate credits:", estimate["estimated_credits"], "affordable:", estimate["affordable"])

    outline = client.post(f"/books/{book_id}/outline", headers=headers, json={"chapter_count": 3})
    assert outline.status_code == 202, outline.text
    outline_job = wait_for_job(client, outline.json()["id"], headers)
    assert outline_job["status"] == "succeeded", outline_job.get("error")
    print("outline job:", outline_job["status"], outline_job["completed_steps"])

    approve = client.post(f"/books/{book_id}/outline/approve", headers=headers)
    assert approve.status_code == 200, approve.text
    print("approved chapters:", approve.json()["chapter_count"])

    gen = client.post(f"/books/{book_id}/generate", headers=headers, json={"type": "full_book"})
    assert gen.status_code == 202, gen.text
    full_job = wait_for_job(client, gen.json()["id"], headers)
    assert full_job["status"] == "succeeded", full_job.get("error")
    print("full_book job:", full_job["status"])

    final = client.get(f"/books/{book_id}", headers=headers).json()
    print("final book status:", final["status"])

    exports = client.get(f"/books/{book_id}/exports", headers=headers).json()["items"]
    formats = sorted({e["format"] for e in exports})
    print("exports:", [(e["format"], e["status"], e["size_bytes"]) for e in exports])
    assert {"pdf", "epub", "docx"} <= set(formats), formats

    pdf = next(e for e in exports if e["format"] == "pdf")
    download = client.get(f"/exports/{pdf['id']}/download", headers=headers)
    assert download.status_code == 200, download.text
    url = download.json()["url"]
    if url.startswith("http") and "localhost" not in url and "127.0.0.1" not in url:
        # A remote (S3/MinIO) URL may be unreachable from here; skip the byte check.
        print("download url (remote):", url)
    else:
        file_resp = client.get(url)
        assert file_resp.status_code == 200, file_resp.status_code
        assert file_resp.content[:5] == b"%PDF-", file_resp.content[:8]
        print("pdf bytes:", len(file_resp.content), "magic ok")

    kit = client.get(f"/books/{book_id}/marketing", headers=headers)
    assert kit.status_code == 200, kit.text
    print("marketing kit description length:", len(kit.json()["description"] or ""))

    cover = client.get(f"/books/{book_id}/cover", headers=headers).json()
    print("cover asset:", bool(cover["asset_id"]))

    txs = client.get(
        "/users/me/credits/transactions", headers=headers, params={"limit": 100}
    ).json()["items"]
    generation_txs = [t for t in txs if t["reason"] == "generation"]
    print("generation charges:", len(generation_txs))
    assert len(generation_txs) == 2, generation_txs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Live smoke test for the eBook Studio AI API.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="API origin (no /api/v1).")
    args = parser.parse_args(argv)

    with httpx.Client(base_url=f"{args.base_url.rstrip('/')}/api/v1", timeout=30.0) as client:
        run(client)
    print("SMOKE OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
