"""Pydantic schemas for membership plans and applications
(docs/api-contract.md section 6, docs/decisions.md "Booking and membership")."""

from datetime import date
from typing import Optional

from pydantic import BaseModel, Field


class MembershipPlanOut(BaseModel):
    id: int
    key: str
    display_name: str
    price_cents: int
    duration_months: int
    adults_covered: int
    max_children: int
    benefits: list[str]
    featured: bool


class MembershipPlanListOut(BaseModel):
    items: list[MembershipPlanOut]
    total: int
    page: int
    size: int


class MembershipApplicationIn(BaseModel):
    plan_id: int
    children_covered: int = Field(default=0, ge=0)


class MembershipPlanRef(BaseModel):
    id: int
    display_name: str


class MembershipOut(BaseModel):
    """One membership row, in the shape the front end's mocks already use."""

    id: int
    user_id: int
    member_ref: str
    full_name: str
    email: str
    plan_id: Optional[int]
    tier: str
    plan: Optional[MembershipPlanRef]
    # pending | active | expired | revoked (Rejected/Cancelled rows)
    status: str
    adults_covered: Optional[int]
    # Not stored: membership has no children_covered column yet
    # (docs/decisions.md schema question 3). Only the application response
    # echoes the requested value.
    children_covered: Optional[int]
    applied_at: date
    approved_at: Optional[date]
    expires_at: Optional[date]


class MemberCounts(BaseModel):
    pending: int
    active: int
    revoked: int


class AdminMemberListOut(BaseModel):
    """GET /api/admin/members, the shape frontend/src/api/members.js reads."""

    items: list[MembershipOut]
    total: int
    counts: MemberCounts


class ReasonIn(BaseModel):
    reason: Optional[str] = Field(default=None, max_length=500)


class MembershipListOut(BaseModel):
    items: list[MembershipOut]
    total: int
    page: int
    size: int
