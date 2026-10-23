"""Opening hours (docs/api-contract.md section 10; client: "update opening
hours" -- they change seasonally).

opening_hours stores the weekly pattern, one row per day name ('Monday' ...
'Sunday'); opening_hours_override (migration 009) stores dated exceptions
such as public holidays. The API sends day_of_week as 0-6 with Sunday
first, like JavaScript's Date.getDay(), because that is how the front end
looks a date up.

Booking availability reads the same rows through hours_on(), so an override
closes the booking page for that date too.
"""

from datetime import date, time
from types import SimpleNamespace
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApiError
from app.schemas.opening_hours import (
    DateOverrideOut,
    OpeningHoursIn,
    OpeningHoursOut,
    WeeklyHoursOut,
)

# opening_hours.day_of_week values, indexed like date.weekday() (Monday is 0).
DAY_NAMES = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")

# The platform has one museum (locked scope); every read uses its rows.
_MUSEUM_ID = "(SELECT MIN(museum_info_id) FROM museum_information)"


def _hhmm(value: Optional[time]) -> Optional[str]:
    return value.strftime("%H:%M") if value is not None else None


def _js_day(day_name: str) -> int:
    return (DAY_NAMES.index(day_name) + 1) % 7  # Sunday -> 0


def _parse(value: Optional[str]) -> Optional[time]:
    if value in (None, ""):
        return None
    try:
        hours, minutes = value.split(":")[:2]
        return time(int(hours), int(minutes))
    except (ValueError, AttributeError):
        raise ApiError(422, f"{value!r} is not a time (HH:MM).", "INVALID_HOURS")


async def get_opening_hours(db: AsyncSession, *, include_past_overrides: bool = False) -> OpeningHoursOut:
    rows = (
        await db.execute(
            text("SELECT opening_hours_id, day_of_week, open_time, close_time, is_closed, note "
                 f"FROM opening_hours WHERE museum_info_id = {_MUSEUM_ID}")
        )
    ).all()
    weekly = sorted(
        (
            WeeklyHoursOut(
                id=row.opening_hours_id,
                day_of_week=_js_day(row.day_of_week),
                opens_at=_hhmm(row.open_time),
                closes_at=_hhmm(row.close_time),
                is_closed=row.is_closed,
                note=row.note,
            )
            for row in rows
        ),
        key=lambda row: row.day_of_week,
    )
    since = "" if include_past_overrides else \
        "AND override_date >= (now() AT TIME ZONE 'Australia/Adelaide')::date "
    overrides = [
        DateOverrideOut(
            id=row.override_id,
            specific_date=row.override_date,
            opens_at=_hhmm(row.open_time),
            closes_at=_hhmm(row.close_time),
            is_closed=row.is_closed,
            note=row.note,
        )
        for row in (
            await db.execute(
                text("SELECT override_id, override_date, open_time, close_time, is_closed, note "
                     f"FROM opening_hours_override WHERE museum_info_id = {_MUSEUM_ID} {since}"
                     "ORDER BY override_date")
            )
        ).all()
    ]
    return OpeningHoursOut(weekly=weekly, overrides=overrides)


async def hours_on(db: AsyncSession, day: date):
    """What applies on one date: (open_time, close_time, is_closed, note),
    from that date's override if there is one, else its weekday. None when
    the weekday has no row."""
    override = (
        await db.execute(
            text("SELECT ov.open_time, ov.close_time, ov.is_closed, ov.note "
                 "FROM opening_hours_override ov "
                 f"WHERE ov.museum_info_id = {_MUSEUM_ID} AND ov.override_date = :day"),
            {"day": day},
        )
    ).first()
    if override is not None:
        return override
    row = (
        await db.execute(
            text("SELECT oh.open_time, oh.close_time, oh.is_closed, oh.note FROM opening_hours oh "
                 f"WHERE oh.day_of_week = :day AND oh.museum_info_id = {_MUSEUM_ID}"),
            {"day": DAY_NAMES[day.weekday()]},
        )
    ).first()
    if row is None:
        return None
    return SimpleNamespace(open_time=row.open_time, close_time=row.close_time,
                           is_closed=row.is_closed, note=getattr(row, "note", "") or "")


def _validated(row) -> tuple[Optional[time], Optional[time]]:
    if row.is_closed:
        return None, None
    opens, closes = _parse(row.opens_at), _parse(row.closes_at)
    if opens is None or closes is None or opens >= closes:
        raise ApiError(422, "Every open day needs an opening time earlier than its closing time.",
                       "INVALID_HOURS")
    return opens, closes


async def save_opening_hours(db: AsyncSession, body: OpeningHoursIn) -> OpeningHoursOut:
    """Replace the weekly pattern (all seven days) and the list of dated
    overrides in one transaction."""
    days = sorted(row.day_of_week for row in body.weekly)
    if days != list(range(7)):
        raise ApiError(422, "Send all seven days of the week, once each.", "INVALID_HOURS")
    dates = [row.specific_date for row in body.overrides]
    if len(dates) != len(set(dates)):
        raise ApiError(422, "Each date can only have one exception.", "INVALID_HOURS")

    museum_id = (await db.execute(text(f"SELECT {_MUSEUM_ID}"))).scalar_one()
    for row in body.weekly:
        opens, closes = _validated(row)
        name = DAY_NAMES[(row.day_of_week - 1) % 7]  # JS 0 (Sunday) -> 'Sunday'
        params = {"museum": museum_id, "day": name, "opens": opens, "closes": closes,
                  "closed": row.is_closed, "note": row.note.strip()}
        updated = await db.execute(
            text("UPDATE opening_hours SET open_time = :opens, close_time = :closes, "
                 "is_closed = :closed, note = :note WHERE museum_info_id = :museum AND day_of_week = :day"),
            params,
        )
        if updated.rowcount == 0:
            await db.execute(
                text("INSERT INTO opening_hours (museum_info_id, day_of_week, open_time, close_time, "
                     "is_closed, note) VALUES (:museum, :day, :opens, :closes, :closed, :note)"),
                params,
            )

    await db.execute(text("DELETE FROM opening_hours_override WHERE museum_info_id = :museum"),
                     {"museum": museum_id})
    for row in body.overrides:
        opens, closes = _validated(row)
        await db.execute(
            text("INSERT INTO opening_hours_override (museum_info_id, override_date, open_time, "
                 "close_time, is_closed, note) VALUES (:museum, :day, :opens, :closes, :closed, :note)"),
            {"museum": museum_id, "day": row.specific_date, "opens": opens, "closes": closes,
             "closed": row.is_closed, "note": row.note.strip()},
        )
    await db.commit()
    return await get_opening_hours(db, include_past_overrides=True)
