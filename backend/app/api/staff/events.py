"""Staff event management (role-permission matrix: "Create / edit / delete
events", "Set event capacity", "View all bookings and event registrations";
client requirement 3(iii) "publish event details").

GET    /api/staff/events?q=&status=&gallery=     -> { items, total }  (drafts included)
POST   /api/staff/events                          -> 201
PATCH  /api/staff/events/{id}                     -> updated event; publishing is a PATCH
                                                     of status; capacity can't drop below
                                                     places taken (409)
DELETE /api/staff/events/{id}                     -> 204; 409 while people are registered
GET    /api/staff/events/{id}/registrations       -> who is registered
"""

from typing import Literal, Optional

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_staff
from app.db.session import get_session
from app.schemas.event import EventIn, EventOut, EventPatch, StaffEventListOut, StaffRegistrationOut
from app.services import activity_service, event_service

router = APIRouter(
    prefix="/api/staff/events",
    tags=["staff-events"],
    dependencies=[Depends(require_staff)],
)


@router.get("", response_model=StaffEventListOut)
async def list_events(
    q: Optional[str] = None,
    status: Optional[Literal["draft", "published", "cancelled", "completed"]] = None,
    gallery: Optional[Literal["main_hall", "telegraph", "monster_mine", "encounter_bay"]] = None,
    db: AsyncSession = Depends(get_session),
):
    items, total = await event_service.staff_list(db, q=q, status=status, gallery=gallery)
    return StaffEventListOut(items=items, total=total)


@router.post("", response_model=EventOut, status_code=201)
async def create_event(
    body: EventIn,
    actor: dict = Depends(require_staff),
    db: AsyncSession = Depends(get_session),
):
    event = await event_service.create(db, body)
    action = "event.published" if event.status == "published" else "event.created"
    await activity_service.record(db, actor, action, event.title)
    return event


@router.patch("/{event_id}", response_model=EventOut)
async def update_event(
    event_id: int,
    body: EventPatch,
    actor: dict = Depends(require_staff),
    db: AsyncSession = Depends(get_session),
):
    event = await event_service.update(db, event_id, body)
    action = {"published": "event.published", "draft": "event.unpublished",
              "cancelled": "event.cancelled"}.get(body.status or "", "event.updated")
    await activity_service.record(db, actor, action, event.title)
    return event


@router.delete("/{event_id}", status_code=204, response_class=Response)
async def delete_event(
    event_id: int,
    actor: dict = Depends(require_staff),
    db: AsyncSession = Depends(get_session),
):
    title = await event_service.delete(db, event_id)
    await activity_service.record(db, actor, "event.deleted", title)
    return Response(status_code=204)


@router.get("/{event_id}/registrations", response_model=list[StaffRegistrationOut])
async def event_registrations(event_id: int, db: AsyncSession = Depends(get_session)):
    return await event_service.registrations_for_event(db, event_id)
