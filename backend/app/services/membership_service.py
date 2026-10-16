"""Membership plans and applications (Flow 6).

There is no membership_plan table yet (docs/decisions.md, "Schema
questions" item 4), so the plans live here as constants. The values match
frontend/src/api/mocks/membershipPlans.js, and display_name matches the
membership.membership_type strings in the seed ("Individual"), so an
application stores the plan's display_name there. Move these to a table
once the schema question is settled.

An application inserts a 'Pending' membership row. An admin approves it
('Active', starting today for the plan's duration, and the applicant gains
the Member role) or rejects it ('Rejected').
membership has no children_covered column (schema question 3), so the
requested number of children is validated and echoed back but not stored.
"""

import re
from datetime import date
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ApiError
from app.schemas.membership import (
    MembershipApplicationIn,
    MembershipOut,
    MembershipPlanOut,
    MembershipPlanRef,
)

MEMBERSHIP_PLANS: list[MembershipPlanOut] = [
    MembershipPlanOut(
        id=1,
        key="individual",
        display_name="Individual",
        price_cents=6500,
        duration_months=12,
        adults_covered=1,
        max_children=0,
        benefits=["One adult", "Unlimited entry", "Members' preview evenings"],
        featured=False,
    ),
    MembershipPlanOut(
        id=2,
        key="family",
        display_name="Family",
        price_cents=12000,
        duration_months=12,
        adults_covered=2,
        max_children=3,
        benefits=[
            "2 adults + up to 3 children",
            "Discovery Kit on each visit",
            "Priority workshop booking",
        ],
        featured=True,
    ),
    MembershipPlanOut(
        id=3,
        key="patron",
        display_name="Patron",
        price_cents=28000,
        duration_months=12,
        adults_covered=2,
        max_children=3,
        benefits=[
            "All family benefits",
            "Guided vault access",
            "Named in the annual report",
        ],
        featured=False,
    ),
]


def list_plans(page: int, size: int) -> tuple[list[MembershipPlanOut], int]:
    start = (page - 1) * size
    return MEMBERSHIP_PLANS[start : start + size], len(MEMBERSHIP_PLANS)


def _plan_by_name(name: str) -> Optional[MembershipPlanOut]:
    return next((p for p in MEMBERSHIP_PLANS if p.display_name.lower() == name.lower()), None)


# The table's capitalised statuses -> the front end's vocabulary. The UI
# has no "rejected"/"cancelled" state; both mean the membership is not in
# force for a reason the museum decided, which it shows as "revoked".
_STATUS = {
    "pending": "pending",
    "active": "active",
    "expired": "expired",
    "rejected": "revoked",
    "cancelled": "revoked",
}

_MEMBERSHIP_SELECT = (
    "SELECT m.membership_id, m.user_id, m.membership_type, m.application_date, "
    " m.start_date, m.expiry_date, m.status, "
    " u.email, u.first_name, u.last_name "
    "FROM membership m JOIN user_account u ON u.user_id = m.user_id "
)


def _status(row) -> str:
    status = _STATUS.get(row.status.lower(), row.status.lower())
    if status == "active" and row.expiry_date is not None and row.expiry_date < date.today():
        return "expired"
    return status


def _to_membership(row, children_covered: Optional[int] = None) -> MembershipOut:
    plan = _plan_by_name(row.membership_type)
    return MembershipOut(
        id=row.membership_id,
        user_id=row.user_id,
        member_ref=f"SA-{row.membership_id:04d}",
        full_name=f"{row.first_name} {row.last_name}",
        email=row.email,
        plan_id=plan.id if plan else None,
        tier=plan.key if plan else row.membership_type.lower(),
        plan=MembershipPlanRef(id=plan.id, display_name=plan.display_name) if plan else None,
        status=_status(row),
        adults_covered=plan.adults_covered if plan else None,
        children_covered=children_covered,
        applied_at=row.application_date,
        approved_at=row.start_date,
        expires_at=row.expiry_date,
    )


async def current_membership(db: AsyncSession, user_id: int) -> Optional[MembershipOut]:
    """The user's most relevant record: active, then pending, then newest."""
    rows = (
        await db.execute(
            text(_MEMBERSHIP_SELECT + "WHERE m.user_id = :user_id "
                 "ORDER BY m.application_date DESC, m.membership_id DESC"),
            {"user_id": user_id},
        )
    ).all()
    records = [_to_membership(row) for row in rows]
    for wanted in ("active", "pending"):
        match = next((r for r in records if r.status == wanted), None)
        if match:
            return match
    return records[0] if records else None


async def apply(
    db: AsyncSession, user_id: int, body: MembershipApplicationIn
) -> MembershipOut:
    plan = next((p for p in MEMBERSHIP_PLANS if p.id == body.plan_id), None)
    if plan is None:
        raise ApiError(404, "Membership plan not found", "NOT_FOUND")
    if body.children_covered > plan.max_children:
        raise ApiError(
            400,
            f"The {plan.display_name} plan covers up to {plan.max_children} children.",
            "INVALID_REQUEST",
        )

    # Lock the applicant's account row so two concurrent submissions can't
    # both pass the "no active/pending membership" check below.
    await db.execute(
        text("SELECT 1 FROM user_account WHERE user_id = :user_id FOR UPDATE"),
        {"user_id": user_id},
    )
    existing = await current_membership(db, user_id)
    if existing is not None and existing.status in ("active", "pending"):
        await db.rollback()
        detail = (
            "You already have an active membership."
            if existing.status == "active"
            else "You already have an application waiting for approval."
        )
        raise ApiError(409, detail, "MEMBERSHIP_ACTIVE")

    membership_id = (
        await db.execute(
            text(
                "INSERT INTO membership (user_id, membership_type, status) "
                "VALUES (:user_id, :membership_type, 'Pending') "
                "RETURNING membership_id"
            ),
            {"user_id": user_id, "membership_type": plan.display_name},
        )
    ).scalar_one()
    row = (
        await db.execute(
            text(_MEMBERSHIP_SELECT + "WHERE m.membership_id = :membership_id"),
            {"membership_id": membership_id},
        )
    ).first()
    await db.commit()
    return _to_membership(row, children_covered=body.children_covered)


# Filter values (the API's status vocabulary) -> SQL on membership m.
_STATUS_FILTER = {
    "pending": "m.status = 'Pending'",
    "active": "m.status = 'Active' AND (m.expiry_date IS NULL OR m.expiry_date >= CURRENT_DATE)",
    "expired": "(m.status = 'Expired' OR (m.status = 'Active' AND m.expiry_date < CURRENT_DATE))",
    "revoked": "m.status IN ('Rejected', 'Cancelled')",
}


async def list_memberships(
    db: AsyncSession, status: Optional[str], page: int, size: int
) -> tuple[list[MembershipOut], int]:
    where = f"WHERE {_STATUS_FILTER[status]} " if status else ""
    total = (
        await db.execute(text(f"SELECT COUNT(*) FROM membership m {where}"))
    ).scalar_one()
    rows = (
        await db.execute(
            text(_MEMBERSHIP_SELECT + where
                 + "ORDER BY m.application_date, m.membership_id LIMIT :limit OFFSET :offset"),
            {"limit": size, "offset": (page - 1) * size},
        )
    ).all()
    return [_to_membership(row) for row in rows], total


async def _load(db: AsyncSession, membership_id: int):
    return (
        await db.execute(
            text(_MEMBERSHIP_SELECT + "WHERE m.membership_id = :membership_id"),
            {"membership_id": membership_id},
        )
    ).first()


async def _decide(db: AsyncSession, membership_id: int, update_sql: str, params: dict):
    """Run a Pending-only status UPDATE; 404 if the row is missing, 409 if it
    was already decided. The status condition sits in the UPDATE itself so
    two admins clicking at once can't both win."""
    row = await _load(db, membership_id)
    if row is None:
        raise ApiError(404, "Membership application not found", "NOT_FOUND")
    updated = (
        await db.execute(
            text(update_sql + " WHERE membership_id = :membership_id "
                 "AND status = 'Pending' RETURNING user_id"),
            {"membership_id": membership_id, **params},
        )
    ).first()
    if updated is None:
        await db.rollback()
        raise ApiError(409, "This application has already been decided", "NOT_PENDING")
    return row


async def approve(db: AsyncSession, membership_id: int) -> MembershipOut:
    row = await _load(db, membership_id)
    plan = _plan_by_name(row.membership_type) if row else None
    months = plan.duration_months if plan else 12
    row = await _decide(
        db,
        membership_id,
        "UPDATE membership SET status = 'Active', start_date = CURRENT_DATE, "
        "expiry_date = (CURRENT_DATE + make_interval(months => :months))::date",
        {"months": months},
    )
    # Approval is what makes the applicant a member: add the Member role
    # (the front end's /account page is member-only). Other roles are kept.
    await db.execute(
        text(
            "INSERT INTO user_role (user_id, role_id) "
            "SELECT :user_id, role_id FROM role WHERE lower(role_name) = 'member' "
            "ON CONFLICT DO NOTHING"
        ),
        {"user_id": row.user_id},
    )
    await db.commit()
    return _to_membership(await _load(db, membership_id))


async def reject(db: AsyncSession, membership_id: int) -> MembershipOut:
    await _decide(db, membership_id, "UPDATE membership SET status = 'Rejected'", {})
    await db.commit()
    return _to_membership(await _load(db, membership_id))


# ---------------------------------------------------------------------------
# Admin Members screen (frontend/src/api/members.js: /api/admin/members).
# Same rows as the contract endpoints above, in the screen's request shape.
# Reasons for decline/revoke are required/accepted but not stored: neither
# membership nor any activity-log table has a column for them yet.
# ---------------------------------------------------------------------------


async def list_for_admin(
    db: AsyncSession, q: Optional[str], status: Optional[str], tier: Optional[str]
) -> tuple[list[MembershipOut], dict]:
    clauses, params = [], {}
    if status:
        clauses.append(f"({_STATUS_FILTER[status]})")
    if tier:
        plan = next((p for p in MEMBERSHIP_PLANS if p.key == tier), None)
        if plan is None:
            return [], await _counts(db)
        clauses.append("lower(m.membership_type) = lower(:tier_name)")
        params["tier_name"] = plan.display_name
    if q and q.strip():
        needle = q.strip()
        ref = re.fullmatch(r"(?:SA-?)?0*(\d+)", needle, re.IGNORECASE)
        like = re.sub(r"([\%_])", r"\\1", needle)
        search = ("(u.first_name || ' ' || u.last_name) ILIKE :q OR u.email ILIKE :q")
        if ref:
            search += " OR m.membership_id = :ref"
            params["ref"] = int(ref.group(1))
        clauses.append(f"({search})")
        params["q"] = f"%{like}%"
    where = f"WHERE {' AND '.join(clauses)} " if clauses else ""
    rows = (
        await db.execute(
            text(_MEMBERSHIP_SELECT + where
                 + "ORDER BY m.application_date DESC, m.membership_id DESC"),
            params,
        )
    ).all()
    return [_to_membership(row) for row in rows], await _counts(db)


async def _counts(db: AsyncSession) -> dict:
    counts = {}
    for key in ("pending", "active", "revoked"):
        counts[key] = (
            await db.execute(text(f"SELECT COUNT(*) FROM membership m WHERE {_STATUS_FILTER[key]}"))
        ).scalar_one()
    return counts


async def revoke(db: AsyncSession, membership_id: int) -> MembershipOut:
    """Active -> Cancelled, and the member's login is disabled (the screen
    promises they are signed out and can't use the membership)."""
    row = await _load(db, membership_id)
    if row is None:
        raise ApiError(404, "That member record no longer exists.", "NOT_FOUND")
    if _status(row) != "active":
        raise ApiError(409, "Only an active membership can be revoked", "NOT_ACTIVE")
    await db.execute(
        text("UPDATE membership SET status = 'Cancelled' WHERE membership_id = :id"),
        {"id": membership_id},
    )
    await db.execute(
        text("UPDATE user_account SET is_active = FALSE WHERE user_id = :user_id"),
        {"user_id": row.user_id},
    )
    await db.commit()
    return _to_membership(await _load(db, membership_id))


async def restore(db: AsyncSession, membership_id: int) -> MembershipOut:
    """Revoked/declined/expired -> Active, re-enabling the login. A record
    that never started or has run out gets a fresh period from today."""
    row = await _load(db, membership_id)
    if row is None:
        raise ApiError(404, "That member record no longer exists.", "NOT_FOUND")
    if _status(row) not in ("revoked", "expired"):
        raise ApiError(409, "Only a revoked or expired membership can be restored", "NOT_RESTORABLE")
    other = await current_membership(db, row.user_id)
    if other is not None and other.id != membership_id and other.status in ("active", "pending"):
        raise ApiError(409, "This person already has another active or pending membership",
                       "MEMBERSHIP_ACTIVE")
    plan = _plan_by_name(row.membership_type)
    if row.expiry_date is None or row.expiry_date < date.today():
        await db.execute(
            text("UPDATE membership SET status = 'Active', start_date = CURRENT_DATE, "
                 "expiry_date = (CURRENT_DATE + make_interval(months => :months))::date "
                 "WHERE membership_id = :id"),
            {"id": membership_id, "months": plan.duration_months if plan else 12},
        )
    else:
        await db.execute(
            text("UPDATE membership SET status = 'Active' WHERE membership_id = :id"),
            {"id": membership_id},
        )
    await db.execute(
        text("UPDATE user_account SET is_active = TRUE WHERE user_id = :user_id"),
        {"user_id": row.user_id},
    )
    await db.execute(
        text("INSERT INTO user_role (user_id, role_id) "
             "SELECT :user_id, role_id FROM role WHERE lower(role_name) = 'member' "
             "ON CONFLICT DO NOTHING"),
        {"user_id": row.user_id},
    )
    await db.commit()
    return _to_membership(await _load(db, membership_id))
