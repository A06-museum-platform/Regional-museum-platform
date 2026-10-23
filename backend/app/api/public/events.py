"""Events for visitors (docs/api-contract.md sections 3-4, in the shape
frontend/src/api/events.js uses).

GET  /api/events?q=&gallery=&audience=&from=&to=&page=&page_size=
         -> { items, total, page, page_size, size }   drafts never listed
         (`size` and `tag` from the contract are accepted too)
GET  /api/events/{slug or id}            -> one event, or 404
POST /api/events/{slug or id}/registrations  (signed in; any role)
         body { contact_name, contact_email, party_size }
         -> 201 registration; 409 EVENT_FULL / ALREADY_REGISTERED / REGISTRATION_CLOSED
GET  /api/event-registrations/me          -> the caller's registrations
POST /api/event-registrations/{reference}/cancel -> cancel an upcoming one
"""

from datetime import datetime
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import STAFF_ROLES, get_current_user
from app.db.session import get_session
from app.schemas.event import EventListOut, EventOut, RegistrationIn, RegistrationListOut, RegistrationOut
from app.schemas.user import UserOut
from app.services import activity_service, event_service

router = APIRouter(prefix="/api", tags=["events"])


@router.get("/events", response_model=EventListOut)
async def search_events(
    q: Optional[str] = None,
    tag: Optional[str] = None,
    gallery: Optional[Literal["main_hall", "telegraph", "monster_mine", "encounter_bay"]] = None,
    audience: Optional[Literal["families", "adults"]] = None,
    date_from: Optional[datetime] = Query(None, alias="from"),
    date_to: Optional[datetime] = Query(None, alias="to"),
    page: int = Query(1, ge=1),
    page_size: Optional[int] = Query(None, ge=1, le=100),
    size: Optional[int] = Query(None, ge=1, le=100),
    db: AsyncSession = Depends(get_session),
):
    per_page = page_size or size or 10
    items, total = await event_service.search(
        db, q=q, tag=tag, gallery=gallery, audience=audience, date_from=date_from, date_to=date_to,
        page=page, size=per_page,
    )
    return EventListOut(items=items, total=total, page=page, page_size=per_page, size=per_page)


@router.get("/events/{key}", response_model=EventOut)
async def get_event(key: str, db: AsyncSession = Depends(get_session)):
    return await event_service.get_event(db, key)


@router.post("/events/{key}/registrations", response_model=RegistrationOut, status_code=201)
async def register_for_event(
    key: str,
    body: RegistrationIn,
    user: UserOut = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    registration = await event_service.register(db, key, user.id, body)
    await activity_service.record(
        db, user, "event.registered",
        f"{registration.event_title} — {registration.party_size} "
        f"{'person' if registration.party_size == 1 else 'people'}",
        reference=registration.reference,
    )
    return registration


@router.get("/event-registrations/me", response_model=RegistrationListOut)
async def my_registrations(
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=100),
    user: UserOut = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    items, total = await event_service.my_registrations(db, user.id, page, size)
    return RegistrationListOut(items=items, total=total, page=page, size=size)


@router.post("/event-registrations/{reference}/cancel", response_model=RegistrationOut)
async def cancel_registration(
    reference: str,
    user: UserOut = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    registration = await event_service.cancel_registration(
        db, reference, user.id, sees_all=user.role in STAFF_ROLES
    )
    await activity_service.record(db, user, "event.registration_cancelled", registration.event_title,
                                  reference=registration.reference)
    return registration
