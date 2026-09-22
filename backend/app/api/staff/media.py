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
    UploadRejected,
    get_storage,
    r2_public_base,
    storage_key,
    validate_upload,
)

router = APIRouter(prefix="/api/staff", tags=["staff-media"])

# URL segment -> (table, pk column, media_asset fk column).
# To make a new entity ownable, add one entry here + migration 00N
# (new FK + CHECK arm) + seeds — full recipe: docs/design/media-storage.md §5.2.
OWNERS = {
    "collection-items": ("collection_item", "item_id", "collection_item_id"),
    "exhibitions": ("exhibition", "exhibition_id", "exhibition_id"),
    "events": ("event", "event_id", "event_id"),
}


def _storage():
    settings = get_settings()
    try:
        return get_storage(settings), settings.media_backend.lower()
    except StorageNotConfigured as exc:
        raise ApiError(503, exc.detail, exc.code)
    except ValueError as exc:
        # Unknown MEDIA_BACKEND (belt-and-braces behind the Settings
        # validator): fail loudly before any bytes move, never silently
        # fall through to another backend and orphan objects.
        raise ApiError(500, str(exc), "CONFIG_ERROR")


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
        storage=row.storage,
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

    store, mode = _storage()
    _, fk = await _get_owner(db, owner, owner_id)

    # JWT 'sub' is a string; uploaded_by is INTEGER. Non-numeric subs
    # (e.g. future UUID subjects) degrade to NULL, never to a 500.
    try:
        uploader = (
            int(staff.get("sub")) if staff.get("sub") is not None else None
        )
    except (TypeError, ValueError):
        uploader = None

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
                " media_type, storage, sort_order, is_primary, uploaded_by) "
                "VALUES (:item, :exhibition, :event, :url, "
                " :media_type, :storage, :sort_order, :is_primary, :uploaded_by) "
                "RETURNING media_id, collection_item_id, exhibition_id, "
                " event_id, url, media_type, storage, sort_order, "
                " is_primary, created_at"
            ),
            {
                "item": owner_id if fk == "collection_item_id" else None,
                "exhibition": owner_id if fk == "exhibition_id" else None,
                "event": owner_id if fk == "event_id" else None,
                "url": url,
                "media_type": media_type,
                "storage": mode,
                "sort_order": sort_order,
                "is_primary": is_primary,
                "uploaded_by": uploader,
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
                " url, media_type, storage, sort_order, is_primary, created_at "
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
            text(
                "SELECT media_id, url, storage FROM media_asset "
                "WHERE media_id = :id"
            ),
            {"id": media_id},
        )
    ).first()
    if not row:
        raise ApiError(404, f"Media {media_id} not found", "NOT_FOUND")
    # Best effort: a missing storage object must not block row deletion.
    # 'remote' seed rows point at third-party URLs — nothing to delete.
    if row.storage in ("supabase", "r2", "local"):
        try:
            store, _ = _storage()
            await store.remove(_key_from_url(row.url, row.storage))
        except Exception:
            pass
    await db.execute(
        text("DELETE FROM media_asset WHERE media_id = :id"), {"id": media_id}
    )
    await db.commit()
    return None


def _key_from_url(url: str, storage: str) -> str:
    """Inverse of public_url(), sharing the same base-URL helper so upload
    and delete can never disagree about what a key looks like."""
    settings = get_settings()
    if storage == "supabase":
        prefix = (
            f"{settings.supabase_url.rstrip('/')}/storage/v1/object/public/"
            f"{settings.supabase_bucket}/"
        )
    elif storage == "r2":
        prefix = (
            r2_public_base(
                settings.r2_endpoint, settings.r2_bucket, settings.r2_public_base
            )
            + "/"
        )
    elif storage == "local":
        prefix = "/uploads/"
    else:
        return url
    return url[len(prefix):] if url.startswith(prefix) else url
