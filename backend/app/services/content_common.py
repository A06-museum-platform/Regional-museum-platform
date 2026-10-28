"""Helpers shared by the content services (collections, exhibitions, events).

Vocabularies are the keys of GALLERIES / CATEGORIES in
frontend/src/api/constants.js and the CHECK constraints in migration 009.
"""

import re
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

GALLERIES = ("main_hall", "telegraph", "monster_mine", "encounter_bay")
GALLERY_LABELS = {
    "main_hall": "Main Hall",
    "telegraph": "Telegraph Gallery",
    "monster_mine": "Monster Mine Gallery",
    "encounter_bay": "Encounter Bay Gallery",
}
CATEGORIES = ("mineral", "instrument", "document", "photograph", "machinery")
PUBLISH_STATUSES = ("draft", "published")


def slugify(value: str) -> str:
    """"Malachite matrix, Burra" -> "malachite-matrix-burra" (max 60 chars)."""
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")[:60].strip("-") or "item"


async def unique_slug(
    db: AsyncSession, table: str, id_column: str, title: str, own_id: Optional[int] = None
) -> str:
    """A slug for title that no other row of table uses: "title", then
    "title-2", "title-3"... own_id is the row being renamed, which may keep
    its own slug. table and id_column are code constants, never user input."""
    base = slugify(title)
    taken = {
        row.slug
        for row in (
            await db.execute(
                text(f"SELECT slug FROM {table} WHERE (slug = :base OR slug LIKE :pattern) "
                     f"AND (CAST(:own_id AS INTEGER) IS NULL OR {id_column} <> :own_id)"),
                {"base": base, "pattern": f"{base}-%", "own_id": own_id},
            )
        ).all()
    }
    if base not in taken:
        return base
    n = 2
    while f"{base}-{n}" in taken:
        n += 1
    return f"{base}-{n}"


def like_pattern(q: str) -> str:
    """A case-insensitive substring pattern with LIKE wildcards escaped, so a
    search for "100%" is literal."""
    return "%" + re.sub(r"([\\%_])", r"\\\1", q.strip()) + "%"


def primary_image_sql(owner_column: str, alias: str) -> str:
    """Subquery for an owner's primary image URL (lowest sort_order otherwise)."""
    return (
        "(SELECT ma.url FROM media_asset ma "
        f" WHERE ma.{owner_column} = {alias} AND ma.media_type = 'image' "
        " ORDER BY ma.is_primary DESC, ma.sort_order, ma.media_id LIMIT 1)"
    )
