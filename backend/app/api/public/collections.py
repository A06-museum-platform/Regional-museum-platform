"""Public collection endpoints, in the shape frontend/src/api/collections.js
requests (see app/services/collection_service.py).

GET /api/collection-items?q=&gallery=&category=&year_from=&year_to=
                         &family_friendly=&highlight=&page=&page_size=
    -> { items, total, page, page_size }   published items only
GET /api/collection-items/{slug} -> one published item with its exhibition, or 404
"""

from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.collection_item import CollectionItemDetailOut, CollectionItemListOut
from app.services.collection_service import get_by_slug, search

router = APIRouter(prefix="/api/collection-items", tags=["collections"])


@router.get("", response_model=CollectionItemListOut)
async def search_collection_items(
    q: Optional[str] = None,
    gallery: Optional[Literal["main_hall", "telegraph", "monster_mine", "encounter_bay"]] = None,
    category: Optional[Literal["mineral", "instrument", "document", "photograph", "machinery"]] = None,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    family_friendly: bool = False,
    highlight: bool = False,
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=100),
    db: AsyncSession = Depends(get_session),
):
    items, total = await search(
        db,
        q=q,
        gallery=gallery,
        category=category,
        year_from=year_from,
        year_to=year_to,
        family_friendly=family_friendly,
        highlight=highlight,
        page=page,
        page_size=page_size,
    )
    return CollectionItemListOut(items=items, total=total, page=page, page_size=page_size)


@router.get("/{slug}", response_model=CollectionItemDetailOut)
async def get_collection_item(slug: str, db: AsyncSession = Depends(get_session)):
    return await get_by_slug(db, slug)
