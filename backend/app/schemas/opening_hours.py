"""Pydantic schemas for opening hours (docs/api-contract.md section 10), in
the { weekly, overrides } shape frontend/src/api/openingHours.js reads.
Times of day are museum-local "HH:MM" strings, null on a closed day."""

import datetime
from typing import Optional

from pydantic import BaseModel, Field


class WeeklyHoursOut(BaseModel):
    id: int
    # 0-6 with Sunday first, like JavaScript's Date.getDay().
    day_of_week: int
    opens_at: Optional[str]
    closes_at: Optional[str]
    is_closed: bool
    note: str


class DateOverrideOut(BaseModel):
    """One date's exception to the weekly pattern (a holiday or closure),
    from opening_hours_override (migration 009)."""

    id: int
    specific_date: datetime.date
    opens_at: Optional[str]
    closes_at: Optional[str]
    is_closed: bool
    note: str


class OpeningHoursOut(BaseModel):
    weekly: list[WeeklyHoursOut]
    overrides: list[DateOverrideOut]


class WeeklyHoursIn(BaseModel):
    day_of_week: int = Field(ge=0, le=6)
    opens_at: Optional[str] = None
    closes_at: Optional[str] = None
    is_closed: bool = False
    note: str = Field(default="", max_length=200)


class DateOverrideIn(BaseModel):
    specific_date: datetime.date
    opens_at: Optional[str] = None
    closes_at: Optional[str] = None
    is_closed: bool = False
    note: str = Field(default="", max_length=200)


class OpeningHoursIn(BaseModel):
    """PUT /api/staff/opening-hours: the whole weekly pattern and the full
    list of dated exceptions (OpeningHoursPage.jsx saves both together)."""

    weekly: list[WeeklyHoursIn] = Field(min_length=7, max_length=7)
    overrides: list[DateOverrideIn] = Field(default_factory=list, max_length=366)
