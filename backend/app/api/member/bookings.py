"""Booking endpoints for signed-in accounts (docs/decisions.md, "Booking and
membership").

POST /api/bookings                      -> 201 booking with its reference
GET  /api/bookings/me                   -> the caller's bookings, newest visit first
GET  /api/bookings/{reference}          -> that booking, for its owner; staff and
                                           admins see any. Anyone else gets 404,
                                           not 403, so references can't be probed.
POST /api/bookings/{reference}/cancel   -> cancel an upcoming (reserved) booking;
                                           409 CONFLICT otherwise

Any account may book (role-permission matrix, "Book tickets": every role);
Member tickets also need an active membership. Not signed in -> 401.

Declare fixed paths such as /me above /{reference}: routes match in order,
so "me" would otherwise be read as a booking reference.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import STAFF_ROLES, get_current_user
from app.db.session import get_session
from app.schemas.booking import BookingIn, BookingListOut, BookingOut
from app.schemas.user import UserOut
from app.services import activity_service
from app.services.booking_service import cancel_booking, create_booking, get_booking, list_bookings

router = APIRouter(prefix="/api/bookings", tags=["bookings"])


@router.post("", response_model=BookingOut, status_code=201)
async def book_tickets(
    body: BookingIn,
    user: UserOut = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    booking = await create_booking(db, user.id, body)
    count = sum(line.quantity for line in booking.lines)
    await activity_service.record(db, user, "booking.created",
                                  f"{booking.visit_date:%a %d %b %Y}, {booking.arrival_window.start} — "
                                  f"{count} ticket{'s' if count != 1 else ''}",
                                  reference=booking.reference)
    return booking


@router.get("/me", response_model=BookingListOut)
async def my_bookings(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    user: UserOut = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    items, total = await list_bookings(db, user_id=user.id, page=page, size=size)
    return BookingListOut(items=items, total=total, page=page, size=size)


@router.get("/{reference}", response_model=BookingOut)
async def read_booking(
    reference: str,
    user: UserOut = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    return await get_booking(db, reference, user.id, sees_all=user.role in STAFF_ROLES)


@router.post("/{reference}/cancel", response_model=BookingOut)
async def cancel_my_booking(
    reference: str,
    user: UserOut = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    booking = await cancel_booking(db, reference, user.id, sees_all=user.role in STAFF_ROLES)
    await activity_service.record(db, user, "booking.cancelled",
                                  f"{booking.visit_date:%a %d %b %Y}, {booking.arrival_window.start}",
                                  reference=booking.reference, subject_user_id=booking.user_id)
    return booking
