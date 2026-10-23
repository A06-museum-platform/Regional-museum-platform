"""A signed-in account's own activity (docs/api-contract.md section 10:
/api/activity/me; client requirement 3(iv): members see their "last
activity"). Entries the account made, or that were about it (an
administrator approving its membership).

GET /api/activity/me?page=&size=  -> { items, total, page, size }
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_session
from app.schemas.user import UserOut
from app.services.activity_service import ActivityListOut, list_activity

router = APIRouter(prefix="/api", tags=["activity"])


@router.get("/activity/me", response_model=ActivityListOut)
async def my_activity(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    user: UserOut = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    items, total = await list_activity(db, user_id=user.id, page=page, size=size)
    return ActivityListOut(items=items, total=total, page=page, size=size)
