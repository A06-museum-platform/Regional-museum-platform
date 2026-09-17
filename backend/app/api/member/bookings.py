"""
Member-only ticket bookings.
POST /bookings      -> FR-07, FR-14, NFR-08 (atomic capacity decrement)
GET  /bookings/me   -> FR-17
GET  /bookings/{id} -> FR-08 (confirmation w/ reference code)
DELETE /bookings/{id} -> FR-20 (cancel before cutoff)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.booking import Booking, BookingStatus, TimeSlot
from app.models.user import User, UserRole
from app.schemas.booking import BookingCreate, BookingOut

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.post("", response_model=BookingOut, status_code=status.HTTP_201_CREATED)
def create_booking(
    payload: BookingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Atomic capacity decrement (NFR-08): a single conditional UPDATE means
    # the DB enforces "don't oversell" under concurrent requests.
    result = db.execute(
        update(TimeSlot)
        .where(
            TimeSlot.slot_id == payload.slot_id,
            TimeSlot.remaining_capacity >= payload.party_size,
        )
        .values(remaining_capacity=TimeSlot.remaining_capacity - payload.party_size)
    )
    if result.rowcount == 0:
        slot_exists = db.get(TimeSlot, payload.slot_id) is not None
        db.rollback()
        if not slot_exists:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Time slot not found")
        raise HTTPException(status.HTTP_409_CONFLICT, "Not enough capacity for this time slot")

    booking = Booking(
        user_id=current_user.user_id,
        slot_id=payload.slot_id,
        party_size=payload.party_size,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking
    # TODO: trigger confirmation email here (FR-08) -- outside this
    # transaction (background task) so email latency can't block bookings.


@router.get("/me", response_model=list[BookingOut])
def my_bookings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(Booking)
        .filter(Booking.user_id == current_user.user_id)
        .order_by(Booking.created_at.desc())
        .all()
    )


@router.get("/{booking_id}", response_model=BookingOut)
def get_booking(
    booking_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    booking = db.get(Booking, booking_id)
    if not booking:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Booking not found")

    is_owner = booking.user_id == current_user.user_id
    is_staff = current_user.role in (UserRole.STAFF, UserRole.ADMINISTRATOR)
    if not (is_owner or is_staff):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your booking")
    return booking


@router.delete("/{booking_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_booking(
    booking_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    booking = db.get(Booking, booking_id)
    if not booking:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Booking not found")

    is_owner = booking.user_id == current_user.user_id
    is_staff = current_user.role in (UserRole.STAFF, UserRole.ADMINISTRATOR)
    if not (is_owner or is_staff):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your booking")

    if booking.status != BookingStatus.CONFIRMED:
        raise HTTPException(status.HTTP_409_CONFLICT, "Booking is not in a cancellable state")

    # TODO (FR-20): reject if now is past the agreed cancellation cutoff.

    booking.status = BookingStatus.CANCELLED
    db.execute(
        update(TimeSlot)
        .where(TimeSlot.slot_id == booking.slot_id)
        .values(remaining_capacity=TimeSlot.remaining_capacity + booking.party_size)
    )
    db.commit()
    return None
