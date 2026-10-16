"""Public collection search and detail.

Built to the shape frontend/src/api/collections.js already requests
(/collection-items, page_size, slug lookup) rather than docs/api-contract.md
section 2 (/collections, size, numeric id), so the pages work unchanged.

collection_item only has item_id, exhibition_id, item_name, description,
historical_period and is_highlight. The front end's other fields are filled
like this rather than invented:
  slug      -> "<slugified item_name>-<item_id>"; lookup uses the trailing id
               and 404s unless the whole slug matches
  category  -> "uncategorised" for every item (the item page calls
               categoryLabel(category).toLowerCase(), so it can't be null);
               a category filter matches only that value
  gallery, accession_number, materials, year_from/to, is_family_friendly
            -> null. A gallery or family_friendly filter therefore matches
               nothing; year filters keep items of unknown date, as the
               front end's mock filter does.
  image_url -> the item's primary media_asset (lowest sort_order otherwise)
  status    -> "published": the table has no draft state, so every row is
               public.
"""

import re
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApiError
from app.schemas.collection_item import (
    CollectionItemDetailOut,
    CollectionItemOut,
    ExhibitionRef,
)

UNCATEGORISED = "uncategorised"

_SELECT = (
    "SELECT c.item_id, c.exhibition_id, c.item_name, c.description, "
    " c.historical_period, c.is_highlight, "
    " (SELECT ma.url FROM media_asset ma "
    "   WHERE ma.collection_item_id = c.item_id AND ma.media_type = 'image' "
    "   ORDER BY ma.is_primary DESC, ma.sort_order, ma.media_id LIMIT 1) AS image_url, "
    " e.title AS exhibition_title "
    "FROM collection_item c "
    "LEFT JOIN exhibition e ON e.exhibition_id = c.exhibition_id "
)


def slugify(value: str, record_id: int) -> str:
    base = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")[:60].strip("-")
    return f"{base}-{record_id}" if base else str(record_id)


def _to_item(row) -> CollectionItemOut:
    return CollectionItemOut(
        id=row.item_id,
        slug=slugify(row.item_name, row.item_id),
        title=row.item_name,
        description=row.description,
        period_text=row.historical_period,
        is_highlight=row.is_highlight,
        image_url=row.image_url,
        exhibition_id=row.exhibition_id,
        status="published",
        category=UNCATEGORISED,
        gallery=None,
        accession_number=None,
        materials=None,
        year_from=None,
        year_to=None,
        is_family_friendly=None,
    )


async def search(
    db: AsyncSession,
    *,
    q: Optional[str],
    gallery: Optional[str],
    category: Optional[str],
    family_friendly: bool,
    page: int,
    page_size: int,
) -> tuple[list[CollectionItemOut], int]:
    # Filters on data the table doesn't hold can't match anything.
    if gallery or family_friendly or (category and category != UNCATEGORISED):
        return [], 0

    where, params = "", {}
    if q and q.strip():
        where = (
            "WHERE c.item_name ILIKE :q OR c.description ILIKE :q "
            "OR c.historical_period ILIKE :q "
        )
        # Escape LIKE wildcards so a search for "100%" is literal.
        needle = re.sub(r"([\\%_])", r"\\\1", q.strip())
        params["q"] = f"%{needle}%"

    total = (
        await db.execute(text(f"SELECT COUNT(*) FROM collection_item c {where}"), params)
    ).scalar_one()
    rows = (
        await db.execute(
            text(_SELECT + where + "ORDER BY c.item_id LIMIT :limit OFFSET :offset"),
            {**params, "limit": page_size, "offset": (page - 1) * page_size},
        )
    ).all()
    return [_to_item(row) for row in rows], total


async def get_by_slug(db: AsyncSession, slug: str) -> CollectionItemDetailOut:
    match = re.search(r"(?:^|-)(\d+)$", slug)
    row = None
    if match:
        row = (
            await db.execute(text(_SELECT + "WHERE c.item_id = :item_id"),
                             {"item_id": int(match.group(1))})
        ).first()
    if row is None or slugify(row.item_name, row.item_id) != slug:
        raise ApiError(404, "That collection item does not exist.", "NOT_FOUND")

    exhibition = None
    if row.exhibition_id is not None:
        exhibition = ExhibitionRef(
            id=row.exhibition_id,
            title=row.exhibition_title,
            slug=slugify(row.exhibition_title, row.exhibition_id),
        )
    return CollectionItemDetailOut(**_to_item(row).model_dump(), exhibition=exhibition)
