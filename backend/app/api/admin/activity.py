"""Activity log (role-permission matrix: "View audit / activity log for all
users" -- Admin only).

GET /api/admin/activity-log?q=&action=&page=&size=  -> { items, total, page, size }
    newest first; written by the backend as a side effect of each action
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.db.session import get_session
from app.services.activity_service import ActivityListOut, list_activity

router = APIRouter(
    prefix="/api/admin",
    tags=["admin-activity"],
    dependencies=[Depends(require_admin)],
)


@router.get("/activity-log", response_model=ActivityListOut)
async def activity_log(
    q: Optional[str] = None,
    action: Optional[str] = Query(None, max_length=50),
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=200),
    db: AsyncSession = Depends(get_session),
):
    items, total = await list_activity(db, q=q, action=action, page=page, size=size)
    return ActivityListOut(items=items, total=total, page=page, size=size)
