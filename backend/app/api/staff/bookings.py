"""
Staff booking management.
GET /bookings -> FR-13 (filter by date)
POST/PUT /time-slots -> FR-12 (staff sets up slots/capacity)
"""
from datetime import date as date_type

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.db.session import get_db
from app.models.booking import Booking, TimeSlot
from app.models.user import User, UserRole
from app.schemas.booking import TimeSlotCreate, TimeSlotOut, TimeSlotUpdate
from app.schemas.booking import BookingOut
from app.schemas.common import PaginatedResponse

router = APIRouter(tags=["bookings-admin"])


@router.get("/bookings", response_model=PaginatedResponse[BookingOut])
def list_bookings(
    booking_date: date_type | None = Query(None, alias="date"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _staff: User = Depends(require_role(UserRole.STAFF, UserRole.ADMINISTRATOR)),
):
    query = db.query(Booking)
    if booking_date:
        query = query.join(TimeSlot).filter(TimeSlot.date == booking_date)

    total = query.count()
    items = (
        query.order_by(Booking.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return PaginatedResponse(items=items, total=total, page=page, page_size=page_size)


@router.post("/time-slots", response_model=TimeSlotOut, status_code=status.HTTP_201_CREATED)
def create_time_slot(
    payload: TimeSlotCreate,
    db: Session = Depends(get_db),
    _staff: User = Depends(require_role(UserRole.STAFF, UserRole.ADMINISTRATOR)),
):
    slot = TimeSlot(**payload.model_dump(), remaining_capacity=payload.capacity)
    db.add(slot)
    db.commit()
    db.refresh(slot)
    return slot


@router.put("/time-slots/{slot_id}", response_model=TimeSlotOut)
def update_time_slot(
    slot_id: str,
    payload: TimeSlotUpdate,
    db: Session = Depends(get_db),
    _staff: User = Depends(require_role(UserRole.STAFF, UserRole.ADMINISTRATOR)),
):
    slot = db.get(TimeSlot, slot_id)
    if not slot:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Time slot not found")

    data = payload.model_dump(exclude_unset=True)
    if "capacity" in data:
        delta = data["capacity"] - slot.capacity
        slot.remaining_capacity = max(0, slot.remaining_capacity + delta)
        slot.capacity = data["capacity"]
    if "slot_type" in data:
        slot.slot_type = data["slot_type"]

    db.commit()
    db.refresh(slot)
    return slot
