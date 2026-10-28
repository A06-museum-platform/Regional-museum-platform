"""Public visitor information (docs/api-contract.md section 10).

GET /api/visitor-information -> address, transport, parking, contact,
                                about text and facilities / accessibility
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.visitor_information import VisitorInformationOut
from app.services.visitor_information_service import get_visitor_information

router = APIRouter(prefix="/api", tags=["visitor-information"])


@router.get("/visitor-information", response_model=VisitorInformationOut)
async def read_visitor_information(db: AsyncSession = Depends(get_session)):
    return await get_visitor_information(db)
