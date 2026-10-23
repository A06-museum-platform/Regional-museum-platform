"""Public booking endpoints (docs/decisions.md, "Booking and membership").

GET /api/bookings/availability?date=YYYY-MM-DD
    -> { date, is_closed, opens_at, closes_at, note,
         windows: [{ start, end, places_left }] }

Times are museum-local "HH:MM". A missing or malformed date is 400
VALIDATION_ERROR, the contract's answer to bad query input.
"""

import re
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApiError
from app.db.session import get_session
from app.schemas.booking import AvailabilityOut
from app.services.booking_service import get_availability

router = APIRouter(prefix="/api/bookings", tags=["bookings"])

_ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")


def _parse_date(value: Optional[str]) -> date:
    # The pattern first: fromisoformat alone also accepts 20261024 and 2026-W43-6.
    if value is not None and _ISO_DATE.fullmatch(value):
        try:
            return date.fromisoformat(value)
        except ValueError:  # e.g. 2026-02-30
            pass
    raise ApiError(400, "date must be YYYY-MM-DD", "VALIDATION_ERROR")


@router.get("/availability", response_model=AvailabilityOut)
async def get_booking_availability(
    visit_date: Optional[str] = Query(None, alias="date"),
    db: AsyncSession = Depends(get_session),
):
    return await get_availability(db, _parse_date(visit_date))
