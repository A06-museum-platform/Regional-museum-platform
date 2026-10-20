"""Public event endpoints (docs/api-contract.md section 3).

GET /api/events?q=&tag=&page=&size= -> { items, total, page, size }
GET /api/events/{id}                -> one event, or 404 NOT_FOUND
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.common import PaginatedResponse
from app.schemas.event import EventOut
from app.services.event_service import get_by_id, search

router = APIRouter(prefix="/api/events", tags=["events"])


@router.get("", response_model=PaginatedResponse[EventOut])
async def search_events(
    q: Optional[str] = None,
    tag: Optional[str] = None,
    page: int = Query(1, ge=1),
    size: int = Query(12, ge=1, le=100),
    db: AsyncSession = Depends(get_session),
):
    items, total = await search(db, q=q, tag=tag, page=page, size=size)
    return PaginatedResponse[EventOut](items=items, total=total, page=page, size=size)


@router.get("/{event_id}", response_model=EventOut)
async def get_event(event_id: int, db: AsyncSession = Depends(get_session)):
    return await get_by_id(db, event_id)
