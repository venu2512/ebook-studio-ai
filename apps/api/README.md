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

## Live smoke test

With the server running, exercise the full vertical slice over HTTP (register →
create book → outline → approve → full book → download → marketing kit):

```bash
uv run python -m app.scripts.smoke_live --base-url http://127.0.0.1:8000
```

It exits non-zero on the first failed assertion and also checks that billing is
idempotent (exactly two generation charges). See the root README for the
SQLite + mock-LLM setup it expects.
