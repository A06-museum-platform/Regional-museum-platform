"""Interests and recommendations (docs/api-contract.md section 7;
role-permission matrix: "View personalised recommendations" -- Member, Staff,
Admin; a plain visitor account gets 403 and is invited to join).

GET /api/interest-tags              (public)  the interest vocabulary
GET /api/me/interests               (signed in) the caller's chosen interests
PUT /api/me/interests  {tags: [...]} (signed in) replace them
GET /api/recommendations?type=&page=&size=   (Member+) ranked suggestions
"""

from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.errors import ApiError
from app.db.session import get_session
from app.schemas.user import UserOut
from app.services import recommendation_service as recs

router = APIRouter(prefix="/api", tags=["recommendations"])

MEMBER_ROLES = {"member", "staff", "admin"}


class InterestsIn(BaseModel):
    tags: list[str] = Field(default_factory=list, max_length=20)


@router.get("/interest-tags", response_model=list[recs.InterestTagOut])
async def interest_tags(db: AsyncSession = Depends(get_session)):
    return await recs.list_tags(db)


@router.get("/me/interests", response_model=list[recs.InterestTagOut])
async def my_interests(user: UserOut = Depends(get_current_user), db: AsyncSession = Depends(get_session)):
    return await recs.user_interests(db, user.id)


@router.put("/me/interests", response_model=list[recs.InterestTagOut])
async def set_my_interests(
    body: InterestsIn,
    user: UserOut = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    return await recs.set_user_interests(db, user.id, body.tags)


@router.get("/recommendations", response_model=recs.RecommendationListOut)
async def recommendations(
    type: Optional[Literal["exhibition", "event", "collection_item"]] = None,
    page: int = Query(1, ge=1),
    size: int = Query(12, ge=1, le=50),
    user: UserOut = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    if user.role not in MEMBER_ROLES:
        raise ApiError(403, "Member access required", "FORBIDDEN")
    return await recs.recommend(db, user.id, page, size, kind=type)
