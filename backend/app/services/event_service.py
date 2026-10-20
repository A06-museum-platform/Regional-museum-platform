"""Public event search and detail (docs/api-contract.md section 3).

event only has event_id, title, description, event_date, start_time,
end_time, location, capacity and status. The contract's fields are filled
like this:
  display_name  -> title
  event_time    -> event_date + start_time, stored as museum-local time with
                   no zone, so Postgres converts it from Australia/Adelaide
                   to UTC
  thumbnail_url -> the event's primary media_asset (lowest sort_order otherwise)
  tag           -> there is no tag data for events, so a tag filter matches
                   nothing, like collection_service's gallery filter.
Every status (Scheduled, Cancelled, Completed) is listed: there is no draft
state, so every row is public.
"""

import re
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApiError
from app.schemas.event import EventOut

MUSEUM_TIMEZONE = "Australia/Adelaide"

_SELECT = (
    "SELECT ev.event_id, ev.title, ev.description, ev.location, "
    f" (ev.event_date + ev.start_time) AT TIME ZONE '{MUSEUM_TIMEZONE}' AS event_time, "
    " (SELECT ma.url FROM media_asset ma "
    "   WHERE ma.event_id = ev.event_id AND ma.media_type = 'image' "
    "   ORDER BY ma.is_primary DESC, ma.sort_order, ma.media_id LIMIT 1) AS thumbnail_url "
    "FROM event ev "
)


def _to_event(row) -> EventOut:
    return EventOut(
        id=row.event_id,
        display_name=row.title,
        event_time=row.event_time,
        description=row.description,
        location=row.location,
        thumbnail_url=row.thumbnail_url,
    )


async def search(
    db: AsyncSession,
    *,
    q: Optional[str],
    tag: Optional[str],
    page: int,
    size: int,
) -> tuple[list[EventOut], int]:
    # Events carry no tags yet, so a tag filter can't match anything.
    if tag:
        return [], 0

    where, params = "", {}
    if q and q.strip():
        where = (
            "WHERE ev.title ILIKE :q OR ev.description ILIKE :q "
            "OR ev.location ILIKE :q "
        )
        # Escape LIKE wildcards so a search for "100%" is literal.
        needle = re.sub(r"([\\%_])", r"\\\1", q.strip())
        params["q"] = f"%{needle}%"

    total = (
        await db.execute(text(f"SELECT COUNT(*) FROM event ev {where}"), params)
    ).scalar_one()
    rows = (
        await db.execute(
            text(_SELECT + where
                 + "ORDER BY ev.event_date, ev.start_time, ev.event_id "
                 "LIMIT :limit OFFSET :offset"),
            {**params, "limit": size, "offset": (page - 1) * size},
        )
    ).all()
    return [_to_event(row) for row in rows], total


async def get_by_id(db: AsyncSession, event_id: int) -> EventOut:
    row = (
        await db.execute(text(_SELECT + "WHERE ev.event_id = :event_id"),
                         {"event_id": event_id})
    ).first()
    if row is None:
        raise ApiError(404, "Event not found", "NOT_FOUND")
    return _to_event(row)
