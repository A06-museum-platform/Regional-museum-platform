"""Staff visitor information (role-permission matrix: "Update visitor
information pages" -- Staff and Admin).

PUT /api/staff/visitor-information  body: the whole page incl. facilities
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_staff
from app.db.session import get_session
from app.schemas.visitor_information import VisitorInformationIn, VisitorInformationOut
from app.services import activity_service
from app.services.visitor_information_service import save_visitor_information

router = APIRouter(
    prefix="/api/staff",
    tags=["staff-visitor-information"],
    dependencies=[Depends(require_staff)],
)


@router.put("/visitor-information", response_model=VisitorInformationOut)
async def update_visitor_information(
    body: VisitorInformationIn,
    actor: dict = Depends(require_staff),
    db: AsyncSession = Depends(get_session),
):
    saved = await save_visitor_information(db, body)
    await activity_service.record(db, actor, "visitor_info.updated",
                                  f"Plan your visit page — {len(body.facilities)} facilities")
    return saved
