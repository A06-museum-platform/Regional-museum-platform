"""Booking endpoints for signed-in accounts (docs/decisions.md, "Booking and
membership").

POST /api/bookings             -> 201 booking with its reference
GET  /api/bookings/{reference} -> that booking, for its owner; staff and
                                  admins see any. Anyone else gets 404, not
                                  403, so references can't be probed.

Any account may book (role-permission matrix, "Book tickets": every role);
Member tickets also need an active membership. Not signed in -> 401.

Declare fixed paths such as /me above /{reference}: routes match in order,
so "me" would otherwise be read as a booking reference.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import STAFF_ROLES, get_current_user
from app.db.session import get_session
from app.schemas.booking import BookingIn, BookingOut
from app.schemas.user import UserOut
from app.services.booking_service import create_booking, get_booking

router = APIRouter(prefix="/api/bookings", tags=["bookings"])


@router.post("", response_model=BookingOut, status_code=201)
async def book_tickets(
    body: BookingIn,
    user: UserOut = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    return await create_booking(db, user.id, body)


@router.get("/{reference}", response_model=BookingOut)
async def read_booking(
    reference: str,
    user: UserOut = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    return await get_booking(db, reference, user.id, sees_all=user.role in STAFF_ROLES)
