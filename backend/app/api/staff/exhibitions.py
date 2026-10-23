"""Staff exhibition management (role-permission matrix: "Create / edit
collection items and exhibitions" -- Staff and Admin).

GET    /api/staff/exhibitions?q=&status=&gallery=  -> { items, total }  (drafts included)
POST   /api/staff/exhibitions        -> 201
PATCH  /api/staff/exhibitions/{id}   -> updated exhibition
DELETE /api/staff/exhibitions/{id}   -> 204; 409 EXHIBITION_HAS_ITEMS while objects are attached
"""

from typing import Literal, Optional

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_staff
from app.db.session import get_session
from app.schemas.exhibition import (
    ExhibitionIn,
    ExhibitionOut,
    ExhibitionPatch,
    StaffExhibitionListOut,
)
from app.services import activity_service, exhibition_service

router = APIRouter(
    prefix="/api/staff/exhibitions",
    tags=["staff-exhibitions"],
    dependencies=[Depends(require_staff)],
)


@router.get("", response_model=StaffExhibitionListOut)
async def list_exhibitions(
    q: Optional[str] = None,
    status: Optional[Literal["draft", "published"]] = None,
    gallery: Optional[Literal["main_hall", "telegraph", "monster_mine", "encounter_bay"]] = None,
    db: AsyncSession = Depends(get_session),
):
    items, total = await exhibition_service.staff_list(db, q=q, gallery=gallery, status=status)
    return StaffExhibitionListOut(items=items, total=total)


@router.post("", response_model=ExhibitionOut, status_code=201)
async def create_exhibition(
    body: ExhibitionIn,
    actor: dict = Depends(require_staff),
    db: AsyncSession = Depends(get_session),
):
    exhibition = await exhibition_service.create(db, body)
    await activity_service.record(db, actor, "exhibition.created", exhibition.title)
    return exhibition


@router.patch("/{exhibition_id}", response_model=ExhibitionOut)
async def update_exhibition(
    exhibition_id: int,
    body: ExhibitionPatch,
    actor: dict = Depends(require_staff),
    db: AsyncSession = Depends(get_session),
):
    exhibition = await exhibition_service.update(db, exhibition_id, body)
    action = {"published": "exhibition.published", "draft": "exhibition.unpublished"}.get(
        body.status or "", "exhibition.updated")
    await activity_service.record(db, actor, action, exhibition.title)
    return exhibition


@router.delete("/{exhibition_id}", status_code=204, response_class=Response)
async def delete_exhibition(
    exhibition_id: int,
    actor: dict = Depends(require_staff),
    db: AsyncSession = Depends(get_session),
):
    title = await exhibition_service.delete(db, exhibition_id)
    await activity_service.record(db, actor, "exhibition.deleted", title)
    return Response(status_code=204)
