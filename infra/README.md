# Infrastructure

All service definitions live in the root [`docker-compose.yml`](../docker-compose.yml).
This directory holds **local, git-ignored data** created by the stack at runtime:

| Path | Owner | Contents |
| --- | --- | --- |
| `infra/postgres-data/` | `postgres` service | Database files (named volume by default) |
| `infra/minio-data/` | `minio` service | Object-storage bucket data |
| `infra/data/` | local dev | Ad-hoc scratch data (generated exports, etc.) |

These paths are ignored via `.gitignore` and `.dockerignore`, so they never end up
in commits or Docker build contexts.

## Runtime services

| Service | Image | Port(s) | Purpose |
| --- | --- | --- | --- |
| `postgres` | `postgres:16-alpine` | 5432 | Primary datastore |
| `redis` | `redis:7-alpine` | 6379 | Queue, cache, rate limiting |
| `minio` | `minio/minio` | 9000/9001 | S3-compatible object storage |
| `minio-init` | `minio/mc` | — | Creates the bucket once, then exits |
| `api` | built from `apps/api` | 8000 | FastAPI + migrations on boot |
| `worker` | built from `apps/api` | — | arq worker for background jobs |
| `web` | built from `apps/web` | 3000 | Next.js front end |

## Common commands

```bash
docker compose up --build          # start everything
docker compose exec api python -m app.scripts.seed   # seed templates + demo data
docker compose logs -f api worker  # follow logs
docker compose down                # stop (keeps volumes)
docker compose down -v             # stop and delete volumes/data
```

> To wipe locally-persisted data manually, delete the corresponding directory
> under `infra/` (or remove the named volumes with `docker compose down -v`).
