"""Staff collection management (role-permission matrix: "Create / edit
collection items and exhibitions" -- Staff and Admin).

GET    /api/staff/collection-items?q=&status=&gallery=&category=  -> { items, total }  (drafts included)
POST   /api/staff/collection-items         -> 201 the new item
PATCH  /api/staff/collection-items/{id}    -> the updated item (publishing is a PATCH of status)
DELETE /api/staff/collection-items/{id}    -> 204

Authorisation is the router-level dependency, so no handler can forget it.
"""

from typing import Literal, Optional

from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_staff
from app.db.session import get_session
from app.schemas.collection_item import (
    CollectionItemDetailOut,
    CollectionItemIn,
    CollectionItemPatch,
    StaffCollectionItemListOut,
)
from app.services import activity_service, collection_service

router = APIRouter(
    prefix="/api/staff/collection-items",
    tags=["staff-collections"],
    dependencies=[Depends(require_staff)],
)


@router.get("", response_model=StaffCollectionItemListOut)
async def list_items(
    q: Optional[str] = None,
    status: Optional[Literal["draft", "published"]] = None,
    gallery: Optional[Literal["main_hall", "telegraph", "monster_mine", "encounter_bay"]] = None,
    category: Optional[Literal["mineral", "instrument", "document", "photograph", "machinery"]] = None,
    db: AsyncSession = Depends(get_session),
):
    items, total = await collection_service.staff_list(
        db, q=q, status=status, gallery=gallery, category=category
    )
    return StaffCollectionItemListOut(items=items, total=total)


@router.post("", response_model=CollectionItemDetailOut, status_code=201)
async def create_item(
    body: CollectionItemIn,
    actor: dict = Depends(require_staff),
    db: AsyncSession = Depends(get_session),
):
    item = await collection_service.create(db, body)
    await activity_service.record(db, actor, "collection.created", item.title)
    return item


@router.patch("/{item_id}", response_model=CollectionItemDetailOut)
async def update_item(
    item_id: int,
    body: CollectionItemPatch,
    actor: dict = Depends(require_staff),
    db: AsyncSession = Depends(get_session),
):
    item = await collection_service.update(db, item_id, body)
    action = "collection.published" if body.status == "published" else "collection.updated"
    await activity_service.record(db, actor, action, item.title)
    return item


@router.delete("/{item_id}", status_code=204, response_class=Response)
async def delete_item(
    item_id: int,
    actor: dict = Depends(require_staff),
    db: AsyncSession = Depends(get_session),
):
    await collection_service.delete(db, item_id)
    await activity_service.record(db, actor, "collection.deleted", f"object #{item_id}")
    return Response(status_code=204)
