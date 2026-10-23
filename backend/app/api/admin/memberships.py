"""Admin membership approval (docs/api-contract.md section 10).

GET  /api/membership-applications?status=&page=&size= -> {items, total, page, size}
POST /api/membership-applications/{id}/approve        -> 200 updated application
POST /api/membership-applications/{id}/reject         -> 200 updated application

status filters on the API's vocabulary (pending | active | expired |
revoked); omitted lists every record. approve/reject only act on a pending
application: 404 if it doesn't exist, 409 NOT_PENDING if already decided.
"""

from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.db.session import get_session
from app.schemas.membership import MembershipListOut, MembershipOut
from app.services import activity_service
from app.services.membership_service import approve, list_memberships, reject

router = APIRouter(
    prefix="/api/membership-applications",
    tags=["admin-memberships"],
    dependencies=[Depends(require_admin)],
)


@router.get("", response_model=MembershipListOut)
async def list_applications(
    status: Optional[Literal["pending", "active", "expired", "revoked"]] = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_session),
):
    items, total = await list_memberships(db, status, page, size)
    return MembershipListOut(items=items, total=total, page=page, size=size)


@router.post("/{membership_id}/approve", response_model=MembershipOut)
async def approve_application(
    membership_id: int,
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
):
    member = await approve(db, membership_id)
    await activity_service.record(db, admin, "member.approved", member.full_name,
                                  reference=member.member_ref, subject_user_id=member.user_id)
    return member


@router.post("/{membership_id}/reject", response_model=MembershipOut)
async def reject_application(
    membership_id: int,
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
):
    member = await reject(db, membership_id)
    await activity_service.record(db, admin, "member.declined", member.full_name,
                                  reference=member.member_ref, subject_user_id=member.user_id)
    return member
