"""Public collection endpoints, in the shape frontend/src/api/collections.js
requests (see app/services/collection_service.py for how this differs from
docs/api-contract.md section 2).

GET /api/collection-items?q=&gallery=&category=&year_from=&year_to=
                         &family_friendly=&page=&page_size=
    -> { items, total, page, page_size }
GET /api/collection-items/{slug} -> one item with its exhibition, or 404
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.collection_item import CollectionItemDetailOut, CollectionItemListOut
from app.services.collection_service import get_by_slug, search

router = APIRouter(prefix="/api/collection-items", tags=["collections"])


@router.get("", response_model=CollectionItemListOut)
async def search_collection_items(
    q: Optional[str] = None,
    gallery: Optional[str] = None,
    category: Optional[str] = None,
    # Accepted for the front end's filters; no item has a known year yet,
    # so they don't narrow anything (see collection_service).
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    family_friendly: bool = False,
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=100),
    db: AsyncSession = Depends(get_session),
):
    items, total = await search(
        db,
        q=q,
        gallery=gallery,
        category=category,
        family_friendly=family_friendly,
        page=page,
        page_size=page_size,
    )
    return CollectionItemListOut(items=items, total=total, page=page, page_size=page_size)


@router.get("/{slug}", response_model=CollectionItemDetailOut)
async def get_collection_item(slug: str, db: AsyncSession = Depends(get_session)):
    return await get_by_slug(db, slug)
