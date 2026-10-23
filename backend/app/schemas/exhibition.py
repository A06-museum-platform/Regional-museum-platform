"""Exhibition schemas, in the shape frontend/src/api/exhibitions.js uses.

An exhibition groups collection objects in a gallery for a period. `status`
is what staff control (draft / published); `phase` follows the dates
(upcoming / current / closed) and is computed, never stored by the client."""

import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.schemas.collection_item import CollectionItemOut, Gallery, PublishStatus


class ExhibitionOut(BaseModel):
    id: int
    slug: str
    title: str
    summary: Optional[str]
    body: Optional[str]
    gallery: Optional[str]
    start_date: datetime.date
    end_date: Optional[datetime.date]
    age_min: Optional[int]
    age_max: Optional[int]
    hero_image_url: Optional[str]
    status: str
    phase: Literal["upcoming", "current", "closed"]
    item_count: int


class ExhibitionDetailOut(ExhibitionOut):
    items: list[CollectionItemOut]


class ExhibitionListOut(BaseModel):
    items: list[ExhibitionOut]
    total: int
    page: int
    page_size: int


class StaffExhibitionListOut(BaseModel):
    items: list[ExhibitionOut]
    total: int


class ExhibitionIn(BaseModel):
    """POST /api/staff/exhibitions, as ExhibitionEditor.jsx sends it. A draft
    only needs a title; a missing start date defaults to today."""

    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=150)
    summary: Optional[str] = Field(default=None, max_length=500)
    body: Optional[str] = Field(default=None, max_length=10000)
    gallery: Optional[Gallery] = None
    start_date: Optional[datetime.date] = None
    end_date: Optional[datetime.date] = None
    age_min: Optional[int] = Field(default=None, ge=0, le=120)
    age_max: Optional[int] = Field(default=None, ge=0, le=120)
    status: PublishStatus = "draft"

    @model_validator(mode="before")
    @classmethod
    def _blank_dates(cls, data):
        # The form sends "" for an empty date input.
        if isinstance(data, dict):
            for key in ("start_date", "end_date"):
                if data.get(key) == "":
                    data[key] = None
        return data

    @model_validator(mode="after")
    def _check(self):
        if self.start_date and self.end_date and self.end_date < self.start_date:
            raise ValueError("end_date must not be before start_date")
        if self.age_min is not None and self.age_max is not None and self.age_max < self.age_min:
            raise ValueError("age_max must not be below age_min")
        if self.status == "published":
            # A missing start date defaults to today, so it isn't required here.
            missing = [n for n in ("summary", "gallery") if not getattr(self, n)]
            if missing:
                raise ValueError(f"To publish, fill in: {', '.join(missing)}")
        return self


class ExhibitionPatch(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: Optional[str] = Field(default=None, min_length=1, max_length=150)
    summary: Optional[str] = Field(default=None, max_length=500)
    body: Optional[str] = Field(default=None, max_length=10000)
    gallery: Optional[Gallery] = None
    start_date: Optional[datetime.date] = None
    end_date: Optional[datetime.date] = None
    age_min: Optional[int] = Field(default=None, ge=0, le=120)
    age_max: Optional[int] = Field(default=None, ge=0, le=120)
    status: Optional[PublishStatus] = None

    @model_validator(mode="before")
    @classmethod
    def _blank_dates(cls, data):
        if isinstance(data, dict):
            for key in ("start_date", "end_date"):
                if data.get(key) == "":
                    data[key] = None
        return data
