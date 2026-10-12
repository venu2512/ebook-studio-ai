"""Object storage abstraction (local filesystem or S3-compatible).

Exports, covers and uploads all go through :func:`get_storage`. Downloads are
always served via expiring signed URLs - never a public bucket listing.

* ``STORAGE_BACKEND=local`` -> files under ``LOCAL_STORAGE_DIR``; "signed URLs"
  are HMAC-signed links served by ``GET /api/v1/files/{key}``.
* ``STORAGE_BACKEND=s3`` -> S3 / Cloudflare R2 / MinIO presigned URLs.
"""

from __future__ import annotations

import asyncio
import hashlib
import mimetypes
from abc import ABC, abstractmethod
from functools import lru_cache
from pathlib import Path

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.core.config import get_settings
from app.core.errors import StorageError
from app.core.logging import get_logger

log = get_logger(__name__)


class Storage(ABC):
    """Storage backend interface."""

    @abstractmethod
    async def put_bytes(self, key: str, data: bytes, content_type: str | None = None) -> int:
        """Store bytes and return the size."""

    @abstractmethod
    async def get_bytes(self, key: str) -> bytes:
        """Read bytes back."""

    @abstractmethod
    async def exists(self, key: str) -> bool: ...

    @abstractmethod
    async def delete(self, key: str) -> None: ...

    @abstractmethod
    def signed_url(
        self, key: str, *, expires_in: int | None = None, filename: str | None = None
    ) -> str:
        """Return a time-limited download URL for a key."""

    async def put_text(
        self, key: str, text: str, content_type: str = "text/plain; charset=utf-8"
    ) -> int:
        return await self.put_bytes(key, text.encode("utf-8"), content_type)


def guess_content_type(key: str, fallback: str = "application/octet-stream") -> str:
    guessed, _ = mimetypes.guess_type(key)
    return guessed or fallback


def content_disposition(filename: str) -> str:
    return f'attachment; filename="{filename}"'


class LocalStorage(Storage):
    """Filesystem-backed storage for local development and tests."""

    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self._serializer = URLSafeTimedSerializer(get_settings().jwt_secret, salt="local-storage")

    def _path(self, key: str) -> Path:
        safe = key.replace("..", "_").lstrip("/\\")
        return self.base_dir / safe

    def local_path(self, key: str) -> Path:
        """Public accessor for the on-disk path (used by the download route)."""
        return self._path(key)

    async def put_bytes(self, key: str, data: bytes, content_type: str | None = None) -> int:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(path.write_bytes, data)
        return len(data)

    async def get_bytes(self, key: str) -> bytes:
        path = self._path(key)
        if not path.exists():
            raise StorageError(f"Object not found: {key}", status_code=404)
        return await asyncio.to_thread(path.read_bytes)

    async def exists(self, key: str) -> bool:
        return self._path(key).exists()

    async def delete(self, key: str) -> None:
        path = self._path(key)
        if path.exists():
            await asyncio.to_thread(path.unlink)

    def sign(self, key: str, expires_in: int) -> str:
        """Create a signed token for the download endpoint."""
        return self._serializer.dumps({"key": key, "exp": expires_in})

    def verify(self, token: str, max_age: int) -> str:
        try:
            data = self._serializer.loads(token, max_age=max_age)
        except SignatureExpired as exc:
            raise StorageError("Download link has expired.", status_code=410) from exc
        except BadSignature as exc:
            raise StorageError("Download link is invalid.", status_code=403) from exc
        return str(data["key"])

    def signed_url(
        self, key: str, *, expires_in: int | None = None, filename: str | None = None
    ) -> str:
        settings = get_settings()
        ttl = expires_in or settings.signed_url_expire_seconds
        token = self.sign(key, ttl)
        url = f"{settings.api_base_url}/api/v1/files/{key}?token={token}"
        if filename:
            url += f"&filename={filename}"
        return url


class S3Storage(Storage):
    """S3 / R2 / MinIO storage using presigned URLs."""

    def __init__(self) -> None:
        import boto3

        settings = get_settings()
        self._settings = settings
        self._bucket = settings.s3_bucket
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url or None,
            region_name=settings.s3_region,
            aws_access_key_id=settings.s3_access_key_id,
            aws_secret_access_key=settings.s3_secret_access_key,
        )

    async def put_bytes(self, key: str, data: bytes, content_type: str | None = None) -> int:
        ctype = content_type or guess_content_type(key)
        try:
            await asyncio.to_thread(
                self._client.put_object,
                Bucket=self._bucket,
                Key=key,
                Body=data,
                ContentType=ctype,
            )
        except Exception as exc:
            log.error("s3_put_failed", key=key, error=str(exc))
            raise StorageError("Failed to upload file to storage.") from exc
        return len(data)

    async def get_bytes(self, key: str) -> bytes:
        try:
            response = await asyncio.to_thread(
                self._client.get_object, Bucket=self._bucket, Key=key
            )
            return await asyncio.to_thread(response["Body"].read)
        except Exception as exc:
            raise StorageError(f"Object not found: {key}", status_code=404) from exc

    async def exists(self, key: str) -> bool:
        try:
            await asyncio.to_thread(self._client.head_object, Bucket=self._bucket, Key=key)
            return True
        except Exception:  # noqa: BLE001
            return False

    async def delete(self, key: str) -> None:
        try:
            await asyncio.to_thread(self._client.delete_object, Bucket=self._bucket, Key=key)
        except Exception as exc:  # noqa: BLE001
            log.warning("s3_delete_failed", key=key, error=str(exc))

    def signed_url(
        self, key: str, *, expires_in: int | None = None, filename: str | None = None
    ) -> str:
        settings = self._settings
        ttl = expires_in or settings.signed_url_expire_seconds
        params: dict[str, str] = {"Bucket": self._bucket, "Key": key}
        if filename:
            params["ResponseContentDisposition"] = content_disposition(filename)
        return self._client.generate_presigned_url("get_object", Params=params, ExpiresIn=ttl)


@lru_cache
def get_storage() -> Storage:
    settings = get_settings()
    if settings.storage_backend == "s3":
        return S3Storage()
    return LocalStorage(settings.local_storage_path)


def reset_storage_cache() -> None:
    """Used by tests when settings change."""
    get_storage.cache_clear()


def checksum(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()
