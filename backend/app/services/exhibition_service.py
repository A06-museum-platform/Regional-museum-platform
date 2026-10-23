"""Exhibitions: public list and detail, staff create / edit / delete.

Visitors see published exhibitions that haven't closed (current first, then
upcoming). Staff see everything. `phase` is computed from the dates in the
museum's time zone, and the old `status` column (Upcoming / Current /
Closed, migration 001) is kept in step on every staff save.
"""

from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApiError
from app.schemas.exhibition import (
    ExhibitionDetailOut,
    ExhibitionIn,
    ExhibitionOut,
    ExhibitionPatch,
)
from app.services import collection_service
from app.services.content_common import GALLERY_LABELS, like_pattern, primary_image_sql, unique_slug
from app.services.event_service import MUSEUM_TIMEZONE

_TODAY = f"(now() AT TIME ZONE '{MUSEUM_TIMEZONE}')::date"

_PHASE = (
    f"CASE WHEN x.start_date > {_TODAY} THEN 'upcoming' "
    f"     WHEN x.end_date IS NOT NULL AND x.end_date < {_TODAY} THEN 'closed' "
    "      ELSE 'current' END"
)

_SELECT = (
    "SELECT x.exhibition_id, x.slug, x.title, x.summary, x.description, x.gallery, "
    " x.start_date, x.end_date, x.age_min, x.age_max, x.publish_status, "
    f" {_PHASE} AS phase, "
    f" {primary_image_sql('exhibition_id', 'x.exhibition_id')} AS hero_image_url, "
    " (SELECT COUNT(*) FROM collection_item c WHERE c.exhibition_id = x.exhibition_id "
    "   AND (:staff OR c.publish_status = 'published')) AS item_count "
    "FROM exhibition x "
)


def _to_out(row) -> ExhibitionOut:
    return ExhibitionOut(
        id=row.exhibition_id,
        slug=row.slug,
        title=row.title,
        summary=row.summary,
        body=row.description,
        gallery=row.gallery,
        start_date=row.start_date,
        end_date=row.end_date,
        age_min=row.age_min,
        age_max=row.age_max,
        hero_image_url=row.hero_image_url,
        status=row.publish_status,
        phase=row.phase,
        item_count=row.item_count,
    )


def _filters(q, gallery, status, *, public: bool) -> tuple[str, dict]:
    clauses, params = [], {}
    if public:
        clauses.append("x.publish_status = 'published'")
        clauses.append(f"(x.end_date IS NULL OR x.end_date >= {_TODAY})")
    if q and q.strip():
        clauses.append("(x.title ILIKE :q OR x.summary ILIKE :q OR x.description ILIKE :q)")
        params["q"] = like_pattern(q)
    if gallery:
        clauses.append("x.gallery = :gallery")
        params["gallery"] = gallery
    if status:
        clauses.append("x.publish_status = :status")
        params["status"] = status
    return (f"WHERE {' AND '.join(clauses)} " if clauses else ""), params


async def list_public(
    db: AsyncSession, *, q: Optional[str], gallery: Optional[str], page: int, page_size: int
) -> tuple[list[ExhibitionOut], int]:
    where, params = _filters(q, gallery, None, public=True)
    total = (await db.execute(text(f"SELECT COUNT(*) FROM exhibition x {where}"), params)).scalar_one()
    rows = (
        await db.execute(
            text(_SELECT + where + f"ORDER BY (x.start_date > {_TODAY}), x.start_date, x.exhibition_id "
                 "LIMIT :limit OFFSET :offset"),
            {**params, "staff": False, "limit": page_size, "offset": (page - 1) * page_size},
        )
    ).all()
    return [_to_out(r) for r in rows], total


async def get_public(db: AsyncSession, slug: str) -> ExhibitionDetailOut:
    row = (
        await db.execute(
            text(_SELECT + "WHERE x.slug = :slug AND x.publish_status = 'published'"),
            {"slug": slug, "staff": False},
        )
    ).first()
    if row is None:
        raise ApiError(404, "That exhibition does not exist.", "NOT_FOUND")
    items = await collection_service.items_for_exhibition(db, row.exhibition_id)
    return ExhibitionDetailOut(**_to_out(row).model_dump(), items=items)


# ---------------------------------------------------------------------------
# Staff
# ---------------------------------------------------------------------------

async def staff_list(db: AsyncSession, *, q=None, gallery=None, status=None):
    where, params = _filters(q, gallery, status, public=False)
    rows = (
        await db.execute(text(_SELECT + where + "ORDER BY x.start_date DESC, x.exhibition_id DESC"),
                         {**params, "staff": True})
    ).all()
    return [_to_out(r) for r in rows], len(rows)


async def _staff_get(db: AsyncSession, exhibition_id: int) -> ExhibitionOut:
    row = (
        await db.execute(text(_SELECT + "WHERE x.exhibition_id = :id"),
                         {"id": exhibition_id, "staff": True})
    ).first()
    if row is None:
        raise ApiError(404, "That exhibition no longer exists.", "NOT_FOUND")
    return _to_out(row)


def _legacy_status(start, end, today) -> str:
    if start > today:
        return "Upcoming"
    if end is not None and end < today:
        return "Closed"
    return "Current"


async def _today(db: AsyncSession):
    return (await db.execute(text(f"SELECT {_TODAY}"))).scalar_one()


async def create(db: AsyncSession, body: ExhibitionIn) -> ExhibitionOut:
    today = await _today(db)
    start = body.start_date or today
    if body.end_date and body.end_date < start:
        raise ApiError(400, "The end date can't be before the start date.", "VALIDATION_ERROR")
    slug = await unique_slug(db, "exhibition", "exhibition_id", body.title)
    new_id = (
        await db.execute(
            text("INSERT INTO exhibition (title, slug, summary, description, gallery, start_date, "
                 "end_date, location, status, age_min, age_max, publish_status) VALUES (:title, :slug, "
                 ":summary, :body, :gallery, :start, :end, :location, :legacy, :age_min, :age_max, "
                 ":status) RETURNING exhibition_id"),
            {"title": body.title, "slug": slug, "summary": body.summary or None,
             "body": body.body or None, "gallery": body.gallery, "start": start, "end": body.end_date,
             "location": GALLERY_LABELS.get(body.gallery), "legacy": _legacy_status(start, body.end_date, today),
             "age_min": body.age_min, "age_max": body.age_max, "status": body.status},
        )
    ).scalar_one()
    await db.commit()
    return await _staff_get(db, new_id)


async def update(db: AsyncSession, exhibition_id: int, body: ExhibitionPatch) -> ExhibitionOut:
    current = await _staff_get(db, exhibition_id)
    changes = body.model_dump(exclude_unset=True)
    if not changes:
        return current
    merged = current.model_dump() | changes
    if merged["start_date"] is None:
        raise ApiError(400, "An exhibition needs a start date.", "VALIDATION_ERROR")
    if merged["end_date"] and merged["end_date"] < merged["start_date"]:
        raise ApiError(400, "The end date can't be before the start date.", "VALIDATION_ERROR")
    if merged["age_min"] is not None and merged["age_max"] is not None \
            and merged["age_max"] < merged["age_min"]:
        raise ApiError(400, "The maximum age can't be below the minimum age.", "VALIDATION_ERROR")
    if merged["status"] == "published":
        missing = [n for n in ("summary", "gallery") if not merged.get(n)]
        if missing:
            raise ApiError(400, f"To publish, fill in: {', '.join(missing)}", "VALIDATION_ERROR")

    columns = {"title": "title", "summary": "summary", "body": "description", "gallery": "gallery",
               "start_date": "start_date", "end_date": "end_date", "age_min": "age_min",
               "age_max": "age_max", "status": "publish_status"}
    sets = {columns[k]: (v if v != "" else None) for k, v in changes.items()}
    if "title" in changes and changes["title"] != current.title:
        sets["slug"] = await unique_slug(db, "exhibition", "exhibition_id", changes["title"], exhibition_id)
    if "gallery" in changes:
        sets["location"] = GALLERY_LABELS.get(changes["gallery"])
    sets["status"] = _legacy_status(merged["start_date"], merged["end_date"], await _today(db))
    assignments = ", ".join(f"{c} = :{c}" for c in sets)
    await db.execute(
        text(f"UPDATE exhibition SET {assignments}, updated_at = now() WHERE exhibition_id = :id"),
        {**sets, "id": exhibition_id},
    )
    await db.commit()
    return await _staff_get(db, exhibition_id)


async def delete(db: AsyncSession, exhibition_id: int) -> str:
    current = await _staff_get(db, exhibition_id)
    if current.item_count > 0:
        noun = "object is" if current.item_count == 1 else "objects are"
        raise ApiError(
            409,
            f"{current.item_count} collection {noun} still attached. Move them to another "
            "exhibition first, or unpublish this one instead.",
            "EXHIBITION_HAS_ITEMS",
        )
    await db.execute(text("DELETE FROM exhibition WHERE exhibition_id = :id"), {"id": exhibition_id})
    await db.commit()
    return current.title
