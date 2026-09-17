"""
Public visit-planning info that doesn't need login.
GET /time-slots -> FR-07 (check availability for a date, before booking)

Opening hours / facilities / accessibility (FR-04, FR-05) belong here too
once built -- this file is the natural home for all "plan your visit" reads.
"""
from datetime import date as date_type

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.booking import TimeSlot
from app.schemas.booking import TimeSlotOut

router = APIRouter(tags=["visit-information"])


@router.get("/time-slots", response_model=list[TimeSlotOut])
def list_available_time_slots(
    slot_date: date_type = Query(..., alias="date"),
    db: Session = Depends(get_db),
):
    return (
        db.query(TimeSlot)
        .filter(TimeSlot.date == slot_date)
        .order_by(TimeSlot.start_time)
        .all()
    )
