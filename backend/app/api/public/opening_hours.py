"""Public opening hours (docs/api-contract.md section 10).

GET /api/opening-hours -> { weekly: [...], overrides: [] }

The contract table only says "weekly array"; this is the shape
frontend/src/api/openingHours.js already reads, for the booking page's
date picker and the staff opening-hours editor.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.opening_hours import OpeningHoursOut
from app.services.opening_hours_service import get_opening_hours

router = APIRouter(prefix="/api", tags=["opening-hours"])


@router.get("/opening-hours", response_model=OpeningHoursOut)
async def read_opening_hours(db: AsyncSession = Depends(get_session)):
    return await get_opening_hours(db)
