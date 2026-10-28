"""Staff bookings and check-in (role-permission matrix: "View all bookings
and event registrations" -- Staff and Admin; proposal scope: "Booking
Management: enable staff to manage ticket reservations and event
registrations").

GET  /api/staff/bookings?date=&q=&page=&size=   all accounts' bookings
GET  /api/staff/bookings/summary?date=          bookings, tickets, check-ins per window
POST /api/staff/bookings/{reference}/check-in   mark visitors as arrived
POST /api/staff/bookings/{reference}/cancel     cancel on a visitor's behalf
GET  /api/staff/today                           numbers for "Today at a glance"
"""

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_staff
from app.db.session import get_session
from app.schemas.booking import BookingListOut, BookingOut
from app.services import activity_service, booking_service
from app.services.event_service import MUSEUM_TIMEZONE
from app.services.opening_hours_service import hours_on

router = APIRouter(prefix="/api/staff", tags=["staff-bookings"], dependencies=[Depends(require_staff)])


async def _today(db: AsyncSession) -> date:
    return (await db.execute(text(f"SELECT (now() AT TIME ZONE '{MUSEUM_TIMEZONE}')::date"))).scalar_one()


@router.get("/bookings", response_model=BookingListOut)
async def list_bookings(
    visit_date: Optional[date] = Query(None, alias="date"),
    q: Optional[str] = None,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_session),
):
    items, total = await booking_service.list_bookings(
        db, user_id=None, page=page, size=size, visit_date=visit_date, q=q
    )
    return BookingListOut(items=items, total=total, page=page, size=size)


@router.get("/bookings/summary")
async def bookings_summary(visit_date: Optional[date] = Query(None, alias="date"),
                           db: AsyncSession = Depends(get_session)):
    return await booking_service.day_summary(db, visit_date or await _today(db))


@router.post("/bookings/{reference}/check-in", response_model=BookingOut)
async def check_in(reference: str, actor: dict = Depends(require_staff),
                   db: AsyncSession = Depends(get_session)):
    booking = await booking_service.check_in(db, reference)
    count = sum(line.quantity for line in booking.lines)
    await activity_service.record(db, actor, "booking.checked_in",
                                  f"{booking.visitor.first_name} {booking.visitor.last_name} — {count} "
                                  f"ticket{'s' if count != 1 else ''}",
                                  reference=booking.reference, subject_user_id=booking.user_id)
    return booking


@router.post("/bookings/{reference}/cancel", response_model=BookingOut)
async def cancel_for_visitor(reference: str, actor: dict = Depends(require_staff),
                             db: AsyncSession = Depends(get_session)):
    booking = await booking_service.cancel_booking(db, reference, user_id=0, sees_all=True)
    await activity_service.record(db, actor, "booking.cancelled",
                                  f"Cancelled for {booking.visitor.first_name} {booking.visitor.last_name}",
                                  reference=booking.reference, subject_user_id=booking.user_id)
    return booking


@router.get("/today")
async def today_at_a_glance(db: AsyncSession = Depends(get_session)):
    today = await _today(db)
    hours = await hours_on(db, today)
    summary = await booking_service.day_summary(db, today)
    counts = (
        await db.execute(text(
            "SELECT "
            " (SELECT COUNT(*) FROM collection_item) AS objects, "
            " (SELECT COUNT(*) FROM collection_item WHERE publish_status = 'draft') AS draft_objects, "
            " (SELECT COUNT(*) FROM exhibition WHERE publish_status = 'published' "
            f"   AND (end_date IS NULL OR end_date >= (now() AT TIME ZONE '{MUSEUM_TIMEZONE}')::date)) AS exhibitions, "
            " (SELECT COUNT(*) FROM event WHERE status = 'Draft') AS draft_events, "
            " (SELECT COUNT(*) FROM membership WHERE status = 'Pending') AS pending_applications"
        ))
    ).first()
    return {
        "date": today,
        "is_open": bool(hours and not hours.is_closed),
        "opens_at": hours.open_time.strftime("%H:%M") if hours and hours.open_time else None,
        "closes_at": hours.close_time.strftime("%H:%M") if hours and hours.close_time else None,
        "note": getattr(hours, "note", "") if hours else "",
        "bookings": summary,
        "objects": counts.objects,
        "draft_objects": counts.draft_objects,
        "exhibitions": counts.exhibitions,
        "draft_events": counts.draft_events,
        "pending_applications": counts.pending_applications,
    }
