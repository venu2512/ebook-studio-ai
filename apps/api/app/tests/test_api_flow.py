"""End-to-end API flow with the inline worker and mock LLM.

Covers the acceptance path: register -> create book -> outline job -> approve
-> full-book job -> PDF/EPUB/DOCX exports -> download. Also checks ownership
isolation, credit accounting and error envelopes.
"""

from __future__ import annotations

import uuid

from app.db.models import Book as BookModel
from app.db.session import session_scope

API = "/api/v1"


async def _elevate_token_budget(book_id: str, budget: int = 5_000_000) -> None:
    """Give a book room so this test exercises the pipeline, not budgeting.

    Uses a short-lived session that commits and closes immediately, so it does
    not hold a SQLite writer lock while the API client runs.
    """
    async with session_scope() as session:
        book = await session.get(BookModel, uuid.UUID(book_id))
        assert book is not None
        book.token_budget = budget


async def test_end_to_end_book_pipeline(client, register, wait_for_job):
    # -- Ops probes -------------------------------------------------------
    health = await client.get(f"{API}/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    ready = await client.get(f"{API}/ready")
    assert ready.status_code == 200
    assert ready.json()["checks"]["database"] == "ok"

    # -- Unauthenticated access is rejected with the standard envelope ----
    unauth = await client.get(f"{API}/users/me")
    assert unauth.status_code == 401
    body = unauth.json()
    assert body["error"]["code"] == "missing_token"

    session = await register()
    headers = session["headers"]

    me = await client.get(f"{API}/users/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["email"] == session["email"]

    credits0 = await client.get(f"{API}/users/me/credits", headers=headers)
    assert credits0.status_code == 200
    assert credits0.json()["balance"] == 100  # free-plan signup grant

    # -- Create the book --------------------------------------------------
    create = await client.post(
        f"{API}/books",
        headers=headers,
        json={
            "topic": "Bread baking for absolute beginners",
            "audience": "home cooks",
            "category": "Cooking",
            "language": "en",
            "tone": "conversational",
            "target_pages": 6,
            "chapter_count": 3,
        },
    )
    assert create.status_code == 201, create.text
    book = create.json()
    book_id = book["id"]
    assert book["status"] == "draft"
    assert book["estimated_credits"] >= 1

    await _elevate_token_budget(book_id)

    estimate = await client.get(f"{API}/books/{book_id}/cost-estimate", headers=headers)
    assert estimate.status_code == 200
    assert estimate.json()["affordable"] is True
    assert estimate.json()["user_balance"] == 100

    # -- Outline job ------------------------------------------------------
    outline_resp = await client.post(
        f"{API}/books/{book_id}/outline", headers=headers, json={"chapter_count": 3}
    )
    assert outline_resp.status_code == 202, outline_resp.text
    outline_job_id = outline_resp.json()["id"]
    outline_job = await wait_for_job(outline_job_id, headers)
    assert outline_job["status"] == "succeeded", outline_job.get("error")
    assert outline_job["completed_steps"]  # research + plan

    # Book now awaits approval.
    after_outline = await client.get(f"{API}/books/{book_id}", headers=headers)
    assert after_outline.json()["status"] == "awaiting_approval"

    outline = await client.get(f"{API}/books/{book_id}/outline", headers=headers)
    assert outline.status_code == 200
    planned = sum(len(p["chapters"]) for p in outline.json()["structure"]["parts"])
    assert planned == 3

    # -- Approve -> chapters materialise ----------------------------------
    approve = await client.post(f"{API}/books/{book_id}/outline/approve", headers=headers)
    assert approve.status_code == 200, approve.text
    assert approve.json()["chapter_count"] == 3

    chapters = await client.get(f"{API}/books/{book_id}/chapters", headers=headers)
    assert chapters.status_code == 200
    assert chapters.json()["total"] == 3

    # -- Full book job ----------------------------------------------------
    gen = await client.post(
        f"{API}/books/{book_id}/generate", headers=headers, json={"type": "full_book"}
    )
    assert gen.status_code == 202, gen.text
    full_job = await wait_for_job(gen.json()["id"], headers, timeout=240)
    assert full_job["status"] == "succeeded", full_job.get("error")

    final_book = await client.get(f"{API}/books/{book_id}", headers=headers)
    assert final_book.json()["status"] == "ready"

    # Every pipeline stage is recorded as an AgentRun.
    runs = await client.get(f"{API}/jobs/{full_job['id']}/runs", headers=headers)
    agents = {r["agent_name"] for r in runs.json()["items"]}
    assert {"writer", "editor", "fact_checker", "designer", "publisher", "marketer"} <= agents

    # -- Exports ----------------------------------------------------------
    exports = await client.get(f"{API}/books/{book_id}/exports", headers=headers)
    assert exports.status_code == 200, exports.text
    formats = {e["format"] for e in exports.json()["items"]}
    assert {"pdf", "epub", "docx"} <= formats
    for item in exports.json()["items"]:
        assert item["status"] == "ready"
        assert item["size_bytes"] > 0

    pdf_export = next(e for e in exports.json()["items"] if e["format"] == "pdf")
    download = await client.get(f"{API}/exports/{pdf_export['id']}/download", headers=headers)
    assert download.status_code == 200, download.text
    file_resp = await client.get(download.json()["url"])
    assert file_resp.status_code == 200
    assert file_resp.content[:5] == b"%PDF-"

    # -- Marketing kit + cover -------------------------------------------
    kit = await client.get(f"{API}/books/{book_id}/marketing", headers=headers)
    assert kit.status_code == 200, kit.text
    assert kit.json()["description"]
    cover = await client.get(f"{API}/books/{book_id}/cover", headers=headers)
    assert cover.status_code == 200
    assert cover.json()["asset_id"]

    # -- Credit accounting: one generation charge per job -----------------
    txs = await client.get(
        f"{API}/users/me/credits/transactions", headers=headers, params={"limit": 100}
    )
    generation_txs = [t for t in txs.json()["items"] if t["reason"] == "generation"]
    assert len(generation_txs) == 2  # outline + full_book, exactly once each
    spent = sum(-t["amount"] for t in generation_txs)
    remaining = await client.get(f"{API}/users/me/credits", headers=headers)
    assert remaining.json()["balance"] == 100 - spent
    assert remaining.json()["balance"] < 100

    # -- Cross-user isolation --------------------------------------------
    other = await register()
    isolated = await client.get(f"{API}/books/{book_id}", headers=other["headers"])
    assert isolated.status_code == 404
    assert isolated.json()["error"]["code"] == "book_not_found"


async def test_full_book_without_approved_outline_fails_readably(client, register, wait_for_job):
    session = await register()
    headers = session["headers"]
    create = await client.post(
        f"{API}/books",
        headers=headers,
        json={"topic": "A topic with no outline yet", "target_pages": 6, "chapter_count": 3},
    )
    book_id = create.json()["id"]

    gen = await client.post(
        f"{API}/books/{book_id}/generate", headers=headers, json={"type": "full_book"}
    )
    assert gen.status_code == 202
    job = await wait_for_job(gen.json()["id"], headers)
    assert job["status"] == "failed"
    assert job["error_code"] == "outline_not_approved"
    assert job["error"]

    # The failed job produced nothing, so its credits were refunded.
    credits = await client.get(f"{API}/users/me/credits", headers=headers)
    assert credits.json()["balance"] == 100

    # And it can be retried (same job, attempt counter increments).
    retried = await client.post(f"{API}/jobs/{job['id']}/retry", headers=headers)
    assert retried.status_code == 200, retried.text
    assert retried.json()["attempts"] == 1
    await wait_for_job(job["id"], headers)


async def test_registration_validation_and_conflict(client, register):
    # Too-short password -> 422 with the standard envelope.
    bad = await client.post(
        f"{API}/auth/register", json={"email": "x@example.com", "password": "short"}
    )
    assert bad.status_code == 422
    assert bad.json()["error"]["code"] == "validation_error"

    session = await register()
    # Registering the same email again is a conflict.
    duplicate = await client.post(
        f"{API}/auth/register",
        json={"email": session["email"], "password": "anotherpassword"},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "email_taken"


async def test_login_and_refresh(client, register):
    session = await register()
    login = await client.post(
        f"{API}/auth/login",
        json={"email": session["email"], "password": session["password"]},
    )
    assert login.status_code == 200, login.text
    tokens = login.json()
    assert tokens["access_token"]
    assert tokens["refresh_token"]

    refresh = await client.post(
        f"{API}/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert refresh.status_code == 200
    assert refresh.json()["access_token"]

    wrong = await client.post(
        f"{API}/auth/login", json={"email": session["email"], "password": "wrong-password"}
    )
    assert wrong.status_code == 401
    assert wrong.json()["error"]["code"] == "invalid_credentials"


async def test_cross_user_cannot_generate_on_someone_elses_book(client, register):
    owner = await register()
    create = await client.post(
        f"{API}/books",
        headers=owner["headers"],
        json={"topic": "Owner's private book", "target_pages": 6, "chapter_count": 3},
    )
    book_id = create.json()["id"]

    intruder = await register()
    resp = await client.post(
        f"{API}/books/{book_id}/generate",
        headers=intruder["headers"],
        json={"type": "full_book"},
    )
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "book_not_found"


async def test_book_listing_and_cost_estimate(client, register):
    session = await register()
    headers = session["headers"]
    for n in range(2):
        await client.post(
            f"{API}/books",
            headers=headers,
            json={"topic": f"Topic number {n}", "target_pages": 6, "chapter_count": 3},
        )
    listing = await client.get(f"{API}/books", headers=headers)
    assert listing.status_code == 200
    assert listing.json()["total"] == 2
    assert len(listing.json()["items"]) == 2
