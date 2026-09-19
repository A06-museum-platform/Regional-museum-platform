"""Application settings loaded from the environment / .env.

Supabase keys are optional at import time so the API (and its tests)
can start without a bucket configured; the storage service raises a
clear 503 only when an upload is actually attempted.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql://museum:museum@localhost:5432/museum"
    secret_key: str = "change-me-in-local-development"
    access_token_expire_minutes: int = 60
    frontend_origin: str = "http://localhost:5173"

    # Supabase Storage (staff media uploads). Leave blank for local-only dev.
    supabase_url: str = ""
    supabase_service_key: str = ""
    supabase_bucket: str = "museum-media"
    max_image_mb: int = 5
    max_video_mb: int = 40

    model_config = {"env_file": ".env", "extra": "ignore"}

    @property
    def storage_configured(self) -> bool:
        return bool(self.supabase_url and self.supabase_service_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
