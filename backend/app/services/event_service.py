"""Events: public listing and detail, registration, and staff management
(client requirement 3(iii): staff publish event details, visitors search
them; role-permission matrix: "Create / edit / delete events", "Set event
capacity").

Dates and times are stored museum-local (event_date, start_time, end_time,
migration 001) and sent as UTC ISO 8601: Postgres converts with
AT TIME ZONE 'Australia/Adelaide', so daylight saving is handled there.

Status mapping (column -> API): Draft -> draft, Scheduled -> published,
Cancelled -> cancelled, Completed -> completed. Visitors never see drafts.

Places: spots_remaining = capacity - the party sizes of 'Registered'
registrations. Registering locks the event row, so two people can't both
take the last places.
"""

import secrets
from datetime import datetime
from decimal import Decimal
from typing import Optional
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApiError
from app.schemas.event import (
    EventIn,
    EventOut,
    EventPatch,
    RegistrationIn,
    RegistrationOut,
    StaffRegistrationOut,
)

MUSEUM_TIMEZONE = "Australia/Adelaide"
_TZ = ZoneInfo(MUSEUM_TIMEZONE)

STATUS_TO_API = {"Draft": "draft", "Scheduled": "published", "Cancelled": "cancelled",
                 "Completed": "completed"}
STATUS_TO_DB = {v: k for k, v in STATUS_TO_API.items()}

async def _tagged(db: AsyncSession, items):
    from app.services.recommendation_service import attach_tags
    return await attach_tags(db, "event", items)


_STARTS = f"((ev.event_date + ev.start_time) AT TIME ZONE '{MUSEUM_TIMEZONE}')"
_ENDS = f"((ev.event_date + ev.end_time) AT TIME ZONE '{MUSEUM_TIMEZONE}')"
_TAKEN = ("(SELECT COALESCE(SUM(r.party_size), 0) FROM event_registration r "
          " WHERE r.event_id = ev.event_id AND r.status = 'Registered')")

_SELECT = (
    "SELECT ev.event_id, ev.slug, ev.title, ev.description, ev.gallery, ev.location, "
    f" {_STARTS} AS starts_at, {_ENDS} AS ends_at, ev.capacity, ev.price, ev.member_price, "
    f" ev.age_min, ev.age_max, ev.status, {_TAKEN} AS taken, ({_ENDS} < now()) AS is_past, "
    " (SELECT ma.url FROM media_asset ma "
    "   WHERE ma.event_id = ev.event_id AND ma.media_type = 'image' "
    "   ORDER BY ma.is_primary DESC, ma.sort_order, ma.media_id LIMIT 1) AS image_url "
    "FROM event ev "
)


def _cents(value) -> int:
    return int((Decimal(str(value)) * 100).to_integral_value())


def _to_event(row) -> EventOut:
    remaining = max(0, row.capacity - row.taken)
    status = STATUS_TO_API.get(row.status, row.status.lower())
    if status == "published" and row.is_past:
        status = "completed"
    return EventOut(
        id=row.event_id,
        slug=row.slug,
        title=row.title,
        description=row.description,
        gallery=row.gallery,
        starts_at=row.starts_at,
        ends_at=row.ends_at,
        capacity=row.capacity,
        spots_remaining=remaining,
        is_sold_out=remaining == 0,
        is_past=row.is_past,
        price_cents=_cents(row.price),
        member_price_cents=_cents(row.member_price),
        age_min=row.age_min,
        age_max=row.age_max,
        status=status,
        image_url=row.image_url,
        display_name=row.title,
        event_time=row.starts_at,
        location=row.location,
        thumbnail_url=row.image_url,
    )


def _filters(*, q=None, gallery=None, audience=None, date_from=None, date_to=None, status=None,
             public: bool) -> tuple[str, dict]:
    clauses, params = [], {}
    if public:
        clauses.append("ev.status IN ('Scheduled', 'Cancelled', 'Completed')")
    if q and q.strip():
        from app.services.content_common import like_pattern
        clauses.append("(ev.title ILIKE :q OR ev.description ILIKE :q OR ev.location ILIKE :q)")
        params["q"] = like_pattern(q)
    if gallery:
        clauses.append("ev.gallery = :gallery")
        params["gallery"] = gallery
    if audience == "families":
        # Something a 10 to 14 year old can attend (the museum's main audience).
        clauses.append("COALESCE(ev.age_min, 0) <= 14 AND COALESCE(ev.age_max, 99) >= 10")
    elif audience == "adults":
        clauses.append("COALESCE(ev.age_min, 0) >= 16")
    if date_from is not None:
        clauses.append(f"{_ENDS} >= :date_from")
        params["date_from"] = date_from
    if date_to is not None:
        clauses.append(f"{_STARTS} <= :date_to")
        params["date_to"] = date_to
    if status:
        clauses.append("ev.status = :status")
        params["status"] = STATUS_TO_DB[status]
    return (f"WHERE {' AND '.join(clauses)} " if clauses else ""), params


async def search(
    db: AsyncSession,
    *,
    q: Optional[str] = None,
    tag: Optional[str] = None,
    gallery: Optional[str] = None,
    audience: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    page: int = 1,
    size: int = 10,
) -> tuple[list[EventOut], int]:
    """Visible events, soonest first. `tag` (contract section 3) matches a
    gallery key, the only grouping events carry."""
    where, params = _filters(q=q, gallery=gallery or tag, audience=audience, date_from=date_from,
                             date_to=date_to, public=True)
    total = (await db.execute(text(f"SELECT COUNT(*) FROM event ev {where}"), params)).scalar_one()
    rows = (
        await db.execute(
            text(_SELECT + where + "ORDER BY ev.event_date, ev.start_time, ev.event_id "
                 "LIMIT :limit OFFSET :offset"),
            {**params, "limit": size, "offset": (page - 1) * size},
        )
    ).all()
    return await _tagged(db, [_to_event(row) for row in rows]), total


async def _row_by_key(db: AsyncSession, key: str, *, public: bool):
    """An event by slug, or by numeric id (the contract's /events/{id})."""
    column, value = ("ev.event_id", int(key)) if key.isdigit() else ("ev.slug", key)
    where = f"WHERE {column} = :key" + (" AND ev.status <> 'Draft'" if public else "")
    return (await db.execute(text(_SELECT + where), {"key": value})).first()


async def get_event(db: AsyncSession, key) -> EventOut:
    row = await _row_by_key(db, str(key), public=True)
    if row is None:
        raise ApiError(404, "Event not found", "NOT_FOUND")
    return (await _tagged(db, [_to_event(row)]))[0]


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

_REG_SELECT = (
    "SELECT r.registration_id, r.registration_reference, r.status, r.party_size, r.contact_name, "
    " r.contact_email, r.registration_date, r.user_id, u.email AS account_email, "
    f" ev.event_id, ev.slug, ev.title, ev.gallery, {_STARTS} AS starts_at, {_ENDS} AS ends_at, "
    f" ({_ENDS} < now()) AS is_past "
    "FROM event_registration r "
    "JOIN event ev ON ev.event_id = r.event_id "
    "JOIN user_account u ON u.user_id = r.user_id "
)

_REG_STATUS = {"Registered": "confirmed", "Cancelled": "cancelled", "Attended": "attended"}


def _to_registration(row) -> RegistrationOut:
    return RegistrationOut(
        id=row.registration_id,
        reference=row.registration_reference or f"SARHN-EV-{row.registration_id}",
        status=_REG_STATUS.get(row.status, "confirmed"),
        event_id=row.event_id,
        event_slug=row.slug,
        event_title=row.title,
        starts_at=row.starts_at,
        ends_at=row.ends_at,
        gallery=row.gallery,
        contact_name=row.contact_name,
        contact_email=row.contact_email,
        party_size=row.party_size,
        registered_at=row.registration_date,
        is_past=row.is_past,
    )


async def register(db: AsyncSession, key: str, user_id: int, body: RegistrationIn) -> RegistrationOut:
    row = await _row_by_key(db, key, public=True)
    if row is None:
        raise ApiError(404, "That event does not exist.", "NOT_FOUND")
    event = _to_event(row)
    if event.status != "published":
        raise ApiError(409, "Registration is closed for this session.", "REGISTRATION_CLOSED")

    # Lock the event so concurrent registrations queue for the last places.
    await db.execute(text("SELECT event_id FROM event WHERE event_id = :id FOR UPDATE"),
                     {"id": event.id})
    taken = (
        await db.execute(
            text("SELECT COALESCE(SUM(party_size), 0) FROM event_registration "
                 "WHERE event_id = :id AND status = 'Registered'"),
            {"id": event.id},
        )
    ).scalar_one()
    remaining = event.capacity - taken
    if body.party_size > remaining:
        await db.rollback()
        raise ApiError(
            409,
            "This session is now full." if remaining <= 0 else f"Only {remaining} places are left.",
            "EVENT_FULL",
        )

    for _ in range(10):
        reference = f"SARHN-EV-{10000 + secrets.randbelow(90000)}"
        try:
            reg_id = (
                await db.execute(
                    text("INSERT INTO event_registration (user_id, event_id, party_size, contact_name, "
                         "contact_email, registration_reference, status) VALUES (:uid, :eid, :party, "
                         ":name, :email, :ref, 'Registered') "
                         "ON CONFLICT (registration_reference) DO NOTHING RETURNING registration_id"),
                    {"uid": user_id, "eid": event.id, "party": body.party_size,
                     "name": body.contact_name, "email": body.contact_email, "ref": reference},
                )
            ).scalar_one_or_none()
        except IntegrityError:
            await db.rollback()
            raise ApiError(409, "You are already registered for this session.", "ALREADY_REGISTERED")
        if reg_id is not None:
            break
    else:  # pragma: no cover
        await db.rollback()
        raise ApiError(500, "Could not create a registration reference.", "INTERNAL_ERROR")
    await db.commit()
    return await _registration(db, reg_id)


async def _registration(db: AsyncSession, reg_id: int) -> RegistrationOut:
    row = (await db.execute(text(_REG_SELECT + "WHERE r.registration_id = :id"), {"id": reg_id})).first()
    return _to_registration(row)


async def my_registrations(db: AsyncSession, user_id: int, page: int, size: int):
    total = (
        await db.execute(text("SELECT COUNT(*) FROM event_registration WHERE user_id = :uid"),
                         {"uid": user_id})
    ).scalar_one()
    rows = (
        await db.execute(
            text(_REG_SELECT + "WHERE r.user_id = :uid ORDER BY ev.event_date DESC, ev.start_time DESC "
                 "LIMIT :limit OFFSET :offset"),
            {"uid": user_id, "limit": size, "offset": (page - 1) * size},
        )
    ).all()
    return [_to_registration(r) for r in rows], total


async def cancel_registration(db: AsyncSession, reference: str, user_id: int, sees_all: bool):
    row = (
        await db.execute(text(_REG_SELECT + "WHERE r.registration_reference = :ref"),
                         {"ref": reference.strip().upper()})
    ).first()
    if row is None or (row.user_id != user_id and not sees_all):
        raise ApiError(404, "We could not find that registration.", "NOT_FOUND")
    if row.status != "Registered" or row.is_past:
        raise ApiError(409, "Only an upcoming registration can be cancelled.", "CONFLICT")
    await db.execute(text("UPDATE event_registration SET status = 'Cancelled' WHERE registration_id = :id"),
                     {"id": row.registration_id})
    await db.commit()
    return await _registration(db, row.registration_id)


async def registrations_for_event(db: AsyncSession, event_id: int) -> list[StaffRegistrationOut]:
    await _staff_row(db, event_id)
    rows = (
        await db.execute(text(_REG_SELECT + "WHERE r.event_id = :id ORDER BY r.registration_date"),
                         {"id": event_id})
    ).all()
    return [StaffRegistrationOut(**_to_registration(r).model_dump(), user_id=r.user_id,
                                 account_email=r.account_email) for r in rows]


# ---------------------------------------------------------------------------
# Staff
# ---------------------------------------------------------------------------

async def staff_list(db: AsyncSession, *, q=None, status=None, gallery=None):
    where, params = _filters(q=q, status=status, gallery=gallery, public=False)
    rows = (
        await db.execute(text(_SELECT + where + "ORDER BY ev.event_date, ev.start_time, ev.event_id"),
                         params)
    ).all()
    return await _tagged(db, [_to_event(r) for r in rows]), len(rows)


async def _staff_row(db: AsyncSession, event_id: int):
    row = (await db.execute(text(_SELECT + "WHERE ev.event_id = :id"), {"id": event_id})).first()
    if row is None:
        raise ApiError(404, "That event no longer exists.", "NOT_FOUND")
    return row


def _local_parts(starts_at: datetime, ends_at: datetime):
    start, end = starts_at.astimezone(_TZ), ends_at.astimezone(_TZ)
    if start.date() != end.date():
        raise ApiError(400, "A session has to start and finish on the same day.", "VALIDATION_ERROR")
    if end <= start:
        raise ApiError(400, "The finish time needs to be after the start time.", "VALIDATION_ERROR")
    return start.date(), start.time().replace(second=0, microsecond=0), \
        end.time().replace(second=0, microsecond=0)


async def create(db: AsyncSession, body: EventIn) -> EventOut:
    from app.services.content_common import GALLERY_LABELS, unique_slug

    day, start, end = _local_parts(body.starts_at, body.ends_at)
    slug = await unique_slug(db, "event", "event_id", body.title)
    new_id = (
        await db.execute(
            text("INSERT INTO event (title, slug, description, gallery, event_date, start_time, end_time, "
                 "location, capacity, price, member_price, age_min, age_max, status) VALUES (:title, :slug, "
                 ":description, :gallery, :day, :start, :end, :location, :capacity, :price, :member_price, "
                 ":age_min, :age_max, :status) RETURNING event_id"),
            {"title": body.title, "slug": slug, "description": body.description or None,
             "gallery": body.gallery, "day": day, "start": start, "end": end,
             "location": GALLERY_LABELS.get(body.gallery), "capacity": body.capacity,
             "price": Decimal(body.price_cents) / 100, "member_price": Decimal(body.member_price_cents) / 100,
             "age_min": body.age_min, "age_max": body.age_max, "status": STATUS_TO_DB[body.status]},
        )
    ).scalar_one()
    if body.tags:
        from app.services.recommendation_service import set_content_tags
        await set_content_tags(db, "event", new_id, body.tags)
    await db.commit()
    return (await _tagged(db, [_to_event(await _staff_row(db, new_id))]))[0]


async def update(db: AsyncSession, event_id: int, body: EventPatch) -> EventOut:
    from app.services.content_common import GALLERY_LABELS, unique_slug

    row = await _staff_row(db, event_id)
    current = _to_event(row)
    changes = body.model_dump(exclude_unset=True)
    tags = changes.pop("tags", None)
    if tags is not None:
        from app.services.recommendation_service import set_content_tags
        await set_content_tags(db, "event", event_id, tags)
        await db.commit()
    if not changes:
        return (await _tagged(db, [_to_event(await _staff_row(db, event_id))]))[0]
    merged = current.model_dump() | {k: v for k, v in changes.items() if v is not None}

    sets: dict = {}
    if "starts_at" in changes or "ends_at" in changes:
        day, start, end = _local_parts(merged["starts_at"], merged["ends_at"])
        sets.update(event_date=day, start_time=start, end_time=end)
    if "capacity" in changes:
        taken = row.taken
        if changes["capacity"] < taken:
            raise ApiError(409, f"{taken} places are already taken, so capacity cannot be set "
                                f"below {taken}.", "CAPACITY_BELOW_REGISTRATIONS")
        sets["capacity"] = changes["capacity"]
    if merged["member_price_cents"] > merged["price_cents"]:
        raise ApiError(400, "The member price can't be more than the standard price.", "VALIDATION_ERROR")
    if merged["age_min"] is not None and merged["age_max"] is not None \
            and merged["age_max"] < merged["age_min"]:
        raise ApiError(400, "The maximum age can't be below the minimum age.", "VALIDATION_ERROR")
    for key in ("title", "description", "gallery", "age_min", "age_max"):
        if key in changes:
            sets[key] = changes[key] if changes[key] != "" else None
    if "gallery" in changes:
        sets["location"] = GALLERY_LABELS.get(changes["gallery"])
    if "price_cents" in changes and changes["price_cents"] is not None:
        sets["price"] = Decimal(changes["price_cents"]) / 100
    if "member_price_cents" in changes and changes["member_price_cents"] is not None:
        sets["member_price"] = Decimal(changes["member_price_cents"]) / 100
    if changes.get("status"):
        sets["status"] = STATUS_TO_DB[changes["status"]]
    if "title" in changes and changes["title"] != current.title:
        sets["slug"] = await unique_slug(db, "event", "event_id", changes["title"], event_id)
    if not sets:
        return (await _tagged(db, [current]))[0]
    assignments = ", ".join(f"{c} = :{c}" for c in sets)
    await db.execute(text(f"UPDATE event SET {assignments}, updated_at = now() WHERE event_id = :id"),
                     {**sets, "id": event_id})
    await db.commit()
    return (await _tagged(db, [_to_event(await _staff_row(db, event_id))]))[0]


async def delete(db: AsyncSession, event_id: int) -> str:
    row = await _staff_row(db, event_id)
    if row.taken > 0:
        raise ApiError(
            409,
            f"{row.taken} people are registered. Cancel the session instead of deleting it, "
            "so their records are kept.",
            "EVENT_HAS_REGISTRATIONS",
        )
    await db.execute(text("DELETE FROM event WHERE event_id = :id"), {"id": event_id})
    await db.commit()
    return row.title
