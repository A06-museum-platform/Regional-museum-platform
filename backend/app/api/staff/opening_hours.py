"""Staff opening hours (role-permission matrix: "Update opening hours" --
Staff and Admin; client: staff update opening hours as seasons change).

PUT /api/staff/opening-hours  body { weekly: [7 days], overrides: [...] }
    -> { weekly, overrides }; 422 INVALID_HOURS when an open day's times
       don't make sense
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_staff
from app.db.session import get_session
from app.schemas.opening_hours import OpeningHoursIn, OpeningHoursOut
from app.services import activity_service
from app.services.opening_hours_service import save_opening_hours

router = APIRouter(
    prefix="/api/staff",
    tags=["staff-opening-hours"],
    dependencies=[Depends(require_staff)],
)


@router.put("/opening-hours", response_model=OpeningHoursOut)
async def update_opening_hours(
    body: OpeningHoursIn,
    actor: dict = Depends(require_staff),
    db: AsyncSession = Depends(get_session),
):
    saved = await save_opening_hours(db, body)
    exceptions = len(body.overrides)
    await activity_service.record(
        db, actor, "opening_hours.updated",
        f"Weekly pattern and {exceptions} dated exception{'s' if exceptions != 1 else ''}",
    )
    return saved
