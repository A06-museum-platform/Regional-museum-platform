"""Membership applications (Flow 6, docs/api-contract.md section 6) and the
caller's own record (docs/decisions.md "Booking and membership").

GET  /api/memberships/me          -> the caller's current record, or 404
POST /api/membership-applications -> body {plan_id, children_covered};
                                     creates a pending membership row

Applying is for visitor and member accounts (role-permission matrix:
"Apply for membership"); staff and admin accounts don't hold memberships.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.errors import ApiError
from app.db.session import get_session
from app.schemas.membership import MembershipApplicationIn, MembershipOut
from app.schemas.user import UserOut
from app.services import activity_service
from app.services.membership_service import apply, current_membership

router = APIRouter(prefix="/api", tags=["membership"])

APPLICANT_ROLES = {"visitor", "member"}


@router.get("/memberships/me", response_model=MembershipOut)
async def my_membership(
    user: UserOut = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    record = await current_membership(db, user.id)
    if record is None:
        raise ApiError(404, "No membership found", "NOT_FOUND")
    return record


@router.post("/membership-applications", response_model=MembershipOut)
async def apply_for_membership(
    body: MembershipApplicationIn,
    user: UserOut = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    if user.role not in APPLICANT_ROLES:
        raise ApiError(
            403, "Staff and administrator accounts cannot hold a membership", "FORBIDDEN"
        )
    record = await apply(db, user.id, body)
    await activity_service.record(db, user, "member.applied",
                                  f"{record.plan.display_name if record.plan else record.tier} membership",
                                  reference=record.member_ref)
    return record
