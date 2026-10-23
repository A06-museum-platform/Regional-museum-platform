"""Event schemas, in the shape frontend/src/api/events.js uses.

The frozen contract's fields (display_name, event_time, location,
thumbnail_url -- docs/api-contract.md section 3) are sent as well, so a
client written to the contract keeps working.

status: draft (hidden from visitors) / published / cancelled / completed.
spots_remaining and is_sold_out are computed from confirmed registrations;
a page must never count registrations itself."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator

from app.schemas.collection_item import Gallery

EventStatus = Literal["draft", "published", "cancelled", "completed"]


class EventOut(BaseModel):
    id: int
    slug: str
    title: str
    description: Optional[str]
    gallery: Optional[str]
    starts_at: datetime
    ends_at: datetime
    capacity: int
    spots_remaining: int
    is_sold_out: bool
    is_past: bool
    price_cents: int
    member_price_cents: int
    age_min: Optional[int]
    age_max: Optional[int]
    status: str
    image_url: Optional[str]
    # docs/api-contract.md section 3 names
    display_name: str
    event_time: datetime
    location: Optional[str]
    thumbnail_url: Optional[str]
    # Interest tag slugs (migration 011), used for recommendations.
    tags: list[str] = []


class EventListOut(BaseModel):
    items: list[EventOut]
    total: int
    page: int
    page_size: int
    size: int


class StaffEventListOut(BaseModel):
    items: list[EventOut]
    total: int


class EventIn(BaseModel):
    """POST /api/staff/events, as EventEditor.jsx sends it. Times are ISO
    8601 with an offset; they're stored as museum-local date and times, so a
    session must start and finish on the same local day."""

    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=150)
    description: Optional[str] = Field(default=None, max_length=5000)
    gallery: Optional[Gallery] = None
    starts_at: datetime
    ends_at: datetime
    capacity: int = Field(gt=0, le=10000)
    price_cents: int = Field(default=0, ge=0, le=1000000)
    member_price_cents: int = Field(default=0, ge=0, le=1000000)
    age_min: Optional[int] = Field(default=None, ge=0, le=120)
    age_max: Optional[int] = Field(default=None, ge=0, le=120)
    status: EventStatus = "draft"
    tags: list[str] = Field(default_factory=list, max_length=8)

    @model_validator(mode="after")
    def _check(self):
        if self.starts_at.tzinfo is None or self.ends_at.tzinfo is None:
            raise ValueError("starts_at and ends_at need a time zone offset")
        if self.ends_at <= self.starts_at:
            raise ValueError("The finish time needs to be after the start time.")
        if self.age_min is not None and self.age_max is not None and self.age_max < self.age_min:
            raise ValueError("age_max must not be below age_min")
        if self.member_price_cents > self.price_cents:
            raise ValueError("The member price can't be more than the standard price.")
        return self


class EventPatch(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: Optional[str] = Field(default=None, min_length=1, max_length=150)
    description: Optional[str] = Field(default=None, max_length=5000)
    gallery: Optional[Gallery] = None
    starts_at: Optional[datetime] = None
    ends_at: Optional[datetime] = None
    capacity: Optional[int] = Field(default=None, gt=0, le=10000)
    price_cents: Optional[int] = Field(default=None, ge=0, le=1000000)
    member_price_cents: Optional[int] = Field(default=None, ge=0, le=1000000)
    age_min: Optional[int] = Field(default=None, ge=0, le=120)
    age_max: Optional[int] = Field(default=None, ge=0, le=120)
    status: Optional[EventStatus] = None
    tags: Optional[list[str]] = None


class RegistrationIn(BaseModel):
    """POST /api/events/{slug}/registrations (EventDetailPage.jsx)."""

    model_config = ConfigDict(str_strip_whitespace=True)

    contact_name: str = Field(min_length=1, max_length=150)
    contact_email: EmailStr
    party_size: int = Field(ge=1, le=10)


class RegistrationOut(BaseModel):
    id: int
    reference: str
    status: Literal["confirmed", "cancelled", "attended"]
    event_id: int
    event_slug: str
    event_title: str
    starts_at: datetime
    ends_at: datetime
    gallery: Optional[str]
    contact_name: Optional[str]
    contact_email: Optional[str]
    party_size: int
    registered_at: datetime
    is_past: bool


class RegistrationListOut(BaseModel):
    items: list[RegistrationOut]
    total: int
    page: int
    size: int


class StaffRegistrationOut(RegistrationOut):
    user_id: int
    account_email: str
