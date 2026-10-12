"""Local signed-download endpoint.

When ``STORAGE_BACKEND=local`` there is no object store to mint presigned URLs.
Instead :meth:`LocalStorage.signed_url` returns a link to this route with an
HMAC-signed token. Tokens are single-purpose (they only authorise the exact key
they were signed for) and expire after ``SIGNED_URL_EXPIRE_SECONDS``.

With ``STORAGE_BACKEND=s3`` downloads go straight to the presigned S3 URL and
this route returns 404, so nothing is exposed by accident.
"""

from __future__ import annotations

from fastapi import APIRouter, Query
from fastapi.responses import FileResponse

from app.core.config import get_settings
from app.core.errors import NotFoundError, StorageError
from app.services.storage import LocalStorage, get_storage, guess_content_type

router = APIRouter(tags=["files"])


@router.get("/files/{key:path}")
async def download_file(
    key: str,
    token: str = Query(..., description="Signed token returned by a download-URL endpoint."),
    filename: str | None = Query(default=None),
) -> FileResponse:
    storage = get_storage()
    if not isinstance(storage, LocalStorage):
        raise NotFoundError("Direct downloads are disabled.", code="not_available")

    settings = get_settings()
    verified_key = storage.verify(token, max_age=settings.signed_url_expire_seconds)
    if verified_key != key:
        raise StorageError("Token does not match the requested file.", status_code=403)

    path = storage.local_path(key)
    if not path.exists():
        raise NotFoundError("File not found.", code="file_not_found")

    return FileResponse(
        path,
        media_type=guess_content_type(key),
        filename=filename or path.name,
    )
