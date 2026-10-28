"""Choose an existing image as its owner's public cover without moving files."""
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApiError

# Identifiers are internal constants, never user-provided SQL.
OWNERS = (
    ('collection_item_id', 'collection_item', 'item_id'),
    ('exhibition_id', 'exhibition', 'exhibition_id'),
    ('event_id', 'event', 'event_id'),
)


async def make_primary(db: AsyncSession, media_id: int):
    row = (await db.execute(text(
        'SELECT media_id, collection_item_id, exhibition_id, event_id, media_type '
        'FROM media_asset WHERE media_id = :id'
    ), {'id': media_id})).first()
    if not row:
        raise ApiError(404, 'Image not found', 'NOT_FOUND')
    if row.media_type != 'image':
        raise ApiError(400, 'Only images can be used as a public cover', 'VALIDATION_ERROR')
    fk, table, pk = next(owner for owner in OWNERS if getattr(row, owner[0]) is not None)
    owner_id = getattr(row, fk)
    # Serialize cover changes per owner, including requests for different images.
    await db.execute(text(f'SELECT {pk} FROM {table} WHERE {pk} = :id FOR UPDATE'), {'id': owner_id})
    # Check it still exists before clearing a previous cover (a delete may race).
    target = (await db.execute(text(
        f'SELECT media_id FROM media_asset WHERE media_id = :id AND {fk} = :owner FOR UPDATE'
    ), {'id': media_id, 'owner': owner_id})).first()
    if not target:
        raise ApiError(404, 'Image no longer available', 'NOT_FOUND')
    await db.execute(text(f'UPDATE media_asset SET is_primary = FALSE WHERE {fk} = :owner'), {'owner': owner_id})
    result = (await db.execute(text(
        'UPDATE media_asset SET is_primary = TRUE WHERE media_id = :id '
        'RETURNING media_id, collection_item_id, exhibition_id, event_id, url, '
        'media_type, storage, sort_order, is_primary, created_at'
    ), {'id': media_id})).first()
    await db.commit()
    return result
