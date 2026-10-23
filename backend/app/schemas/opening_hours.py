"""Pydantic schemas for opening hours (docs/api-contract.md section 10), in
the { weekly, overrides } shape frontend/src/api/openingHours.js reads.
Times of day are museum-local "HH:MM" strings, null on a closed day."""

import datetime
from typing import Optional

from pydantic import BaseModel


class WeeklyHoursOut(BaseModel):
    id: int
    # 0-6 with Sunday first, like JavaScript's Date.getDay().
    day_of_week: int
    opens_at: Optional[str]
    closes_at: Optional[str]
    is_closed: bool
    note: str


class DateOverrideOut(BaseModel):
    """One date's exception to the weekly pattern (a holiday or closure).
    Nothing stores these yet, so the list is always empty."""

    id: int
    specific_date: datetime.date
    opens_at: Optional[str]
    closes_at: Optional[str]
    is_closed: bool
    note: str


class OpeningHoursOut(BaseModel):
    weekly: list[WeeklyHoursOut]
    overrides: list[DateOverrideOut]
