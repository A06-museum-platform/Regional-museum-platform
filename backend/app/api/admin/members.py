"""Admin Members screen, in the shape frontend/src/api/members.js requests.

GET  /api/admin/members?q=&status=&tier= -> {items, total, counts}
POST /api/admin/members/{id}/approve      -> pending  -> active (+ Member role)
POST /api/admin/members/{id}/decline      -> pending  -> revoked (Rejected)
POST /api/admin/members/{id}/revoke       body {reason}, required;
                                             active -> revoked (Cancelled),
                                             and the member's login is disabled
POST /api/admin/members/{id}/restore      revoked/expired -> active, login
                                             re-enabled

approve/decline share their logic with the contract's
/api/membership-applications endpoints (app/api/admin/memberships.py).
Every decision is written to the activity log with its reason (if given)
and the member as subject, so it shows in the member's own activity too.
"""

from typing import Literal, Optional

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin
from app.core.errors import ApiError
from app.db.session import get_session
from app.schemas.membership import AdminMemberListOut, MembershipOut, ReasonIn
from app.services import activity_service
from app.services.membership_service import (
    approve,
    list_for_admin,
    reject,
    restore,
    revoke,
)

router = APIRouter(
    prefix="/api/admin/members",
    tags=["admin-members"],
    dependencies=[Depends(require_admin)],
)


@router.get("", response_model=AdminMemberListOut)
async def list_members(
    q: Optional[str] = None,
    status: Optional[Literal["pending", "active", "expired", "revoked"]] = None,
    tier: Optional[str] = None,
    db: AsyncSession = Depends(get_session),
):
    items, counts = await list_for_admin(db, q, status, tier)
    return AdminMemberListOut(items=items, total=len(items), counts=counts)


def _target(m: MembershipOut) -> str:
    return f"{m.full_name} — {m.plan.display_name if m.plan else m.tier} ({m.member_ref})"


@router.post("/{membership_id}/approve", response_model=MembershipOut)
async def approve_member(
    membership_id: int,
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
):
    member = await approve(db, membership_id)
    await activity_service.record(db, admin, "member.approved", _target(member),
                                  reference=member.member_ref, subject_user_id=member.user_id)
    return member


@router.post("/{membership_id}/decline", response_model=MembershipOut)
async def decline_member(
    membership_id: int,
    body: Optional[ReasonIn] = None,
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
):
    member = await reject(db, membership_id)
    await activity_service.record(db, admin, "member.declined", _target(member),
                                  reason=(body.reason or None) if body else None,
                                  reference=member.member_ref, subject_user_id=member.user_id)
    return member


@router.post("/{membership_id}/revoke", response_model=MembershipOut)
async def revoke_member(
    membership_id: int,
    body: ReasonIn,
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
):
    if not (body.reason or "").strip():
        raise ApiError(
            422,
            "A reason is required so the decision can be explained later.",
            "REASON_REQUIRED",
        )
    member = await revoke(db, membership_id)
    await activity_service.record(db, admin, "member.revoked", _target(member),
                                  reason=body.reason.strip(), reference=member.member_ref,
                                  subject_user_id=member.user_id)
    return member


@router.post("/{membership_id}/restore", response_model=MembershipOut)
async def restore_member(
    membership_id: int,
    admin: dict = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
):
    member = await restore(db, membership_id)
    await activity_service.record(db, admin, "member.restored", _target(member),
                                  reference=member.member_ref, subject_user_id=member.user_id)
    return member
