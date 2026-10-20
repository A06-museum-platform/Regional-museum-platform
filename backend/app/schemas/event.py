"""Pydantic schemas for public events (docs/api-contract.md section 3)."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class EventOut(BaseModel):
    id: int
    display_name: str
    event_time: datetime
    description: Optional[str]
    location: Optional[str]
    thumbnail_url: Optional[str]
