# =============================================================================
# eBook Studio AI API image
# Multi-stage: install deps with uv, then run as a non-root user.
# =============================================================================
FROM python:3.12-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/usr/local

# System dependencies:
#  - libpq5: asyncpg runtime
#  - weasyprint libs (pango/cairo/gdk-pixbuf) enable the high-fidelity PDF renderer
#  - fonts-dejavu: embedded PDF fonts
#  - curl: container healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
      libpq5 \
      curl \
      libpango-1.0-0 \
      libpangoft2-1.0-0 \
      libcairo2 \
      libgdk-pixbuf-2.0-0 \
      libffi-dev \
      shared-mime-info \
      fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# ---------------------------------------------------------------------------
# Dependencies (cached layer)
# ---------------------------------------------------------------------------
FROM base AS deps
COPY pyproject.toml uv.lock* ./
# Install the base project plus the optional `pdf` extra (weasyprint).
RUN uv sync --no-install-project --extra pdf || uv pip install --system -e ".[pdf]"

# ---------------------------------------------------------------------------
# Runtime
# ---------------------------------------------------------------------------
FROM base AS runtime
COPY --from=deps /usr/local /usr/local
COPY . .

# Non-root user
RUN useradd --create-home --uid 10001 appuser && \
    mkdir -p /app/storage && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Run migrations, then serve. `sh -c` so the exec form isn't needed.
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers"]
