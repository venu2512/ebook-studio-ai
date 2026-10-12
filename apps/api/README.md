# eBook Studio AI — API

FastAPI backend for eBook Studio AI: auth, books, the eight-agent generation
pipeline, exports and billing.

See the [root README](../../README.md) for full setup, architecture and the
agent flow. Quick start:

```bash
# From apps/api
uv sync --group dev
cp ../../.env.example ../../.env
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

Without PostgreSQL you can run everything on SQLite:

```bash
export DATABASE_URL="sqlite+aiosqlite:///./ebook_studio.db"
uv run python -m app.scripts.seed   # seed templates + demo data
uv run uvicorn app.main:app --reload
```
