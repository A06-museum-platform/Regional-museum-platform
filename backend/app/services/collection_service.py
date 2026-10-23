"""Collection items: public search and detail, and staff create / edit /
delete (role-permission matrix: "Create / edit collection items").

Built to the shape frontend/src/api/collections.js requests
(/collection-items, page_size, slug lookup) rather than docs/api-contract.md
section 2; the columns come from migration 009.

Visitors only ever see published items. Staff see drafts too. The item's
image is its primary media_asset (staff upload it on the Media page).
"""

from typing import Optional

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApiError
from app.schemas.collection_item import (
    CollectionItemDetailOut,
    CollectionItemIn,
    CollectionItemOut,
    CollectionItemPatch,
    ExhibitionRef,
)
from app.services.content_common import like_pattern, primary_image_sql, unique_slug

_SELECT = (
    "SELECT c.item_id, c.slug, c.item_name, c.accession_number, c.description, c.category, "
    " c.gallery, c.historical_period, c.year_from, c.year_to, c.materials, c.exhibition_id, "
    " c.is_family_friendly, c.is_highlight, c.publish_status, "
    f" {primary_image_sql('collection_item_id', 'c.item_id')} AS image_url, "
    " e.title AS exhibition_title, e.slug AS exhibition_slug "
    "FROM collection_item c "
    "LEFT JOIN exhibition e ON e.exhibition_id = c.exhibition_id "
)

_NOT_FOUND = "That collection item does not exist."


def _to_item(row) -> CollectionItemOut:
    return CollectionItemOut(
        id=row.item_id,
        slug=row.slug,
        title=row.item_name,
        accession_number=row.accession_number,
        description=row.description,
        category=row.category,
        gallery=row.gallery,
        period_text=row.historical_period,
        year_from=row.year_from,
        year_to=row.year_to,
        materials=row.materials,
        image_url=row.image_url,
        exhibition_id=row.exhibition_id,
        is_family_friendly=row.is_family_friendly,
        is_highlight=row.is_highlight,
        status=row.publish_status,
    )


def _to_detail(row) -> CollectionItemDetailOut:
    exhibition = None
    if row.exhibition_id is not None:
        exhibition = ExhibitionRef(
            id=row.exhibition_id, title=row.exhibition_title, slug=row.exhibition_slug
        )
    return CollectionItemDetailOut(**_to_item(row).model_dump(), exhibition=exhibition)


def _filters(
    *,
    q: Optional[str] = None,
    gallery: Optional[str] = None,
    category: Optional[str] = None,
    year_from: Optional[int] = None,
    year_to: Optional[int] = None,
    family_friendly: bool = False,
    status: Optional[str] = None,
    exhibition_id: Optional[int] = None,
    highlight: bool = False,
) -> tuple[str, dict]:
    clauses, params = [], {}
    if q and q.strip():
        clauses.append("(c.item_name ILIKE :q OR c.description ILIKE :q "
                       "OR c.materials ILIKE :q OR c.accession_number ILIKE :q "
                       "OR c.historical_period ILIKE :q)")
        params["q"] = like_pattern(q)
    if gallery:
        clauses.append("c.gallery = :gallery")
        params["gallery"] = gallery
    if category:
        clauses.append("c.category = :category")
        params["category"] = category
    # Items of unknown date stay in a year-filtered list, as the mock did.
    if year_from is not None:
        clauses.append("(c.year_to IS NULL OR c.year_to >= :year_from)")
        params["year_from"] = year_from
    if year_to is not None:
        clauses.append("(c.year_from IS NULL OR c.year_from <= :year_to)")
        params["year_to"] = year_to
    if family_friendly:
        clauses.append("c.is_family_friendly")
    if status:
        clauses.append("c.publish_status = :status")
        params["status"] = status
    if exhibition_id is not None:
        clauses.append("c.exhibition_id = :exhibition_id")
        params["exhibition_id"] = exhibition_id
    if highlight:
        clauses.append("c.is_highlight")
    return (f"WHERE {' AND '.join(clauses)} " if clauses else ""), params


async def search(
    db: AsyncSession,
    *,
    page: int,
    page_size: int,
    **filters,
) -> tuple[list[CollectionItemOut], int]:
    """Published items matching the filters, highlights first."""
    where, params = _filters(status="published", **filters)
    total = (
        await db.execute(text(f"SELECT COUNT(*) FROM collection_item c {where}"), params)
    ).scalar_one()
    rows = (
        await db.execute(
            text(_SELECT + where
                 + "ORDER BY c.is_highlight DESC, c.item_name, c.item_id LIMIT :limit OFFSET :offset"),
            {**params, "limit": page_size, "offset": (page - 1) * page_size},
        )
    ).all()
    return [_to_item(row) for row in rows], total


async def get_by_slug(db: AsyncSession, slug: str) -> CollectionItemDetailOut:
    row = (
        await db.execute(text(_SELECT + "WHERE c.slug = :slug AND c.publish_status = 'published'"),
                         {"slug": slug})
    ).first()
    if row is None:
        raise ApiError(404, _NOT_FOUND, "NOT_FOUND")
    return _to_detail(row)


async def items_for_exhibition(db: AsyncSession, exhibition_id: int) -> list[CollectionItemOut]:
    rows = (
        await db.execute(
            text(_SELECT + "WHERE c.exhibition_id = :id AND c.publish_status = 'published' "
                 "ORDER BY c.is_highlight DESC, c.item_name"),
            {"id": exhibition_id},
        )
    ).all()
    return [_to_item(row) for row in rows]


# ---------------------------------------------------------------------------
# Staff
# ---------------------------------------------------------------------------

async def staff_list(db: AsyncSession, **filters) -> tuple[list[CollectionItemDetailOut], int]:
    where, params = _filters(**filters)
    rows = (
        await db.execute(text(_SELECT + where + "ORDER BY c.updated_at DESC, c.item_id DESC"), params)
    ).all()
    return [_to_detail(row) for row in rows], len(rows)


async def _staff_get(db: AsyncSession, item_id: int) -> CollectionItemDetailOut:
    row = (await db.execute(text(_SELECT + "WHERE c.item_id = :id"), {"id": item_id})).first()
    if row is None:
        raise ApiError(404, "That object no longer exists.", "NOT_FOUND")
    return _to_detail(row)


async def _check_exhibition(db: AsyncSession, exhibition_id: Optional[int]) -> None:
    if exhibition_id is None:
        return
    found = (
        await db.execute(text("SELECT 1 FROM exhibition WHERE exhibition_id = :id"),
                         {"id": exhibition_id})
    ).first()
    if found is None:
        raise ApiError(400, "That exhibition does not exist.", "VALIDATION_ERROR")


async def _accession_clash(db: AsyncSession, accession: Optional[str], own_id: Optional[int]):
    if not accession:
        return
    clash = (
        await db.execute(
            text("SELECT item_name FROM collection_item WHERE lower(accession_number) = lower(:a) "
                 "AND (CAST(:own_id AS INTEGER) IS NULL OR item_id <> :own_id)"),
            {"a": accession, "own_id": own_id},
        )
    ).first()
    if clash is not None:
        raise ApiError(409, f"Accession number {accession} is already used by "
                            f"“{clash.item_name}”.", "ACCESSION_TAKEN")


# Request field -> column. Empty strings from the form are stored as NULL.
_COLUMNS = {
    "title": "item_name",
    "accession_number": "accession_number",
    "description": "description",
    "category": "category",
    "gallery": "gallery",
    "period_text": "historical_period",
    "year_from": "year_from",
    "year_to": "year_to",
    "materials": "materials",
    "exhibition_id": "exhibition_id",
    "is_family_friendly": "is_family_friendly",
    "is_highlight": "is_highlight",
    "status": "publish_status",
}


def _clean(values: dict) -> dict:
    return {k: (None if isinstance(v, str) and v == "" else v) for k, v in values.items()}


async def create(db: AsyncSession, body: CollectionItemIn) -> CollectionItemDetailOut:
    values = _clean(body.model_dump())
    await _check_exhibition(db, values["exhibition_id"])
    await _accession_clash(db, values["accession_number"], None)
    values["slug"] = await unique_slug(db, "collection_item", "item_id", values["title"])
    columns = [_COLUMNS[k] for k in _COLUMNS] + ["slug"]
    params = {_COLUMNS[k]: values[k] for k in _COLUMNS} | {"slug": values["slug"]}
    try:
        new_id = (
            await db.execute(
                text(f"INSERT INTO collection_item ({', '.join(columns)}) "
                     f"VALUES ({', '.join(':' + c for c in columns)}) RETURNING item_id"),
                params,
            )
        ).scalar_one()
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ApiError(409, "That accession number or title is already in use.", "CONFLICT")
    return await _staff_get(db, new_id)


async def update(db: AsyncSession, item_id: int, body: CollectionItemPatch) -> CollectionItemDetailOut:
    current = await _staff_get(db, item_id)
    changes = _clean(body.model_dump(exclude_unset=True))
    if not changes:
        return current

    merged = current.model_dump() | changes
    if merged["year_from"] is not None and merged["year_to"] is not None \
            and merged["year_to"] < merged["year_from"]:
        raise ApiError(400, "The end year can't be earlier than the start year.", "VALIDATION_ERROR")
    if merged["status"] == "published":
        missing = [n for n in ("accession_number", "description", "category", "gallery")
                   if not merged.get(n)]
        if missing:
            raise ApiError(400, f"To publish, fill in: {', '.join(missing)}", "VALIDATION_ERROR")
    if "exhibition_id" in changes:
        await _check_exhibition(db, changes["exhibition_id"])
    if changes.get("accession_number"):
        await _accession_clash(db, changes["accession_number"], item_id)

    sets = {_COLUMNS[k]: v for k, v in changes.items() if k in _COLUMNS}
    if "title" in changes and changes["title"] != current.title:
        sets["slug"] = await unique_slug(db, "collection_item", "item_id", changes["title"], item_id)
    assignments = ", ".join(f"{column} = :{column}" for column in sets)
    try:
        await db.execute(
            text(f"UPDATE collection_item SET {assignments}, updated_at = now() WHERE item_id = :id"),
            {**sets, "id": item_id},
        )
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise ApiError(409, "That accession number is already in use.", "ACCESSION_TAKEN")
    return await _staff_get(db, item_id)


async def delete(db: AsyncSession, item_id: int) -> None:
    await _staff_get(db, item_id)
    await db.execute(text("DELETE FROM media_asset WHERE collection_item_id = :id"), {"id": item_id})
    await db.execute(text("DELETE FROM collection_item WHERE item_id = :id"), {"id": item_id})
    await db.commit()
