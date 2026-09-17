"""
Member-only event participation.
POST /events/{id}/register -> FR-15 (capacity-checked, atomic via row lock)
GET /registrations/me -> FR-17 (own registration history)
DELETE /registrations/{id} -> FR-20 (cancel own registration)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.event import Event, EventRegistration, EventRegistrationStatus
from app.models.user import User, UserRole
from app.schemas.event import EventRegistrationCreate, EventRegistrationOut

router = APIRouter(tags=["activity"])


@router.post(
    "/events/{event_id}/register",
    response_model=EventRegistrationOut,
    status_code=status.HTTP_201_CREATED,
)
def register_for_event(
    event_id: str,
    payload: EventRegistrationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Lock the event row so two concurrent registrations can't both pass
    # the capacity check and oversell the same event.
    event = db.query(Event).filter(Event.event_id == event_id).with_for_update().first()
    if not event:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Event not found")

    confirmed_count = (
        db.query(func.coalesce(func.sum(EventRegistration.party_size), 0))
        .filter(
            EventRegistration.event_id == event_id,
            EventRegistration.status == EventRegistrationStatus.CONFIRMED,
        )
        .scalar()
    )
    if confirmed_count + payload.party_size > event.capacity:
        raise HTTPException(status.HTTP_409_CONFLICT, "Not enough capacity for this event")

    registration = EventRegistration(
        event_id=event_id,
        user_id=current_user.user_id,
        party_size=payload.party_size,
    )
    db.add(registration)
    db.commit()
    db.refresh(registration)
    return registration


@router.get("/registrations/me", response_model=list[EventRegistrationOut])
def my_registrations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(EventRegistration)
        .filter(EventRegistration.user_id == current_user.user_id)
        .order_by(EventRegistration.created_at.desc())
        .all()
    )


@router.delete("/registrations/{registration_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_registration(
    registration_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    registration = db.get(EventRegistration, registration_id)
    if not registration:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Registration not found")

    is_owner = registration.user_id == current_user.user_id
    is_staff = current_user.role in (UserRole.STAFF, UserRole.ADMINISTRATOR)
    if not (is_owner or is_staff):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Not your registration")

    # TODO (FR-20): enforce the agreed cancellation cutoff once it's defined.
    registration.status = EventRegistrationStatus.CANCELLED
    db.commit()
    return None
