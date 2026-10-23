"""Opening hours (docs/api-contract.md section 10).

opening_hours stores the museum's weekly pattern, one row per day name
('Monday' ... 'Sunday'). The API sends day_of_week as 0-6 with Sunday first,
like JavaScript's Date.getDay(), because that is how the front end looks a
date up. There is no note column and no table for one-off date overrides
(holidays, closures) yet, so note is "" and overrides is always empty.

Booking availability reads the same rows through hours_on(), so the dates
the booking page offers and the arrival windows it then shows agree.
"""

from datetime import date, time
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.opening_hours import OpeningHoursOut, WeeklyHoursOut

# opening_hours.day_of_week values, indexed like date.weekday() (Monday is 0).
DAY_NAMES = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")

# Rows are keyed by museum_information; the platform has one museum, so
# every read uses the lowest id's rows.
_ONE_MUSEUM = "oh.museum_info_id = (SELECT MIN(museum_info_id) FROM opening_hours)"


def _hhmm(value: Optional[time]) -> Optional[str]:
    return value.strftime("%H:%M") if value is not None else None


async def get_opening_hours(db: AsyncSession) -> OpeningHoursOut:
    rows = (
        await db.execute(
            text("SELECT oh.opening_hours_id, oh.day_of_week, oh.open_time, oh.close_time, "
                 f"oh.is_closed FROM opening_hours oh WHERE {_ONE_MUSEUM}")
        )
    ).all()
    weekly = [
        WeeklyHoursOut(
            id=row.opening_hours_id,
            day_of_week=(DAY_NAMES.index(row.day_of_week) + 1) % 7,  # Sunday -> 0
            opens_at=_hhmm(row.open_time),
            closes_at=_hhmm(row.close_time),
            is_closed=row.is_closed,
            note="",
        )
        for row in rows
    ]
    weekly.sort(key=lambda row: row.day_of_week)
    return OpeningHoursOut(weekly=weekly, overrides=[])


async def hours_on(db: AsyncSession, day: date):
    """The row (open_time, close_time, is_closed) that applies to one date,
    or None when its weekday has no row."""
    return (
        await db.execute(
            text("SELECT oh.open_time, oh.close_time, oh.is_closed FROM opening_hours oh "
                 f"WHERE oh.day_of_week = :day AND {_ONE_MUSEUM}"),
            {"day": DAY_NAMES[day.weekday()]},
        )
    ).first()
