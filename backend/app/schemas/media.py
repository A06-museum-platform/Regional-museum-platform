"""Pydantic schemas for media assets (snake_case per API contract)."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class MediaOut(BaseModel):
    media_id: int
    collection_item_id: Optional[int] = None
    exhibition_id: Optional[int] = None
    event_id: Optional[int] = None
    url: str
    media_type: str
    sort_order: int = 0
    is_primary: bool = False
    created_at: Optional[datetime] = None


class MediaUploadOut(BaseModel):
    media: MediaOut
    thumbnail_url: str
