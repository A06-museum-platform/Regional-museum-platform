"""Public exhibitions (frontend/src/api/exhibitions.js).

GET /api/exhibitions?q=&gallery=&page=&page_size=  -> { items, total, page, page_size }
    published exhibitions that haven't closed, current first
GET /api/exhibitions/{slug} -> the exhibition with its published objects, or 404
"""

from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.exhibition import ExhibitionDetailOut, ExhibitionListOut
from app.services import exhibition_service

router = APIRouter(prefix="/api/exhibitions", tags=["exhibitions"])


@router.get("", response_model=ExhibitionListOut)
async def list_exhibitions(
    q: Optional[str] = None,
    gallery: Optional[Literal["main_hall", "telegraph", "monster_mine", "encounter_bay"]] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=100),
    db: AsyncSession = Depends(get_session),
):
    items, total = await exhibition_service.list_public(
        db, q=q, gallery=gallery, page=page, page_size=page_size
    )
    return ExhibitionListOut(items=items, total=total, page=page, page_size=page_size)


@router.get("/{slug}", response_model=ExhibitionDetailOut)
async def get_exhibition(slug: str, db: AsyncSession = Depends(get_session)):
    return await exhibition_service.get_public(db, slug)
