"""Interests and personalised recommendations (docs/api-contract.md section 7;
proposal: "interest-based filtering algorithm").

Algorithm -- content-based filtering on the interest tags of migration 011:

  1. Candidates are what a visitor could act on now: published exhibitions
     that haven't closed, published sessions that haven't started and still
     have places (minus ones the member already registered for), and
     published collection objects.
  2. score = 10 x (tags shared with the member's interests)
             + 3 if the membership covers children and the content suits
                 ages 10-14 (the museum's main audience)
             + 2 for a session in the next 14 days
             + 1 for an exhibition or a collection highlight
     Content sharing no tag with the member's interests is dropped, unless
     the member hasn't chosen any interests yet: then the boosts alone rank
     everything, labelled "Popular with visitors".
  3. Ties go to the soonest session / newest content.

Every result carries the tag labels that matched, so the page can say why
it was recommended.
"""

from datetime import datetime, timedelta, timezone
from typing import Literal, Optional

from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApiError
from app.services.event_service import MUSEUM_TIMEZONE

_TODAY = f"(now() AT TIME ZONE '{MUSEUM_TIMEZONE}')::date"


class InterestTagOut(BaseModel):
    id: int
    slug: str
    label: str
    description: str


class RecommendationOut(BaseModel):
    type: Literal["exhibition", "event", "collection_item"]
    id: int
    slug: str
    title: str
    summary: Optional[str]
    gallery: Optional[str]
    starts_at: Optional[datetime] = None
    matched_tags: list[str]
    reason: str
    score: int


class RecommendationListOut(BaseModel):
    items: list[RecommendationOut]
    total: int
    page: int
    size: int
    interests: list[InterestTagOut]
    personalised: bool


# ---------------------------------------------------------------------------
# Vocabulary and a user's interests
# ---------------------------------------------------------------------------

async def list_tags(db: AsyncSession) -> list[InterestTagOut]:
    rows = (
        await db.execute(text("SELECT tag_id, slug, label, description FROM interest_tag "
                              "ORDER BY sort_order, label"))
    ).all()
    return [InterestTagOut(id=r.tag_id, slug=r.slug, label=r.label, description=r.description)
            for r in rows]


async def user_interests(db: AsyncSession, user_id: int) -> list[InterestTagOut]:
    rows = (
        await db.execute(
            text("SELECT t.tag_id, t.slug, t.label, t.description FROM user_interest ui "
                 "JOIN interest_tag t ON t.tag_id = ui.tag_id WHERE ui.user_id = :uid "
                 "ORDER BY t.sort_order"),
            {"uid": user_id},
        )
    ).all()
    return [InterestTagOut(id=r.tag_id, slug=r.slug, label=r.label, description=r.description)
            for r in rows]


async def _tag_ids(db: AsyncSession, slugs: list[str]) -> list[int]:
    slugs = list(dict.fromkeys(slugs))
    if not slugs:
        return []
    rows = (await db.execute(text("SELECT tag_id, slug FROM interest_tag WHERE slug = ANY(:s)"),
                             {"s": slugs})).all()
    unknown = set(slugs) - {r.slug for r in rows}
    if unknown:
        raise ApiError(422, f"Unknown interest: {', '.join(sorted(unknown))}", "VALIDATION_ERROR")
    return [r.tag_id for r in rows]


async def set_user_interests(db: AsyncSession, user_id: int, slugs: list[str]) -> list[InterestTagOut]:
    ids = await _tag_ids(db, slugs)
    await db.execute(text("DELETE FROM user_interest WHERE user_id = :uid"), {"uid": user_id})
    for tag_id in ids:
        await db.execute(text("INSERT INTO user_interest (user_id, tag_id) VALUES (:uid, :tid)"),
                         {"uid": user_id, "tid": tag_id})
    await db.commit()
    return await user_interests(db, user_id)


# ---------------------------------------------------------------------------
# Tags on content (staff editors set them; public APIs show them)
# ---------------------------------------------------------------------------

_LINKS = {
    "exhibition": ("exhibition_tag", "exhibition_id"),
    "event": ("event_tag", "event_id"),
    "collection_item": ("collection_item_tag", "item_id"),
}


async def tags_for(db: AsyncSession, kind: str, ids: list[int]) -> dict[int, list[str]]:
    """{content id: [tag slug, ...]} for several rows of one kind."""
    if not ids:
        return {}
    table, column = _LINKS[kind]
    rows = (
        await db.execute(
            text(f"SELECT l.{column} AS owner, t.slug FROM {table} l JOIN interest_tag t "
                 f"ON t.tag_id = l.tag_id WHERE l.{column} = ANY(:ids) ORDER BY t.sort_order"),
            {"ids": ids},
        )
    ).all()
    out: dict[int, list[str]] = {i: [] for i in ids}
    for row in rows:
        out[row.owner].append(row.slug)
    return out


async def set_content_tags(db: AsyncSession, kind: str, owner_id: int, slugs: list[str]) -> None:
    """Replace one row's tags. The caller commits."""
    table, column = _LINKS[kind]
    ids = await _tag_ids(db, slugs)
    await db.execute(text(f"DELETE FROM {table} WHERE {column} = :id"), {"id": owner_id})
    for tag_id in ids:
        await db.execute(text(f"INSERT INTO {table} ({column}, tag_id) VALUES (:id, :tid)"),
                         {"id": owner_id, "tid": tag_id})


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------

async def _candidates(db: AsyncSession, user_id: int) -> list[dict]:
    exhibitions = (
        await db.execute(
            text("SELECT x.exhibition_id AS id, x.slug, x.title, x.summary, x.gallery, x.age_min, "
                 "x.age_max, x.start_date FROM exhibition x WHERE x.publish_status = 'published' "
                 f"AND (x.end_date IS NULL OR x.end_date >= {_TODAY})")
        )
    ).all()
    events = (
        await db.execute(
            text("SELECT ev.event_id AS id, ev.slug, ev.title, ev.description AS summary, ev.gallery, "
                 "ev.age_min, ev.age_max, "
                 f"((ev.event_date + ev.start_time) AT TIME ZONE '{MUSEUM_TIMEZONE}') AS starts_at "
                 "FROM event ev WHERE ev.status = 'Scheduled' "
                 f"AND ((ev.event_date + ev.start_time) AT TIME ZONE '{MUSEUM_TIMEZONE}') > now() "
                 "AND ev.capacity > (SELECT COALESCE(SUM(r.party_size), 0) FROM event_registration r "
                 "  WHERE r.event_id = ev.event_id AND r.status = 'Registered') "
                 "AND NOT EXISTS (SELECT 1 FROM event_registration r WHERE r.event_id = ev.event_id "
                 "  AND r.user_id = :uid AND r.status = 'Registered')"),
            {"uid": user_id},
        )
    ).all()
    items = (
        await db.execute(
            text("SELECT c.item_id AS id, c.slug, c.item_name AS title, c.description AS summary, "
                 "c.gallery, c.is_family_friendly, c.is_highlight FROM collection_item c "
                 "WHERE c.publish_status = 'published'")
        )
    ).all()

    ex_tags = await tags_for(db, "exhibition", [r.id for r in exhibitions])
    ev_tags = await tags_for(db, "event", [r.id for r in events])
    ci_tags = await tags_for(db, "collection_item", [r.id for r in items])

    def suits_families(age_min, age_max) -> bool:
        return (age_min or 0) <= 14 and (age_max if age_max is not None else 99) >= 10

    out = []
    for r in exhibitions:
        out.append({"type": "exhibition", "row": r, "tags": ex_tags[r.id],
                    "family": suits_families(r.age_min, r.age_max), "soon": False, "highlight": False})
    now = datetime.now(timezone.utc)
    for r in events:
        out.append({"type": "event", "row": r, "tags": ev_tags[r.id],
                    "family": suits_families(r.age_min, r.age_max),
                    "soon": r.starts_at - now <= timedelta(days=14), "highlight": False})
    for r in items:
        out.append({"type": "collection_item", "row": r, "tags": ci_tags[r.id],
                    "family": r.is_family_friendly, "soon": False, "highlight": r.is_highlight})
    return out


async def recommend(db: AsyncSession, user_id: int, page: int, size: int,
                    kind: Optional[str] = None) -> RecommendationListOut:
    interests = await user_interests(db, user_id)
    wanted = {t.slug: t.label for t in interests}
    children = (
        await db.execute(
            text("SELECT COALESCE(MAX(children_covered), 0) FROM membership WHERE user_id = :uid "
                 "AND status = 'Active'"),
            {"uid": user_id},
        )
    ).scalar_one()

    ranked = []
    for c in await _candidates(db, user_id):
        if kind and c["type"] != kind:
            continue
        matched = [wanted[t] for t in c["tags"] if t in wanted]
        if wanted and not matched:
            continue
        score = 10 * len(matched)
        reasons = []
        if matched:
            reasons.append("Matches your interest in " + _join([m.lower() for m in matched]))
        if children and c["family"]:
            score += 3
            reasons.append("suits your family")
        if c["soon"]:
            score += 2
            reasons.append("coming up soon")
        if c["highlight"] or c["type"] == "exhibition":
            score += 1  # exhibitions are what the proposal promises to recommend
        if not wanted:
            reasons.insert(0, "Popular with visitors")
        row = c["row"]
        ranked.append(RecommendationOut(
            type=c["type"], id=row.id, slug=row.slug, title=row.title,
            summary=(row.summary or "")[:240] or None, gallery=row.gallery,
            starts_at=getattr(row, "starts_at", None), matched_tags=matched,
            reason=_sentence(reasons), score=score,
        ))

    far_future = datetime.max.replace(tzinfo=timezone.utc)
    ranked.sort(key=lambda r: (-r.score, r.starts_at or far_future, r.title))
    start = (page - 1) * size
    return RecommendationListOut(items=ranked[start:start + size], total=len(ranked), page=page,
                                 size=size, interests=interests, personalised=bool(wanted))


def _join(words: list[str]) -> str:
    return words[0] if len(words) == 1 else ", ".join(words[:-1]) + " and " + words[-1]


def _sentence(parts: list[str]) -> str:
    if not parts:
        return "Recommended for you"
    text_ = "; ".join(parts)
    return text_[0].upper() + text_[1:]


async def attach_tags(db: AsyncSession, kind: str, items: list) -> list:
    """Fill `tags` on API models of one content kind, in one query."""
    mapping = await tags_for(db, kind, [i.id for i in items])
    for item in items:
        item.tags = mapping.get(item.id, [])
    return items
