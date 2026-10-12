"""Shared pytest fixtures.

The environment is configured **before** importing any application module so
that the cached ``Settings`` singleton, the SQLAlchemy engine and the LLM client
factory all pick up the test values:

* ``APP_ENV=test``
* SQLite on a temp file (so the inline job task, which opens its own session,
  sees the same database as the request handler)
* the mock LLM provider (no network) and local object storage
"""

from __future__ import annotations

import os
import shutil
import tempfile
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Environment must be set before importing app modules.
# ---------------------------------------------------------------------------
_TMP_ROOT = Path(tempfile.mkdtemp(prefix="ebook-studio-tests-"))
_DB_FILE = _TMP_ROOT / "test.db"
_STORAGE_DIR = _TMP_ROOT / "storage"
_API_BASE_URL = "http://testserver"

os.environ.update(
    {
        "APP_ENV": "test",
        "LOG_LEVEL": "WARNING",
        "DATABASE_URL": f"sqlite+aiosqlite:///{_DB_FILE.as_posix()}?timeout=30",
        "DB_ECHO": "false",
        "LLM_PROVIDER": "mock",
        "JOB_EXECUTION_MODE": "inline",
        "STORAGE_BACKEND": "local",
        "LOCAL_STORAGE_DIR": str(_STORAGE_DIR),
        "JWT_SECRET": "test-secret-do-not-use-in-production",
        "EMAIL_BACKEND": "console",
        "REQUIRE_EMAIL_VERIFICATION": "false",
        "COOKIE_SECURE": "false",
        "SIGNED_URL_EXPIRE_SECONDS": "3600",
        "API_BASE_URL": _API_BASE_URL,
        "RATE_LIMIT_ENABLED": "false",
    }
)

import pytest  # noqa: E402
import pytest_asyncio  # noqa: E402
from asgi_lifespan import LifespanManager  # noqa: E402
from httpx import ASGITransport, AsyncClient  # noqa: E402

import app.db.models  # noqa: E402,F401 - register every model on Base.metadata
from app.core.ratelimit import reset_rate_limits  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import dispose_engine, get_engine  # noqa: E402
from app.services.storage import reset_storage_cache  # noqa: E402

API = "/api/v1"


def _clear_storage() -> None:
    if _STORAGE_DIR.exists():
        shutil.rmtree(_STORAGE_DIR, ignore_errors=True)
    _STORAGE_DIR.mkdir(parents=True, exist_ok=True)


@pytest.fixture(autouse=True)
def reset_app_state() -> None:
    """Reset in-memory caches that could leak between tests."""
    reset_rate_limits()
    reset_storage_cache()
    _clear_storage()
    yield


@pytest_asyncio.fixture
async def prepared_db() -> None:
    """Create a fresh schema on the current event loop and drop it afterwards."""
    await dispose_engine()
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
        await conn.exec_driver_sql("PRAGMA journal_mode=WAL")
    yield
    await dispose_engine()


@pytest_asyncio.fixture
async def db(prepared_db):
    """A transactional session for service-level tests."""
    from app.db.session import session_scope

    async with session_scope() as session:
        yield session


@pytest_asyncio.fixture
async def client(prepared_db):
    """An httpx client wired to the ASGI app with lifespan enabled."""
    from app.main import create_app

    app = create_app()
    async with LifespanManager(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url=_API_BASE_URL) as c:
            yield c


@pytest_asyncio.fixture
async def register(client):
    """Return an async helper that registers a verified user and returns its session."""
    import uuid

    async def _register(
        email: str | None = None,
        password: str = "supersecret123",
        full_name: str = "Test User",
    ) -> dict:
        email = email or f"user-{uuid.uuid4().hex[:10]}@example.com"
        resp = await client.post(
            f"{API}/auth/register",
            json={"email": email, "password": password, "full_name": full_name},
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        token = resp.headers.get("X-Access-Token")
        assert token, "register must return an access token header"
        return {
            "email": email,
            "password": password,
            "user": body,
            "token": token,
            "headers": {"Authorization": f"Bearer {token}"},
        }

    return _register


@pytest_asyncio.fixture
async def wait_for_job(client):
    """Poll a job endpoint until it reaches a terminal state."""

    async def _wait(job_id: str, headers: dict, timeout: float = 120.0) -> dict:  # noqa: ASYNC109
        deadline = time.monotonic() + timeout
        last: dict = {}
        while time.monotonic() < deadline:
            resp = await client.get(f"{API}/jobs/{job_id}", headers=headers)
            assert resp.status_code == 200, resp.text
            last = resp.json()
            if last["status"] in {"succeeded", "failed", "cancelled"}:
                return last
            import asyncio

            await asyncio.sleep(0.1)
        raise AssertionError(f"job {job_id} did not finish within {timeout}s: {last}")

    return _wait


@pytest.fixture
def api_base_url() -> str:
    return _API_BASE_URL
