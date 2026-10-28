"""Application settings loaded from the environment / .env.

Supabase keys are optional at import time so the API (and its tests)
can start without a bucket configured; the storage service raises a
clear 503 only when an upload is actually attempted.
"""

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings

_ALLOWED_BACKENDS = ("supabase", "r2", "local")


class Settings(BaseSettings):
    database_url: str = "postgresql://museum:museum@localhost:5432/museum"
    secret_key: str = "change-me-in-local-development"
    access_token_expire_minutes: int = 60
    frontend_origin: str = "http://localhost:5173"

    # Media backend switch: supabase | r2 | local (default local =
    # zero-config uploads on a docker volume; see docs/design/media-storage.md).
    media_backend: str = "local"

    # Supabase Storage (staff media uploads). Leave blank for local-only dev.
    supabase_url: str = ""
    supabase_service_key: str = ""
    supabase_bucket: str = "museum-media"

    # Cloudflare R2 warm standby (S3 API). Token scoped to one bucket.
    r2_endpoint: str = ""
    r2_access_key: str = ""
    r2_secret_key: str = ""
    r2_bucket: str = "museum-media"
    r2_public_base: str = ""

    # Local fallback: directory served at /uploads (docker volume).
    local_upload_dir: str = "/app/uploads"

    max_image_mb: int = 5
    max_video_mb: int = 40

    model_config = {"env_file": ".env", "extra": "ignore"}

    @field_validator("media_backend")
    @classmethod
    def _known_backend(cls, value: str) -> str:
        if value.lower() not in _ALLOWED_BACKENDS:
            raise ValueError(
                f"Unsupported MEDIA_BACKEND={value!r}. "
                f"Expected one of: {', '.join(_ALLOWED_BACKENDS)}."
            )
        return value.lower()

    @property
    def storage_configured(self) -> bool:
        return bool(self.supabase_url and self.supabase_service_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
