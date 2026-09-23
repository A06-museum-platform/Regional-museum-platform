"""Supabase Storage client over plain httpx (no supabase-py dependency).

Business rules live here, not in route handlers (CONTRIBUTING.md):
file validation, storage key layout, upload/delete against the
Storage REST API. Postgres only ever stores the public URL.
"""

import uuid
from typing import Optional

import httpx

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
    def __init__(self):
        super().__init__("Supabase storage is not configured")
        self.detail = "Media uploads are not configured on this server"
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
            "Authorization": f"Bearer {service_key}",
        }

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
