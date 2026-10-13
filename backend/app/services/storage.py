"""Storage backends behind one interface (design: docs/design/media-storage.md).

- SupabaseStorage: primary, plain httpx REST (no supabase-py dependency).
- S3Storage: warm standby for Cloudflare R2 (S3 API via boto3).
- LocalStorage: last-resort fallback, docker volume + StaticFiles.

Business rules live here, not in route handlers (CONTRIBUTING.md):
file validation, storage key layout, upload/delete. Postgres only ever
stores the public URL (or local path); see media_asset.storage.
"""

import uuid
from pathlib import Path
from typing import Optional

import anyio
import httpx

MEDIA_BACKENDS = ("supabase", "r2", "local")


def r2_public_base(endpoint: str, bucket: str, public_base: str = "") -> str:
    """Single source of truth for R2 public URLs, shared by upload and
    delete-path key extraction so the two can never drift apart.

    R2's S3 *API* endpoint does not serve browsers — a public base (the
    bucket's r2.dev subdomain or a custom domain, Dashboard → R2 →
    Settings) is required. Failing fast here beats storing URLs nobody
    can fetch.
    """
    base = (public_base or "").rstrip("/")
    if not base:
        raise StorageNotConfigured(
            "R2 public base URL is not configured. Set R2_PUBLIC_BASE to "
            "the bucket's public r2.dev subdomain or custom domain."
        )
    return base

IMAGE_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}
VIDEO_CONTENT_TYPES = {"video/mp4", "video/webm"}
EXTENSION_BY_TYPE = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "video/mp4": ".mp4",
    "video/webm": ".webm",
}


class UploadRejected(ValueError):
    """Raised when a file fails validation. `code` maps to the API contract."""

    def __init__(self, detail: str, code: str = "VALIDATION_ERROR"):
        super().__init__(detail)
        self.detail = detail
        self.code = code


class StorageNotConfigured(RuntimeError):
    def __init__(self, detail: str = "Media uploads are not configured on this server"):
        super().__init__(detail)
        self.detail = detail
        self.code = "STORAGE_NOT_CONFIGURED"


def validate_upload(
    filename: str,
    content_type: Optional[str],
    size_bytes: int,
    max_image_mb: int,
    max_video_mb: int,
) -> str:
    """Return 'image' or 'video' if the upload is acceptable, else raise."""
    media_type = None
    if content_type in IMAGE_CONTENT_TYPES:
        media_type = "image"
        limit_mb = max_image_mb
    elif content_type in VIDEO_CONTENT_TYPES:
        media_type = "video"
        limit_mb = max_video_mb
    else:
        raise UploadRejected(
            f"Unsupported file type: {content_type or 'unknown'}. "
            "Allowed: JPEG, PNG, WebP images and MP4, WebM video."
        )
    if size_bytes <= 0:
        raise UploadRejected("Uploaded file is empty.")
    if size_bytes > limit_mb * 1024 * 1024:
        raise UploadRejected(
            f"File is too large ({size_bytes / 1048576:.1f} MB). "
            f"Limit for {media_type} is {limit_mb} MB.",
            code="FILE_TOO_LARGE",
        )
    ext = "." + (filename.rsplit(".", 1)[-1].lower() if "." in filename else "")
    if ext != EXTENSION_BY_TYPE[content_type]:
        raise UploadRejected(
            f"File extension {ext or '(none)'} does not match content type {content_type}."
        )
    return media_type


def storage_key(owner_type: str, owner_id: int, content_type: str) -> str:
    """uploads/<owner_type>/<owner_id>/<uuid>.<ext> — no user input in path."""
    return (
        f"uploads/{owner_type}/{owner_id}/"
        f"{uuid.uuid4().hex}{EXTENSION_BY_TYPE[content_type]}"
    )


class SupabaseStorage:
    def __init__(self, url: str, service_key: str, bucket: str):
        if not url or not service_key:
            raise StorageNotConfigured()
        self.url = url.rstrip("/")
        self.bucket = bucket
        self._headers = {
            "apikey": service_key,
        }
        # New secret keys resolve to service_role via apikey and aren't JWTs.
        if not service_key.startswith("sb_secret_"):
            self._headers["Authorization"] = f"Bearer {service_key}"

    def public_url(self, key: str) -> str:
        return f"{self.url}/storage/v1/object/public/{self.bucket}/{key}"

    async def upload(self, key: str, data: bytes, content_type: str) -> str:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{self.url}/storage/v1/object/{self.bucket}/{key}",
                content=data,
                headers={
                    **self._headers,
                    "Content-Type": content_type,
                    "x-upsert": "false",
                },
            )
        if resp.status_code not in (200, 201):
            raise RuntimeError(f"Supabase upload failed: {resp.status_code}")
        return self.public_url(key)

    async def remove(self, key: str) -> None:
        async with httpx.AsyncClient(timeout=30) as client:
            await client.delete(
                f"{self.url}/storage/v1/object/{self.bucket}/{key}",
                headers=self._headers,
            )


class LocalStorage:
    """Fallback backend: files on a docker volume, served by StaticFiles
    mounted at /uploads (see main.py). URLs are paths, resolved by the
    frontend against the API origin (media.js resolveMediaUrl)."""

    def __init__(self, root: str = "/app/uploads"):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def public_url(self, key: str) -> str:
        return f"/uploads/{key}"

    async def upload(self, key: str, data: bytes, content_type: str) -> str:
        dest = self.root / key
        if ".." in Path(key).parts:
            raise UploadRejected("Invalid storage key.")
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return self.public_url(key)

    async def remove(self, key: str) -> None:
        dest = self.root / key
        if ".." in Path(key).parts:
            return
        try:
            dest.unlink()
        except FileNotFoundError:
            pass


class S3Storage:
    """Warm-standby backend for Cloudflare R2 (or any S3 API target).
    Bucket must be public-read; credentials are a scoped R2 API token."""

    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        public_base: str = "",
    ):
        if not endpoint or not access_key or not secret_key:
            raise StorageNotConfigured()
        import boto3

        self.bucket = bucket
        self.public_base = r2_public_base(endpoint, bucket, public_base)
        # R2 signs S3 requests for the `auto` region. boto3's default
        # (us-east-1) produces signatures R2 rejects — the live path would
        # fail while mocked tests pass, exactly the kind of gap that only
        # shows up during an outage.
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            region_name="auto",
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )

    def public_url(self, key: str) -> str:
        return f"{self.public_base}/{key}"

    async def upload(self, key: str, data: bytes, content_type: str) -> str:
        # boto3 is synchronous: never block the event loop with it. A slow
        # R2 call would otherwise stall unrelated API traffic — exactly the
        # wrong failure mode for the backend meant to survive outages.
        await anyio.to_thread.run_sync(
            lambda: self._client.put_object(
                Bucket=self.bucket, Key=key, Body=data, ContentType=content_type
            )
        )
        return self.public_url(key)

    async def remove(self, key: str) -> None:
        await anyio.to_thread.run_sync(
            lambda: self._client.delete_object(Bucket=self.bucket, Key=key)
        )


def build_storage(mode, settings):
    """Build the backend named by `mode` (not necessarily the active one).
    Delete paths use this with the ROW's stored backend: after a flip, old
    rows still live where they were written, and removing via the current
    backend would target the wrong system with the wrong key.
    """
    mode = (mode or "local").lower()
    if mode not in MEDIA_BACKENDS:
        raise ValueError(
            f"Unsupported storage backend={mode!r}. "
            f"Expected one of: {', '.join(MEDIA_BACKENDS)}."
        )
    if mode == "local":
        return LocalStorage(settings.local_upload_dir)
    if mode == "r2":
        return S3Storage(
            settings.r2_endpoint,
            settings.r2_access_key,
            settings.r2_secret_key,
            settings.r2_bucket,
            settings.r2_public_base,
        )
    return SupabaseStorage(
        settings.supabase_url,
        settings.supabase_service_key,
        settings.supabase_bucket,
    )


def get_storage(settings):
    """Factory honoring MEDIA_BACKEND. Raises StorageNotConfigured (→503)
    when the selected backend lacks credentials. 'local' never fails.
    Unknown modes raise ValueError (also rejected at startup by the
    Settings validator) — never silently fall through to Supabase, which
    would upload bytes and then fail the storage CHECK, orphaning objects.
    """
    return build_storage(settings.media_backend, settings)
