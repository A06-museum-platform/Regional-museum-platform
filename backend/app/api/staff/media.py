"""Staff media upload endpoints (images priority, video-ready).

One router serves all three ownable resources so the validation,
storage and permission logic exists exactly once:

    POST   /api/staff/{collection-items,exhibitions,events}/{id}/media
    GET    /api/staff/{collection-items,exhibitions,events}/{id}/media
    DELETE /api/staff/media/{media_id}

Contract amendment proposed in the PR description (contract is frozen
at G2 — Ray/Harbor/Rock agreement required before merge).
"""

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_staff
from app.core.config import get_settings
from app.core.errors import ApiError
from app.db.session import get_session
from app.schemas.media import MediaOut, MediaUploadOut
from app.services.storage import (
    StorageNotConfigured,
    SupabaseStorage,
    UploadRejected,
    storage_key,
    validate_upload,
)

router = APIRouter(prefix="/api/staff", tags=["staff-media"])

# URL segment -> (table, pk column, media_asset fk column)
OWNERS = {
    "collection-items": ("collection_item", "item_id", "collection_item_id"),
    "exhibitions": ("exhibition", "exhibition_id", "exhibition_id"),
    "events": ("event", "event_id", "event_id"),
}


def _storage() -> SupabaseStorage:
    settings = get_settings()
    try:
        return SupabaseStorage(
            settings.supabase_url,
            settings.supabase_service_key,
            settings.supabase_bucket,
        )
    except StorageNotConfigured as exc:
        raise ApiError(503, exc.detail, exc.code)


async def _get_owner(db: AsyncSession, owner: str, owner_id: int) -> tuple[str, str]:
    table, pk, fk = OWNERS[owner]
    exists = (
        await db.execute(
            text(f"SELECT 1 FROM {table} WHERE {pk} = :id"), {"id": owner_id}
        )
    ).first()
    if not exists:
        raise ApiError(404, f"{owner} {owner_id} not found", "NOT_FOUND")
    return table, fk


def _row_to_out(row) -> MediaOut:
    return MediaOut(
        media_id=row.media_id,
        collection_item_id=row.collection_item_id,
        exhibition_id=row.exhibition_id,
        event_id=row.event_id,
        url=row.url,
        media_type=row.media_type,
        sort_order=row.sort_order,
        is_primary=row.is_primary,
        created_at=row.created_at,
    )


@router.post("/{owner}/{owner_id}/media", status_code=201, response_model=MediaUploadOut)
async def upload_media(
    owner: str,
    owner_id: int,
    file: UploadFile = File(...),
    is_primary: bool = False,
    sort_order: int = 0,
    db: AsyncSession = Depends(get_session),
    staff: dict = Depends(require_staff),
):
    if owner not in OWNERS:
        raise ApiError(404, f"Unknown resource: {owner}", "NOT_FOUND")
    settings = get_settings()

    data = await file.read()
    try:
        media_type = validate_upload(
            file.filename or "upload",
            file.content_type,
            len(data),
            settings.max_image_mb,
            settings.max_video_mb,
        )
    except UploadRejected as exc:
        status_code = 413 if exc.code == "FILE_TOO_LARGE" else 400
        raise ApiError(status_code, exc.detail, exc.code)

    store = _storage()
    _, fk = await _get_owner(db, owner, owner_id)

    key = storage_key(owner, owner_id, file.content_type)
    try:
        url = await store.upload(key, data, file.content_type)
    except Exception:
        raise ApiError(502, "Media upload failed, try again", "STORAGE_ERROR")

    if is_primary:
        await db.execute(
            text(
                f"UPDATE media_asset SET is_primary = FALSE "
                f"WHERE {fk} = :id"
            ),
            {"id": owner_id},
        )
    row = (
        await db.execute(
            text(
                "INSERT INTO media_asset "
                "(collection_item_id, exhibition_id, event_id, url, "
                " media_type, sort_order, is_primary, uploaded_by) "
                "VALUES (:item, :exhibition, :event, :url, "
                " :media_type, :sort_order, :is_primary, :uploaded_by) "
                "RETURNING media_id, collection_item_id, exhibition_id, "
                " event_id, url, media_type, sort_order, is_primary, created_at"
            ),
            {
                "item": owner_id if fk == "collection_item_id" else None,
                "exhibition": owner_id if fk == "exhibition_id" else None,
                "event": owner_id if fk == "event_id" else None,
                "url": url,
                "media_type": media_type,
                "sort_order": sort_order,
                "is_primary": is_primary,
                "uploaded_by": staff.get("sub"),
            },
        )
    ).first()
    await db.commit()
    return MediaUploadOut(media=_row_to_out(row), thumbnail_url=url)


@router.get("/{owner}/{owner_id}/media", response_model=list[MediaOut])
async def list_media(
    owner: str,
    owner_id: int,
    db: AsyncSession = Depends(get_session),
    staff: dict = Depends(require_staff),
):
    if owner not in OWNERS:
        raise ApiError(404, f"Unknown resource: {owner}", "NOT_FOUND")
    _, fk = await _get_owner(db, owner, owner_id)
    rows = (
        await db.execute(
            text(
                "SELECT media_id, collection_item_id, exhibition_id, event_id, "
                " url, media_type, sort_order, is_primary, created_at "
                f"FROM media_asset WHERE {fk} = :id "
                "ORDER BY is_primary DESC, sort_order, media_id"
            ),
            {"id": owner_id},
        )
    ).all()
    return [_row_to_out(r) for r in rows]


@router.delete("/media/{media_id}", status_code=204)
async def delete_media(
    media_id: int,
    db: AsyncSession = Depends(get_session),
    staff: dict = Depends(require_staff),
):
    row = (
        await db.execute(
            text("SELECT media_id, url FROM media_asset WHERE media_id = :id"),
            {"id": media_id},
        )
    ).first()
    if not row:
        raise ApiError(404, f"Media {media_id} not found", "NOT_FOUND")
    # Best effort: a missing storage object must not block row deletion.
    try:
        await _storage().remove(_key_from_url(row.url))
    except Exception:
        pass
    await db.execute(
        text("DELETE FROM media_asset WHERE media_id = :id"), {"id": media_id}
    )
    await db.commit()
    return None


def _key_from_url(url: str) -> str:
    settings = get_settings()
    prefix = (
        f"{settings.supabase_url.rstrip('/')}/storage/v1/object/public/"
        f"{settings.supabase_bucket}/"
    )
    return url[len(prefix):] if url.startswith(prefix) else url
