"""Public auth endpoints (docs/api-contract.md section 1).

POST /api/auth/login -> { access_token, token_type, user }
GET  /api/auth/me    -> user (section 10; the front end calls it on every
                        page load to restore the session)
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.security import create_access_token
from app.db.session import get_session
from app.schemas.auth import LoginIn, TokenOut
from app.schemas.user import UserOut
from app.services.auth_service import authenticate

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenOut)
async def login(
    body: LoginIn,
    db: AsyncSession = Depends(get_session),
):
    user = await authenticate(db, body.email, body.password)
    token = create_access_token(user_id=user.id, role=user.role)
    return TokenOut(access_token=token, user=user)


@router.get("/me", response_model=UserOut)
async def me(user: UserOut = Depends(get_current_user)):
    return user
