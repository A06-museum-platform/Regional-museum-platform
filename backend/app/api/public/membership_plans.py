"""Public membership plan listing (docs/api-contract.md section 6).

GET /api/membership-plans -> paginated {items, total, page, size}
"""

from fastapi import APIRouter, Query

from app.schemas.membership import MembershipPlanListOut
from app.services.membership_service import list_plans

router = APIRouter(prefix="/api", tags=["membership"])


@router.get("/membership-plans", response_model=MembershipPlanListOut)
async def list_membership_plans(
    page: int = Query(1, ge=1),
    size: int = Query(12, ge=1, le=100),
):
    items, total = list_plans(page, size)
    return MembershipPlanListOut(items=items, total=total, page=page, size=size)
